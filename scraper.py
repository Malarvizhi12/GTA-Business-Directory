"""
GTA Business Directory Scraper
================================
Source  : https://www.gtasearch.com/
Policy  : robots.txt allows all generic bots on /directory/* pages.
          /directory/search is disallowed, so we use the category+city URL
          pattern (/directory/{category}/{city}?page={n}) which is allowed.

HTML selectors are based on live inspection of the site (Next.js SSR output):
  Listing card  : article.rounded-card
  Name          : span.min-w-0.flex-1.truncate.text-sm.font-semibold.text-ink
  Category      : p.text-xs.text-ink-muted  (first <p> inside card body .p-3)
  Address       : p.text-xs.text-ink-faint  (second <p> inside card body .p-3)
  Phone         : a[href^="tel:"]           (absolute-positioned button)
  Detail URL    : a.block[href^="/biz/"]

Detail page selectors:
  Name          : h1
  Category      : p.text-sm.text-ink-faint  (first <p> after <h1>)
  Address       : dl div:first-child dd:first-child
  Phone         : a[href^="tel:"]  inside dl
  Website       : a[rel*="nofollow"]  inside dl
  Description   : section[aria-labelledby="business-description-heading"] p
  Rating/Reviews: not publicly exposed on detail pages (no star/count markup)
"""

import csv
import os
import re
import time
import logging
from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE_URL = "https://www.gtasearch.com"

CATEGORIES = [
    "restaurants",
    "health",
    "home-services",
    "beauty",
    "automotive",
    "professional",
    "shopping",
    "education",
    "fitness",
    "pets",
    "religion",
]

# City slugs that map to display names (robots.txt allows these pages)
CITIES = {
    "toronto":      "Toronto",
    "mississauga":  "Mississauga",
    "brampton":     "Brampton",
    "vaughan":      "Vaughan",
    "markham":      "Markham",
    "richmond-hill":"Richmond Hill",
    "ajax":         "Ajax",
    "pickering":    "Pickering",
    "whitby":       "Whitby",
    "oshawa":       "Oshawa",
}

# Polite crawl settings
REQUEST_DELAY_S   = 1.5   # seconds between requests
MAX_PAGES_PER_COMBO = 3   # pages per category+city combo (24 cards/page → ≤72 records each)

HEADERS = {
    "User-Agent": (
        "GTABusinessDirectoryBot/1.0 (educational data-analysis project; "
        "respects robots.txt; contact: noreply@example.com)"
    ),
    "Accept-Language": "en-CA,en;q=0.9",
}

DATA_DIR  = Path(__file__).parent / "data"
CSV_PATH  = DATA_DIR / "businesses.csv"

CSV_FIELDS = [
    "business_name",
    "category",
    "subcategory",
    "address",
    "city",
    "phone",
    "website",
    "rating",
    "num_reviews",
    "description",
    "source_url",
]

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def fetch(url: str, retries: int = 3, backoff: float = 3.0) -> Optional[BeautifulSoup]:
    """Fetch a URL and return a BeautifulSoup object, or None on failure."""
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.status_code == 200:
                return BeautifulSoup(resp.text, "lxml")
            elif resp.status_code == 429:
                wait = backoff * attempt
                log.warning("429 Too Many Requests for %s — waiting %.0fs", url, wait)
                time.sleep(wait)
            elif resp.status_code == 404:
                log.debug("404 Not Found: %s", url)
                return None
            else:
                log.warning("HTTP %s for %s (attempt %d)", resp.status_code, url, attempt)
                time.sleep(backoff)
        except requests.ConnectionError as exc:
            log.warning("Connection error (%s) for %s — attempt %d", exc, url, attempt)
            time.sleep(backoff * attempt)
        except requests.Timeout:
            log.warning("Timeout for %s — attempt %d", url, attempt)
            time.sleep(backoff)
    log.error("Failed to fetch %s after %d attempts", url, retries)
    return None


def clean(text: Optional[str]) -> str:
    """Strip HTML entities, extra whitespace, and normalise to a single line."""
    if not text:
        return ""
    return " ".join(text.split())


# ---------------------------------------------------------------------------
# Scraping: listing pages
# ---------------------------------------------------------------------------

def parse_cards(soup: BeautifulSoup, city_display: str) -> list[dict]:
    """
    Extract business cards from a category/city listing page.

    Each <article class="... rounded-card ..."> contains:
      - <a class="block" href="/biz/{slug}">
          <div class="p-3">
            <h2><span class="... text-sm font-semibold text-ink">NAME</span></h2>
            <p class="... text-xs text-ink-muted">CATEGORY [· SUBCATEGORY]</p>
            <p class="... text-xs text-ink-faint">ADDRESS</p>
          </div>
        </a>
      - <a href="tel:..." ...>  (phone – sometimes absent)
    """
    records = []
    articles = soup.select("article.rounded-card")
    for article in articles:
        # --- Name ---
        name_el = article.select_one(
            "span.min-w-0.flex-1.truncate.text-sm.font-semibold.text-ink"
        )
        name = clean(name_el.get_text()) if name_el else ""
        if not name:
            continue

        # --- Detail URL ---
        link_el = article.select_one("a.block[href^='/biz/']")
        detail_url = (BASE_URL + link_el["href"]) if link_el else ""

        # --- Phone (on card) ---
        tel_el = article.select_one("a[href^='tel:']")
        phone_raw = ""
        if tel_el:
            phone_raw = tel_el["href"].replace("tel:", "").strip()

        # --- Category / subcategory ---
        card_body = article.select_one("div.p-3")
        cat_el = card_body.select_one("p.text-xs.text-ink-muted") if card_body else None
        cat_text = clean(cat_el.get_text()) if cat_el else ""
        # cat_text might be "Restaurants & Food · Caribbean"
        if "·" in cat_text:
            parts = [p.strip() for p in cat_text.split("·", 1)]
            category, subcategory = parts[0], parts[1]
        else:
            category, subcategory = cat_text, ""

        # --- Address ---
        addr_el = card_body.select_one("p.text-xs.text-ink-faint") if card_body else None
        address = clean(addr_el.get_text()) if addr_el else ""

        records.append({
            "business_name": name,
            "category":      category,
            "subcategory":   subcategory,
            "address":       address,
            "city":          city_display,
            "phone":         phone_raw,
            "website":       "",
            "rating":        "",
            "num_reviews":   "",
            "description":   "",
            "source_url":    detail_url,
        })
    return records


# ---------------------------------------------------------------------------
# Scraping: detail page enrichment
# ---------------------------------------------------------------------------

def enrich_from_detail(record: dict) -> dict:
    """
    Visit the individual business page to fill in missing fields.
    The detail page provides: phone (if missing), website, description.
    Rating / review count are not exposed as structured HTML on these pages.
    """
    url = record.get("source_url", "")
    if not url:
        return record

    soup = fetch(url)
    if soup is None:
        return record

    # Phone (fallback to card value)
    if not record["phone"]:
        tel_el = soup.select_one("dl a[href^='tel:']")
        if tel_el:
            record["phone"] = tel_el["href"].replace("tel:", "").strip()

    # Website
    web_el = soup.select_one("dl a[rel*='nofollow']")
    if web_el:
        record["website"] = web_el.get("href", "").strip()

    # Description
    desc_el = soup.select_one(
        "section[aria-labelledby='business-description-heading'] p"
    )
    if desc_el:
        record["description"] = clean(desc_el.get_text())

    # Rating / review count — no star markup found in live HTML;
    # the site uses a sign-in wall for user-submitted reviews.
    # Fields remain empty (""  → NaN after cleaning).

    return record


# ---------------------------------------------------------------------------
# Phone normalisation
# ---------------------------------------------------------------------------

def normalise_phone(raw: str) -> str:
    """
    Attempt to format a phone number as (XXX) XXX-XXXX.
    Returns the cleaned digits string if it doesn't match a 10-digit pattern.
    """
    digits = re.sub(r"\D", "", raw)
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    return raw  # return original if we can't normalise


# ---------------------------------------------------------------------------
# Main scraping loop
# ---------------------------------------------------------------------------

def scrape(
    max_pages: int = MAX_PAGES_PER_COMBO,
    enrich: bool = False,          # set True to also visit detail pages
) -> list[dict]:
    """
    Scrape category × city listing pages.

    Parameters
    ----------
    max_pages : int
        Maximum number of listing pages to scrape per category+city combo.
    enrich : bool
        If True, also visits each business detail page for website/description.
        This multiplies HTTP requests significantly; use with care.
    """
    all_records: list[dict] = []
    seen_urls: set[str] = set()

    total_combos = len(CATEGORIES) * len(CITIES)
    combo_n = 0

    for cat in CATEGORIES:
        for city_slug, city_display in CITIES.items():
            combo_n += 1
            log.info(
                "[%d/%d] Scraping category=%s city=%s",
                combo_n, total_combos, cat, city_display,
            )

            for page in range(1, max_pages + 1):
                # URL pattern: /directory/{category}/{city}?page={n}
                # Page 1 can be accessed without ?page= but works with it too.
                url = f"{BASE_URL}/directory/{cat}/{city_slug}?page={page}"
                soup = fetch(url)

                if soup is None:
                    log.warning("  Skipping %s (fetch failed)", url)
                    break

                records = parse_cards(soup, city_display)
                if not records:
                    log.info("  No more cards on page %d — stopping this combo", page)
                    break

                new_count = 0
                for rec in records:
                    src = rec["source_url"]
                    if src and src in seen_urls:
                        continue  # deduplicate
                    seen_urls.add(src)

                    if enrich and src:
                        time.sleep(REQUEST_DELAY_S)
                        rec = enrich_from_detail(rec)

                    all_records.append(rec)
                    new_count += 1

                log.info("  Page %d → %d new records (running total: %d)",
                         page, new_count, len(all_records))

                # Pagination: check whether a "Next" link exists
                next_link = soup.select_one("nav[aria-label='Pagination'] a[rel='next']")
                if not next_link and page >= 2:
                    break  # reached last page

                time.sleep(REQUEST_DELAY_S)

    return all_records


# ---------------------------------------------------------------------------
# Save to CSV
# ---------------------------------------------------------------------------

def save_csv(records: list[dict]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(records)
    log.info("Saved %d records → %s", len(records), CSV_PATH)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="GTA Business Directory Scraper")
    parser.add_argument(
        "--pages", type=int, default=MAX_PAGES_PER_COMBO,
        help="Max listing pages per category+city combo (default: %(default)s)",
    )
    parser.add_argument(
        "--enrich", action="store_true",
        help="Also visit each business detail page (slow — many extra requests)",
    )
    args = parser.parse_args()

    log.info("=== GTA Business Directory Scraper ===")
    log.info("Robots.txt status : /directory/* pages are ALLOWED for generic bots")
    log.info("Max pages/combo   : %d", args.pages)
    log.info("Detail enrichment : %s", args.enrich)
    log.info("")

    records = scrape(max_pages=args.pages, enrich=args.enrich)

    # Normalise phones before saving
    for r in records:
        if r["phone"]:
            r["phone"] = normalise_phone(r["phone"])

    save_csv(records)
    log.info("Done.")
