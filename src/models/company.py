from datetime import date, datetime

from sqlalchemy import BigInteger, Date, Index, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


class MiCompany(Base):
    __tablename__ = "mi_companies"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    legal_name: Mapped[str | None] = mapped_column(String(500))
    uid: Mapped[str | None] = mapped_column(String(15), unique=True)
    hr_number: Mapped[str | None] = mapped_column(String(50))
    legal_form: Mapped[str | None] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="ACTIVE")
    purpose: Mapped[str | None] = mapped_column(Text)
    founding_date: Mapped[date | None] = mapped_column(Date)
    deletion_date: Mapped[date | None] = mapped_column(Date)
    capital: Mapped[float | None] = mapped_column(Numeric(15, 2))
    capital_currency: Mapped[str] = mapped_column(String(3), default="CHF")
    noga_code: Mapped[str | None] = mapped_column(String(10))
    industry: Mapped[str | None] = mapped_column(String(100))
    industry_detail: Mapped[str | None] = mapped_column(String(255))
    employee_count_est: Mapped[int | None] = mapped_column()
    size_class: Mapped[str | None] = mapped_column(String(20))
    language_region: Mapped[str | None] = mapped_column(String(5))
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())

    identifiers: Mapped[list["MiCompanyIdentifier"]] = relationship(back_populates="company", cascade="all, delete-orphan")
    locations: Mapped[list["MiCompanyLocation"]] = relationship(back_populates="company", cascade="all, delete-orphan")
    enrichment: Mapped["MiEnrichment | None"] = relationship(back_populates="company", cascade="all, delete-orphan", uselist=False)
    source_records: Mapped[list["MiSourceRecord"]] = relationship(back_populates="company", cascade="all, delete-orphan")
    events: Mapped[list["MiCompanyEvent"]] = relationship(back_populates="company", cascade="all, delete-orphan")
    contacts: Mapped[list["MiContact"]] = relationship(back_populates="company", cascade="all, delete-orphan")
    lead_account: Mapped["LeadAccount | None"] = relationship(back_populates="company", cascade="all, delete-orphan", uselist=False)

    __table_args__ = (
        Index("idx_mi_companies_status", "status"),
        Index("idx_mi_companies_industry", "industry"),
        Index("idx_mi_companies_industry_detail", "industry_detail"),
        Index("idx_mi_companies_noga", "noga_code"),
        Index("idx_mi_companies_legal_form", "legal_form"),
        Index("idx_mi_companies_founding_date", "founding_date"),
    )


class MiCompanyIdentifier(Base):
    __tablename__ = "mi_company_identifiers"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    identifier_type: Mapped[str] = mapped_column(String(30), nullable=False)
    identifier_value: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=func.now())

    company: Mapped["MiCompany"] = relationship(back_populates="identifiers")

    __table_args__ = (
        Index("idx_mi_identifiers_company", "company_id"),
        {"info": {"unique_constraints": [("identifier_type", "identifier_value")]}},
    )


class MiCompanyLocation(Base):
    __tablename__ = "mi_company_locations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    location_type: Mapped[str] = mapped_column(String(20), default="HQ")
    street: Mapped[str | None] = mapped_column(String(300))
    zip_code: Mapped[str | None] = mapped_column(String(10))
    city: Mapped[str | None] = mapped_column(String(200))
    canton: Mapped[str | None] = mapped_column(String(2))
    country: Mapped[str] = mapped_column(String(2), default="CH")
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())

    company: Mapped["MiCompany"] = relationship(back_populates="locations")

    __table_args__ = (
        Index("idx_mi_locations_company", "company_id"),
        Index("idx_mi_locations_canton", "canton"),
        Index("idx_mi_locations_zip", "zip_code"),
    )


# Forward references for type checking
from src.models.contact import MiContact  # noqa: E402, F811
from src.models.enrichment import MiEnrichment  # noqa: E402, F811
from src.models.lead import LeadAccount  # noqa: E402, F811
from src.models.source import MiCompanyEvent, MiSourceRecord  # noqa: E402, F811
