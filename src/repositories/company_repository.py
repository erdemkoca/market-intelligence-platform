from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.company import MiCompany, MiCompanyLocation
from src.models.enrichment import MiEnrichment
from src.models.lead import LeadAccount


class CompanyRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_all(
        self,
        offset: int = 0,
        limit: int = 50,
        canton: str | None = None,
        industry: str | None = None,
        industry_detail: str | None = None,
        legal_form: str | None = None,
        status: str | None = None,
        size_class: str | None = None,
        q: str | None = None,
    ) -> tuple[list[MiCompany], int]:
        query = select(MiCompany)
        count_query = select(func.count(MiCompany.id))

        # Apply filters
        if canton:
            query = query.join(MiCompanyLocation, MiCompany.id == MiCompanyLocation.company_id)
            query = query.where(MiCompanyLocation.canton == canton.upper())
            count_query = count_query.join(MiCompanyLocation, MiCompany.id == MiCompanyLocation.company_id)
            count_query = count_query.where(MiCompanyLocation.canton == canton.upper())
        if industry:
            query = query.where(MiCompany.industry == industry)
            count_query = count_query.where(MiCompany.industry == industry)
        if industry_detail:
            query = query.where(MiCompany.industry_detail.ilike(f"%{industry_detail}%"))
            count_query = count_query.where(MiCompany.industry_detail.ilike(f"%{industry_detail}%"))
        if legal_form:
            query = query.where(MiCompany.legal_form == legal_form)
            count_query = count_query.where(MiCompany.legal_form == legal_form)
        if status:
            query = query.where(MiCompany.status == status)
            count_query = count_query.where(MiCompany.status == status)
        if size_class:
            query = query.where(MiCompany.size_class == size_class)
            count_query = count_query.where(MiCompany.size_class == size_class)
        if q:
            query = query.where(MiCompany.name.ilike(f"%{q}%"))
            count_query = count_query.where(MiCompany.name.ilike(f"%{q}%"))

        total = (await self.session.execute(count_query)).scalar() or 0

        query = query.order_by(MiCompany.name).offset(offset).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all()), total

    async def find_by_id(self, company_id: int) -> MiCompany | None:
        result = await self.session.execute(
            select(MiCompany)
            .options(
                selectinload(MiCompany.locations),
                selectinload(MiCompany.identifiers),
                selectinload(MiCompany.enrichment),
                selectinload(MiCompany.lead_account),
            )
            .where(MiCompany.id == company_id)
        )
        return result.scalar_one_or_none()

    async def find_by_uid(self, uid: str) -> MiCompany | None:
        result = await self.session.execute(
            select(MiCompany).where(MiCompany.uid == uid)
        )
        return result.scalar_one_or_none()

    async def get_stats(self) -> dict:
        total = (await self.session.execute(select(func.count(MiCompany.id)))).scalar() or 0
        active = (await self.session.execute(
            select(func.count(MiCompany.id)).where(MiCompany.status == "ACTIVE")
        )).scalar() or 0

        # By canton
        canton_result = await self.session.execute(
            select(MiCompanyLocation.canton, func.count(MiCompanyLocation.id))
            .where(MiCompanyLocation.canton.isnot(None))
            .group_by(MiCompanyLocation.canton)
        )
        by_canton = {row[0]: row[1] for row in canton_result.all()}

        # By industry
        industry_result = await self.session.execute(
            select(MiCompany.industry, func.count(MiCompany.id))
            .where(MiCompany.industry.isnot(None))
            .group_by(MiCompany.industry)
        )
        by_industry = {row[0]: row[1] for row in industry_result.all()}

        # By legal form
        legal_result = await self.session.execute(
            select(MiCompany.legal_form, func.count(MiCompany.id))
            .where(MiCompany.legal_form.isnot(None))
            .group_by(MiCompany.legal_form)
        )
        by_legal_form = {row[0]: row[1] for row in legal_result.all()}

        # New this week
        week_ago = datetime.utcnow() - timedelta(days=7)
        new_this_week = (await self.session.execute(
            select(func.count(MiCompany.id)).where(MiCompany.created_at >= week_ago)
        )).scalar() or 0

        return {
            "total_companies": total,
            "active_companies": active,
            "by_canton": by_canton,
            "by_industry": by_industry,
            "by_legal_form": by_legal_form,
            "new_this_week": new_this_week,
        }
