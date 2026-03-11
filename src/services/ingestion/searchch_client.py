import asyncio
import logging
import re
from dataclasses import dataclass, field

import httpx

logger = logging.getLogger(__name__)

SEARCH_TERMS = ["maler", "gipser", "fassadenbau"]
RESULTS_PER_PAGE = 12


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
    source_url: str | None = None
    raw: dict = field(default_factory=dict)


class SearchChClient:
    """Scrapes company data from search.ch telephone directory."""

    BASE_URL = "https://www.search.ch/tel/"

    def __init__(self, delay: float = 3.0, max_results_per_term: int = 750):
        self.delay = delay
        self.max_results_per_term = max_results_per_term
        self._client: httpx.AsyncClient | None = None
        self._retry_delay = 30.0
        self._max_retries = 3

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=30.0,
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "de-CH,de;q=0.9",
                },
                follow_redirects=True,
            )
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def fetch_all_trades(self) -> list[SearchChCompany]:
        """Fetch companies for all target trade search terms."""
        all_companies: dict[str, SearchChCompany] = {}

        for term in SEARCH_TERMS:
            logger.info(f"search.ch: scraping '{term}'...")
            companies = await self._fetch_search_term(term)

            for company in companies:
                key = f"{company.name.lower().strip()}|{company.zip_code or ''}"
                if key not in all_companies:
                    all_companies[key] = company
                else:
                    # Merge: keep the one with more data
                    existing = all_companies[key]
                    if not existing.phone and company.phone:
                        existing.phone = company.phone
                    if not existing.website and company.website:
                        existing.website = company.website

            logger.info(
                f"search.ch: '{term}' yielded {len(companies)} results, "
                f"unique so far: {len(all_companies)}"
            )

        logger.info(f"search.ch: total unique companies: {len(all_companies)}")
        return list(all_companies.values())

    async def _fetch_search_term(self, term: str) -> list[SearchChCompany]:
        """Fetch results for a single search term with pagination."""
        companies = []
        pos = 1

        while pos <= self.max_results_per_term:
            url = f"{self.BASE_URL}?q={term}&pos={pos}"
            success = False

            for retry in range(self._max_retries):
                try:
                    client = await self._get_client()
                    response = await client.get(url)

                    if response.status_code == 429:
                        wait = self._retry_delay * (retry + 1)
                        logger.warning(f"search.ch: rate limited, waiting {wait}s (retry {retry + 1})")
                        await asyncio.sleep(wait)
                        continue

                    if response.status_code == 404:
                        return companies
                    response.raise_for_status()

                    html = response.text
                    page_companies = self._parse_search_page(html, url)

                    if not page_companies:
                        return companies

                    companies.extend(page_companies)
                    success = True

                    if len(companies) % 100 < RESULTS_PER_PAGE:
                        logger.info(f"search.ch: '{term}' pos={pos}: {len(companies)} total")

                    break

                except httpx.HTTPStatusError as e:
                    logger.warning(f"search.ch: HTTP {e.response.status_code} at pos={pos} for '{term}'")
                    if e.response.status_code == 429:
                        await asyncio.sleep(self._retry_delay * (retry + 1))
                        continue
                    return companies
                except httpx.RequestError as e:
                    logger.warning(f"search.ch: request error at pos={pos} for '{term}': {e}")
                    return companies

            if not success:
                logger.warning(f"search.ch: giving up on pos={pos} for '{term}' after {self._max_retries} retries")
                return companies

            await asyncio.sleep(self.delay)
            pos += RESULTS_PER_PAGE

        return companies

    def _parse_search_page(self, html: str, source_url: str) -> list[SearchChCompany]:
        """Parse company listings from search.ch HTML."""
        companies = []

        # search.ch uses structured listing blocks
        # Extract individual result entries
        # Pattern: company name, address, phone, website in structured blocks

        # Find all tel: links (phone numbers) — these are the most reliable anchors
        phone_pattern = re.compile(
            r'href="tel:(\+?[\d\s]+)"',
        )

        # Find listing blocks by looking for address patterns near phone numbers
        # search.ch typically has: Name, Address (street, PLZ city), Phone, Website

        # Strategy: extract structured data from listing blocks
        # Look for vcard/hcard microformat or similar patterns
        listing_blocks = re.split(r'<(?:article|div)[^>]*class="[^"]*(?:tel-result|listing|entry)[^"]*"', html)

        if len(listing_blocks) <= 1:
            # Try alternative split pattern
            listing_blocks = re.split(r'<h[23][^>]*>\s*<a[^>]*href="/tel/[^"]*"', html)

        # Alternative approach: find all company entries by their detail links
        # search.ch detail URLs look like: /tel/schaffhausen/scheffmacher-ag
        detail_links = re.findall(
            r'<a[^>]*href="(/tel/[^"]+)"[^>]*>\s*([^<]+)</a>',
            html,
        )

        # Also extract phone numbers
        phones = re.findall(r'href="tel:(\+?[0-9\s]+)"', html)

        # Extract addresses: "Street Nr, PLZ City"
        addresses = re.findall(
            r'(?:>|\s)([A-ZÄÖÜa-zäöüéèêàâ][a-zäöüéèêàâ\-]+(?:strasse|str\.|weg|gasse|platz|ring|allee|rain|matt|feld|acker|wies|hof|boden|graben|berg|tal|dorf|au|bühl|egg|stein|wald|holz|moos|brunn|bach|wil|ikon|iken|ingen|ikon)\s*\d*\w*)\s*,?\s*(\d{4})\s+([A-ZÄÖÜa-zäöüéèêàâ][A-Za-zÄÖÜäöüéèêàâ\s\-]+?)(?:\s*[A-Z]{2})?\s*(?:<|$)',
            html,
        )

        # Extract websites
        websites = re.findall(
            r'href="(https?://(?:www\.)?(?!search\.ch|local\.ch|google\.|facebook\.|instagram\.|twitter\.|youtube\.)[a-z0-9\-]+\.[a-z]{2,}[^"]*)"',
            html,
            re.IGNORECASE,
        )

        # Build company entries from detail links (most reliable)
        seen_names = set()
        for link_path, name in detail_links:
            name = name.strip()
            if not name or len(name) < 3:
                continue
            if name.lower() in seen_names:
                continue
            # Skip navigation/UI links
            if any(x in name.lower() for x in ["suche", "filter", "seite", "mehr", "karte", "login"]):
                continue

            seen_names.add(name.lower())

            company = SearchChCompany(
                name=name,
                source_url=source_url,
                raw={"detail_path": link_path},
            )
            companies.append(company)

        # Match phone numbers to companies (by order of appearance)
        phone_idx = 0
        for company in companies:
            if phone_idx < len(phones):
                phone = phones[phone_idx].strip()
                if len(phone) >= 10:
                    company.phone = self._normalize_phone(phone)
                phone_idx += 1

        # Match addresses to companies
        addr_idx = 0
        for company in companies:
            if addr_idx < len(addresses):
                street, plz, city = addresses[addr_idx]
                company.street = street.strip()
                company.zip_code = plz.strip()
                company.city = city.strip()
                company.canton = self._plz_to_canton(plz.strip())
                addr_idx += 1

        # Match websites to companies
        web_idx = 0
        for company in companies:
            if web_idx < len(websites):
                company.website = websites[web_idx]
                web_idx += 1

        return companies

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
        """Map Swiss PLZ ranges to cantons."""
        try:
            p = int(plz)
        except ValueError:
            return None

        # Major PLZ ranges (simplified)
        if 1000 <= p <= 1299:
            return "VD"
        if 1200 <= p <= 1299:
            return "GE"
        if 1300 <= p <= 1399:
            return "VD"
        if 1400 <= p <= 1499:
            return "VD"
        if 1500 <= p <= 1599:
            return "FR" if p < 1530 else "VD"
        if 1600 <= p <= 1699:
            return "FR" if p < 1690 else "VD"
        if 1700 <= p <= 1799:
            return "FR"
        if 1800 <= p <= 1899:
            return "VD"
        if 1900 <= p <= 1999:
            return "VS"
        if 2000 <= p <= 2099:
            return "NE"
        if 2100 <= p <= 2199:
            return "NE"
        if 2300 <= p <= 2399:
            return "JU" if p < 2365 else "NE"
        if 2400 <= p <= 2499:
            return "BE"
        if 2500 <= p <= 2599:
            return "BE"
        if 2600 <= p <= 2699:
            return "BE"
        if 2700 <= p <= 2799:
            return "JU"
        if 2800 <= p <= 2899:
            return "JU"
        if 2900 <= p <= 2999:
            return "JU"
        if 3000 <= p <= 3999:
            return "BE"
        if 4000 <= p <= 4099:
            return "BS" if p < 4060 else "BL"
        if 4100 <= p <= 4199:
            return "BL"
        if 4200 <= p <= 4299:
            return "BL" if p < 4230 else "SO"
        if 4300 <= p <= 4399:
            return "BL"
        if 4400 <= p <= 4499:
            return "BL"
        if 4500 <= p <= 4699:
            return "SO"
        if 4700 <= p <= 4799:
            return "SO"
        if 4800 <= p <= 4899:
            return "AG"
        if 4900 <= p <= 4999:
            return "BE"
        if 5000 <= p <= 5999:
            return "AG"
        if 6000 <= p <= 6099:
            return "LU"
        if 6100 <= p <= 6199:
            return "LU"
        if 6200 <= p <= 6299:
            return "LU"
        if 6300 <= p <= 6399:
            return "ZG"
        if 6400 <= p <= 6499:
            return "SZ"
        if 6500 <= p <= 6599:
            return "TI"
        if 6600 <= p <= 6999:
            return "TI"
        if 7000 <= p <= 7599:
            return "GR"
        if 7600 <= p <= 7999:
            return "GR"
        if 8000 <= p <= 8099:
            return "ZH"
        if 8100 <= p <= 8199:
            return "ZH"
        if 8200 <= p <= 8299:
            return "SH" if p < 8260 else "TG" if p < 8280 else "ZH"
        if 8300 <= p <= 8399:
            return "ZH" if p < 8355 else "TG"
        if 8400 <= p <= 8499:
            return "ZH"
        if 8500 <= p <= 8599:
            return "TG"
        if 8600 <= p <= 8699:
            return "ZH"
        if 8700 <= p <= 8799:
            return "ZH" if p < 8730 else "SZ" if p < 8750 else "GL"
        if 8800 <= p <= 8899:
            return "SZ" if p < 8850 else "GL"
        if 8900 <= p <= 8999:
            return "AG" if p < 8910 else "ZH" if p < 8960 else "SG" if p < 8970 else "AR"
        if 9000 <= p <= 9099:
            return "SG"
        if 9100 <= p <= 9199:
            return "AR" if p < 9130 else "AI" if p < 9115 else "SG"
        if 9200 <= p <= 9299:
            return "TG" if p < 9250 else "SG"
        if 9300 <= p <= 9399:
            return "SG"
        if 9400 <= p <= 9499:
            return "SG" if p < 9450 else "AR"
        if 9500 <= p <= 9599:
            return "TG" if p < 9560 else "SG"
        if 9600 <= p <= 9699:
            return "SG"
        if 9700 <= p <= 9799:
            return "SG"
        if 9800 <= p <= 9899:
            return "SG"
        return None
