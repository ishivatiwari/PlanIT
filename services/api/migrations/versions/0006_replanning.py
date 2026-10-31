"""adaptive replanning proposals and immutable approvals"""
# ruff: noqa: E501

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0006_replanning"
down_revision = "0005_vendor_studio"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "replan_proposals",
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("base_plan_id", sa.Uuid(), nullable=False),
        sa.Column("base_event_revision", sa.Integer(), nullable=False),
        sa.Column("change_type", sa.String(32), nullable=False),
        sa.Column("request", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("impact", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("alternative", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(16), server_default="pending", nullable=False),
        sa.Column("rejection_reason", sa.String(500), nullable=True),
        sa.Column("accepted_plan_id", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["event_id", "owner_id"],
            ["events.id", "events.owner_id"],
            name="replan_owner",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"], ["users.id"], name="replan_user_owner", ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["base_plan_id", "event_id"],
            ["event_plan_versions.id", "event_plan_versions.event_id"],
            name="replan_base_plan",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["accepted_plan_id", "event_id"],
            ["event_plan_versions.id", "event_plan_versions.event_id"],
            name="replan_accepted_plan",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "change_type IN ('guest_count','venue_change','quote_increase','date_change','task_delay','budget_constraint')",
            name="replan_change_type",
        ),
        sa.CheckConstraint(
            "status IN ('pending','accepted','rejected','stale')", name="replan_status"
        ),
        sa.CheckConstraint("base_event_revision >= 1", name="replan_base_revision"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_replan_event_created", "replan_proposals", ["event_id", "created_at", "id"])
    op.drop_constraint("audit_action", "audit_events", type_="check")
    op.create_check_constraint(
        "audit_action",
        "audit_events",
        "action IN ('event.created','event.updated','event.archived','plan.generated','plan.saved','replan.proposed','replan.approved','replan.rejected')",
    )
    op.execute(
        """DO $$ BEGIN IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='eventora_app') THEN GRANT SELECT, INSERT, UPDATE ON replan_proposals, event_plan_versions TO eventora_app; END IF; END $$"""
    )


def downgrade():
    op.drop_constraint("audit_action", "audit_events", type_="check")
    op.create_check_constraint(
        "audit_action",
        "audit_events",
        "action IN ('event.created','event.updated','event.archived','plan.generated','plan.saved')",
    )
    op.execute(
        """DO $$ BEGIN IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='eventora_app') THEN REVOKE INSERT, UPDATE ON replan_proposals FROM eventora_app; END IF; END $$"""
    )
    op.drop_index("ix_replan_event_created", table_name="replan_proposals")
    op.drop_table("replan_proposals")
