from datetime import datetime

from sqlalchemy import BigInteger, Boolean, Index, String, func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


class MiEnrichment(Base):
    __tablename__ = "mi_enrichments"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    website: Mapped[str | None] = mapped_column(String(500))
    email_general: Mapped[str | None] = mapped_column(String(300))
    phone: Mapped[str | None] = mapped_column(String(50))
    has_contact_form: Mapped[bool] = mapped_column(Boolean, default=False)
    services: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    service_regions: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    digital_maturity_score: Mapped[int | None] = mapped_column()
    last_enriched_at: Mapped[datetime | None] = mapped_column()
    enrichment_source: Mapped[str | None] = mapped_column(String(30))
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())

    company: Mapped["MiCompany"] = relationship(back_populates="enrichment")

    __table_args__ = (
        Index("idx_mi_enrichments_company", "company_id", unique=True),
    )


from src.models.company import MiCompany  # noqa: E402, F811
