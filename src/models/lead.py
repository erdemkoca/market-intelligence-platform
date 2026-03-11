from datetime import date, datetime

from sqlalchemy import BigInteger, Boolean, Date, ForeignKey, Index, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


class LeadAccount(Base):
    __tablename__ = "mi_lead_accounts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("mi_companies.id", ondelete="CASCADE"), unique=True, nullable=False)
    is_baunex_customer: Mapped[bool] = mapped_column(Boolean, default=False)
    is_baunex_trial: Mapped[bool] = mapped_column(Boolean, default=False)
    had_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    lead_status: Mapped[str] = mapped_column(String(30), nullable=False, default="NEW")
    lead_score: Mapped[int] = mapped_column(default=0)
    lead_temperature: Mapped[str | None] = mapped_column(String(10))
    sales_owner: Mapped[str | None] = mapped_column(String(200))
    priority: Mapped[str] = mapped_column(String(10), default="MEDIUM")
    deal_value_est: Mapped[float | None] = mapped_column(Numeric(10, 2))
    next_action: Mapped[str | None] = mapped_column(String(500))
    next_action_date: Mapped[date | None] = mapped_column(Date)
    first_contacted_at: Mapped[datetime | None] = mapped_column()
    last_contacted_at: Mapped[datetime | None] = mapped_column()
    lost_reason: Mapped[str | None] = mapped_column(String(500))
    notes: Mapped[str | None] = mapped_column(Text)
    tags: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())

    company: Mapped["MiCompany"] = relationship(back_populates="lead_account")
    interactions: Mapped[list["LeadInteraction"]] = relationship(back_populates="lead", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_mi_leads_status", "lead_status"),
        Index("idx_mi_leads_score", lead_score.desc()),
        Index("idx_mi_leads_owner", "sales_owner"),
        Index("idx_mi_leads_temperature", "lead_temperature"),
    )


class LeadInteraction(Base):
    __tablename__ = "mi_lead_interactions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    lead_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("mi_lead_accounts.id", ondelete="CASCADE"), nullable=False)
    contact_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("mi_contacts.id"))
    interaction_type: Mapped[str] = mapped_column(String(30), nullable=False)
    direction: Mapped[str | None] = mapped_column(String(10))
    subject: Mapped[str | None] = mapped_column(String(500))
    body: Mapped[str | None] = mapped_column(Text)
    outcome: Mapped[str | None] = mapped_column(String(30))
    performed_by: Mapped[str | None] = mapped_column(String(200))
    performed_at: Mapped[datetime] = mapped_column(default=func.now())
    created_at: Mapped[datetime] = mapped_column(default=func.now())

    lead: Mapped["LeadAccount"] = relationship(back_populates="interactions")

    __table_args__ = (
        Index("idx_mi_interactions_lead", "lead_id"),
        Index("idx_mi_interactions_type", "interaction_type"),
        Index("idx_mi_interactions_date", "performed_at"),
    )


from src.models.company import MiCompany  # noqa: E402, F811
