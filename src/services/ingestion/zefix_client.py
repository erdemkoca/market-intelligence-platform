import asyncio
import logging
from dataclasses import dataclass

import httpx

from src.config import settings

logger = logging.getLogger(__name__)

# Search terms for Maler/Gipser/Fassaden trades
TRADE_SEARCH_TERMS = [
    "Maler",
    "Malerei",
    "Gipser",
    "Gipserei",
    "Fassade",
    "Fassadenbau",
    "Verputz",
    "Verputzerei",
    "Anstrich",
    "Stuckateur",
    "Stuckaturen",
    "peinture",
    "plâtrerie",
    "façade",
    "pittore",
    "gessatore",
    "facciata",
]

# NOGA codes for target trades
TARGET_NOGA_CODES = [
    "43.31",   # Gipserei und Verputzerei
    "43.34",   # Malerei und Glaserei
]


@dataclass
class ZefixCompanyResult:
    name: str
    uid: str | None
    chid: str | None
    legal_seat: str | None
    canton: str | None
    legal_form: str | None
    status: str | None
    purpose: str | None
    address: dict | None
    raw: dict


class ZefixClient:
    """Client for the Zefix REST API (Swiss Commercial Register)."""

    def __init__(self):
        self.base_url = settings.zefix_base_url
        self.delay = settings.zefix_request_delay
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=30.0,
                headers={
                    "Accept": "application/json",
                    "User-Agent": "BaunexMarketIntelligence/1.0",
                },
            )
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def search_by_name(self, name: str, active_only: bool = True, max_entries: int = 200) -> list[dict]:
        """Search companies by name on Zefix."""
        client = await self._get_client()
        results = []
        offset = 0

        while True:
            try:
                payload = {
                    "name": name,
                    "activeOnly": active_only,
                    "maxEntries": max_entries,
                    "offset": offset,
                }
                response = await client.post("/company/search", json=payload)

                if response.status_code == 429:
                    logger.warning("Zefix rate limit hit, waiting 10s...")
                    await asyncio.sleep(10)
                    continue

                response.raise_for_status()
                data = response.json()

                if not data:
                    break

                results.extend(data)
                logger.info(f"Zefix search '{name}': got {len(data)} results (offset={offset})")

                if len(data) < max_entries:
                    break

                offset += max_entries
                await asyncio.sleep(self.delay)

            except httpx.HTTPStatusError as e:
                logger.error(f"Zefix API error for '{name}': {e.response.status_code} - {e.response.text}")
                break
            except httpx.RequestError as e:
                logger.error(f"Zefix request error for '{name}': {e}")
                break

        return results

    async def get_by_uid(self, uid: str) -> dict | None:
        """Get company details by UID."""
        client = await self._get_client()
        try:
            response = await client.get(f"/company/uid/{uid}")
            response.raise_for_status()
            data = response.json()
            return data[0] if isinstance(data, list) and data else data
        except httpx.HTTPStatusError as e:
            logger.error(f"Zefix UID lookup error for '{uid}': {e.response.status_code}")
            return None

    async def search_all_trades(self, active_only: bool = True) -> list[dict]:
        """Search for all target trade companies across all search terms."""
        all_results: dict[str, dict] = {}

        for term in TRADE_SEARCH_TERMS:
            logger.info(f"Searching Zefix for: {term}")
            results = await self.search_by_name(term, active_only=active_only)

            for company in results:
                uid = company.get("uid")
                if uid and uid not in all_results:
                    all_results[uid] = company

            await asyncio.sleep(self.delay)

        logger.info(f"Zefix search complete: {len(all_results)} unique companies found")
        return list(all_results.values())

    def parse_company(self, raw: dict) -> ZefixCompanyResult:
        """Parse raw Zefix API response into structured result."""
        address = raw.get("address", {}) or {}
        return ZefixCompanyResult(
            name=raw.get("name", ""),
            uid=raw.get("uid"),
            chid=raw.get("chid"),
            legal_seat=raw.get("legalSeat"),
            canton=raw.get("canton"),
            legal_form=self._map_legal_form(raw.get("legalForm")),
            status=self._map_status(raw.get("status")),
            purpose=raw.get("purpose"),
            address=address if address else None,
            raw=raw,
        )

    @staticmethod
    def _map_legal_form(code: str | None) -> str | None:
        forms = {
            "0106": "AG",
            "0107": "GmbH",
            "0101": "Einzelfirma",
            "0108": "Genossenschaft",
            "0109": "Verein",
            "0110": "Stiftung",
            "0103": "Kollektivgesellschaft",
            "0104": "Kommanditgesellschaft",
            "0302": "Zweigniederlassung",
        }
        return forms.get(code or "", code)

    @staticmethod
    def _map_status(status: str | None) -> str:
        if not status:
            return "UNKNOWN"
        status_map = {
            "ACTIVE": "ACTIVE",
            "CANCELLED": "LIQUIDATED",
            "BEING_CANCELLED": "LIQUIDATED",
        }
        return status_map.get(status.upper(), "UNKNOWN")
