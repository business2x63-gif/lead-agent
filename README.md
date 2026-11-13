# Lead Agent

Find local businesses with **outdated websites** — your best redesign
prospects — in any US city + niche. No API keys, no installs, no signups.

## Where it runs

It runs in a **terminal window on your own computer** — not in a browser.
You double-click the launcher, a black text window opens, you type your
answers there, and results appear in that window plus a CSV file.

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
  Skip previous runs?      (Enter = yes)
```

It finds the businesses, checks every website, prints the hottest prospects
ranked by how outdated their site is, and saves everything to
`leads_<niche>_<city>.csv` in the same folder.

## Never see the same business twice

The agent remembers every business it has ever shown you
(`seen_businesses.json` in the same folder). Next time you run it — even
weeks later — it **skips all of those and only shows NEW businesses**.

- Enter (or `y`) → only new businesses
- `n` → show everything again, but memory is still updated
- `reset` → wipe the memory and start fresh

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
(keyless, paced ~1 page/second).

Straight answer about "scrape the whole internet": **every major source
actively blocks automated access** — Google Maps encrypts its data for
non-browser clients, Yelp/Manta/ChamberofCommerce return 403 to robots,
and Bing renders results only in JavaScript. Yellowpages is the one
directory that serves real, complete data (name, phone, address,
website, rating) to a simple scraper. It covers the same US local
businesses, so you're not missing leads.

## That's it

No config, no accounts, nothing to subscribe to. If a lead says
"blocks bots — check manually", open their site yourself in a browser;
some sites simply reject automated requests.
