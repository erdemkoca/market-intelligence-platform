from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.company import MiCompany, MiCompanyLocation
from src.models.lead import LeadAccount, LeadInteraction


class LeadRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_all(
        self,
        offset: int = 0,
        limit: int = 50,
        lead_status: str | None = None,
        lead_temperature: str | None = None,
        sales_owner: str | None = None,
        canton: str | None = None,
        industry: str | None = None,
    ) -> tuple[list[LeadAccount], int]:
        query = select(LeadAccount).join(MiCompany, LeadAccount.company_id == MiCompany.id)
        count_query = select(func.count(LeadAccount.id)).join(MiCompany, LeadAccount.company_id == MiCompany.id)

        if lead_status:
            query = query.where(LeadAccount.lead_status == lead_status)
            count_query = count_query.where(LeadAccount.lead_status == lead_status)
        if lead_temperature:
            query = query.where(LeadAccount.lead_temperature == lead_temperature)
            count_query = count_query.where(LeadAccount.lead_temperature == lead_temperature)
        if sales_owner:
            query = query.where(LeadAccount.sales_owner == sales_owner)
            count_query = count_query.where(LeadAccount.sales_owner == sales_owner)
        if canton:
            query = query.join(MiCompanyLocation, MiCompany.id == MiCompanyLocation.company_id)
            query = query.where(MiCompanyLocation.canton == canton.upper())
            count_query = count_query.join(MiCompanyLocation, MiCompany.id == MiCompanyLocation.company_id)
            count_query = count_query.where(MiCompanyLocation.canton == canton.upper())
        if industry:
            query = query.where(MiCompany.industry == industry)
            count_query = count_query.where(MiCompany.industry == industry)

        total = (await self.session.execute(count_query)).scalar() or 0

        query = (
            query.options(selectinload(LeadAccount.company))
            .order_by(LeadAccount.lead_score.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all()), total

    async def find_by_id(self, lead_id: int) -> LeadAccount | None:
        result = await self.session.execute(
            select(LeadAccount)
            .options(
                selectinload(LeadAccount.company),
                selectinload(LeadAccount.interactions),
            )
            .where(LeadAccount.id == lead_id)
        )
        return result.scalar_one_or_none()

    async def find_by_company_id(self, company_id: int) -> LeadAccount | None:
        result = await self.session.execute(
            select(LeadAccount).where(LeadAccount.company_id == company_id)
        )
        return result.scalar_one_or_none()

    async def create_for_company(self, company_id: int) -> LeadAccount:
        lead = LeadAccount(company_id=company_id)
        self.session.add(lead)
        await self.session.flush()
        return lead
