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


@router.post("/upload-searchch", response_model=IngestionTriggerResponse)
async def upload_searchch_data(
    companies: list[dict],
    db: AsyncSession = Depends(get_db),
):
    """Upload pre-scraped search.ch data (from local machine) for import with dedup."""
    import uuid
    from datetime import date, datetime
    from src.models.company import MiCompany, MiCompanyLocation
    from src.models.enrichment import MiEnrichment
    from src.models.source import MiIngestionJob, MiSourceRecord
    from src.services.classification.industry_classifier import IndustryClassifier
    from src.services.matching.deduplication import DeduplicationService

    job_id = f"searchch-upload-{date.today()}-{uuid.uuid4().hex[:8]}"
    job = MiIngestionJob(id=job_id, source_type="SEARCH_CH", status="RUNNING")
    db.add(job)
    await db.flush()

    dedup = DeduplicationService(db)
    classifier = IndustryClassifier()
    job.records_fetched = len(companies)

    for c in companies:
        name = c.get("name", "")
        if not name or len(name) < 3:
            job.records_skipped += 1
            continue

        existing = await dedup.find_match(
            name=name,
            zip_code=c.get("zip_code"),
            phone=c.get("phone"),
        )

        if existing:
            existing.updated_at = datetime.utcnow()
            company_id = existing.id
            job.records_updated += 1
        else:
            classification = classifier.classify(name, None)
            canton = c.get("canton")
            french = {"GE", "VD", "NE", "JU"}
            italian = {"TI"}
            lang = "fr" if canton in french else "it" if canton in italian else "de"

            company = MiCompany(
                name=name, legal_name=name, status="ACTIVE",
                industry=classification.industry,
                industry_detail=classification.industry_detail,
                noga_code=classification.noga_code,
                language_region=lang,
            )
            db.add(company)
            await db.flush()
            company_id = company.id

            if c.get("zip_code") or c.get("city"):
                db.add(MiCompanyLocation(
                    company_id=company_id, location_type="HQ",
                    street=c.get("street"), zip_code=c.get("zip_code"),
                    city=c.get("city"), canton=canton,
                ))
            job.records_created += 1

        # Upsert enrichment
        if c.get("phone") or c.get("website"):
            from sqlalchemy import select
            result = await db.execute(
                select(MiEnrichment).where(MiEnrichment.company_id == company_id)
            )
            enrichment = result.scalar_one_or_none()
            if enrichment:
                if not enrichment.phone and c.get("phone"):
                    enrichment.phone = c["phone"]
                if not enrichment.website and c.get("website"):
                    enrichment.website = c["website"]
            else:
                db.add(MiEnrichment(
                    company_id=company_id,
                    phone=c.get("phone"), website=c.get("website"),
                    enrichment_source="SEARCH_CH",
                    last_enriched_at=datetime.utcnow(),
                ))

        db.add(MiSourceRecord(
            company_id=company_id, source_type="SEARCH_CH",
            source_url=c.get("detail_url"),
            raw_data=c, ingestion_job_id=job_id,
        ))

    job.status = "COMPLETED"
    job.completed_at = datetime.utcnow()
    logger.info(f"Job {job_id}: {job.records_created} created, {job.records_updated} updated, {job.records_skipped} skipped")
    return IngestionTriggerResponse(message=f"Imported {job.records_created} new, {job.records_updated} updated", job_id=job_id)


@router.get("/jobs", response_model=list[IngestionJobOut])
async def list_ingestion_jobs(
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    repo = SourceRepository(db)
    jobs = await repo.get_recent_jobs(limit=limit)
    return [IngestionJobOut.model_validate(job) for job in jobs]
