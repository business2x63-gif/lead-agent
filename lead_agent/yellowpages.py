"""Keyless lead scraper: Yellowpages.com local business directory.

No API keys required. Extracts business name, phone, address, website,
rating, review count, and categories from public search-result pages.
"""

import re
import time

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

SEARCH_URL = "https://www.yellowpages.com/search"

RATING_WORDS = {
    "one": 1.0, "one_half": 1.5, "two": 2.0, "two_half": 2.5,
    "three": 3.0, "three_half": 3.5, "four": 4.0, "four_half": 4.5,
    "five": 5.0,
}


def scrape_yellowpages(niche: str, city: str, max_results: int = 60,
                       max_pages: int = 5, progress=None) -> list[dict]:
    """Scrape up to max_results businesses for `niche` in `city`."""
    session = requests.Session()
    session.headers.update(HEADERS)
    leads: list[dict] = []
    seen: dict[str, int] = {}

    for page in range(1, max_pages + 1):
        if len(leads) >= max_results:
            break
        params = {"search_terms": niche, "geo_location_terms": city}
        if page > 1:
            params["page"] = str(page)
        try:
            resp = session.get(SEARCH_URL, params=params, timeout=20)
        except requests.RequestException:
            break
        if resp.status_code != 200:
            break
        cards = BeautifulSoup(resp.text, "html.parser").select("div.result")
        if not cards:
            break
        new_on_page = 0
        for card in cards:
            lead = _parse_card(card)
            if not lead or lead["business_name"] is None:
                continue
            if not lead["phone"] and not lead["website"]:
                continue
            key = lead["business_name"].lower()
            if key in seen:
                index = seen[key]
                if not leads[index]["website"] and lead["website"]:
                    leads[index] = lead
                continue
            seen[key] = len(leads)
            leads.append(lead)
            new_on_page += 1
            if len(leads) >= max_results:
                break
        if progress:
            progress(f"Page {page}: {new_on_page} new businesses "
                     f"({len(leads)} total)")
        if new_on_page == 0:
            break
        time.sleep(1.0)
    return leads


def _parse_card(card) -> dict | None:
    name_el = card.select_one("h2 a.business-name span") or \
        card.select_one("a.business-name span") or card.select_one("h2")
    if name_el is None:
        return None
    website_el = card.select_one("a.track-visit-website")
    website = (website_el.get("href") or "").strip() if website_el else ""
    if "yellowpages.com" in website:
        website = ""
    phone_el = card.select_one("div.phones.phone.primary") or \
        card.select_one(".phones")
    street_el = card.select_one(".street-address") or \
        card.select_one("div.street-address")
    locality_el = card.select_one(".locality")
    rating_el = card.select_one("div.result-rating")
    count_el = card.select_one("span.count")
    categories = [a.get_text(strip=True)
                  for a in card.select("div.categories a")]
    return {
        "business_name": name_el.get_text(strip=True),
        "phone": phone_el.get_text(strip=True) if phone_el else "",
        "address": " ".join(
            part.strip() for part in [
                street_el.get_text(strip=True) if street_el else "",
                locality_el.get_text(strip=True) if locality_el else "",
            ] if part
        ),
        "website": website,
        "rating": _parse_rating(rating_el) if rating_el else "",
        "reviews": _parse_int(count_el.get_text()) if count_el else "",
        "categories": ", ".join(categories[:3]),
    }


def _parse_rating(el) -> str:
    classes = " ".join(el.get("class", []))
    for word, value in RATING_WORDS.items():
        if word in classes:
            return value
    return ""


def _parse_int(text: str):
    match = re.search(r"\d+", text or "")
    return int(match.group()) if match else ""
