from datetime import datetime

from sqlalchemy import BigInteger, Date, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


class MiSourceRecord(Base):
    __tablename__ = "mi_source_records"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("mi_companies.id", ondelete="CASCADE"), nullable=False)
    source_type: Mapped[str] = mapped_column(String(30), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(1000))
    raw_data: Mapped[dict | None] = mapped_column(JSONB)
    ingestion_job_id: Mapped[str | None] = mapped_column(String(100))
    ingested_at: Mapped[datetime] = mapped_column(default=func.now())

    company: Mapped["MiCompany"] = relationship(back_populates="source_records")

    __table_args__ = (
        Index("idx_mi_sources_company", "company_id"),
        Index("idx_mi_sources_type", "source_type"),
        Index("idx_mi_sources_job", "ingestion_job_id"),
    )


class MiCompanyEvent(Base):
    __tablename__ = "mi_company_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("mi_companies.id", ondelete="CASCADE"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    event_date: Mapped[datetime | None] = mapped_column(Date)
    summary: Mapped[str | None] = mapped_column(Text)
    source_type: Mapped[str | None] = mapped_column(String(30))
    source_ref: Mapped[str | None] = mapped_column(String(500))
    raw_data: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(default=func.now())

    company: Mapped["MiCompany"] = relationship(back_populates="events")

    __table_args__ = (
        Index("idx_mi_events_company", "company_id"),
        Index("idx_mi_events_type", "event_type"),
        Index("idx_mi_events_date", "event_date"),
    )


class MiIngestionJob(Base):
    __tablename__ = "mi_ingestion_jobs"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    source_type: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="RUNNING")
    started_at: Mapped[datetime] = mapped_column(default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column()
    records_fetched: Mapped[int] = mapped_column(default=0)
    records_created: Mapped[int] = mapped_column(default=0)
    records_updated: Mapped[int] = mapped_column(default=0)
    records_skipped: Mapped[int] = mapped_column(default=0)
    error_message: Mapped[str | None] = mapped_column(Text)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB)


from src.models.company import MiCompany  # noqa: E402, F811
