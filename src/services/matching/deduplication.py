import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.company import MiCompany

logger = logging.getLogger(__name__)


class DeduplicationService:
    """Identifies and merges duplicate company records."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_duplicates_by_uid(self) -> list[tuple[int, int, str]]:
        """Find companies with the same UID (should not happen, but safety check)."""
        result = await self.session.execute(
            select(MiCompany.uid, func.count(MiCompany.id))
            .where(MiCompany.uid.isnot(None))
            .group_by(MiCompany.uid)
            .having(func.count(MiCompany.id) > 1)
        )
        return [(row[0], row[1]) for row in result.all()]

    async def find_similar_by_name(self, name: str, threshold: float = 0.4) -> list[MiCompany]:
        """Find companies with similar names using trigram similarity.

        Requires pg_trgm extension.
        """
        result = await self.session.execute(
            select(MiCompany)
            .where(func.similarity(MiCompany.name, name) > threshold)
            .order_by(func.similarity(MiCompany.name, name).desc())
            .limit(10)
        )
        return list(result.scalars().all())
