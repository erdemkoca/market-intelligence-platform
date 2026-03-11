import logging
import re

from sqlalchemy import func, select, and_, or_, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.company import MiCompany, MiCompanyLocation

logger = logging.getLogger(__name__)


class DeduplicationService:
    """Identifies and merges duplicate company records using multi-level matching."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_match(
        self,
        name: str,
        zip_code: str | None = None,
        phone: str | None = None,
        uid: str | None = None,
    ) -> MiCompany | None:
        """Find an existing company matching the given data.

        Matching priority:
        1. UID (exact) — most reliable
        2. Phone number (normalized)
        3. Name + PLZ (fuzzy name, exact zip) — threshold 0.6
        4. Name + City (fuzzy name, exact city) — threshold 0.7
        """
        # 1. Match by UID
        if uid:
            normalized_uid = self._normalize_uid(uid)
            if normalized_uid:
                result = await self.session.execute(
                    select(MiCompany).where(MiCompany.uid == normalized_uid)
                )
                match = result.scalar_one_or_none()
                if match:
                    logger.debug(f"UID match: '{name}' → existing '{match.name}' (UID: {normalized_uid})")
                    return match

        # 2. Match by phone number
        if phone:
            normalized_phone = self._normalize_phone(phone)
            if normalized_phone:
                from src.models.enrichment import MiEnrichment
                result = await self.session.execute(
                    select(MiCompany)
                    .join(MiEnrichment, MiCompany.id == MiEnrichment.company_id)
                    .where(MiEnrichment.phone == normalized_phone)
                )
                match = result.scalar_one_or_none()
                if match:
                    logger.debug(f"Phone match: '{name}' → existing '{match.name}'")
                    return match

        # 3. Match by name + PLZ (fuzzy name similarity > 0.6)
        if zip_code:
            result = await self.session.execute(
                select(MiCompany, func.similarity(MiCompany.name, name).label("sim"))
                .join(MiCompanyLocation, MiCompany.id == MiCompanyLocation.company_id)
                .where(
                    and_(
                        MiCompanyLocation.zip_code == zip_code,
                        func.similarity(MiCompany.name, name) > 0.6,
                    )
                )
                .order_by(func.similarity(MiCompany.name, name).desc())
                .limit(1)
            )
            row = result.first()
            if row:
                match = row[0]
                sim = row[1]
                logger.debug(f"Name+PLZ match: '{name}' → existing '{match.name}' (sim={sim:.2f}, PLZ={zip_code})")
                return match

        # 4. Match by cleaned name (exact) — catches "Müller Malerei" vs "Müller Malerei GmbH"
        cleaned = self._clean_company_name(name)
        if cleaned and len(cleaned) > 5:
            result = await self.session.execute(
                select(MiCompany, func.similarity(MiCompany.name, name).label("sim"))
                .where(func.similarity(MiCompany.name, name) > 0.75)
                .order_by(func.similarity(MiCompany.name, name).desc())
                .limit(1)
            )
            row = result.first()
            if row:
                match = row[0]
                sim = row[1]
                logger.debug(f"Fuzzy name match: '{name}' → existing '{match.name}' (sim={sim:.2f})")
                return match

        return None

    async def find_duplicates_by_uid(self) -> list[tuple[str, int]]:
        """Find companies with the same UID."""
        result = await self.session.execute(
            select(MiCompany.uid, func.count(MiCompany.id))
            .where(MiCompany.uid.isnot(None))
            .group_by(MiCompany.uid)
            .having(func.count(MiCompany.id) > 1)
        )
        return [(row[0], row[1]) for row in result.all()]

    async def find_similar_by_name(self, name: str, threshold: float = 0.4) -> list[MiCompany]:
        """Find companies with similar names using trigram similarity."""
        result = await self.session.execute(
            select(MiCompany)
            .where(func.similarity(MiCompany.name, name) > threshold)
            .order_by(func.similarity(MiCompany.name, name).desc())
            .limit(10)
        )
        return list(result.scalars().all())

    @staticmethod
    def _normalize_uid(uid: str) -> str | None:
        """Normalize UID to CHE-XXX.XXX.XXX format."""
        digits = re.sub(r"[^0-9]", "", uid.replace("CHE", ""))
        if len(digits) == 9:
            return f"CHE-{digits[:3]}.{digits[3:6]}.{digits[6:9]}"
        return None

    @staticmethod
    def _normalize_phone(phone: str) -> str | None:
        """Normalize phone to +41XXXXXXXXX format."""
        digits = re.sub(r"[^0-9+]", "", phone)
        if digits.startswith("0") and len(digits) == 10:
            return f"+41{digits[1:]}"
        if digits.startswith("+41") and len(digits) == 12:
            return digits
        if digits.startswith("0041") and len(digits) == 13:
            return f"+41{digits[4:]}"
        return digits if len(digits) >= 10 else None

    @staticmethod
    def _clean_company_name(name: str) -> str:
        """Remove common suffixes for comparison."""
        cleaned = name.lower().strip()
        # Remove legal form suffixes
        for suffix in [
            r"\s+(ag|gmbh|sagl|sa|sàrl|s\.a\.|llc|inc)\b",
            r"\s+in\s+liquidation\b",
            r"\s+in\s+liq\.?\b",
        ]:
            cleaned = re.sub(suffix, "", cleaned, flags=re.IGNORECASE)
        return cleaned.strip()
