from datetime import date, datetime

from pydantic import BaseModel


class CompanyLocationOut(BaseModel):
    id: int
    location_type: str | None = None
    street: str | None = None
    zip_code: str | None = None
    city: str | None = None
    canton: str | None = None
    country: str = "CH"

    model_config = {"from_attributes": True}


class CompanyIdentifierOut(BaseModel):
    identifier_type: str
    identifier_value: str

    model_config = {"from_attributes": True}


class EnrichmentOut(BaseModel):
    website: str | None = None
    email_general: str | None = None
    phone: str | None = None
    has_contact_form: bool = False
    services: list[str] | None = None
    service_regions: list[str] | None = None
    digital_maturity_score: int | None = None
    last_enriched_at: datetime | None = None

    model_config = {"from_attributes": True}


class LeadSummaryOut(BaseModel):
    lead_status: str = "NEW"
    lead_score: int = 0
    lead_temperature: str | None = None
    sales_owner: str | None = None
    is_baunex_customer: bool = False

    model_config = {"from_attributes": True}


class CompanyListOut(BaseModel):
    id: int
    name: str
    uid: str | None = None
    legal_form: str | None = None
    status: str = "ACTIVE"
    industry: str | None = None
    industry_detail: str | None = None
    canton: str | None = None
    city: str | None = None
    founding_date: date | None = None
    language_region: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CompanyDetailOut(BaseModel):
    id: int
    name: str
    legal_name: str | None = None
    uid: str | None = None
    hr_number: str | None = None
    legal_form: str | None = None
    status: str = "ACTIVE"
    purpose: str | None = None
    founding_date: date | None = None
    capital: float | None = None
    capital_currency: str = "CHF"
    noga_code: str | None = None
    industry: str | None = None
    industry_detail: str | None = None
    employee_count_est: int | None = None
    size_class: str | None = None
    language_region: str | None = None
    created_at: datetime
    updated_at: datetime
    locations: list[CompanyLocationOut] = []
    identifiers: list[CompanyIdentifierOut] = []
    enrichment: EnrichmentOut | None = None
    lead: LeadSummaryOut | None = None

    model_config = {"from_attributes": True}


class CompanyStatsOut(BaseModel):
    total_companies: int = 0
    active_companies: int = 0
    by_canton: dict[str, int] = {}
    by_industry: dict[str, int] = {}
    by_legal_form: dict[str, int] = {}
    new_this_week: int = 0


class PaginatedResponse(BaseModel):
    items: list
    total: int
    offset: int
    limit: int
