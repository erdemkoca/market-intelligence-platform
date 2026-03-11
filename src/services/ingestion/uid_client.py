import logging

import httpx

logger = logging.getLogger(__name__)

UID_SEARCH_URL = "https://www.uid.admin.ch/Search.aspx"
UID_API_URL = "https://www.uid.admin.ch"


class UidClient:
    """Client for the Swiss UID Register.

    The UID register provides company identification data.
    Note: The UID register has limited API access; this client
    uses the available search endpoints.
    """

    def __init__(self):
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=30.0,
                headers={"User-Agent": "BaunexMarketIntelligence/1.0"},
            )
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def lookup_uid(self, uid: str) -> dict | None:
        """Look up a company by UID number.

        The UID format is CHE-xxx.xxx.xxx
        """
        client = await self._get_client()
        try:
            # UID SOAP/REST API endpoint
            response = await client.get(
                f"{UID_API_URL}/Search/SearchByUID",
                params={"uidOrganisationId": uid.replace("-", "").replace(".", "")},
            )
            if response.status_code == 200:
                return {"uid": uid, "raw": response.text}
            logger.warning(f"UID lookup for {uid} returned status {response.status_code}")
            return None
        except httpx.RequestError as e:
            logger.error(f"UID lookup error for {uid}: {e}")
            return None
