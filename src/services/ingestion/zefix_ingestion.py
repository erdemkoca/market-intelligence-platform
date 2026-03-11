import logging
import uuid
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.company import MiCompany, MiCompanyIdentifier, MiCompanyLocation
from src.models.source import MiIngestionJob, MiSourceRecord
from src.services.classification.industry_classifier import IndustryClassifier
from src.services.ingestion.zefix_client import ZefixClient, ZefixCompanyResult

logger = logging.getLogger(__name__)


class ZefixIngestionService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.client = ZefixClient()
        self.classifier = IndustryClassifier()

    async def ingest(self) -> str:
        """Run a full LINDAS/Zefix ingestion for target trades. Returns job ID."""
        job_id = f"lindas-{date.today()}-{uuid.uuid4().hex[:8]}"
        job = MiIngestionJob(id=job_id, source_type="LINDAS_ZEFIX", status="RUNNING")
        self.session.add(job)
        await self.session.flush()

        try:
            # Step 1: Fetch all trade companies from LINDAS
            companies = await self.client.fetch_trade_companies()
            job.records_fetched = len(companies)
            logger.info(f"Job {job_id}: fetched {len(companies)} companies from LINDAS")

            # Step 2: Fetch addresses in batch
            company_uris = [
                c.raw.get("company_uri") for c in companies
                if c.raw.get("company_uri")
            ]
            addresses = await self.client.fetch_addresses_batch(company_uris)
            logger.info(f"Job {job_id}: fetched {len(addresses)} addresses")

            # Step 3: Attach addresses to companies
            for company in companies:
                uri = company.raw.get("company_uri")
                if uri and uri in addresses:
                    addr = addresses[uri]
                    company.address = addr
                    company.canton = addr.get("canton")

            # Step 4: Process each company
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

    async def _process_company(self, parsed: ZefixCompanyResult, job_id: str, job: MiIngestionJob):
        # Need at least a UID or zefix_id for dedup
        dedup_key = parsed.uid or parsed.zefix_id
        if not dedup_key:
            job.records_skipped += 1
            return

        # Check if company already exists by UID (preferred) or zefix_id
        existing = None
        if parsed.uid:
            result = await self.session.execute(
                select(MiCompany).where(MiCompany.uid == parsed.uid)
            )
            existing = result.scalar_one_or_none()

        if existing:
            self._update_company(existing, parsed)
            company_id = existing.id
            job.records_updated += 1
        else:
            company = self._create_company(parsed)
            self.session.add(company)
            await self.session.flush()
            company_id = company.id

            # Add identifiers
            if parsed.uid:
                self.session.add(MiCompanyIdentifier(
                    company_id=company_id,
                    identifier_type="UID",
                    identifier_value=parsed.uid,
                ))
            if parsed.chid:
                self.session.add(MiCompanyIdentifier(
                    company_id=company_id,
                    identifier_type="CHID",
                    identifier_value=parsed.chid,
                ))
            if parsed.zefix_id:
                self.session.add(MiCompanyIdentifier(
                    company_id=company_id,
                    identifier_type="ZEFIX_ID",
                    identifier_value=parsed.zefix_id,
                ))

            # Add location
            if parsed.address:
                self.session.add(MiCompanyLocation(
                    company_id=company_id,
                    location_type="HQ",
                    street=parsed.address.get("street"),
                    zip_code=parsed.address.get("zip_code"),
                    city=parsed.address.get("city"),
                    canton=parsed.address.get("canton"),
                ))

            job.records_created += 1

        # Store source record
        self.session.add(MiSourceRecord(
            company_id=company_id,
            source_type="LINDAS_ZEFIX",
            source_url=parsed.raw.get("company_uri"),
            raw_data=parsed.raw,
            ingestion_job_id=job_id,
        ))

    def _create_company(self, parsed: ZefixCompanyResult) -> MiCompany:
        classification = self.classifier.classify(parsed.name, parsed.purpose)
        canton = parsed.canton or (parsed.address.get("canton") if parsed.address else None)
        return MiCompany(
            name=parsed.name,
            legal_name=parsed.name,
            uid=parsed.uid,
            legal_form=parsed.legal_form,
            status="ACTIVE",
            purpose=parsed.purpose,
            noga_code=classification.noga_code,
            industry=classification.industry,
            industry_detail=classification.industry_detail,
            language_region=self._detect_language_region(canton),
        )

    def _update_company(self, company: MiCompany, parsed: ZefixCompanyResult):
        company.name = parsed.name
        company.legal_form = parsed.legal_form or company.legal_form
        company.purpose = parsed.purpose or company.purpose
        company.updated_at = datetime.utcnow()

        if not company.industry:
            classification = self.classifier.classify(parsed.name, parsed.purpose)
            company.noga_code = classification.noga_code
            company.industry = classification.industry
            company.industry_detail = classification.industry_detail

    @staticmethod
    def _detect_language_region(canton: str | None) -> str:
        if not canton:
            return "de"
        french = {"GE", "VD", "NE", "JU"}
        italian = {"TI"}
        bilingual_fr = {"FR", "VS", "BE"}
        if canton.upper() in french:
            return "fr"
        if canton.upper() in italian:
            return "it"
        if canton.upper() in bilingual_fr:
            return "de"
        return "de"
