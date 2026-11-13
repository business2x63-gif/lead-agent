#!/usr/bin/env python3
"""AI lead agent for a website redesign company.

Pipeline:
  1. Discover local businesses in a US city + niche (Google Places API).
  2. Audit each website for outdated-technology signals.
  3. Rank prospects by "outdated score" and export a CSV.

Usage:
  export GOOGLE_PLACES_API_KEY=your_key
  python agent.py --city "Austin, TX" --niche "dentist" --max-results 60 \
      --out leads_austin_dentists.csv

Demo mode (no API key needed, uses built-in sample businesses):
  python agent.py --demo
"""

import argparse
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

from lead_agent.audit import audit_website
from lead_agent.places import PlacesClient, PlacesError
from lead_agent.report import write_csv

DEMO_BUSINESSES = [
    {
        "business_name": "Bright Smile Dental (demo)",
        "phone": "+1 512 555 0100",
        "address": "1200 Congress Ave, Austin, TX 78701",
        "website": "https://www.berkshirehathaway.com",
        "rating": 4.6,
        "reviews": 88,
        "maps_url": "",
        "place_id": "demo-1",
    },
    {
        "business_name": "Austin Family Dentistry (demo)",
        "phone": "+1 512 555 0101",
        "address": "45 Barton Springs Rd, Austin, TX 78704",
        "website": "https://example.com",
        "rating": 4.9,
        "reviews": 210,
        "maps_url": "",
        "place_id": "demo-2",
    },
    {
        "business_name": "Hill Country Dental Group (demo)",
        "phone": "+1 512 555 0102",
        "address": "700 Lamar Blvd, Austin, TX 78702",
        "website": "http://info.cern.ch",
        "rating": 4.4,
        "reviews": 51,
        "maps_url": "",
        "place_id": "demo-3",
    },
]


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--city", help='US city, e.g. "Austin, TX"')
    parser.add_argument("--niche", help='business niche, e.g. "dentist", "plumber"')
    parser.add_argument(
        "--max-results", type=int, default=60, help="max businesses to fetch"
    )
    parser.add_argument(
        "--workers", type=int, default=8, help="parallel website audits"
    )
    parser.add_argument("--out", default="leads.csv", help="output CSV path")
    parser.add_argument(
        "--api-key",
        default=os.environ.get("GOOGLE_PLACES_API_KEY", ""),
        help="Google Places API key (or set GOOGLE_PLACES_API_KEY)",
    )
    parser.add_argument(
        "--demo", action="store_true", help="run on built-in sample data"
    )
    parser.add_argument(
        "--include-missing-websites",
        action="store_true",
        help="also list businesses that have no website at all",
    )
    args = parser.parse_args(argv)
    if not args.demo and not (args.city and args.niche):
        parser.error("--city and --niche are required (or use --demo)")
    return args


def main(argv=None) -> int:
    args = parse_args(argv)

    if args.demo:
        businesses = DEMO_BUSINESSES
    else:
        if not args.api_key:
            print(
                "Error: set GOOGLE_PLACES_API_KEY or pass --api-key.\n"
                "Get one at https://console.cloud.google.com/ "
                "(enable 'Places API (New)').",
                file=sys.stderr,
            )
            return 2
        print(f'Searching Places API: "{args.niche}" in "{args.city}" ...')
        try:
            businesses = PlacesClient(args.api_key).search(
                args.niche, args.city, max_results=args.max_results
            )
        except PlacesError as exc:
            print(f"Places API failed: {exc}", file=sys.stderr)
            return 1
        print(f"Found {len(businesses)} businesses.")

    if not args.include_missing_websites:
        businesses = [b for b in businesses if b.get("website")]
    print(f"{len(businesses)} businesses with a website to audit.\n")

    leads = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(audit_website, b["website"]): b for b in businesses
        }
        for index, future in enumerate(as_completed(futures), start=1):
            business = futures[future]
            try:
                audit = future.result()
            except Exception as exc:  # keep the run alive on one bad site
                audit = {
                    "score": 0,
                    "signals": ["unreachable"],
                    "notes": [f"audit error: {exc}"],
                }
            lead = {**business, **audit}
            leads.append(lead)
            print(
                f"[{index}/{len(futures)}] "
                f"score={lead['score']:>3} {business['business_name']}"
                f" <{business.get('website', '')}> signals={lead['signals']}"
            )

    write_csv(args.out, leads)
    hot = [lead for lead in leads if lead["score"] >= 40]
    print(
        f"\nDone. {len(leads)} leads written to {args.out} "
        f"({len(hot)} hot prospects with score >= 40, sorted best-first)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
