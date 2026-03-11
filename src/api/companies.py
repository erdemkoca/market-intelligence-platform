from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.repositories.company_repository import CompanyRepository
from src.schemas.company import CompanyDetailOut, CompanyListOut, CompanyStatsOut, PaginatedResponse

router = APIRouter(prefix="/api/companies", tags=["companies"])


@router.get("", response_model=PaginatedResponse)
async def list_companies(
    offset: int = 0,
    limit: int = 50,
    canton: str | None = None,
    industry: str | None = None,
    industry_detail: str | None = None,
    legal_form: str | None = None,
    status: str | None = None,
    size_class: str | None = None,
    q: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    repo = CompanyRepository(db)
    companies, total = await repo.find_all(
        offset=offset,
        limit=min(limit, 200),
        canton=canton,
        industry=industry,
        industry_detail=industry_detail,
        legal_form=legal_form,
        status=status,
        size_class=size_class,
        q=q,
    )

    items = []
    for c in companies:
        # Get canton from first location if available
        canton_val = None
        city_val = None
        if c.locations:
            canton_val = c.locations[0].canton
            city_val = c.locations[0].city

        items.append(CompanyListOut(
            id=c.id,
            name=c.name,
            uid=c.uid,
            legal_form=c.legal_form,
            status=c.status,
            industry=c.industry,
            industry_detail=c.industry_detail,
            canton=canton_val,
            city=city_val,
            founding_date=c.founding_date,
            language_region=c.language_region,
            created_at=c.created_at,
            updated_at=c.updated_at,
        ))

    return PaginatedResponse(items=items, total=total, offset=offset, limit=limit)


@router.get("/stats", response_model=CompanyStatsOut)
async def get_stats(db: AsyncSession = Depends(get_db)):
    repo = CompanyRepository(db)
    stats = await repo.get_stats()
    return CompanyStatsOut(**stats)


@router.get("/{company_id}", response_model=CompanyDetailOut)
async def get_company(company_id: int, db: AsyncSession = Depends(get_db)):
    repo = CompanyRepository(db)
    company = await repo.find_by_id(company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    lead_summary = None
    if company.lead_account:
        la = company.lead_account
        lead_summary = {
            "lead_status": la.lead_status,
            "lead_score": la.lead_score,
            "lead_temperature": la.lead_temperature,
            "sales_owner": la.sales_owner,
            "is_baunex_customer": la.is_baunex_customer,
        }

    return CompanyDetailOut(
        id=company.id,
        name=company.name,
        legal_name=company.legal_name,
        uid=company.uid,
        hr_number=company.hr_number,
        legal_form=company.legal_form,
        status=company.status,
        purpose=company.purpose,
        founding_date=company.founding_date,
        capital=float(company.capital) if company.capital else None,
        capital_currency=company.capital_currency,
        noga_code=company.noga_code,
        industry=company.industry,
        industry_detail=company.industry_detail,
        employee_count_est=company.employee_count_est,
        size_class=company.size_class,
        language_region=company.language_region,
        created_at=company.created_at,
        updated_at=company.updated_at,
        locations=[loc for loc in company.locations],
        identifiers=[ident for ident in company.identifiers],
        enrichment=company.enrichment,
        lead=lead_summary,
    )
