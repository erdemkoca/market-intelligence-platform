import asyncio
import logging
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

import httpx

logger = logging.getLogger(__name__)

SEARCH_TERMS = ["maler", "gipser", "fassadenbau", "verputzer", "stuckateur"]

# Atom/OpenSearch namespaces
NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "os": "http://a9.com/-/spec/opensearchrss/1.0/",
    "tel": "http://tel.search.ch/api/spec/result/1.0/",
}


@dataclass
class SearchChCompany:
    name: str
    street: str | None = None
    zip_code: str | None = None
    city: str | None = None
    canton: str | None = None
    phone: str | None = None
    website: str | None = None
    email: str | None = None
    categories: list[str] = field(default_factory=list)
    detail_url: str | None = None
    source_url: str | None = None
    raw: dict = field(default_factory=dict)


class SearchChClient:
    """Fetches company data from search.ch public API (Atom/OpenSearch)."""

    API_URL = "https://tel.search.ch/api/"

    def __init__(self, delay: float = 1.0, max_results_per_term: int = 1000):
        self.delay = delay
        self.max_results_per_term = max_results_per_term
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=30.0,
                headers={
                    "User-Agent": "BaunexMarketIntelligence/1.0",
                    "Accept": "application/atom+xml",
                },
                follow_redirects=True,
            )
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def fetch_all_trades(self) -> list[SearchChCompany]:
        """Fetch companies for all target trade search terms via API."""
        all_companies: dict[str, SearchChCompany] = {}

        for term in SEARCH_TERMS:
            logger.info(f"search.ch API: fetching '{term}'...")
            companies = await self._fetch_search_term(term)

            for company in companies:
                key = f"{company.name.lower().strip()}|{company.zip_code or ''}"
                if key not in all_companies:
                    all_companies[key] = company
                else:
                    existing = all_companies[key]
                    if not existing.phone and company.phone:
                        existing.phone = company.phone
                    if not existing.website and company.website:
                        existing.website = company.website

            logger.info(
                f"search.ch API: '{term}' yielded {len(companies)} results, "
                f"unique so far: {len(all_companies)}"
            )

        logger.info(f"search.ch API: total unique companies: {len(all_companies)}")
        return list(all_companies.values())

    async def _fetch_search_term(self, term: str) -> list[SearchChCompany]:
        """Fetch all results for a search term using API pagination."""
        companies = []
        pos = 1
        batch_size = 50  # Max per request

        while pos <= self.max_results_per_term:
            try:
                client = await self._get_client()
                response = await client.get(
                    self.API_URL,
                    params={"was": term, "maxnum": batch_size, "pos": pos},
                )

                if response.status_code == 429:
                    logger.warning(f"search.ch API: rate limited, waiting 30s...")
                    await asyncio.sleep(30)
                    continue

                response.raise_for_status()

                page_companies, total = self._parse_api_response(response.text, term)

                if not page_companies:
                    break

                companies.extend(page_companies)

                if len(companies) % 200 < batch_size:
                    logger.info(f"search.ch API: '{term}' pos={pos}: {len(companies)}/{total}")

                # Check if we've fetched all
                if pos + batch_size > total:
                    break

                pos += batch_size
                await asyncio.sleep(self.delay)

            except httpx.HTTPStatusError as e:
                logger.warning(f"search.ch API: HTTP {e.response.status_code} for '{term}' at pos={pos}")
                break
            except httpx.RequestError as e:
                logger.warning(f"search.ch API: request error for '{term}': {e}")
                break

        return companies

    def _parse_api_response(self, xml_text: str, search_term: str) -> tuple[list[SearchChCompany], int]:
        """Parse Atom/OpenSearch XML response from search.ch API."""
        companies = []
        total = 0

        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as e:
            logger.warning(f"search.ch API: XML parse error: {e}")
            return companies, total

        # Get total results
        total_el = root.find("os:totalResults", NS)
        if total_el is not None and total_el.text:
            total = int(total_el.text)

        # Parse entries
        for entry in root.findall("atom:entry", NS):
            company = self._parse_entry(entry, search_term)
            if company:
                companies.append(company)

        return companies, total

    def _parse_entry(self, entry: ET.Element, search_term: str) -> SearchChCompany | None:
        """Parse a single Atom entry into a SearchChCompany."""
        title = entry.find("atom:title", NS)
        if title is None or not title.text:
            return None

        name = title.text.strip()

        # Parse content block: "Name\nDescription\nStreet\nPLZ City Canton\nPhone"
        content = entry.find("atom:content", NS)
        street = None
        zip_code = None
        city = None
        canton = None
        phone = None

        if content is not None and content.text:
            lines = [l.strip() for l in content.text.strip().split("\n") if l.strip()]

            for line in lines:
                # Phone number (starts with * or +41 or 0)
                phone_match = re.match(r'^\*?(\+?[\d\s]{10,})', line)
                if phone_match:
                    phone = self._normalize_phone(phone_match.group(1))
                    continue

                # Address: PLZ City Canton
                addr_match = re.match(r'^(\d{4})\s+(.+?)(?:\s+([A-Z]{2}))?\s*$', line)
                if addr_match:
                    zip_code = addr_match.group(1)
                    city = addr_match.group(2).strip()
                    canton = addr_match.group(3)
                    if not canton:
                        canton = self._plz_to_canton(zip_code)
                    continue

                # Street (contains number and common street suffixes)
                if re.search(r'\d', line) and line != name and not re.match(r'^\d{4}\s', line):
                    street = line

        # Detail URL
        detail_url = None
        for link in entry.findall("atom:link", NS):
            if link.get("rel") == "alternate" and link.get("type") == "text/html":
                detail_url = link.get("href")
                break

        return SearchChCompany(
            name=name,
            street=street,
            zip_code=zip_code,
            city=city,
            canton=canton,
            phone=phone,
            detail_url=detail_url,
            source_url=f"search.ch:{search_term}",
            raw={"search_term": search_term, "detail_url": detail_url},
        )

    @staticmethod
    def _normalize_phone(phone: str) -> str:
        """Normalize phone to +41 format."""
        digits = re.sub(r"[^0-9+]", "", phone)
        if digits.startswith("0") and len(digits) == 10:
            return f"+41{digits[1:]}"
        if digits.startswith("+41"):
            return digits
        if digits.startswith("0041"):
            return f"+41{digits[4:]}"
        return digits

    @staticmethod
    def _plz_to_canton(plz: str) -> str | None:
        """Map Swiss PLZ to canton (simplified major ranges)."""
        try:
            p = int(plz)
        except ValueError:
            return None

        ranges = [
            (1000, 1199, "VD"), (1200, 1299, "GE"), (1300, 1499, "VD"),
            (1500, 1529, "FR"), (1530, 1599, "VD"), (1600, 1689, "FR"),
            (1690, 1699, "VD"), (1700, 1799, "FR"), (1800, 1899, "VD"),
            (1900, 1999, "VS"), (2000, 2199, "NE"), (2300, 2364, "JU"),
            (2400, 2699, "BE"), (2700, 2999, "JU"), (3000, 3999, "BE"),
            (4000, 4059, "BS"), (4060, 4199, "BL"), (4200, 4229, "BL"),
            (4230, 4299, "SO"), (4300, 4499, "BL"), (4500, 4799, "SO"),
            (4800, 4899, "AG"), (4900, 4999, "BE"), (5000, 5999, "AG"),
            (6000, 6299, "LU"), (6300, 6399, "ZG"), (6400, 6499, "SZ"),
            (6500, 6999, "TI"), (7000, 7999, "GR"), (8000, 8199, "ZH"),
            (8200, 8259, "SH"), (8260, 8279, "TG"), (8280, 8499, "ZH"),
            (8500, 8599, "TG"), (8600, 8729, "ZH"), (8730, 8749, "SZ"),
            (8750, 8899, "GL"), (8900, 8909, "AG"), (8910, 8959, "ZH"),
            (8960, 8969, "SG"), (8970, 8999, "AR"), (9000, 9099, "SG"),
            (9100, 9199, "AR"), (9200, 9249, "TG"), (9250, 9399, "SG"),
            (9400, 9449, "SG"), (9450, 9499, "AR"), (9500, 9559, "TG"),
            (9560, 9699, "SG"), (9700, 9999, "SG"),
        ]
        for low, high, ct in ranges:
            if low <= p <= high:
                return ct
        return None
