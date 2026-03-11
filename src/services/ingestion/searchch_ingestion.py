import logging
import uuid
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.company import MiCompany, MiCompanyLocation
from src.models.enrichment import MiEnrichment
from src.models.source import MiIngestionJob, MiSourceRecord
from src.services.classification.industry_classifier import IndustryClassifier
from src.services.ingestion.searchch_client import SearchChClient, SearchChCompany
from src.services.matching.deduplication import DeduplicationService

logger = logging.getLogger(__name__)


class SearchChIngestionService:
    """Ingests company data from search.ch and merges with existing records."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.client = SearchChClient(delay=3.0, max_results_per_term=750)
        self.dedup = DeduplicationService(session)
        self.classifier = IndustryClassifier()

    async def ingest(self) -> str:
        """Run a full search.ch ingestion. Returns job ID."""
        job_id = f"searchch-{date.today()}-{uuid.uuid4().hex[:8]}"
        job = MiIngestionJob(id=job_id, source_type="SEARCH_CH", status="RUNNING")
        self.session.add(job)
        await self.session.flush()

        try:
            companies = await self.client.fetch_all_trades()
            job.records_fetched = len(companies)
            logger.info(f"Job {job_id}: fetched {len(companies)} companies from search.ch")

            for company in companies:
                await self._process_company(company, job_id, job)

            job.status = "COMPLETED"
            job.completed_at = datetime.utcnow()
            logger.info(
                f"Job {job_id} completed: "
                f"{job.records_created} created, {job.records_updated} updated, "
                f"{job.records_skipped} skipped"
            )
        except Exception as e:
            job.status = "FAILED"
            job.error_message = str(e)[:2000]
            job.completed_at = datetime.utcnow()
            logger.error(f"Job {job_id} failed: {e}", exc_info=True)
        finally:
            await self.client.close()

        return job_id

    async def _process_company(self, parsed: SearchChCompany, job_id: str, job: MiIngestionJob):
        if not parsed.name or len(parsed.name) < 3:
            job.records_skipped += 1
            return

        # Try to find existing match
        existing = await self.dedup.find_match(
            name=parsed.name,
            zip_code=parsed.zip_code,
            phone=parsed.phone,
        )

        if existing:
            self._enrich_existing(existing, parsed)
            company_id = existing.id
            job.records_updated += 1
        else:
            company = self._create_company(parsed)
            self.session.add(company)
            await self.session.flush()
            company_id = company.id

            # Add location
            if parsed.zip_code or parsed.city:
                self.session.add(MiCompanyLocation(
                    company_id=company_id,
                    location_type="HQ",
                    street=parsed.street,
                    zip_code=parsed.zip_code,
                    city=parsed.city,
                    canton=parsed.canton,
                ))

            job.records_created += 1

        # Create or update enrichment with contact data
        if parsed.phone or parsed.website or parsed.email:
            await self._upsert_enrichment(company_id, parsed)

        # Store source record
        self.session.add(MiSourceRecord(
            company_id=company_id,
            source_type="SEARCH_CH",
            source_url=parsed.source_url,
            raw_data=parsed.raw,
            ingestion_job_id=job_id,
        ))

    async def _upsert_enrichment(self, company_id: int, parsed: SearchChCompany):
        """Create or update enrichment record with search.ch contact data."""
        result = await self.session.execute(
            select(MiEnrichment).where(MiEnrichment.company_id == company_id)
        )
        enrichment = result.scalar_one_or_none()

        if enrichment:
            # Only fill in missing fields, don't overwrite
            if not enrichment.phone and parsed.phone:
                enrichment.phone = parsed.phone
            if not enrichment.website and parsed.website:
                enrichment.website = parsed.website
            if not enrichment.email_general and parsed.email:
                enrichment.email_general = parsed.email
            enrichment.updated_at = datetime.utcnow()
        else:
            self.session.add(MiEnrichment(
                company_id=company_id,
                phone=parsed.phone,
                website=parsed.website,
                email_general=parsed.email,
                enrichment_source="SEARCH_CH",
                last_enriched_at=datetime.utcnow(),
            ))

    def _create_company(self, parsed: SearchChCompany) -> MiCompany:
        classification = self.classifier.classify(parsed.name, None)
        return MiCompany(
            name=parsed.name,
            legal_name=parsed.name,
            status="ACTIVE",
            industry=classification.industry,
            industry_detail=classification.industry_detail,
            noga_code=classification.noga_code,
            language_region=self._detect_language_region(parsed.canton),
        )

    def _enrich_existing(self, company: MiCompany, parsed: SearchChCompany):
        """Enrich existing company with search.ch data."""
        company.updated_at = datetime.utcnow()
        if not company.industry:
            classification = self.classifier.classify(parsed.name, None)
            company.industry = classification.industry
            company.industry_detail = classification.industry_detail
            company.noga_code = classification.noga_code

    @staticmethod
    def _detect_language_region(canton: str | None) -> str:
        if not canton:
            return "de"
        french = {"GE", "VD", "NE", "JU"}
        italian = {"TI"}
        if canton.upper() in french:
            return "fr"
        if canton.upper() in italian:
            return "it"
        return "de"
