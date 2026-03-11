"""Initial schema for Market Intelligence Platform

Revision ID: 001
Revises:
Create Date: 2026-03-11
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, JSONB

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # === mi_companies ===
    op.create_table(
        "mi_companies",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column("legal_name", sa.String(500)),
        sa.Column("uid", sa.String(15), unique=True),
        sa.Column("hr_number", sa.String(50)),
        sa.Column("legal_form", sa.String(50)),
        sa.Column("status", sa.String(30), nullable=False, server_default="ACTIVE"),
        sa.Column("purpose", sa.Text),
        sa.Column("founding_date", sa.Date),
        sa.Column("deletion_date", sa.Date),
        sa.Column("capital", sa.Numeric(15, 2)),
        sa.Column("capital_currency", sa.String(3), server_default="CHF"),
        sa.Column("noga_code", sa.String(10)),
        sa.Column("industry", sa.String(100)),
        sa.Column("industry_detail", sa.String(255)),
        sa.Column("employee_count_est", sa.Integer),
        sa.Column("size_class", sa.String(20)),
        sa.Column("language_region", sa.String(5)),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_mi_companies_uid", "mi_companies", ["uid"])
    op.create_index("idx_mi_companies_status", "mi_companies", ["status"])
    op.create_index("idx_mi_companies_industry", "mi_companies", ["industry"])
    op.create_index("idx_mi_companies_industry_detail", "mi_companies", ["industry_detail"])
    op.create_index("idx_mi_companies_noga", "mi_companies", ["noga_code"])
    op.create_index("idx_mi_companies_legal_form", "mi_companies", ["legal_form"])
    op.create_index("idx_mi_companies_founding_date", "mi_companies", ["founding_date"])

    # Trigram index for name search (requires pg_trgm extension)
    op.execute("CREATE INDEX idx_mi_companies_name_trgm ON mi_companies USING gin (name gin_trgm_ops)")

    # === mi_company_identifiers ===
    op.create_table(
        "mi_company_identifiers",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("company_id", sa.BigInteger, sa.ForeignKey("mi_companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("identifier_type", sa.String(30), nullable=False),
        sa.Column("identifier_value", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.UniqueConstraint("identifier_type", "identifier_value", name="uq_identifier_type_value"),
    )
    op.create_index("idx_mi_identifiers_company", "mi_company_identifiers", ["company_id"])

    # === mi_company_locations ===
    op.create_table(
        "mi_company_locations",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("company_id", sa.BigInteger, sa.ForeignKey("mi_companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("location_type", sa.String(20), server_default="HQ"),
        sa.Column("street", sa.String(300)),
        sa.Column("zip_code", sa.String(10)),
        sa.Column("city", sa.String(200)),
        sa.Column("canton", sa.String(2)),
        sa.Column("country", sa.String(2), server_default="CH"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_mi_locations_company", "mi_company_locations", ["company_id"])
    op.create_index("idx_mi_locations_canton", "mi_company_locations", ["canton"])
    op.create_index("idx_mi_locations_zip", "mi_company_locations", ["zip_code"])

    # === mi_source_records ===
    op.create_table(
        "mi_source_records",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("company_id", sa.BigInteger, sa.ForeignKey("mi_companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_type", sa.String(30), nullable=False),
        sa.Column("source_url", sa.String(1000)),
        sa.Column("raw_data", JSONB),
        sa.Column("ingestion_job_id", sa.String(100)),
        sa.Column("ingested_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_mi_sources_company", "mi_source_records", ["company_id"])
    op.create_index("idx_mi_sources_type", "mi_source_records", ["source_type"])
    op.create_index("idx_mi_sources_job", "mi_source_records", ["ingestion_job_id"])

    # === mi_company_events ===
    op.create_table(
        "mi_company_events",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("company_id", sa.BigInteger, sa.ForeignKey("mi_companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("event_date", sa.Date),
        sa.Column("summary", sa.Text),
        sa.Column("source_type", sa.String(30)),
        sa.Column("source_ref", sa.String(500)),
        sa.Column("raw_data", JSONB),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_mi_events_company", "mi_company_events", ["company_id"])
    op.create_index("idx_mi_events_type", "mi_company_events", ["event_type"])
    op.create_index("idx_mi_events_date", "mi_company_events", ["event_date"])

    # === mi_enrichments ===
    op.create_table(
        "mi_enrichments",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("company_id", sa.BigInteger, sa.ForeignKey("mi_companies.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("website", sa.String(500)),
        sa.Column("email_general", sa.String(300)),
        sa.Column("phone", sa.String(50)),
        sa.Column("has_contact_form", sa.Boolean, server_default="false"),
        sa.Column("services", ARRAY(sa.String)),
        sa.Column("service_regions", ARRAY(sa.String)),
        sa.Column("digital_maturity_score", sa.Integer),
        sa.Column("last_enriched_at", sa.DateTime),
        sa.Column("enrichment_source", sa.String(30)),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    # === mi_contacts ===
    op.create_table(
        "mi_contacts",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("company_id", sa.BigInteger, sa.ForeignKey("mi_companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("first_name", sa.String(200)),
        sa.Column("last_name", sa.String(200)),
        sa.Column("role", sa.String(100)),
        sa.Column("email", sa.String(300)),
        sa.Column("phone", sa.String(50)),
        sa.Column("source", sa.String(30), nullable=False),
        sa.Column("source_url", sa.String(1000)),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_mi_contacts_company", "mi_contacts", ["company_id"])
    op.create_index("idx_mi_contacts_email", "mi_contacts", ["email"])

    # === mi_contact_permissions ===
    op.create_table(
        "mi_contact_permissions",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("contact_id", sa.BigInteger, sa.ForeignKey("mi_contacts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("permission_type", sa.String(30), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="UNKNOWN"),
        sa.Column("granted_at", sa.DateTime),
        sa.Column("revoked_at", sa.DateTime),
        sa.Column("source", sa.String(100)),
        sa.Column("notes", sa.String(500)),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
        sa.UniqueConstraint("contact_id", "permission_type", name="uq_contact_permission"),
    )
    op.create_index("idx_mi_permissions_contact", "mi_contact_permissions", ["contact_id"])
    op.create_index("idx_mi_permissions_status", "mi_contact_permissions", ["status"])

    # === mi_lead_accounts ===
    op.create_table(
        "mi_lead_accounts",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("company_id", sa.BigInteger, sa.ForeignKey("mi_companies.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("is_baunex_customer", sa.Boolean, server_default="false"),
        sa.Column("is_baunex_trial", sa.Boolean, server_default="false"),
        sa.Column("had_demo", sa.Boolean, server_default="false"),
        sa.Column("lead_status", sa.String(30), nullable=False, server_default="NEW"),
        sa.Column("lead_score", sa.Integer, server_default="0"),
        sa.Column("lead_temperature", sa.String(10)),
        sa.Column("sales_owner", sa.String(200)),
        sa.Column("priority", sa.String(10), server_default="MEDIUM"),
        sa.Column("deal_value_est", sa.Numeric(10, 2)),
        sa.Column("next_action", sa.String(500)),
        sa.Column("next_action_date", sa.Date),
        sa.Column("first_contacted_at", sa.DateTime),
        sa.Column("last_contacted_at", sa.DateTime),
        sa.Column("lost_reason", sa.String(500)),
        sa.Column("notes", sa.Text),
        sa.Column("tags", ARRAY(sa.String)),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_mi_leads_status", "mi_lead_accounts", ["lead_status"])
    op.create_index("idx_mi_leads_score", "mi_lead_accounts", [sa.text("lead_score DESC")])
    op.create_index("idx_mi_leads_owner", "mi_lead_accounts", ["sales_owner"])
    op.create_index("idx_mi_leads_temperature", "mi_lead_accounts", ["lead_temperature"])

    # === mi_lead_interactions ===
    op.create_table(
        "mi_lead_interactions",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("lead_id", sa.BigInteger, sa.ForeignKey("mi_lead_accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("contact_id", sa.BigInteger, sa.ForeignKey("mi_contacts.id")),
        sa.Column("interaction_type", sa.String(30), nullable=False),
        sa.Column("direction", sa.String(10)),
        sa.Column("subject", sa.String(500)),
        sa.Column("body", sa.Text),
        sa.Column("outcome", sa.String(30)),
        sa.Column("performed_by", sa.String(200)),
        sa.Column("performed_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_mi_interactions_lead", "mi_lead_interactions", ["lead_id"])
    op.create_index("idx_mi_interactions_type", "mi_lead_interactions", ["interaction_type"])
    op.create_index("idx_mi_interactions_date", "mi_lead_interactions", ["performed_at"])

    # === mi_campaigns ===
    op.create_table(
        "mi_campaigns",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("campaign_type", sa.String(30), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="DRAFT"),
        sa.Column("segment_filter", JSONB),
        sa.Column("created_by", sa.String(200)),
        sa.Column("started_at", sa.DateTime),
        sa.Column("completed_at", sa.DateTime),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    # === mi_campaign_recipients ===
    op.create_table(
        "mi_campaign_recipients",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("campaign_id", sa.BigInteger, sa.ForeignKey("mi_campaigns.id", ondelete="CASCADE"), nullable=False),
        sa.Column("lead_id", sa.BigInteger, sa.ForeignKey("mi_lead_accounts.id"), nullable=False),
        sa.Column("contact_id", sa.BigInteger, sa.ForeignKey("mi_contacts.id")),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("sent_at", sa.DateTime),
        sa.Column("opened_at", sa.DateTime),
        sa.Column("replied_at", sa.DateTime),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_mi_recipients_campaign", "mi_campaign_recipients", ["campaign_id"])
    op.create_index("idx_mi_recipients_lead", "mi_campaign_recipients", ["lead_id"])
    op.create_index("idx_mi_recipients_status", "mi_campaign_recipients", ["status"])

    # === mi_suppression_list ===
    op.create_table(
        "mi_suppression_list",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("entry_type", sa.String(20), nullable=False),
        sa.Column("entry_value", sa.String(500), nullable=False),
        sa.Column("reason", sa.String(100)),
        sa.Column("source", sa.String(100)),
        sa.Column("suppressed_at", sa.DateTime, server_default=sa.func.now()),
        sa.UniqueConstraint("entry_type", "entry_value", name="uq_suppression_entry"),
    )
    op.create_index("idx_mi_suppression_type", "mi_suppression_list", ["entry_type"])

    # === mi_ingestion_jobs ===
    op.create_table(
        "mi_ingestion_jobs",
        sa.Column("id", sa.String(100), primary_key=True),
        sa.Column("source_type", sa.String(30), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="RUNNING"),
        sa.Column("started_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime),
        sa.Column("records_fetched", sa.Integer, server_default="0"),
        sa.Column("records_created", sa.Integer, server_default="0"),
        sa.Column("records_updated", sa.Integer, server_default="0"),
        sa.Column("records_skipped", sa.Integer, server_default="0"),
        sa.Column("error_message", sa.Text),
        sa.Column("metadata", JSONB),
    )


def downgrade():
    op.drop_table("mi_ingestion_jobs")
    op.drop_table("mi_suppression_list")
    op.drop_table("mi_campaign_recipients")
    op.drop_table("mi_campaigns")
    op.drop_table("mi_lead_interactions")
    op.drop_table("mi_lead_accounts")
    op.drop_table("mi_contact_permissions")
    op.drop_table("mi_contacts")
    op.drop_table("mi_enrichments")
    op.drop_table("mi_company_events")
    op.drop_table("mi_source_records")
    op.drop_table("mi_company_locations")
    op.drop_table("mi_company_identifiers")
    op.drop_table("mi_companies")
