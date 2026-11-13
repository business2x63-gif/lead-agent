# Redesign Lead Agent

Find local businesses with **outdated websites** — your best website-redesign
prospects — in any US city + niche. Runs 100% on your own machine from a
browser dashboard. **No API keys, no signups, no paid services.**

## Quick start (browser dashboard)

```bash
pip install -r requirements.txt
python webapp/app.py
```

Open **http://127.0.0.1:5000** in your browser, type a niche
(`dentist`, `plumber`, `roofer`…) and a city (`Austin, TX`), hit
**Find Leads**. The agent:

1. **Scrapes** the Yellowpages directory for local businesses in that
   city + niche (name, phone, address, website, rating, reviews, categories).
2. **Audits every website** for outdated-technology signals.
3. **Ranks** all leads by an "outdated score", hottest first, in a table
   with one-click **CSV download**.

## How websites are scored

| Signal | Weight | What it means |
|---|---|---|
| `no_website` | 50 | Business has **no website at all** (hottest lead) |
| `unreachable` | 40 | Site is down or broken |
| `no_mobile_viewport` | 25 | Not mobile-responsive |
| `stale_copyright` | 20 | Copyright year frozen 2+ years back (or missing) |
| `flash_or_frames` | 20 | Flash / framesets / applets |
| `no_https` | 20 | Serves only over plain HTTP |
| `old_jquery` | 15 | jQuery 1.x / 2.x still in production |
| `legacy_html` | 10 | `<font>`, `<center>`, `<marquee>`… |
| `old_generator` | 10 | Old WordPress/Joomla/Drupal version exposed |
| `blocked` | 10 | Site returns 403 to bots — verify manually in a browser |
| `slow_load` | 10 | Homepage loads in > 4 s |
| `diy_builder` | 5 | Wix / Squarespace / GoDaddy builder / Weebly |
| `oversized_page` | 5 | 1.5 MB+ of HTML |

**Score ≥ 40 = hot prospect.** Check the "include no-website" box to also
get businesses with zero web presence.

## Data sources (all keyless)

- **Yellowpages.com** — primary business directory (reliable, server-rendered).
- Google Maps and Yelp are *not* used: Google encrypts results for
  non-browser clients and Yelp blocks automated requests outright.

## CLI alternative

```bash
python agent.py --demo   # sample run, no setup
```

## Notes

- Scraping public directory pages is a gray zone — keep volumes modest
  (this tool paces itself at ~1 page/second) and use leads for personal
  outreach, not resale.
- Some sites block datacenter IPs/automated requests (`blocked` signal);
  those may look perfectly fine from your own browser.
