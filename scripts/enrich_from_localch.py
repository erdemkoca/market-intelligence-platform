#!/usr/bin/env python3
"""
Fetch company detail pages from local.ch to extract email, website, phone.
Then upload enrichment data to the MI platform API.

Usage:
    pip install httpx
    python scripts/enrich_from_localch.py
"""
import json
import re
import sys
import time

import httpx

SERVER = "http://209.38.209.149:8000"
SEARCH_TERMS = ["maler", "gipser", "fassadenbau"]
MAX_PAGES = 30
DELAY = 2.0


def scrape_listing_pages() -> list[dict]:
    """Scrape local.ch search result pages to get detail URLs."""
    client = httpx.Client(
        timeout=30.0,
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept-Language": "de-CH,de;q=0.9",
        },
        follow_redirects=True,
    )

    all_companies = {}

    for term in SEARCH_TERMS:
        print(f"\n--- Listing pages for '{term}' ---")
        for page in range(1, MAX_PAGES + 1):
            url = f"https://www.local.ch/de/s/{term}?page={page}"
            try:
                resp = client.get(url)
                if resp.status_code != 200:
                    print(f"  Page {page}: HTTP {resp.status_code}, stopping")
                    break

                html = resp.text

                # Extract detail URLs with city/PLZ from URL pattern
                detail_urls = re.findall(
                    r'href="(/de/d/([^/]+)/(\d{4})/[^/]+/([^"]+))"',
                    html,
                )

                if not detail_urls:
                    break

                # Extract real names from headings
                names = re.findall(
                    r'<h\d[^>]*>\s*<a[^>]*href="/de/d/[^"]*"[^>]*>\s*([^<]+)\s*</a>',
                    html,
                )

                for i, (path, city_slug, plz, name_slug) in enumerate(detail_urls):
                    full_url = f"https://www.local.ch{path}"
                    key = full_url.lower()
                    if key in all_companies:
                        continue

                    # Use real name if available, otherwise parse from slug
                    if i < len(names):
                        name = names[i].strip()
                    else:
                        name = slug_to_name(name_slug)

                    city = city_slug.replace("-", " ").title()

                    all_companies[key] = {
                        "name": name,
                        "zip_code": plz,
                        "city": city,
                        "detail_url": full_url,
                    }

                if page % 10 == 0:
                    print(f"  Page {page}: {len(all_companies)} total unique")

                time.sleep(DELAY)

            except Exception as e:
                print(f"  Page {page} error: {e}")
                break

        print(f"  '{term}' done, total: {len(all_companies)}")

    client.close()
    return list(all_companies.values())


def enrich_details(companies: list[dict]) -> list[dict]:
    """Visit detail pages to extract email, website, phone."""
    client = httpx.Client(
        timeout=15.0,
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept-Language": "de-CH,de;q=0.9",
        },
        follow_redirects=True,
    )

    enriched = 0
    for i, company in enumerate(companies):
        url = company.get("detail_url")
        if not url:
            continue

        try:
            resp = client.get(url)
            if resp.status_code != 200:
                continue

            html = resp.text

            # Email from mailto:
            email_match = re.search(r'href="mailto:([^"?]+)"', html)
            if email_match:
                email = email_match.group(1).lower().strip()
                if "noreply" not in email and "example" not in email:
                    company["email"] = email

            # Phone from tel:
            phone_match = re.search(r'href="tel:([^"]+)"', html)
            if phone_match:
                phone = re.sub(r"[^0-9+]", "", phone_match.group(1))
                if len(phone) >= 10:
                    if phone.startswith("0") and len(phone) == 10:
                        phone = f"+41{phone[1:]}"
                    company["phone"] = phone

            # Website — external links (not local.ch, social media, etc.)
            for match in re.finditer(r'href="(https?://(?!www\.local\.ch|.*google\.|.*facebook\.|.*instagram\.|.*twitter\.|.*youtube\.|.*linkedin\.)[^"]+)"', html):
                url_found = match.group(1)
                # Skip tracking/ad URLs
                if any(x in url_found for x in ["click", "track", "pixel", "analytics", "doubleclick", "adsrv"]):
                    continue
                company["website"] = url_found
                break

            if company.get("email") or company.get("website") or company.get("phone"):
                enriched += 1

        except Exception:
            pass

        if (i + 1) % 50 == 0:
            print(f"  Detail {i + 1}/{len(companies)}: {enriched} enriched")

        time.sleep(1.5)

    client.close()
    print(f"\n  Enriched {enriched}/{len(companies)} companies with contact data")
    return companies


def slug_to_name(slug: str) -> str:
    parts = slug.rsplit("-", 1)
    if len(parts) == 2 and re.search(r'[A-Z0-9_]', parts[1]):
        slug = parts[0]
    name = slug.replace("-", " ").strip()
    words = []
    for word in name.split():
        if word.upper() in ("AG", "GMBH", "SA", "SARL"):
            words.append(word.upper())
        else:
            words.append(word.capitalize())
    return " ".join(words)


def upload(companies: list[dict]):
    """Upload to server."""
    # Filter to only companies with enrichment data
    enriched = [c for c in companies if c.get("email") or c.get("website") or c.get("phone")]

    output_file = "localch_enriched.json"
    with open(output_file, "w") as f:
        json.dump(enriched, f, ensure_ascii=False, indent=2)

    with_phone = sum(1 for c in enriched if c.get("phone"))
    with_email = sum(1 for c in enriched if c.get("email"))
    with_website = sum(1 for c in enriched if c.get("website"))

    print(f"\n=== Results ===")
    print(f"Total companies scraped: {len(companies)}")
    print(f"With contact data: {len(enriched)}")
    print(f"  Phone: {with_phone}")
    print(f"  Email: {with_email}")
    print(f"  Website: {with_website}")
    print(f"\nSaved to {output_file}")
    print(f"\nUploading to server...")

    try:
        client = httpx.Client(timeout=300.0)
        resp = client.post(
            f"{SERVER}/api/ingestion/upload-searchch",
            json=enriched,
            headers={"Content-Type": "application/json"},
        )
        print(f"Server response: {resp.json()}")
        client.close()
    except Exception as e:
        print(f"Upload failed: {e}")
        print(f"Manual upload: curl -X POST {SERVER}/api/ingestion/upload-searchch -H 'Content-Type: application/json' -d @{output_file}")


def main():
    print("Step 1: Scraping listing pages from local.ch...")
    companies = scrape_listing_pages()

    print(f"\nStep 2: Enriching {len(companies)} detail pages...")
    companies = enrich_details(companies)

    print("\nStep 3: Uploading to server...")
    upload(companies)


if __name__ == "__main__":
    main()
