from datetime import date, datetime

from pydantic import BaseModel


class LeadOut(BaseModel):
    id: int
    company_id: int
    company_name: str | None = None
    company_uid: str | None = None
    canton: str | None = None
    industry: str | None = None
    industry_detail: str | None = None
    is_baunex_customer: bool = False
    is_baunex_trial: bool = False
    had_demo: bool = False
    lead_status: str = "NEW"
    lead_score: int = 0
    lead_temperature: str | None = None
    sales_owner: str | None = None
    priority: str = "MEDIUM"
    next_action: str | None = None
    next_action_date: date | None = None
    first_contacted_at: datetime | None = None
    last_contacted_at: datetime | None = None
    notes: str | None = None
    tags: list[str] | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LeadUpdateRequest(BaseModel):
    lead_status: str | None = None
    lead_temperature: str | None = None
    sales_owner: str | None = None
    priority: str | None = None
    next_action: str | None = None
    next_action_date: date | None = None
    notes: str | None = None
    tags: list[str] | None = None
    is_baunex_customer: bool | None = None
    is_baunex_trial: bool | None = None
    had_demo: bool | None = None
    lost_reason: str | None = None


class InteractionCreateRequest(BaseModel):
    interaction_type: str
    direction: str | None = None
    subject: str | None = None
    body: str | None = None
    outcome: str | None = None
    performed_by: str | None = None
    contact_id: int | None = None


class InteractionOut(BaseModel):
    id: int
    lead_id: int
    contact_id: int | None = None
    interaction_type: str
    direction: str | None = None
    subject: str | None = None
    body: str | None = None
    outcome: str | None = None
    performed_by: str | None = None
    performed_at: datetime

    model_config = {"from_attributes": True}
