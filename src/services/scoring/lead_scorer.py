import logging
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.company import MiCompany
from src.models.enrichment import MiEnrichment
from src.models.lead import LeadAccount

logger = logging.getLogger(__name__)

# Target trades that score highest
TARGET_INDUSTRIES = {"MALEREI", "GIPSEREI", "FASSADENBAU", "VERPUTZEREI", "STUCKATEUR"}

# German-speaking cantons (primary market)
DACH_CANTONS = {"ZH", "BE", "LU", "UR", "SZ", "OW", "NW", "GL", "ZG", "SO", "BS", "BL", "SH", "AR", "AI", "SG", "GR", "AG", "TG"}


class LeadScorer:
    """Calculates lead scores for companies based on multiple factors."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def score_company(self, company: MiCompany) -> int:
        """Calculate lead score (0-100) for a company."""
        score = 0

        # Target trade (Maler/Gipser/Fassade): +20
        if company.industry in TARGET_INDUSTRIES:
            score += 20

        # Company size 5-50 employees: +15
        if company.employee_count_est:
            if 5 <= company.employee_count_est <= 50:
                score += 15
            elif 1 <= company.employee_count_est < 5:
                score += 5

        # Has website (from enrichment): +10
        enrichment = company.enrichment
        if enrichment and enrichment.website:
            score += 10

        # No ERP/software detected: +15
        if enrichment and enrichment.digital_maturity_score is not None:
            if enrichment.digital_maturity_score < 30:
                score += 15
            elif enrichment.digital_maturity_score < 60:
                score += 5

        # Young company (<2 years): +10
        if company.founding_date:
            age_years = (date.today() - company.founding_date).days / 365
            if age_years < 2:
                score += 10
            elif age_years < 5:
                score += 5

        # Has job postings (growing): +10
        if enrichment and enrichment.services:
            score += 5

        # German-speaking Switzerland: +5
        if company.language_region == "de":
            score += 5

        # AG or GmbH (more serious business): +5
        if company.legal_form in ("AG", "GmbH"):
            score += 5

        # Active status: +5
        if company.status == "ACTIVE":
            score += 5

        return min(score, 100)

    def temperature_from_score(self, score: int) -> str:
        if score >= 70:
            return "HOT"
        if score >= 40:
            return "WARM"
        return "COLD"

    async def score_all(self) -> int:
        """Rescore all companies that have lead accounts. Returns count scored."""
        result = await self.session.execute(
            select(LeadAccount).options(
                selectinload(LeadAccount.company).selectinload(MiCompany.enrichment)
            )
        )
        leads = result.scalars().all()
        count = 0

        for lead in leads:
            if lead.company:
                score = await self.score_company(lead.company)
                lead.lead_score = score
                lead.lead_temperature = self.temperature_from_score(score)
                count += 1

        logger.info(f"Scored {count} leads")
        return count
