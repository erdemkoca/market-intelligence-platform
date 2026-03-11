from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


class Campaign(Base):
    __tablename__ = "mi_campaigns"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    campaign_type: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT")
    segment_filter: Mapped[dict | None] = mapped_column(JSONB)
    created_by: Mapped[str | None] = mapped_column(String(200))
    started_at: Mapped[datetime | None] = mapped_column()
    completed_at: Mapped[datetime | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())

    recipients: Mapped[list["CampaignRecipient"]] = relationship(back_populates="campaign", cascade="all, delete-orphan")


class CampaignRecipient(Base):
    __tablename__ = "mi_campaign_recipients"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    campaign_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("mi_campaigns.id", ondelete="CASCADE"), nullable=False)
    lead_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("mi_lead_accounts.id"), nullable=False)
    contact_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("mi_contacts.id"))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    sent_at: Mapped[datetime | None] = mapped_column()
    opened_at: Mapped[datetime | None] = mapped_column()
    replied_at: Mapped[datetime | None] = mapped_column()
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())

    campaign: Mapped["Campaign"] = relationship(back_populates="recipients")

    __table_args__ = (
        Index("idx_mi_recipients_campaign", "campaign_id"),
        Index("idx_mi_recipients_lead", "lead_id"),
        Index("idx_mi_recipients_status", "status"),
    )


class SuppressionEntry(Base):
    __tablename__ = "mi_suppression_list"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    entry_type: Mapped[str] = mapped_column(String(20), nullable=False)
    entry_value: Mapped[str] = mapped_column(String(500), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(100))
    source: Mapped[str | None] = mapped_column(String(100))
    suppressed_at: Mapped[datetime] = mapped_column(default=func.now())

    __table_args__ = (
        UniqueConstraint("entry_type", "entry_value", name="uq_suppression_entry"),
        Index("idx_mi_suppression_type", "entry_type"),
    )
