# Lead Agent

Find local businesses with **outdated websites** — your best redesign
prospects — in any US city + niche. No API keys, no installs, no signups.

## Start and go

1. Install Python from [python.org/downloads](https://www.python.org/downloads/)
   (one time; on Windows check "Add Python to PATH").
2. Download this repo (green **Code** button → **Download ZIP** → unzip).
3. Double-click **`run-windows.bat`** (Windows) or **`run-mac.command`** (Mac) —
   or from a terminal: `python start.py`

Then just type:

```
  What kind of business?   dentist
  What city?               Austin, TX
  How many businesses?     (Enter = 60)
  Include NO-website ones? (Enter = no)
```

It finds the businesses, checks every website, prints the hottest prospects
ranked by how outdated their site is, and saves everything to
`leads_<niche>_<city>.csv` in the same folder.

## What it flags (the score)

| Problem | Points |
|---|---|
| No website at all | 50 |
| Site down | 40 |
| Not mobile-friendly | 25 |
| No HTTPS / stale copyright / Flash-frames | 20 |
| Old jQuery | 15 |
| Old WordPress exposed / legacy HTML / slow load / blocks bots | 10 |
| Wix/GoDaddy DIY builder / bloated page | 5 |

**Score ≥ 40 = call them today.**

## Where the data comes from

Public Yellowpages.com listing pages, scraped from your own machine
(keyless, paced ~1 page/second). Google Maps encrypts its data for
non-browser clients and Yelp blocks automated access, so neither can be
scraped reliably without a browser session.

## That's it

No config, no accounts, nothing to subscribe to. If a lead says
"blocks bots — check manually", open their site yourself in a browser;
some sites simply reject automated requests.
