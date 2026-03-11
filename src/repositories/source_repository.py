from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.source import MiIngestionJob


class SourceRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_recent_jobs(self, limit: int = 20) -> list[MiIngestionJob]:
        result = await self.session.execute(
            select(MiIngestionJob)
            .order_by(MiIngestionJob.started_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_job_by_id(self, job_id: str) -> MiIngestionJob | None:
        result = await self.session.execute(
            select(MiIngestionJob).where(MiIngestionJob.id == job_id)
        )
        return result.scalar_one_or_none()
