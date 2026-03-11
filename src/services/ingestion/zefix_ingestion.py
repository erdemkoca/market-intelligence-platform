import logging
import uuid
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.company import MiCompany, MiCompanyIdentifier, MiCompanyLocation
from src.models.source import MiIngestionJob, MiSourceRecord
from src.services.classification.industry_classifier import IndustryClassifier
from src.services.ingestion.zefix_client import ZefixClient

logger = logging.getLogger(__name__)


class ZefixIngestionService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.client = ZefixClient()
        self.classifier = IndustryClassifier()

    async def ingest(self) -> str:
        """Run a full Zefix ingestion for target trades. Returns job ID."""
        job_id = f"zefix-{date.today()}-{uuid.uuid4().hex[:8]}"
        job = MiIngestionJob(id=job_id, source_type="ZEFIX", status="RUNNING")
        self.session.add(job)
        await self.session.flush()

        try:
            raw_companies = await self.client.search_all_trades()
            job.records_fetched = len(raw_companies)
            logger.info(f"Job {job_id}: fetched {len(raw_companies)} companies from Zefix")

            for raw in raw_companies:
                await self._process_company(raw, job_id, job)

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

    async def _process_company(self, raw: dict, job_id: str, job: MiIngestionJob):
        parsed = self.client.parse_company(raw)

        if not parsed.uid:
            job.records_skipped += 1
            return

        # Check if company already exists by UID
        result = await self.session.execute(
            select(MiCompany).where(MiCompany.uid == parsed.uid)
        )
        existing = result.scalar_one_or_none()

        if existing:
            self._update_company(existing, parsed)
            job.records_updated += 1
        else:
            company = self._create_company(parsed)
            self.session.add(company)
            await self.session.flush()

            # Add identifiers
            if parsed.uid:
                self.session.add(MiCompanyIdentifier(
                    company_id=company.id,
                    identifier_type="UID",
                    identifier_value=parsed.uid,
                ))
            if parsed.chid:
                self.session.add(MiCompanyIdentifier(
                    company_id=company.id,
                    identifier_type="ZEFIX_ID",
                    identifier_value=parsed.chid,
                ))

            # Add location
            if parsed.address or parsed.legal_seat:
                address = parsed.address or {}
                self.session.add(MiCompanyLocation(
                    company_id=company.id,
                    location_type="HQ",
                    street=address.get("street"),
                    zip_code=address.get("swissZipCode") or address.get("zipCode"),
                    city=address.get("city") or parsed.legal_seat,
                    canton=parsed.canton,
                ))

            job.records_created += 1

        # Always store source record
        self.session.add(MiSourceRecord(
            company_id=existing.id if existing else company.id,
            source_type="ZEFIX",
            source_url=f"https://www.zefix.admin.ch/ZefixREST/api/v1/company/uid/{parsed.uid}",
            raw_data=parsed.raw,
            ingestion_job_id=job_id,
        ))

    def _create_company(self, parsed) -> MiCompany:
        classification = self.classifier.classify(parsed.name, parsed.raw.get("purpose"))
        return MiCompany(
            name=parsed.name,
            legal_name=parsed.name,
            uid=parsed.uid,
            legal_form=parsed.legal_form,
            status=parsed.status or "ACTIVE",
            purpose=parsed.purpose,
            noga_code=classification.noga_code,
            industry=classification.industry,
            industry_detail=classification.industry_detail,
            language_region=self._detect_language_region(parsed.canton),
        )

    def _update_company(self, company: MiCompany, parsed):
        company.name = parsed.name
        company.legal_form = parsed.legal_form or company.legal_form
        company.status = parsed.status or company.status
        company.purpose = parsed.purpose or company.purpose
        company.updated_at = datetime.utcnow()

        if not company.industry:
            classification = self.classifier.classify(parsed.name, parsed.raw.get("purpose"))
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
            return "de"  # default to German for bilingual
        return "de"
