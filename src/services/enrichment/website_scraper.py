import asyncio
import logging
import re
from datetime import datetime

import httpx
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.enrichment import MiEnrichment

logger = logging.getLogger(__name__)


class WebsiteScraper:
    """Visits company websites to extract contact information (email, phone, contact form)."""

    def __init__(self, session: AsyncSession, delay: float = 1.0, timeout: float = 10.0):
        self.session = session
        self.delay = delay
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                    "Accept": "text/html,application/xhtml+xml",
                    "Accept-Language": "de-CH,de;q=0.9",
                },
                follow_redirects=True,
                verify=False,
            )
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def enrich_all(self, batch_size: int = 100) -> dict:
        """Enrich all companies that have a website but missing email/phone."""
        result = await self.session.execute(
            select(MiEnrichment)
            .where(
                and_(
                    MiEnrichment.website.isnot(None),
                    MiEnrichment.email_general.is_(None),
                )
            )
            .limit(batch_size)
        )
        enrichments = list(result.scalars().all())

        stats = {"total": len(enrichments), "enriched": 0, "failed": 0}
        logger.info(f"Website scraper: {len(enrichments)} companies to enrich")

        for i, enrichment in enumerate(enrichments):
            try:
                updated = await self._scrape_website(enrichment)
                if updated:
                    stats["enriched"] += 1
                else:
                    stats["failed"] += 1
            except Exception as e:
                logger.debug(f"Website scrape failed for {enrichment.website}: {e}")
                stats["failed"] += 1

            if (i + 1) % 50 == 0:
                logger.info(f"Website scraper: {i + 1}/{len(enrichments)} processed")

            await asyncio.sleep(self.delay)

        logger.info(f"Website scraper done: {stats}")
        return stats

    async def _scrape_website(self, enrichment: MiEnrichment) -> bool:
        """Scrape a single website for contact info."""
        website = enrichment.website
        if not website:
            return False

        # Normalize URL
        if not website.startswith("http"):
            website = f"https://{website}"

        updated = False
        pages_to_try = [website]

        # Also try common contact pages
        base = website.rstrip("/")
        for path in ["/kontakt", "/contact", "/impressum", "/about", "/ueber-uns"]:
            pages_to_try.append(f"{base}{path}")

        client = await self._get_client()

        for url in pages_to_try:
            try:
                response = await client.get(url)
                if response.status_code != 200:
                    continue

                html = response.text

                # Extract emails
                if not enrichment.email_general:
                    email = self._extract_email(html)
                    if email:
                        enrichment.email_general = email
                        updated = True

                # Extract phone
                if not enrichment.phone:
                    phone = self._extract_phone(html)
                    if phone:
                        enrichment.phone = phone
                        updated = True

                # Check for contact form
                if self._has_contact_form(html):
                    enrichment.has_contact_form = True
                    updated = True

                # If we found email, we're done
                if enrichment.email_general and enrichment.phone:
                    break

            except Exception:
                continue

        if updated:
            enrichment.last_enriched_at = datetime.utcnow()
            enrichment.updated_at = datetime.utcnow()

        return updated

    @staticmethod
    def _extract_email(html: str) -> str | None:
        """Extract the most likely business email from HTML."""
        # Find mailto: links first (most reliable)
        mailto_matches = re.findall(r'href="mailto:([^"?]+)"', html, re.IGNORECASE)

        # Also find email patterns in text
        text_matches = re.findall(
            r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}',
            html,
        )

        all_emails = mailto_matches + text_matches

        # Filter out unwanted emails
        filtered = []
        for email in all_emails:
            email = email.lower().strip()
            # Skip tracking/system emails
            if any(x in email for x in [
                "noreply", "no-reply", "mailer-daemon", "postmaster",
                "example.com", "sentry", "analytics", "tracking",
                "wix.com", "squarespace", "wordpress",
            ]):
                continue
            filtered.append(email)

        if not filtered:
            return None

        # Prefer info@, kontakt@, office@ emails
        for prefix in ["info@", "kontakt@", "contact@", "office@", "mail@"]:
            for email in filtered:
                if email.startswith(prefix):
                    return email

        return filtered[0]

    @staticmethod
    def _extract_phone(html: str) -> str | None:
        """Extract Swiss phone number from HTML."""
        # tel: links
        tel_matches = re.findall(r'href="tel:([^"]+)"', html)
        for tel in tel_matches:
            cleaned = re.sub(r"[^0-9+]", "", tel)
            if len(cleaned) >= 10:
                if cleaned.startswith("0") and len(cleaned) == 10:
                    return f"+41{cleaned[1:]}"
                if cleaned.startswith("+41"):
                    return cleaned
                if cleaned.startswith("0041"):
                    return f"+41{cleaned[4:]}"

        # Swiss phone patterns in text
        patterns = [
            r"(\+41\s?\d{2}\s?\d{3}\s?\d{2}\s?\d{2})",
            r"(0\d{2}\s?\d{3}\s?\d{2}\s?\d{2})",
        ]
        for pattern in patterns:
            match = re.search(pattern, html)
            if match:
                cleaned = re.sub(r"[^0-9+]", "", match.group(1))
                if cleaned.startswith("0") and len(cleaned) == 10:
                    return f"+41{cleaned[1:]}"
                if cleaned.startswith("+41"):
                    return cleaned

        return None

    @staticmethod
    def _has_contact_form(html: str) -> bool:
        """Check if page has a contact form."""
        form_indicators = [
            r'<form[^>]*(?:contact|kontakt|anfrage|offerte)',
            r'<input[^>]*name="(?:email|phone|telefon|nachricht|message)"',
            r'<textarea[^>]*name="(?:message|nachricht|bemerkung)"',
            r'(?:Kontaktformular|Contact\s*Form|Anfrage\s*senden)',
        ]
        for pattern in form_indicators:
            if re.search(pattern, html, re.IGNORECASE):
                return True
        return False
