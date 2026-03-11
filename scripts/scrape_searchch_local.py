#!/usr/bin/env python3
"""
Scrape search.ch API from local machine (avoids datacenter IP blocking)
and upload results to the server via the API.

Usage:
    pip install httpx
    python scripts/scrape_searchch_local.py [--server http://209.38.209.149:8000]
"""
import argparse
import json
import re
import sys
import time
import xml.etree.ElementTree as ET

import httpx

SEARCH_TERMS = ["maler", "gipser", "fassadenbau", "verputzer", "stuckateur"]
API_URL = "https://tel.search.ch/api/"
NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "os": "http://a9.com/-/spec/opensearchrss/1.0/",
}

PLZ_CANTON = [
    (1000, 1199, "VD"), (1200, 1299, "GE"), (1300, 1499, "VD"),
    (1500, 1529, "FR"), (1530, 1599, "VD"), (1600, 1689, "FR"),
    (1700, 1799, "FR"), (1800, 1899, "VD"), (1900, 1999, "VS"),
    (2000, 2199, "NE"), (2300, 2364, "JU"), (2400, 2699, "BE"),
    (2700, 2999, "JU"), (3000, 3999, "BE"), (4000, 4059, "BS"),
    (4060, 4199, "BL"), (4230, 4299, "SO"), (4300, 4499, "BL"),
    (4500, 4799, "SO"), (4800, 4899, "AG"), (5000, 5999, "AG"),
    (6000, 6299, "LU"), (6300, 6399, "ZG"), (6400, 6499, "SZ"),
    (6500, 6999, "TI"), (7000, 7999, "GR"), (8000, 8199, "ZH"),
    (8200, 8259, "SH"), (8260, 8279, "TG"), (8280, 8499, "ZH"),
    (8500, 8599, "TG"), (8600, 8729, "ZH"), (8730, 8749, "SZ"),
    (8750, 8899, "GL"), (8900, 8909, "AG"), (8910, 8959, "ZH"),
    (9000, 9099, "SG"), (9100, 9199, "AR"), (9200, 9249, "TG"),
    (9250, 9399, "SG"), (9500, 9559, "TG"), (9560, 9999, "SG"),
]


def plz_to_canton(plz: str) -> str | None:
    try:
        p = int(plz)
    except ValueError:
        return None
    for low, high, ct in PLZ_CANTON:
        if low <= p <= high:
            return ct
    return None


def normalize_phone(phone: str) -> str:
    digits = re.sub(r"[^0-9+]", "", phone)
    if digits.startswith("0") and len(digits) == 10:
        return f"+41{digits[1:]}"
    if digits.startswith("+41"):
        return digits
    if digits.startswith("0041"):
        return f"+41{digits[4:]}"
    return digits


def parse_entry(entry: ET.Element) -> dict | None:
    title = entry.find("atom:title", NS)
    if title is None or not title.text:
        return None

    name = title.text.strip()
    content = entry.find("atom:content", NS)
    street = None
    zip_code = None
    city = None
    canton = None
    phone = None

    if content is not None and content.text:
        lines = [l.strip() for l in content.text.strip().split("\n") if l.strip()]
        for line in lines:
            phone_match = re.match(r"^\*?(\+?[\d\s]{10,})", line)
            if phone_match:
                phone = normalize_phone(phone_match.group(1))
                continue

            addr_match = re.match(r"^(\d{4})\s+(.+?)(?:\s+([A-Z]{2}))?\s*$", line)
            if addr_match:
                zip_code = addr_match.group(1)
                city = addr_match.group(2).strip()
                canton = addr_match.group(3) or plz_to_canton(zip_code)
                continue

            if re.search(r"\d", line) and line != name and not re.match(r"^\d{4}\s", line):
                street = line

    detail_url = None
    for link in entry.findall("atom:link", NS):
        if link.get("rel") == "alternate" and link.get("type") == "text/html":
            detail_url = link.get("href")
            break

    return {
        "name": name,
        "street": street,
        "zip_code": zip_code,
        "city": city,
        "canton": canton,
        "phone": phone,
        "detail_url": detail_url,
    }


def fetch_all():
    client = httpx.Client(timeout=30.0, headers={"Accept": "application/atom+xml"})
    all_companies = {}

    for term in SEARCH_TERMS:
        print(f"\n--- Fetching '{term}' ---")
        pos = 1
        term_count = 0

        while pos <= 1000:
            try:
                resp = client.get(API_URL, params={"was": term, "maxnum": 50, "pos": pos})
                if resp.status_code == 429:
                    print(f"  Rate limited at pos={pos}, waiting 30s...")
                    time.sleep(30)
                    continue

                resp.raise_for_status()
                root = ET.fromstring(resp.text)

                total_el = root.find("os:totalResults", NS)
                total = int(total_el.text) if total_el is not None and total_el.text else 0

                entries = root.findall("atom:entry", NS)
                if not entries:
                    break

                for entry in entries:
                    company = parse_entry(entry)
                    if company:
                        key = f"{company['name'].lower()}|{company.get('zip_code', '')}"
                        if key not in all_companies:
                            all_companies[key] = company
                            term_count += 1
                        else:
                            # Merge phone if missing
                            if not all_companies[key].get("phone") and company.get("phone"):
                                all_companies[key]["phone"] = company["phone"]

                if pos % 200 < 50:
                    print(f"  pos={pos}: {term_count} new, {len(all_companies)} total unique")

                if pos + 50 > total:
                    break

                pos += 50
                time.sleep(1.0)

            except Exception as e:
                print(f"  Error at pos={pos}: {e}")
                break

        print(f"  '{term}' done: {term_count} new companies")

    return list(all_companies.values())


def upload_to_server(companies: list[dict], server_url: str):
    """Upload scraped companies to the MI platform API."""
    output_file = "searchch_companies.json"
    with open(output_file, "w") as f:
        json.dump(companies, f, ensure_ascii=False, indent=2)
    print(f"\nSaved {len(companies)} companies to {output_file}")
    print(f"Upload with: curl -X POST {server_url}/api/ingestion/upload-searchch -H 'Content-Type: application/json' -d @{output_file}")


def main():
    parser = argparse.ArgumentParser(description="Scrape search.ch from local machine")
    parser.add_argument("--server", default="http://209.38.209.149:8000")
    args = parser.parse_args()

    print("Scraping search.ch API...")
    companies = fetch_all()

    with_phone = sum(1 for c in companies if c.get("phone"))
    with_address = sum(1 for c in companies if c.get("zip_code"))
    print(f"\n=== Results ===")
    print(f"Total unique companies: {len(companies)}")
    print(f"With phone: {with_phone}")
    print(f"With address: {with_address}")

    upload_to_server(companies, args.server)


if __name__ == "__main__":
    main()
