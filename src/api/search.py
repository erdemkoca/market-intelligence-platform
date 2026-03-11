from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.repositories.company_repository import CompanyRepository
from src.schemas.company import CompanyListOut, PaginatedResponse

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("", response_model=PaginatedResponse)
async def search_companies(
    q: str = "",
    offset: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """Unified search across companies by name."""
    if not q or len(q) < 2:
        return PaginatedResponse(items=[], total=0, offset=offset, limit=limit)

    repo = CompanyRepository(db)
    companies, total = await repo.find_all(offset=offset, limit=min(limit, 200), q=q)

    items = []
    for c in companies:
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
