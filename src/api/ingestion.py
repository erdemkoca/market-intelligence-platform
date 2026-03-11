import logging
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.repositories.source_repository import SourceRepository
from src.services.enrichment.website_scraper import WebsiteScraper
from src.services.ingestion.localch_ingestion import LocalChIngestionService
from src.services.ingestion.searchch_ingestion import SearchChIngestionService
from src.services.ingestion.zefix_ingestion import ZefixIngestionService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ingestion", tags=["ingestion"])


class IngestionJobOut(BaseModel):
    id: str
    source_type: str
    status: str
    started_at: datetime
    completed_at: datetime | None = None
    records_fetched: int = 0
    records_created: int = 0
    records_updated: int = 0
    records_skipped: int = 0
    error_message: str | None = None

    model_config = {"from_attributes": True}


class IngestionTriggerResponse(BaseModel):
    message: str
    job_id: str | None = None


async def _run_zefix_ingestion(db: AsyncSession):
    service = ZefixIngestionService(db)
    job_id = await service.ingest()
    await db.commit()
    logger.info(f"Zefix ingestion completed: {job_id}")


@router.post("/zefix", response_model=IngestionTriggerResponse)
async def trigger_zefix_ingestion(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Trigger a manual Zefix ingestion job."""
    service = ZefixIngestionService(db)
    job_id = await service.ingest()
    return IngestionTriggerResponse(message="Zefix ingestion completed", job_id=job_id)


@router.post("/localch", response_model=IngestionTriggerResponse)
async def trigger_localch_ingestion(
    enrich_details: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """Trigger a local.ch ingestion job. Set enrich_details=true to also scrape detail pages (slower)."""
    service = LocalChIngestionService(db)
    job_id = await service.ingest(enrich_details=enrich_details)
    return IngestionTriggerResponse(message="local.ch ingestion completed", job_id=job_id)


@router.post("/searchch", response_model=IngestionTriggerResponse)
async def trigger_searchch_ingestion(
    db: AsyncSession = Depends(get_db),
):
    """Trigger a search.ch ingestion job."""
    service = SearchChIngestionService(db)
    job_id = await service.ingest()
    return IngestionTriggerResponse(message="search.ch ingestion completed", job_id=job_id)


@router.post("/enrich-websites", response_model=dict)
async def trigger_website_enrichment(
    batch_size: int = 100,
    db: AsyncSession = Depends(get_db),
):
    """Scrape company websites to extract email, phone, and contact form info."""
    scraper = WebsiteScraper(db)
    try:
        stats = await scraper.enrich_all(batch_size=batch_size)
        return {"message": "Website enrichment completed", **stats}
    finally:
        await scraper.close()


@router.get("/jobs", response_model=list[IngestionJobOut])
async def list_ingestion_jobs(
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    repo = SourceRepository(db)
    jobs = await repo.get_recent_jobs(limit=limit)
    return [IngestionJobOut.model_validate(job) for job in jobs]
