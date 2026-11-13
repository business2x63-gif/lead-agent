# Redesign Lead Agent

Finds local businesses in a US city + niche whose websites look outdated —
your best website-redesign prospects — and exports a ranked CSV.

## How it works

1. **Discovery** — Google Places API (New) text search: `{niche} in {city}`
   (name, address, phone, website, rating, reviews).
2. **Audit** — each website is fetched and scored 0–100+ on outdated signals:

   | Signal | Weight | What it means |
   |---|---|---|
   | `unreachable` | 40 | Site is down or broken |
   | `no_mobile_viewport` | 25 | Not mobile-responsive |
   | `stale_copyright` | 20 | Copyright year frozen 2+ years ago (or missing) |
   | `flash_or_frames` | 20 | Flash / framesets / applets |
   | `old_jquery` | 15 | jQuery 1.x / 2.x still in production |
   | `no_https` | 20 | Serves only over plain HTTP |
   | `legacy_html` | 10 | `<font>`, `<center>`, `<marquee>`… |
   | `old_generator` | 10 | Old WordPress/Joomla/Drupal version meta |
   | `slow_load` | 10 | Homepage loads in > 4 s |
   | `diy_builder` | 5 | Wix / Squarespace / GoDaddy builder / Weebly |
   | `oversized_page` | 5 | 1.5 MB+ of HTML |

   Score ≥ 40 = hot prospect. Results are sorted best-first.
3. **Report** — CSV with contact info, signals, and notes per lead.

## Setup

```bash
pip install -r requirements.txt
export GOOGLE_PLACES_API_KEY=your_key   # enable "Places API (New)" in Google Cloud
```

Get a key at [Google Cloud Console](https://console.cloud.google.com/) →
APIs & Services → enable **Places API (New)**. Text Search pricing is
roughly $32 per 1,000 requests (a 60-business run = a few cents).

## Usage

```bash
python agent.py --city "Austin, TX" --niche "dentist" --out leads.csv
python agent.py --city "Miami, FL" --niche "plumber" --max-results 60
python agent.py --demo        # sample data, no API key needed
```

Options: `--workers 8` (parallel audits), `--include-missing-websites`
(also list businesses with **no website at all** — often the hottest leads),
`--out leads.csv`.

## Output columns

`score, business_name, phone, address, website, rating, reviews,
outdated_signals, notes, maps_url, place_id`

## Notes

- Google Places doesn't expose owner names; `business_name` + `phone` is the
  standard outreach identifier for local businesses (many are owner-operated).
- The audit uses polite heuristics (one request per site, browser UA). Stay
  within Google's ToS for Places and robots.txt etiquette for site fetches.
