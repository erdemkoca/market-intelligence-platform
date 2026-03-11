from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.models.lead import LeadInteraction
from src.repositories.lead_repository import LeadRepository
from src.schemas.company import PaginatedResponse
from src.schemas.lead import InteractionCreateRequest, InteractionOut, LeadOut, LeadUpdateRequest

router = APIRouter(prefix="/api/leads", tags=["leads"])


@router.get("", response_model=PaginatedResponse)
async def list_leads(
    offset: int = 0,
    limit: int = 50,
    lead_status: str | None = None,
    lead_temperature: str | None = None,
    sales_owner: str | None = None,
    canton: str | None = None,
    industry: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    repo = LeadRepository(db)
    leads, total = await repo.find_all(
        offset=offset,
        limit=min(limit, 200),
        lead_status=lead_status,
        lead_temperature=lead_temperature,
        sales_owner=sales_owner,
        canton=canton,
        industry=industry,
    )

    items = []
    for lead in leads:
        company = lead.company
        canton_val = None
        if company and company.locations:
            canton_val = company.locations[0].canton if company.locations else None

        items.append(LeadOut(
            id=lead.id,
            company_id=lead.company_id,
            company_name=company.name if company else None,
            company_uid=company.uid if company else None,
            canton=canton_val,
            industry=company.industry if company else None,
            industry_detail=company.industry_detail if company else None,
            is_baunex_customer=lead.is_baunex_customer,
            is_baunex_trial=lead.is_baunex_trial,
            had_demo=lead.had_demo,
            lead_status=lead.lead_status,
            lead_score=lead.lead_score,
            lead_temperature=lead.lead_temperature,
            sales_owner=lead.sales_owner,
            priority=lead.priority,
            next_action=lead.next_action,
            next_action_date=lead.next_action_date,
            first_contacted_at=lead.first_contacted_at,
            last_contacted_at=lead.last_contacted_at,
            notes=lead.notes,
            tags=lead.tags,
            created_at=lead.created_at,
            updated_at=lead.updated_at,
        ))

    return PaginatedResponse(items=items, total=total, offset=offset, limit=limit)


@router.patch("/{lead_id}", response_model=LeadOut)
async def update_lead(lead_id: int, req: LeadUpdateRequest, db: AsyncSession = Depends(get_db)):
    repo = LeadRepository(db)
    lead = await repo.find_by_id(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    update_data = req.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(lead, key, value)
    lead.updated_at = datetime.utcnow()

    company = lead.company
    canton_val = None
    if company and company.locations:
        canton_val = company.locations[0].canton

    return LeadOut(
        id=lead.id,
        company_id=lead.company_id,
        company_name=company.name if company else None,
        company_uid=company.uid if company else None,
        canton=canton_val,
        industry=company.industry if company else None,
        industry_detail=company.industry_detail if company else None,
        is_baunex_customer=lead.is_baunex_customer,
        is_baunex_trial=lead.is_baunex_trial,
        had_demo=lead.had_demo,
        lead_status=lead.lead_status,
        lead_score=lead.lead_score,
        lead_temperature=lead.lead_temperature,
        sales_owner=lead.sales_owner,
        priority=lead.priority,
        next_action=lead.next_action,
        next_action_date=lead.next_action_date,
        first_contacted_at=lead.first_contacted_at,
        last_contacted_at=lead.last_contacted_at,
        notes=lead.notes,
        tags=lead.tags,
        created_at=lead.created_at,
        updated_at=lead.updated_at,
    )


@router.post("/{lead_id}/interactions", response_model=InteractionOut)
async def add_interaction(lead_id: int, req: InteractionCreateRequest, db: AsyncSession = Depends(get_db)):
    repo = LeadRepository(db)
    lead = await repo.find_by_id(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    interaction = LeadInteraction(
        lead_id=lead_id,
        contact_id=req.contact_id,
        interaction_type=req.interaction_type,
        direction=req.direction,
        subject=req.subject,
        body=req.body,
        outcome=req.outcome,
        performed_by=req.performed_by,
    )
    db.add(interaction)
    await db.flush()

    # Update last contacted
    if req.direction == "OUTBOUND":
        lead.last_contacted_at = datetime.utcnow()
        if not lead.first_contacted_at:
            lead.first_contacted_at = datetime.utcnow()

    return InteractionOut(
        id=interaction.id,
        lead_id=interaction.lead_id,
        contact_id=interaction.contact_id,
        interaction_type=interaction.interaction_type,
        direction=interaction.direction,
        subject=interaction.subject,
        body=interaction.body,
        outcome=interaction.outcome,
        performed_by=interaction.performed_by,
        performed_at=interaction.performed_at,
    )
