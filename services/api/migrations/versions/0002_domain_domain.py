"""Phase 2 domain, session, ownership and audit schema. Reviewed frozen migration."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0002_domain"
down_revision = "0001_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "auth_limits",
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.CheckConstraint("attempts >= 1", name="auth_attempts_positive"),
        sa.PrimaryKeyConstraint("key"),
    )
    op.create_index(
        op.f("ix_auth_limits_window_start"), "auth_limits", ["window_start"], unique=False
    )
    op.create_table(
        "users",
        sa.Column("username", sa.String(length=32), nullable=False),
        sa.Column("display_name", sa.String(length=100), nullable=False),
        sa.Column("password_hash", sa.String(length=256), nullable=False),
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
        sa.CheckConstraint("username ~ '^[a-z0-9_]{3,32}$'", name="user_username"),
        sa.CheckConstraint(
            "length(trim(display_name)) BETWEEN 1 AND 100", name="user_display_name"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
    )
    op.create_table(
        "organizations",
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
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
        sa.CheckConstraint("length(trim(name)) BETWEEN 1 AND 160", name="organization_name"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "owner_id", name="organization_owner"),
    )
    op.create_index("ix_organizations_owner", "organizations", ["owner_id"], unique=False)
    op.create_table(
        "sessions",
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("expires_at > created_at", name="session_expiry"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("token_hash"),
    )
    op.create_index(op.f("ix_sessions_expires_at"), "sessions", ["expires_at"], unique=False)
    op.create_index(op.f("ix_sessions_user_id"), "sessions", ["user_id"], unique=False)
    op.create_table(
        "events",
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("event_type", sa.String(length=16), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("location", sa.String(length=300), nullable=True),
        sa.Column("guest_count", sa.Integer(), nullable=True),
        sa.Column("budget_ceiling_minor", sa.BigInteger(), nullable=True),
        sa.Column(
            "preferences",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("dietary_needs", sa.String(length=2000), nullable=True),
        sa.Column("accessibility_needs", sa.String(length=2000), nullable=True),
        sa.Column("status", sa.String(length=16), server_default="draft", nullable=False),
        sa.Column("revision", sa.Integer(), server_default="1", nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.CheckConstraint(
            "(status = 'archived') = (archived_at IS NOT NULL)", name="event_archive"
        ),
        sa.CheckConstraint(
            "currency IN ('INR','USD','EUR','GBP','JPY')", name="event_currency_code"
        ),
        sa.CheckConstraint("event_type IN ('wedding','birthday','community')", name="event_type"),
        sa.CheckConstraint(
            "jsonb_typeof(preferences) = 'array' AND jsonb_array_length(preferences) <= 20",
            name="event_preferences",
        ),
        sa.CheckConstraint(
            "status IN ('draft','confirmed','completed','cancelled','archived')",
            name="event_status",
        ),
        sa.CheckConstraint(
            "status NOT IN ('confirmed','completed') OR (starts_at IS NOT NULL "
            "AND length(trim(location)) > 0 AND location IS NOT NULL "
            "AND guest_count IS NOT NULL AND budget_ceiling_minor IS NOT NULL "
            "AND dietary_needs IS NOT NULL AND accessibility_needs IS NOT NULL)",
            name="event_complete_intake",
        ),
        sa.CheckConstraint(
            "budget_ceiling_minor IS NULL OR budget_ceiling_minor BETWEEN 0 AND 9007199254740991",
            name="event_budget",
        ),
        sa.CheckConstraint(
            "ends_at IS NULL OR (starts_at IS NOT NULL AND ends_at > starts_at)", name="event_dates"
        ),
        sa.CheckConstraint(
            "guest_count IS NULL OR guest_count BETWEEN 1 AND 1000000", name="event_guests"
        ),
        sa.CheckConstraint("length(timezone) BETWEEN 1 AND 64", name="event_timezone"),
        sa.CheckConstraint("length(trim(title)) BETWEEN 1 AND 160", name="event_title"),
        sa.CheckConstraint("revision >= 1", name="event_revision"),
        sa.ForeignKeyConstraint(
            ["organization_id", "owner_id"],
            ["organizations.id", "organizations.owner_id"],
            name="event_organization_owner",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "currency", name="event_currency"),
        sa.UniqueConstraint("id", "owner_id", name="event_owner"),
    )
    op.create_index("ix_events_organization", "events", ["organization_id"], unique=False)
    op.create_index(
        "ix_events_owner_created", "events", ["owner_id", "created_at", "id"], unique=False
    )
    op.create_index(
        "ix_events_owner_status", "events", ["owner_id", "status", "created_at", "id"], unique=False
    )
    op.create_table(
        "audit_events",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("changed_fields", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "action IN ('event.created','event.updated','event.archived')", name="audit_action"
        ),
        sa.CheckConstraint(
            "jsonb_typeof(changed_fields) = 'array' AND jsonb_array_length(changed_fields) <= 30",
            name="audit_fields",
        ),
        sa.CheckConstraint("revision >= 1", name="audit_revision"),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["event_id", "actor_id"],
            ["events.id", "events.owner_id"],
            name="audit_event_owner",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_actor", "audit_events", ["actor_id"], unique=False)
    op.create_index(
        "ix_audit_event_created", "audit_events", ["event_id", "created_at"], unique=False
    )
    op.create_table(
        "event_plan_versions",
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("base_event_revision", sa.Integer(), nullable=False),
        sa.Column("parent_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="draft", nullable=False),
        sa.Column("approved_by", sa.Uuid(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.CheckConstraint(
            "(status = 'approved' AND approved_by IS NOT NULL AND approved_at IS NOT NULL) "
            "OR (status <> 'approved' AND approved_by IS NULL AND approved_at IS NULL)",
            name="plan_approval",
        ),
        sa.CheckConstraint(
            "status IN ('draft','proposed','approved','rejected')", name="plan_status"
        ),
        sa.CheckConstraint("length(trim(title)) BETWEEN 1 AND 160", name="plan_title"),
        sa.CheckConstraint("parent_id IS NULL OR parent_id <> id", name="plan_not_own_parent"),
        sa.CheckConstraint(
            "sequence >= 1 AND base_event_revision >= 1", name="plan_positive_revisions"
        ),
        sa.ForeignKeyConstraint(
            ["event_id", "approved_by"],
            ["events.id", "events.owner_id"],
            name="plan_approver_owner",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["parent_id", "event_id"],
            ["event_plan_versions.id", "event_plan_versions.event_id"],
            name="plan_parent_event",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id", "sequence", name="plan_sequence"),
        sa.UniqueConstraint("id", "event_id", name="plan_event"),
    )
    op.create_table(
        "guests",
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("contact", sa.String(length=300), nullable=False),
        sa.Column("rsvp_status", sa.String(length=16), nullable=False),
        sa.Column("party_size", sa.Integer(), nullable=False),
        sa.Column("dietary_needs", sa.String(length=2000), nullable=True),
        sa.Column("accessibility_needs", sa.String(length=2000), nullable=True),
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
        sa.CheckConstraint(
            "rsvp_status IN ('pending','attending','declined','tentative')", name="guest_rsvp"
        ),
        sa.CheckConstraint("length(trim(name)) > 0", name="guest_name"),
        sa.CheckConstraint("party_size BETWEEN 1 AND 100", name="guest_party_size"),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_guests_event_rsvp", "guests", ["event_id", "rsvp_status"], unique=False)
    op.create_table(
        "vendors",
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("category", sa.String(length=80), nullable=False),
        sa.Column("contact", sa.String(length=300), nullable=False),
        sa.Column("notes", sa.String(length=2000), nullable=False),
        sa.Column("provenance", sa.String(length=32), nullable=False),
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
        sa.CheckConstraint("provenance = 'user_provided'", name="vendor_manual_only"),
        sa.CheckConstraint(
            "length(trim(name)) > 0 AND length(trim(category)) > 0", name="vendor_name_category"
        ),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "event_id", name="vendor_event"),
    )
    op.create_index("ix_vendors_event", "vendors", ["event_id"], unique=False)
    op.create_table(
        "budget_items",
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("plan_id", sa.Uuid(), nullable=False),
        sa.Column("category", sa.String(length=80), nullable=False),
        sa.Column("description", sa.String(length=160), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_amount_minor", sa.BigInteger(), nullable=False),
        sa.Column("tax_minor", sa.BigInteger(), nullable=False),
        sa.Column("fee_minor", sa.BigInteger(), nullable=False),
        sa.Column(
            "total_minor",
            sa.BigInteger(),
            sa.Computed(
                "quantity::numeric * unit_amount_minor + tax_minor + fee_minor", persisted=True
            ),
            nullable=False,
        ),
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
        sa.CheckConstraint(
            "length(trim(category)) > 0 AND length(trim(description)) > 0",
            name="budget_description",
        ),
        sa.CheckConstraint("quantity BETWEEN 1 AND 1000000", name="budget_quantity"),
        sa.CheckConstraint(
            "unit_amount_minor BETWEEN 0 AND 9007199254740991 "
            "AND tax_minor BETWEEN 0 AND 9007199254740991 "
            "AND fee_minor BETWEEN 0 AND 9007199254740991 "
            "AND total_minor BETWEEN 0 AND 9007199254740991",
            name="budget_money",
        ),
        sa.ForeignKeyConstraint(
            ["event_id", "currency"],
            ["events.id", "events.currency"],
            name="budget_event_currency",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["plan_id", "event_id"],
            ["event_plan_versions.id", "event_plan_versions.event_id"],
            name="budget_plan_event",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_budget_event_plan", "budget_items", ["event_id", "plan_id"], unique=False)
    op.create_table(
        "tasks",
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("plan_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("description", sa.String(length=2000), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.CheckConstraint(
            "(status = 'done') = (completed_at IS NOT NULL)", name="task_completion"
        ),
        sa.CheckConstraint(
            "status IN ('todo','in_progress','done','cancelled')", name="task_status"
        ),
        sa.CheckConstraint("length(trim(title)) > 0", name="task_title"),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["plan_id", "event_id"],
            ["event_plan_versions.id", "event_plan_versions.event_id"],
            name="task_plan_event",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tasks_event_due", "tasks", ["event_id", "due_at"], unique=False)
    op.create_table(
        "vendor_quotes",
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("vendor_id", sa.Uuid(), nullable=False),
        sa.Column("amount_minor", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("issued_on", sa.Date(), nullable=False),
        sa.Column("valid_until", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("reference", sa.String(length=300), nullable=False),
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
        sa.CheckConstraint(
            "status IN ('received','accepted','rejected','expired')", name="quote_status"
        ),
        sa.CheckConstraint("amount_minor BETWEEN 0 AND 9007199254740991", name="quote_money"),
        sa.CheckConstraint("valid_until IS NULL OR valid_until >= issued_on", name="quote_dates"),
        sa.ForeignKeyConstraint(
            ["event_id", "currency"],
            ["events.id", "events.currency"],
            name="quote_event_currency",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["vendor_id", "event_id"],
            ["vendors.id", "vendors.event_id"],
            name="quote_vendor_event",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_quotes_event_vendor", "vendor_quotes", ["event_id", "vendor_id"], unique=False
    )
    op.execute("""
        CREATE FUNCTION eventora_event_guard() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          IF TG_OP = 'UPDATE' AND NEW.owner_id <> OLD.owner_id THEN
            RAISE EXCEPTION 'Event ownership is immutable' USING ERRCODE = '23514';
          END IF;
          -- Validate one zone directly; enumerating the full timezone catalog
          -- on every write is expensive, particularly on a cold Windows cache.
          PERFORM CURRENT_TIMESTAMP AT TIME ZONE NEW.timezone;
          RETURN NEW;
        END $$;
        CREATE TRIGGER eventora_event_guard BEFORE INSERT OR UPDATE ON events
          FOR EACH ROW EXECUTE FUNCTION eventora_event_guard();
        CREATE FUNCTION eventora_audit_guard() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          RAISE EXCEPTION 'Audit entries are append only' USING ERRCODE = '23514';
        END $$;
        CREATE TRIGGER eventora_audit_guard BEFORE UPDATE OR DELETE ON audit_events
          FOR EACH ROW EXECUTE FUNCTION eventora_audit_guard();
    """)
    # Local/Compose runtime has no DDL, ownership transfer or audit mutation rights.
    # CI may use an isolated single database owner with no eventora_app role.
    op.execute("""
        DO $$ BEGIN
          IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'eventora_app') THEN
            GRANT SELECT, INSERT ON users, audit_events TO eventora_app;
            GRANT SELECT, INSERT, UPDATE ON events TO eventora_app;
            GRANT SELECT, INSERT, UPDATE, DELETE ON sessions, auth_limits TO eventora_app;
          END IF;
        END $$;
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER eventora_event_guard ON events")
    op.execute("DROP TRIGGER eventora_audit_guard ON audit_events")
    op.execute("DROP FUNCTION eventora_event_guard()")
    op.execute("DROP FUNCTION eventora_audit_guard()")
    op.drop_index("ix_quotes_event_vendor", table_name="vendor_quotes")
    op.drop_table("vendor_quotes")
    op.drop_index("ix_tasks_event_due", table_name="tasks")
    op.drop_table("tasks")
    op.drop_index("ix_budget_event_plan", table_name="budget_items")
    op.drop_table("budget_items")
    op.drop_index("ix_vendors_event", table_name="vendors")
    op.drop_table("vendors")
    op.drop_index("ix_guests_event_rsvp", table_name="guests")
    op.drop_table("guests")
    op.drop_table("event_plan_versions")
    op.drop_index("ix_audit_event_created", table_name="audit_events")
    op.drop_index("ix_audit_actor", table_name="audit_events")
    op.drop_table("audit_events")
    op.drop_index("ix_events_owner_status", table_name="events")
    op.drop_index("ix_events_owner_created", table_name="events")
    op.drop_index("ix_events_organization", table_name="events")
    op.drop_table("events")
    op.drop_index(op.f("ix_sessions_user_id"), table_name="sessions")
    op.drop_index(op.f("ix_sessions_expires_at"), table_name="sessions")
    op.drop_table("sessions")
    op.drop_index("ix_organizations_owner", table_name="organizations")
    op.drop_table("organizations")
    op.drop_table("users")
    op.drop_index(op.f("ix_auth_limits_window_start"), table_name="auth_limits")
    op.drop_table("auth_limits")
