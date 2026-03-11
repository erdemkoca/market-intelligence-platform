import logging
import re
from dataclasses import dataclass, field

import httpx

from src.config import settings

logger = logging.getLogger(__name__)

# Regex pattern for target trades (DE/FR/IT)
TRADE_NAME_PATTERN = (
    r"(maler|malerei|gipser|gipserei|fassade|fassadenbau|verputz|verputzerei"
    r"|anstrich|stuckateur|stuckaturen|tapezier"
    r"|peinture|pl[âa]tr|façade|facciata|pittore|gessator|pittura|gessatura)"
)

# SPARQL query to fetch all Maler/Gipser/Fassaden companies with full details
SPARQL_QUERY_TRADES = """
SELECT DISTINCT
    ?company ?name ?legalName ?description ?identifierUri ?municipality ?legalFormUri
WHERE {{
    ?company a <https://schema.ld.admin.ch/ZefixOrganisation> ;
             <http://schema.org/name> ?name .

    FILTER(REGEX(?name, "{pattern}", "i"))

    OPTIONAL {{ ?company <http://schema.org/legalName> ?legalName }}
    OPTIONAL {{ ?company <http://schema.org/description> ?description }}
    OPTIONAL {{ ?company <http://schema.org/identifier> ?identifierUri }}
    OPTIONAL {{ ?company <https://schema.ld.admin.ch/municipality> ?municipality }}
    OPTIONAL {{ ?company <http://schema.org/additionalType> ?legalFormUri }}
}}
LIMIT {limit}
OFFSET {offset}
"""

SPARQL_ADDRESS_QUERY = """
SELECT ?streetAddress ?postalCode ?addressLocality ?addressRegion
WHERE {{
    <{address_uri}> <http://schema.org/streetAddress> ?streetAddress ;
                     <http://schema.org/postalCode> ?postalCode ;
                     <http://schema.org/addressLocality> ?addressLocality ;
                     <http://schema.org/addressRegion> ?addressRegion .
}}
LIMIT 1
"""

SPARQL_COUNT_QUERY = """
SELECT (COUNT(DISTINCT ?company) AS ?total)
WHERE {{
    ?company a <https://schema.ld.admin.ch/ZefixOrganisation> ;
             <http://schema.org/name> ?name .
    FILTER(REGEX(?name, "{pattern}", "i"))
}}
"""


@dataclass
class ZefixCompanyResult:
    name: str
    uid: str | None = None
    chid: str | None = None
    legal_seat: str | None = None
    canton: str | None = None
    legal_form: str | None = None
    status: str = "ACTIVE"
    purpose: str | None = None
    address: dict | None = None
    zefix_id: str | None = None
    municipality_id: str | None = None
    raw: dict = field(default_factory=dict)


class ZefixClient:
    """Client for Swiss company data via LINDAS SPARQL endpoint (Zefix Linked Data)."""

    def __init__(self):
        self.sparql_url = settings.lindas_sparql_url
        self.delay = settings.lindas_request_delay
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=120.0,
                headers={
                    "Accept": "application/sparql-results+json",
                    "User-Agent": "BaunexMarketIntelligence/1.0",
                },
            )
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def _execute_sparql(self, query: str) -> dict:
        """Execute a SPARQL query against LINDAS endpoint."""
        client = await self._get_client()
        response = await client.get(self.sparql_url, params={"query": query})
        response.raise_for_status()
        return response.json()

    async def count_trade_companies(self) -> int:
        """Count total companies matching target trades."""
        query = SPARQL_COUNT_QUERY.format(pattern=TRADE_NAME_PATTERN)
        data = await self._execute_sparql(query)
        bindings = data.get("results", {}).get("bindings", [])
        if bindings:
            return int(bindings[0]["total"]["value"])
        return 0

    async def fetch_trade_companies(self, batch_size: int = 2000) -> list[ZefixCompanyResult]:
        """Fetch all target trade companies from LINDAS, with pagination."""
        total = await self.count_trade_companies()
        logger.info(f"LINDAS: {total} trade companies found, fetching in batches of {batch_size}...")

        all_companies: dict[str, ZefixCompanyResult] = {}
        offset = 0

        while offset < total + batch_size:
            query = SPARQL_QUERY_TRADES.format(
                pattern=TRADE_NAME_PATTERN,
                limit=batch_size,
                offset=offset,
            )

            try:
                data = await self._execute_sparql(query)
                bindings = data.get("results", {}).get("bindings", [])

                if not bindings:
                    break

                for binding in bindings:
                    result = self._parse_binding(binding)
                    if result and result.zefix_id and result.zefix_id not in all_companies:
                        all_companies[result.zefix_id] = result
                    elif result and result.zefix_id and result.zefix_id in all_companies:
                        # Merge additional identifiers
                        self._merge_identifiers(all_companies[result.zefix_id], binding)

                logger.info(
                    f"LINDAS batch: offset={offset}, rows={len(bindings)}, "
                    f"unique companies so far={len(all_companies)}"
                )

                if len(bindings) < batch_size:
                    break

                offset += batch_size

            except httpx.HTTPStatusError as e:
                logger.error(f"LINDAS SPARQL error: {e.response.status_code} - {e.response.text[:500]}")
                break
            except httpx.RequestError as e:
                logger.error(f"LINDAS request error: {e}")
                break

        logger.info(f"LINDAS fetch complete: {len(all_companies)} unique companies")
        return list(all_companies.values())

    async def fetch_address(self, company_uri: str) -> dict | None:
        """Fetch address details for a company."""
        address_uri = f"{company_uri}/address"
        query = SPARQL_ADDRESS_QUERY.format(address_uri=address_uri)

        try:
            data = await self._execute_sparql(query)
            bindings = data.get("results", {}).get("bindings", [])
            if bindings:
                b = bindings[0]
                return {
                    "street": b.get("streetAddress", {}).get("value"),
                    "zip_code": b.get("postalCode", {}).get("value"),
                    "city": b.get("addressLocality", {}).get("value"),
                    "canton": b.get("addressRegion", {}).get("value"),
                }
        except Exception as e:
            logger.warning(f"Failed to fetch address for {company_uri}: {e}")

        return None

    async def fetch_addresses_batch(self, company_uris: list[str], batch_size: int = 50) -> dict[str, dict]:
        """Fetch addresses for multiple companies using a single SPARQL query."""
        addresses: dict[str, dict] = {}

        for i in range(0, len(company_uris), batch_size):
            batch = company_uris[i:i + batch_size]
            values = " ".join(f"<{uri}/address>" for uri in batch)

            query = f"""
            SELECT ?addr ?streetAddress ?postalCode ?addressLocality ?addressRegion
            WHERE {{
                VALUES ?addr {{ {values} }}
                ?addr <http://schema.org/streetAddress> ?streetAddress ;
                      <http://schema.org/postalCode> ?postalCode ;
                      <http://schema.org/addressLocality> ?addressLocality ;
                      <http://schema.org/addressRegion> ?addressRegion .
            }}
            """

            try:
                data = await self._execute_sparql(query)
                for b in data.get("results", {}).get("bindings", []):
                    addr_uri = b["addr"]["value"]
                    # Extract company URI from address URI (remove /address suffix)
                    company_uri = addr_uri.rsplit("/address", 1)[0]
                    addresses[company_uri] = {
                        "street": b.get("streetAddress", {}).get("value"),
                        "zip_code": b.get("postalCode", {}).get("value"),
                        "city": b.get("addressLocality", {}).get("value"),
                        "canton": b.get("addressRegion", {}).get("value"),
                    }

                logger.info(f"Fetched addresses batch {i // batch_size + 1}: {len(addresses)} total")

            except Exception as e:
                logger.warning(f"Address batch fetch failed: {e}")

        return addresses

    def _parse_binding(self, binding: dict) -> ZefixCompanyResult | None:
        """Parse a SPARQL result binding into a ZefixCompanyResult."""
        company_uri = binding.get("company", {}).get("value", "")
        name = binding.get("name", {}).get("value", "")

        if not name or not company_uri:
            return None

        # Extract zefix ID from URI: https://register.ld.admin.ch/zefix/company/12345
        zefix_id = company_uri.rsplit("/", 1)[-1] if "/zefix/company/" in company_uri else None

        # Extract UID and CHID from identifier URI
        uid = None
        chid = None
        identifier_uri = binding.get("identifierUri", {}).get("value", "")
        if "/UID/" in identifier_uri:
            raw_uid = identifier_uri.rsplit("/UID/", 1)[-1]
            uid = self._format_uid(raw_uid)
        elif "/CHID/" in identifier_uri:
            chid = identifier_uri.rsplit("/CHID/", 1)[-1]

        # Extract legal form from URI
        legal_form = None
        legal_form_uri = binding.get("legalFormUri", {}).get("value", "")
        if legal_form_uri:
            legal_form = self._map_legal_form_uri(legal_form_uri)

        # Extract municipality ID
        municipality_id = binding.get("municipality", {}).get("value")

        return ZefixCompanyResult(
            name=name,
            uid=uid,
            chid=chid,
            legal_form=legal_form,
            purpose=binding.get("description", {}).get("value"),
            zefix_id=zefix_id,
            municipality_id=municipality_id,
            raw={
                "company_uri": company_uri,
                "name": name,
                "legalName": binding.get("legalName", {}).get("value"),
                "description": binding.get("description", {}).get("value"),
                "identifier": identifier_uri,
                "municipality": municipality_id,
                "legalForm": legal_form_uri,
            },
        )

    def _merge_identifiers(self, existing: ZefixCompanyResult, binding: dict):
        """Merge additional identifiers from duplicate SPARQL rows."""
        identifier_uri = binding.get("identifierUri", {}).get("value", "")
        if "/UID/" in identifier_uri and not existing.uid:
            raw_uid = identifier_uri.rsplit("/UID/", 1)[-1]
            existing.uid = self._format_uid(raw_uid)
        elif "/CHID/" in identifier_uri and not existing.chid:
            existing.chid = identifier_uri.rsplit("/CHID/", 1)[-1]

    @staticmethod
    def _format_uid(raw: str) -> str:
        """Convert CHE123456789 to CHE-123.456.789."""
        digits = re.sub(r"[^0-9]", "", raw.replace("CHE", ""))
        if len(digits) == 9:
            return f"CHE-{digits[:3]}.{digits[3:6]}.{digits[6:9]}"
        return raw

    @staticmethod
    def _map_legal_form_uri(uri: str) -> str | None:
        """Map LINDAS legal form URI to human-readable form."""
        # URI pattern: https://register.ld.admin.ch/zefix/legalForm/0106
        code = uri.rsplit("/", 1)[-1] if "/" in uri else uri
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
            "0111": "Kommanditaktiengesellschaft",
            "0113": "Institut des öffentlichen Rechts",
            "0114": "Staatlich anerkannte SICAV",
            "0117": "Investmentgesellschaft mit festem Kapital",
            "0118": "Investmentgesellschaft mit variablem Kapital",
            "0151": "Ausländische Rechtsform",
        }
        return forms.get(code, code)
