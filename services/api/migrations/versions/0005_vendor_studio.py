"""vendor provenance and comparison evidence"""
# ruff: noqa: E501

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0005_vendor_studio"
down_revision = "0004_budget_timeline"
branch_labels = None
depends_on = None


def upgrade():
    for name, col in [
        ("location", sa.String(200)),
        ("availability_evidence", sa.String(500)),
        ("cancellation_terms", sa.String(1000)),
        ("deposit_minor", sa.BigInteger()),
        ("source_label", sa.String(120)),
    ]:
        op.add_column(
            "vendors",
            sa.Column(
                name,
                col,
                nullable=name not in {"location", "source_label"},
                server_default="" if name in {"location", "source_label"} else None,
            ),
        )
    op.add_column(
        "vendors",
        sa.Column(
            "service_inclusions",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    op.drop_constraint("vendor_manual_only", "vendors", type_="check")
    op.create_check_constraint(
        "vendor_provenance",
        "vendors",
        "provenance IN ('user_provided','demo_seeded','verified_evidence','ai_estimate')",
    )
    op.create_check_constraint(
        "vendor_deposit",
        "vendors",
        "deposit_minor IS NULL OR deposit_minor BETWEEN 0 AND 9007199254740991",
    )
    op.create_check_constraint(
        "vendor_inclusions",
        "vendors",
        "jsonb_typeof(service_inclusions) = 'array' AND jsonb_array_length(service_inclusions) <= 20",
    )
    for name, col in [
        ("provenance", sa.String(32)),
        ("cancellation_terms", sa.String(1000)),
        ("deposit_minor", sa.BigInteger()),
        ("availability_evidence", sa.String(500)),
    ]:
        op.add_column(
            "vendor_quotes",
            sa.Column(
                name,
                col,
                nullable=name not in {"provenance"},
                server_default="user_provided" if name == "provenance" else None,
            ),
        )
    op.add_column(
        "vendor_quotes",
        sa.Column(
            "inclusions",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    op.create_check_constraint(
        "quote_provenance",
        "vendor_quotes",
        "provenance IN ('user_provided','demo_seeded','verified_evidence','ai_estimate')",
    )
    op.create_check_constraint(
        "quote_deposit",
        "vendor_quotes",
        "deposit_minor IS NULL OR deposit_minor BETWEEN 0 AND 9007199254740991",
    )
    op.execute(
        """DO $$ BEGIN IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='eventora_app') THEN GRANT SELECT, INSERT, UPDATE ON vendors, vendor_quotes TO eventora_app; END IF; END $$"""
    )


def downgrade():
    op.execute(
        """DO $$ BEGIN IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='eventora_app') THEN REVOKE INSERT, UPDATE ON vendors, vendor_quotes FROM eventora_app; END IF; END $$"""
    )
    op.drop_constraint("quote_deposit", "vendor_quotes", type_="check")
    op.drop_constraint("quote_provenance", "vendor_quotes", type_="check")
    for col in (
        "inclusions",
        "availability_evidence",
        "deposit_minor",
        "cancellation_terms",
        "provenance",
    ):
        op.drop_column("vendor_quotes", col)
    op.drop_constraint("vendor_inclusions", "vendors", type_="check")
    op.drop_constraint("vendor_deposit", "vendors", type_="check")
    op.drop_constraint("vendor_provenance", "vendors", type_="check")
    op.create_check_constraint("vendor_manual_only", "vendors", "provenance = 'user_provided'")
    for col in (
        "service_inclusions",
        "source_label",
        "deposit_minor",
        "cancellation_terms",
        "availability_evidence",
        "location",
    ):
        op.drop_column("vendors", col)
