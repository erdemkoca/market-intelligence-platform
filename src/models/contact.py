from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


class MiContact(Base):
    __tablename__ = "mi_contacts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("mi_companies.id", ondelete="CASCADE"), nullable=False)
    first_name: Mapped[str | None] = mapped_column(String(200))
    last_name: Mapped[str | None] = mapped_column(String(200))
    role: Mapped[str | None] = mapped_column(String(100))
    email: Mapped[str | None] = mapped_column(String(300))
    phone: Mapped[str | None] = mapped_column(String(50))
    source: Mapped[str] = mapped_column(String(30), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())

    company: Mapped["MiCompany"] = relationship(back_populates="contacts")
    permissions: Mapped[list["MiContactPermission"]] = relationship(back_populates="contact", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_mi_contacts_company", "company_id"),
        Index("idx_mi_contacts_email", "email"),
    )


class MiContactPermission(Base):
    __tablename__ = "mi_contact_permissions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    contact_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("mi_contacts.id", ondelete="CASCADE"), nullable=False)
    permission_type: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="UNKNOWN")
    granted_at: Mapped[datetime | None] = mapped_column()
    revoked_at: Mapped[datetime | None] = mapped_column()
    source: Mapped[str | None] = mapped_column(String(100))
    notes: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())

    contact: Mapped["MiContact"] = relationship(back_populates="permissions")

    __table_args__ = (
        UniqueConstraint("contact_id", "permission_type", name="uq_contact_permission"),
        Index("idx_mi_permissions_contact", "contact_id"),
        Index("idx_mi_permissions_status", "status"),
    )


from src.models.company import MiCompany  # noqa: E402, F811
