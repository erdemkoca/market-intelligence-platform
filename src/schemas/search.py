from pydantic import BaseModel


class SearchRequest(BaseModel):
    q: str | None = None
    canton: str | None = None
    industry: str | None = None
    industry_detail: str | None = None
    legal_form: str | None = None
    status: str | None = None
    size_class: str | None = None
    language_region: str | None = None
    offset: int = 0
    limit: int = 50
