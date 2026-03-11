import asyncio
import logging
import re
from dataclasses import dataclass, field

import httpx

logger = logging.getLogger(__name__)

# Search terms for our target trades
SEARCH_TERMS = ["maler", "gipser", "fassadenbau"]

RESULTS_PER_PAGE = 15


@dataclass
class LocalChCompany:
    name: str
    street: str | None = None
    zip_code: str | None = None
    city: str | None = None
    canton: str | None = None
    phone: str | None = None
    email: str | None = None
    website: str | None = None
    categories: list[str] = field(default_factory=list)
    detail_url: str | None = None
    source_url: str | None = None
    raw: dict = field(default_factory=dict)


class LocalChClient:
    """Scrapes company data from local.ch search results."""

    BASE_URL = "https://www.local.ch"

    def __init__(self, delay: float = 2.0, max_pages_per_term: int = 50):
        self.delay = delay
        self.max_pages_per_term = max_pages_per_term
        self._client: httpx.AsyncClient | None = None

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

    async def fetch_all_trades(self) -> list[LocalChCompany]:
        """Fetch companies for all target trade search terms."""
        all_companies: dict[str, LocalChCompany] = {}

        for term in SEARCH_TERMS:
            logger.info(f"local.ch: scraping search term '{term}'...")
            companies = await self._fetch_search_term(term)

            for company in companies:
                # Deduplicate by name+zip within this scrape
                key = f"{company.name.lower().strip()}|{company.zip_code or ''}"
                if key not in all_companies:
                    all_companies[key] = company

            logger.info(
                f"local.ch: '{term}' yielded {len(companies)} results, "
                f"total unique so far: {len(all_companies)}"
            )

        logger.info(f"local.ch: total unique companies: {len(all_companies)}")
        return list(all_companies.values())

    async def _fetch_search_term(self, term: str) -> list[LocalChCompany]:
        """Fetch all pages for a single search term."""
        companies = []
        page = 1

        while page <= self.max_pages_per_term:
            url = f"{self.BASE_URL}/de/s/{term}?page={page}"
            try:
                client = await self._get_client()
                response = await client.get(url)

                if response.status_code == 404:
                    break
                response.raise_for_status()

                html = response.text
                page_companies = self._parse_search_page(html, url)

                if not page_companies:
                    break

                companies.extend(page_companies)
                logger.info(f"local.ch: '{term}' page {page}: {len(page_companies)} results")

                # Rate limiting
                await asyncio.sleep(self.delay)
                page += 1

            except httpx.HTTPStatusError as e:
                logger.warning(f"local.ch: HTTP {e.response.status_code} on page {page} for '{term}'")
                break
            except httpx.RequestError as e:
                logger.warning(f"local.ch: request error on page {page} for '{term}': {e}")
                break

        return companies

    async def enrich_from_detail(self, company: LocalChCompany) -> LocalChCompany:
        """Fetch additional details (email, website) from a company's detail page."""
        if not company.detail_url:
            return company

        try:
            client = await self._get_client()
            response = await client.get(company.detail_url)
            response.raise_for_status()
            html = response.text

            # Extract email
            email_match = re.search(
                r'href="mailto:([^"]+)"', html
            )
            if email_match:
                company.email = email_match.group(1)

            # Extract website
            website_match = re.search(
                r'(?:website|webpage|homepage)[^"]*"([^"]*(?:www\.[^"]+|https?://[^"]+))',
                html, re.IGNORECASE,
            )
            if not website_match:
                # Try common pattern: external link that's not local.ch
                for match in re.finditer(r'href="(https?://(?!www\.local\.ch)[^"]+)"', html):
                    url = match.group(1)
                    if not any(x in url for x in ["google.", "facebook.", "instagram.", "twitter.", "youtube."]):
                        company.website = url
                        break

            # Extract phone from tel: links
            phone_match = re.search(r'href="tel:([^"]+)"', html)
            if phone_match:
                company.phone = phone_match.group(1)

            await asyncio.sleep(self.delay)

        except Exception as e:
            logger.warning(f"local.ch: detail fetch failed for {company.name}: {e}")

        return company

    def _parse_search_page(self, html: str, source_url: str) -> list[LocalChCompany]:
        """Parse company listings from a search results HTML page."""
        companies = []

        # Extract listing blocks — local.ch uses structured patterns
        # Find all detail page links with company info
        listing_pattern = re.compile(
            r'<a[^>]*href="(/de/d/[^"]+)"[^>]*>.*?</a>',
            re.DOTALL,
        )

        # More robust: find detail URLs and nearby address info
        detail_urls = re.findall(r'href="(/de/d/[^"]+)"', html)
        seen_urls = set()
        unique_detail_urls = []
        for url in detail_urls:
            if url not in seen_urls:
                seen_urls.add(url)
                unique_detail_urls.append(url)

        # Parse address blocks: look for patterns like "Strasse 1, 8000 Zürich"
        # and company names near detail URLs
        address_blocks = re.findall(
            r'(/de/d/([^/]+)/(\d{4})/[^/]+/([^"]+))"',
            html,
        )

        for url_path, city_slug, plz, name_slug in address_blocks:
            full_url = f"{self.BASE_URL}{url_path}"
            if full_url in [c.detail_url for c in companies]:
                continue

            # Clean up name from slug: "maler-walser-ag-q1_88oWy5IHOCzhJL4rK7g" → "Maler Walser AG"
            name = self._slug_to_name(name_slug)
            if not name or len(name) < 3:
                continue

            city = city_slug.replace("-", " ").title()

            company = LocalChCompany(
                name=name,
                zip_code=plz,
                city=city,
                detail_url=full_url,
                source_url=source_url,
                raw={"url_path": url_path, "city_slug": city_slug, "name_slug": name_slug},
            )
            companies.append(company)

        # Also try to extract names directly from heading patterns
        name_pattern = re.compile(
            r'<h\d[^>]*>\s*<a[^>]*href="/de/d/[^"]*"[^>]*>\s*([^<]+)\s*</a>\s*</h\d>',
            re.DOTALL,
        )
        name_matches = name_pattern.findall(html)

        # Match extracted names to existing companies (by order)
        for i, real_name in enumerate(name_matches):
            real_name = real_name.strip()
            if i < len(companies) and real_name:
                companies[i].name = real_name

        # Extract street addresses from text near listings
        address_pattern = re.compile(
            r'([A-ZÄÖÜ][a-zäöüéèê\-]+(?:strasse|weg|gasse|platz|ring|allee|str\.)[\s\d]+\w*)\s*,?\s*(\d{4})\s+([A-ZÄÖÜ][a-zäöüéèê\s\-]+)',
            re.UNICODE,
        )
        street_matches = address_pattern.findall(html)
        for i, (street, plz, city) in enumerate(street_matches):
            if i < len(companies):
                companies[i].street = street.strip()
                companies[i].zip_code = plz
                companies[i].city = city.strip()

        return companies

    @staticmethod
    def _slug_to_name(slug: str) -> str:
        """Convert URL slug to approximate company name."""
        # Remove the ID suffix (last part after the last dash that contains non-alpha chars)
        parts = slug.rsplit("-", 1)
        if len(parts) == 2 and re.search(r'[A-Z0-9_]', parts[1]):
            slug = parts[0]

        # Replace dashes with spaces and title-case
        name = slug.replace("-", " ").strip()

        # Fix common abbreviations
        name = re.sub(r'\b(ag|gmbh|sa|sarl)\b', lambda m: m.group().upper(), name, flags=re.IGNORECASE)
        name = re.sub(r'\b(sàrl)\b', 'Sàrl', name, flags=re.IGNORECASE)

        # Title case but keep abbreviations uppercase
        words = []
        for word in name.split():
            if word.upper() in ("AG", "GMBH", "SA", "SARL", "LLC", "UG"):
                words.append(word.upper())
            else:
                words.append(word.capitalize())

        return " ".join(words)
