"""Website audit: score how outdated a small-business website is.

Each detected problem adds to an "outdated score". Higher score = better
redesign prospect.
"""

import re
from datetime import datetime
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

BASE_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

SIGNAL_WEIGHTS = {
    "no_website": 50,
    "unreachable": 40,
    "blocked": 10,
    "no_https": 20,
    "no_mobile_viewport": 25,
    "stale_copyright": 20,
    "old_jquery": 15,
    "flash_or_frames": 20,
    "legacy_html": 10,
    "old_generator": 10,
    "diy_builder": 5,
    "slow_load": 10,
    "oversized_page": 5,
}

DIY_BUILDER_HINTS = [
    "wix.com",
    "squarespace.com",
    "weebly.com",
    "godaddy.com/websites",
    "webnode",
    "jimdo",
    "yola",
    "sitebuilder",
]

LEGACY_TAGS = ["font", "center", "marquee", "blink", "big"]

OLD_GENERATOR_RE = re.compile(
    r"(wordpress\s*(\d+\.\d+)?|joomla!?\s*(\d+\.\d+)?|drupal\s*(\d+)?)", re.I
)

JQUERY_VERSION_RE = re.compile(r"jquery[-.]?(\d+)\.(\d+)", re.I)

COPYRIGHT_YEAR_RE = re.compile(
    r"(?:©|&copy;|copyright|\(c\))\D{0,20}((?:19|20)\d{2})", re.I
)
ANY_YEAR_RE = re.compile(r"\b(19\d{2}|20\d{2})\b")


def audit_website(url: str, timeout: int = 15) -> dict:
    """Fetch a site and return {score, signals, notes} for lead scoring."""
    result = {
        "url": url,
        "reachable": False,
        "score": 0,
        "signals": [],
        "notes": [],
    }
    parsed = urlparse(url if "://" in url else f"http://{url}")
    if not parsed.netloc:
        result["signals"].append("unreachable")
        result["notes"].append("invalid url")
        return _finalize(result)

    https_ok = False
    html = ""
    status_code = 0
    load_seconds = 0.0
    response = None

    for scheme in ("https", "http"):
        for attempt in range(2):
            try:
                started = datetime.now()
                response = requests.get(
                    f"{scheme}://{parsed.netloc}{parsed.path or '/'}",
                    headers=BASE_HEADERS,
                    timeout=timeout,
                    allow_redirects=True,
                    verify=True,
                )
                load_seconds = (datetime.now() - started).total_seconds()
                status_code = response.status_code
                if scheme == "https":
                    https_ok = True
                if status_code == 200:
                    result["reachable"] = True
                    html = response.text or ""
                    break
                if status_code in (401, 403, 429, 503):
                    break
            except requests.RequestException:
                continue
        if result["reachable"] or status_code in (401, 403, 429, 503):
            break

    if not result["reachable"]:
        if status_code in (401, 403, 429, 503):
            result["signals"].append("blocked")
            result["notes"].append(
                f"site returned {status_code} to automated check — "
                "may be fine in a real browser"
            )
        else:
            result["signals"].append("unreachable")
            result["notes"].append(f"last status {status_code or 'no response'}")
        return _finalize(result)

    if not https_ok:
        result["signals"].append("no_https")

    soup = BeautifulSoup(html, "html.parser")

    if not soup.find("meta", attrs={"name": "viewport"}):
        result["signals"].append("no_mobile_viewport")
        result["notes"].append("no responsive viewport meta tag")

    _check_copyright(soup, result)
    _check_jquery(html, result)
    _check_legacy_markup(soup, html, result)
    _check_generator(soup, result)
    _check_builder(soup, result)
    _check_performance(html, load_seconds, result)

    return _finalize(result)


def _check_copyright(soup: BeautifulSoup, result: dict) -> None:
    footer = soup.find("footer") or soup.find("address")
    footer_text = footer.get_text(" ") if footer else ""
    if not footer_text:
        footer_text = soup.get_text(" ")[:4000]
    years = [int(y) for y in COPYRIGHT_YEAR_RE.findall(footer_text)]
    if not years:
        years = [int(y) for y in ANY_YEAR_RE.findall(footer_text)]
    current_year = datetime.now().year
    if not years:
        result["signals"].append("stale_copyright")
        result["notes"].append("no copyright year found")
        return
    newest = max(years)
    if newest <= current_year - 2:
        result["signals"].append("stale_copyright")
        result["notes"].append(f"copyright frozen at {newest}")


def _check_jquery(html: str, result: dict) -> None:
    match = JQUERY_VERSION_RE.search(html)
    if match and int(match.group(1)) < 3:
        result["signals"].append("old_jquery")
        result["notes"].append(
            f"jQuery {match.group(1)}.{match.group(2)} in use"
        )


def _check_legacy_markup(soup: BeautifulSoup, html: str, result: dict) -> None:
    if soup.find(["frame", "frameset", "applet", "object"]) or "shockwave-flash" in html:
        result["signals"].append("flash_or_frames")
        result["notes"].append("flash/frames technology detected")
    legacy = [tag for tag in LEGACY_TAGS if soup.find(tag)]
    if len(legacy) >= 2:
        result["signals"].append("legacy_html")
        result["notes"].append("legacy tags: " + ", ".join(legacy))


def _check_generator(soup: BeautifulSoup, result: dict) -> None:
    generator = soup.find("meta", attrs={"name": "generator"})
    if generator:
        content = generator.get("content", "")
        if OLD_GENERATOR_RE.search(content):
            result["signals"].append("old_generator")
            result["notes"].append(f"generator: {content}")


def _check_builder(soup: BeautifulSoup, result: dict) -> None:
    haystack = " ".join(
        filter(None, [soup.get_text(" ", strip=True)[:2000], str(soup)[:20000]])
    ).lower()
    for hint in DIY_BUILDER_HINTS:
        if hint in haystack:
            result["signals"].append("diy_builder")
            result["notes"].append(f"DIY site builder detected ({hint})")
            break


def _check_performance(html: str, load_seconds: float, result: dict) -> None:
    if load_seconds > 4.0:
        result["signals"].append("slow_load")
        result["notes"].append(f"slow load: {load_seconds:.1f}s")
    if len(html) > 1_500_000:
        result["signals"].append("oversized_page")
        result["notes"].append(f"very large HTML ({len(html) // 1000} KB)")


def _finalize(result: dict) -> dict:
    result["score"] = sum(SIGNAL_WEIGHTS[s] for s in set(result["signals"]))
    result["signals"] = list(dict.fromkeys(result["signals"]))
    return result
