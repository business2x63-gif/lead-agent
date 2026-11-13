#!/usr/bin/env python3
"""LEAD AGENT — find local businesses with outdated websites.

No API keys. No installs. Just run:

    python start.py

It asks you for a niche and a city, scrapes local business listings,
checks every website for outdated technology, prints the hottest
prospects, and saves everything to a CSV file.
"""

import csv
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from html import unescape
from urllib import request as urlreq
from urllib.error import HTTPError, URLError
from urllib.parse import quote

import gzip

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/124.0 Safari/537.36"),
    "Accept": ("text/html,application/xhtml+xml,application/xml;q=0.9,"
               "image/avif,image/webp,*/*;q=0.8"),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",
    "Upgrade-Insecure-Requests": "1",
}

SIGNAL_LABELS = {
    "no_website": "NO WEBSITE AT ALL",
    "unreachable": "site down",
    "blocked": "blocks bots (check manually)",
    "no_https": "no HTTPS",
    "no_mobile_viewport": "not mobile-friendly",
    "stale_copyright": "stale copyright",
    "old_jquery": "old jQuery",
    "flash_or_frames": "flash/frames",
    "legacy_html": "legacy HTML",
    "old_generator": "old WordPress/CMS",
    "diy_builder": "DIY builder (Wix/GoDaddy)",
    "slow_load": "slow load",
    "oversized_page": "bloated page",
}

WEIGHTS = {
    "no_website": 50, "unreachable": 40, "no_https": 20,
    "no_mobile_viewport": 25, "stale_copyright": 20, "old_jquery": 15,
    "flash_or_frames": 20, "legacy_html": 10, "old_generator": 10,
    "diy_builder": 5, "slow_load": 10, "oversized_page": 5, "blocked": 10,
}

RATING_WORDS = {
    "one_half": 1.5, "one": 1.0, "two_half": 2.5, "two": 2.0,
    "three_half": 3.5, "three": 3.0, "four_half": 4.5, "four": 4.0,
    "five": 5.0,
}


def fetch(url, timeout=20, redirects=3):
    try:
        req = urlreq.Request(url, headers=HEADERS)
        with urlreq.urlopen(req, timeout=timeout) as resp:
            return resp.geturl(), _decode(resp)
    except HTTPError as exc:
        if exc.code in (301, 302, 303, 307, 308) and redirects > 0:
            location = (exc.headers or {}).get("Location")
            if location:
                if location.startswith("/"):
                    root = "/".join(url.split("/")[:3])
                    location = root + location
                return fetch(location, timeout, redirects - 1)
        raise


def _decode(resp):
    data = resp.read()
    if (resp.headers or {}).get("Content-Encoding", "") == "gzip":
        data = gzip.decompress(data)
    return data.decode("utf-8", "ignore")


def strip_tags(html):
    html = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html,
                  flags=re.S | re.I)
    return unescape(re.sub(r"<[^>]+>", " ", html))


# ---------------------------------------------------------------- scraping

def scrape(niche, city, max_results=60, max_pages=5, log=print):
    leads, seen = [], {}
    base = ("https://www.yellowpages.com/search?search_terms={}"
            "&geo_location_terms={}").format(quote(niche), quote(city))
    for page in range(1, max_pages + 1):
        url = base if page == 1 else f"{base}&page={page}"
        try:
            _, html = fetch(url)
        except Exception as exc:
            log(f"  ! page {page} failed ({exc})")
            break
        cards = html.split('<div class="result"')[1:]
        if not cards:
            break
        new_on_page = 0
        for card in cards:
            lead = parse_card(card)
            if not lead or not (lead["phone"] or lead["website"]):
                continue
            key = lead["business_name"].lower()
            if key in seen:
                idx = seen[key]
                if not leads[idx]["website"] and lead["website"]:
                    leads[idx] = lead
                continue
            seen[key] = len(leads)
            leads.append(lead)
            new_on_page += 1
            if len(leads) >= max_results:
                break
        log(f"  page {page}: +{new_on_page} businesses ({len(leads)} total)")
        if new_on_page == 0 or len(leads) >= max_results:
            break
        time.sleep(1)
    return leads


def parse_card(card):
    name = search(r'class="business-name"[^>]*>\s*<span>([^<]+)</span>', card)
    if not name:
        name = search(r"<h2[^>]*>\s*<a[^>]*>([^<]+)</a>", card)
    if not name:
        return None
    website = search(r'class="track-visit-website"[^>]*href="([^"]+)"', card)
    if website and "yellowpages.com" in website:
        website = ""
    phone = search(r'class="phones phone primary"[^>]*>\s*([^<]+)', card)
    street = search(r'class="street-address"[^>]*>\s*([^<]+)', card)
    locality = search(r'class="locality"[^>]*>\s*([^<]+)', card)
    rating_word = search(r'result-rating\s+([a-z_]+)', card)
    count = search(r'<span class="count">\((\d+)\)', card)
    cats = re.findall(r'<div class="categories"[^>]*>(.*?)</div>', card, re.S)
    cat_names = re.findall(r">([^<>]+)</a>", cats[0])[:3] if cats else []
    return {
        "business_name": unescape(name).strip(),
        "phone": unescape(phone).strip() if phone else "",
        "address": unescape(f"{street} {locality}").strip()
        if street or locality else "",
        "website": unescape(website).strip() if website else "",
        "rating": RATING_WORDS.get(rating_word, ""),
        "reviews": int(count) if count else "",
        "categories": ", ".join(c.strip() for c in cat_names),
    }


def search(pattern, text):
    match = re.search(pattern, text)
    return match.group(1).strip() if match else ""


# ---------------------------------------------------------------- auditing

def audit(url, timeout=15):
    result = {"score": 0, "signals": [], "notes": []}

    def add(signal, note=None):
        result["signals"].append(signal)
        if note:
            result["notes"].append(note)

    url = url.strip()
    parsed = re.match(r"(https?)://([^/]+)(/[^?]*)?", url)
    if not parsed:
        add("unreachable", "invalid url")
        return finish(result)
    scheme, host, path = (parsed.group(1), parsed.group(2),
                          parsed.group(3) or "/")

    html, https_ok, status, elapsed = "", False, 0, 0.0
    error_note = ""
    for try_scheme in ("https", "http"):
        for _ in range(2):
            try:
                started = time.time()
                final_url, page = fetch(
                    f"{try_scheme}://{host}{path}", timeout=timeout)
                elapsed = time.time() - started
                if try_scheme == "https":
                    https_ok = True
                html = page
                status = 200
                break
            except HTTPError as exc:
                status = exc.code
                if exc.code in (401, 403, 429, 503):
                    break
            except (URLError, OSError, ValueError) as exc:
                error_note = f"{type(exc).__name__}: {exc}"
                continue
        if html or status in (401, 403, 429, 503):
            break

    if not html:
        if status in (401, 403, 429, 503):
            add("blocked", f"site returned {status} to bots — "
                           "open it yourself in a browser")
        elif "name resolution" in error_note or "getaddrinfo" in error_note:
            add("unreachable", "domain not resolving — site may be gone")
        elif ("RemoteDisconnected" in error_note
              or "BadStatusLine" in error_note
              or "ConnectionReset" in error_note):
            add("blocked", "server dropped the connection — "
                           "may block bots, open it yourself in a browser")
        elif "CERTIFICATE_VERIFY_FAILED" in error_note:
            add("blocked", "SSL certificate broken or expired — "
                           "itself a redesign signal, check manually")
        elif status in (301, 302, 303, 307, 308):
            add("blocked", f"redirect problem ({status}) — check manually")
        else:
            add("unreachable", "site did not load")
        return finish(result)
    if not https_ok:
        add("no_https")

    low = html.lower()
    if not re.search(r'<meta[^>]*name=["\']viewport', low):
        add("no_mobile_viewport", "no responsive viewport meta tag")
    check_copyright(strip_tags(html)[-3500:], add)
    jq = re.search(r"jquery[-.]?(\d+)\.(\d+)", low)
    if jq and int(jq.group(1)) < 3:
        add("old_jquery", f"jQuery {jq.group(1)}.{jq.group(2)} still in use")
    if any(t in low for t in ("<frame", "<frameset", "<applet",
                              "shockwave-flash")):
        add("flash_or_frames", "flash/frames technology")
    legacy = [t for t in ("<font", "<center", "<marquee", "<big")
              if low.count(t) >= 2]
    if len(legacy) >= 2:
        add("legacy_html", "legacy tags: " + ", ".join(
            t.strip("<") for t in legacy))
    gen = search(r'<meta[^>]*name=["\']generator["\'][^>]*content="([^"]+)"',
                 html)
    if gen and re.search(r"(wordpress|joomla|drupal)", gen, re.I):
        add("old_generator", f"CMS version exposed: {unescape(gen)}")
    for hint in ("wix.com", "squarespace.com", "weebly.com", "webnode",
                 "jimdo", "sitebuilder"):
        if hint in low:
            add("diy_builder", f"DIY site builder detected ({hint})")
            break
    if elapsed > 4.0:
        add("slow_load", f"slow load: {elapsed:.1f}s")
    if len(html) > 1_500_000:
        add("oversized_page", f"very large page ({len(html)//1000} KB)")
    return finish(result)


def check_copyright(text, add):
    years = [int(y) for y in re.findall(
        r"(?:©|&copy;|copyright|\(c\))\D{0,20}((?:19|20)\d{2})", text, re.I)]
    if not years:
        years = [int(y) for y in re.findall(r"\b(19\d{2}|20\d{2})\b", text)]
    current = datetime.now().year
    if not years:
        add("stale_copyright", "no copyright year found")
    elif max(years) <= current - 2:
        add("stale_copyright", f"copyright frozen at {max(years)}")


def finish(result):
    result["score"] = sum(WEIGHTS[s] for s in set(result["signals"]))
    result["signals"] = list(dict.fromkeys(result["signals"]))
    return result


# ------------------------------------------------------------------- main

def ask(prompt, default=""):
    try:
        value = input(prompt).strip()
        return value or default
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(0)


def main():
    print()
    print("=" * 62)
    print("  LEAD AGENT - find local businesses with outdated websites")
    print("  no API keys, runs on your machine, saves a CSV")
    print("=" * 62)
    print()

    niche = ask("  What kind of business?  (e.g. dentist, plumber, roofer): ")
    if not niche:
        print("  You must type a niche."); return 1
    city = ask("  What city?            (e.g. Austin, TX        ): ")
    if not city:
        print("  You must type a city."); return 1
    how_many = ask("  How many businesses?  (press Enter for 60     ): ", "60")
    try:
        how_many = max(5, min(int(re.sub(r"\D", "", how_many) or 60), 150))
    except ValueError:
        how_many = 60
    no_site = ask("  Also list businesses with NO website? (y/N     ): ",
                   "n").lower().startswith("y")

    print(f"\n  Step 1/2: finding {niche}s in {city} ...")
    leads = scrape(niche, city, max_results=how_many)
    if not leads:
        print("  Nothing found - try a broader niche or check spelling.")
        return 1

    with_site = [l for l in leads if l["website"]]
    print(f"\n  Step 2/2: checking {len(with_site)} websites "
          f"(this takes 30-90 seconds) ...")
    done = 0
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(audit, l["website"]): l for l in with_site}
        for future in as_completed(futures):
            lead = futures[future]
            try:
                lead.update(future.result())
            except Exception as exc:
                lead.update({"score": 0, "signals": ["unreachable"],
                             "notes": [str(exc)]})
            done += 1
            if done % 10 == 0:
                print(f"    ... {done}/{len(with_site)} checked")
    for lead in leads:
        if not lead["website"]:
            lead.update({"score": 50 if no_site else 0,
                         "signals": ["no_website"] if no_site else [],
                         "notes": ["no website found at all"] if no_site else []})

    leads.sort(key=lambda l: l["score"], reverse=True)

    slug = re.sub(r"\W+", "_", f"{niche}_{city}").strip("_").lower()
    csv_name = f"leads_{slug}.csv"
    with open(csv_name, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["score", "business_name", "phone", "address",
                         "website", "rating", "reviews", "signals", "notes"])
        for l in leads:
            writer.writerow([l["score"], l["business_name"], l["phone"],
                             l["address"], l["website"], l["rating"],
                             l["reviews"], ";".join(l["signals"]),
                             "; ".join(l["notes"])])

    hot = [l for l in leads if l["score"] >= 40]
    print(f"\n  DONE. {len(leads)} leads saved to:  {csv_name}")
    print(f"  {len(hot)} HOT prospects (score >= 40). Top of the list:\n")
    print(f"  {'SCORE':<6}{'BUSINESS':<30}{'PHONE':<16}PROBLEM")
    print("  " + "-" * 76)
    for l in leads[:20]:
        problems = ", ".join(SIGNAL_LABELS.get(s, s)
                             for s in l["signals"]) or "looks modern"
        site = l["website"] or "-"
        print(f"  {l['score']:<6}{l['business_name'][:29]:<30}"
              f"{l['phone'][:15]:<16}{problems}")
        if l["website"]:
            print(f"  {'':<6}{'':<30}{'':<16}{site[:60]}")
    print(f"\n  Full details (addresses, notes, every lead) are in "
          f"{csv_name}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
