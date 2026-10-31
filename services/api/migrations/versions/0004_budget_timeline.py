"""deterministic budget and timeline fields"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0004_budget_timeline"
down_revision = "0003_ai"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "events", sa.Column("contingency_bps", sa.Integer(), server_default="0", nullable=False)
    )
    op.create_check_constraint("event_contingency", "events", "contingency_bps BETWEEN 0 AND 5000")
    op.add_column(
        "budget_items",
        sa.Column("estimated_minor", sa.BigInteger(), server_default="0", nullable=False),
    )
    op.add_column(
        "budget_items",
        sa.Column("planned_minor", sa.BigInteger(), server_default="0", nullable=False),
    )
    op.add_column(
        "budget_items",
        sa.Column("actual_minor", sa.BigInteger(), server_default="0", nullable=False),
    )
    op.add_column(
        "budget_items",
        sa.Column("scenario", sa.String(16), server_default="balanced", nullable=False),
    )
    op.create_check_constraint(
        "budget_scenario_money",
        "budget_items",
        "estimated_minor BETWEEN 0 AND 9007199254740991 "
        "AND planned_minor BETWEEN 0 AND 9007199254740991 "
        "AND actual_minor BETWEEN 0 AND 9007199254740991",
    )
    op.create_check_constraint(
        "budget_scenario", "budget_items", "scenario IN ('economical','balanced','premium')"
    )
    op.add_column("tasks", sa.Column("owner", sa.String(100), server_default="", nullable=False))
    op.add_column(
        "tasks", sa.Column("priority", sa.String(16), server_default="normal", nullable=False)
    )
    op.add_column(
        "tasks",
        sa.Column(
            "depends_on",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    op.create_check_constraint(
        "task_priority", "tasks", "priority IN ('low','normal','high','critical')"
    )
    op.create_check_constraint(
        "task_dependencies",
        "tasks",
        "jsonb_typeof(depends_on) = 'array' AND jsonb_array_length(depends_on) <= 20",
    )
    op.execute("""DO $$ BEGIN IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='eventora_app') THEN
      GRANT SELECT, INSERT, UPDATE ON budget_items, tasks TO eventora_app;
    END IF; END $$""")


def downgrade():
    op.drop_constraint("event_contingency", "events", type_="check")
    op.drop_column("events", "contingency_bps")
    op.execute(
        """DO $$ BEGIN IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='eventora_app') THEN
        REVOKE INSERT, UPDATE ON budget_items, tasks FROM eventora_app;
        END IF; END $$"""
    )
    op.drop_constraint("task_dependencies", "tasks", type_="check")
    op.drop_constraint("task_priority", "tasks", type_="check")
    op.drop_column("tasks", "depends_on")
    op.drop_column("tasks", "priority")
    op.drop_column("tasks", "owner")
    op.drop_constraint("budget_scenario", "budget_items", type_="check")
    op.drop_constraint("budget_scenario_money", "budget_items", type_="check")
    op.drop_column("budget_items", "scenario")
    op.drop_column("budget_items", "actual_minor")
    op.drop_column("budget_items", "planned_minor")
    op.drop_column("budget_items", "estimated_minor")
