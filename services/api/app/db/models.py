"""Phase 2 relational model. Children always carry their event boundary."""
# ruff: noqa: E501

from datetime import date, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Computed,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Record:
    id: Mapped[UUID] = mapped_column(
        primary_key=True, default=uuid4, server_default=text("gen_random_uuid()")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class User(Record, Base):
    __tablename__ = "users"
    username: Mapped[str] = mapped_column(String(32), unique=True)
    display_name: Mapped[str] = mapped_column(String(100))
    password_hash: Mapped[str] = mapped_column(String(256))
    __table_args__ = (
        CheckConstraint("username ~ '^[a-z0-9_]{3,32}$'", name="user_username"),
        CheckConstraint("length(trim(display_name)) BETWEEN 1 AND 100", name="user_display_name"),
    )


class Organization(Record, Base):
    __tablename__ = "organizations"
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    name: Mapped[str] = mapped_column(String(160))
    __table_args__ = (
        UniqueConstraint("id", "owner_id", name="organization_owner"),
        CheckConstraint("length(trim(name)) BETWEEN 1 AND 160", name="organization_name"),
        Index("ix_organizations_owner", "owner_id"),
    )


class Session(Base):
    __tablename__ = "sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (CheckConstraint("expires_at > created_at", name="session_expiry"),)


class AuthLimit(Base):
    __tablename__ = "auth_limits"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    attempts: Mapped[int] = mapped_column(Integer)
    __table_args__ = (CheckConstraint("attempts >= 1", name="auth_attempts_positive"),)


class Event(Record, Base):
    __tablename__ = "events"
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    organization_id: Mapped[UUID | None]
    title: Mapped[str] = mapped_column(String(160))
    event_type: Mapped[str] = mapped_column(String(16))
    timezone: Mapped[str] = mapped_column(String(64))
    currency: Mapped[str] = mapped_column(String(3))
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    location: Mapped[str | None] = mapped_column(String(300))
    guest_count: Mapped[int | None] = mapped_column(Integer)
    budget_ceiling_minor: Mapped[int | None] = mapped_column(BigInteger)
    contingency_bps: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    preferences: Mapped[list[str]] = mapped_column(
        JSONB, default=list, server_default=text("'[]'::jsonb")
    )
    dietary_needs: Mapped[str | None] = mapped_column(String(2000))
    accessibility_needs: Mapped[str | None] = mapped_column(String(2000))
    status: Mapped[str] = mapped_column(String(16), default="draft", server_default="draft")
    revision: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        UniqueConstraint("id", "currency", name="event_currency"),
        UniqueConstraint("id", "owner_id", name="event_owner"),
        ForeignKeyConstraint(
            ["organization_id", "owner_id"],
            ["organizations.id", "organizations.owner_id"],
            name="event_organization_owner",
            ondelete="RESTRICT",
        ),
        CheckConstraint("length(trim(title)) BETWEEN 1 AND 160", name="event_title"),
        CheckConstraint("event_type IN ('wedding','birthday','community')", name="event_type"),
        CheckConstraint("currency IN ('INR','USD','EUR','GBP','JPY')", name="event_currency_code"),
        CheckConstraint("length(timezone) BETWEEN 1 AND 64", name="event_timezone"),
        CheckConstraint(
            "guest_count IS NULL OR guest_count BETWEEN 1 AND 1000000", name="event_guests"
        ),
        CheckConstraint("contingency_bps BETWEEN 0 AND 5000", name="event_contingency"),
        CheckConstraint(
            "budget_ceiling_minor IS NULL OR budget_ceiling_minor BETWEEN 0 AND 9007199254740991",
            name="event_budget",
        ),
        CheckConstraint(
            "ends_at IS NULL OR (starts_at IS NOT NULL AND ends_at > starts_at)", name="event_dates"
        ),
        CheckConstraint(
            "status IN ('draft','confirmed','completed','cancelled','archived')",
            name="event_status",
        ),
        CheckConstraint(
            "status NOT IN ('confirmed','completed') OR (starts_at IS NOT NULL "
            "AND length(trim(location)) > 0 AND location IS NOT NULL "
            "AND guest_count IS NOT NULL AND budget_ceiling_minor IS NOT NULL "
            "AND dietary_needs IS NOT NULL AND accessibility_needs IS NOT NULL)",
            name="event_complete_intake",
        ),
        CheckConstraint("(status = 'archived') = (archived_at IS NOT NULL)", name="event_archive"),
        CheckConstraint("revision >= 1", name="event_revision"),
        CheckConstraint(
            "jsonb_typeof(preferences) = 'array' AND jsonb_array_length(preferences) <= 20",
            name="event_preferences",
        ),
        Index("ix_events_owner_created", "owner_id", "created_at", "id"),
        Index("ix_events_owner_status", "owner_id", "status", "created_at", "id"),
        Index("ix_events_organization", "organization_id"),
    )


class EventPlanVersion(Record, Base):
    __tablename__ = "event_plan_versions"
    event_id: Mapped[UUID] = mapped_column(ForeignKey("events.id", ondelete="RESTRICT"))
    sequence: Mapped[int] = mapped_column(Integer)
    base_event_revision: Mapped[int] = mapped_column(Integer)
    parent_id: Mapped[UUID | None]
    title: Mapped[str] = mapped_column(String(160))
    status: Mapped[str] = mapped_column(String(16), default="draft", server_default="draft")
    approved_by: Mapped[UUID | None]
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revision: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    intake: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    document: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    saved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    schema_version: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    prompt_version: Mapped[str | None] = mapped_column(String(64))
    __table_args__ = (
        UniqueConstraint("id", "event_id", name="plan_event"),
        UniqueConstraint("event_id", "sequence", name="plan_sequence"),
        ForeignKeyConstraint(
            ["parent_id", "event_id"],
            ["event_plan_versions.id", "event_plan_versions.event_id"],
            name="plan_parent_event",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["event_id", "approved_by"],
            ["events.id", "events.owner_id"],
            name="plan_approver_owner",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "sequence >= 1 AND base_event_revision >= 1", name="plan_positive_revisions"
        ),
        CheckConstraint("parent_id IS NULL OR parent_id <> id", name="plan_not_own_parent"),
        CheckConstraint("revision >= 1 AND schema_version >= 1", name="plan_document_revision"),
        CheckConstraint("(document IS NULL) = (intake IS NULL)", name="plan_document_intake"),
        CheckConstraint("length(trim(title)) BETWEEN 1 AND 160", name="plan_title"),
        CheckConstraint("status IN ('draft','proposed','approved','rejected')", name="plan_status"),
        CheckConstraint(
            "(status = 'approved' AND approved_by IS NOT NULL AND approved_at IS NOT NULL) "
            "OR (status <> 'approved' AND approved_by IS NULL AND approved_at IS NULL)",
            name="plan_approval",
        ),
    )


class BudgetItem(Record, Base):
    __tablename__ = "budget_items"
    event_id: Mapped[UUID]
    plan_id: Mapped[UUID]
    category: Mapped[str] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(String(160))
    currency: Mapped[str] = mapped_column(String(3))
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    unit_amount_minor: Mapped[int] = mapped_column(BigInteger)
    tax_minor: Mapped[int] = mapped_column(BigInteger, default=0)
    fee_minor: Mapped[int] = mapped_column(BigInteger, default=0)
    estimated_minor: Mapped[int] = mapped_column(BigInteger, default=0)
    planned_minor: Mapped[int] = mapped_column(BigInteger, default=0)
    actual_minor: Mapped[int] = mapped_column(BigInteger, default=0)
    scenario: Mapped[str] = mapped_column(String(16), default="balanced", server_default="balanced")
    total_minor: Mapped[int] = mapped_column(
        BigInteger,
        Computed("quantity::numeric * unit_amount_minor + tax_minor + fee_minor", persisted=True),
    )
    __table_args__ = (
        ForeignKeyConstraint(
            ["plan_id", "event_id"],
            ["event_plan_versions.id", "event_plan_versions.event_id"],
            name="budget_plan_event",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["event_id", "currency"],
            ["events.id", "events.currency"],
            name="budget_event_currency",
            ondelete="RESTRICT",
        ),
        CheckConstraint("quantity BETWEEN 1 AND 1000000", name="budget_quantity"),
        CheckConstraint(
            "unit_amount_minor BETWEEN 0 AND 9007199254740991 "
            "AND tax_minor BETWEEN 0 AND 9007199254740991 "
            "AND fee_minor BETWEEN 0 AND 9007199254740991 "
            "AND total_minor BETWEEN 0 AND 9007199254740991",
            name="budget_money",
        ),
        CheckConstraint(
            "estimated_minor BETWEEN 0 AND 9007199254740991 "
            "AND planned_minor BETWEEN 0 AND 9007199254740991 "
            "AND actual_minor BETWEEN 0 AND 9007199254740991",
            name="budget_scenario_money",
        ),
        CheckConstraint("scenario IN ('economical','balanced','premium')", name="budget_scenario"),
        CheckConstraint(
            "length(trim(category)) > 0 AND length(trim(description)) > 0",
            name="budget_description",
        ),
        Index("ix_budget_event_plan", "event_id", "plan_id"),
    )


class Task(Record, Base):
    __tablename__ = "tasks"
    event_id: Mapped[UUID] = mapped_column(ForeignKey("events.id", ondelete="RESTRICT"))
    plan_id: Mapped[UUID | None]
    title: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(String(2000), default="")
    status: Mapped[str] = mapped_column(String(16), default="todo")
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    owner: Mapped[str] = mapped_column(String(100), default="", server_default="")
    priority: Mapped[str] = mapped_column(String(16), default="normal", server_default="normal")
    depends_on: Mapped[list[str]] = mapped_column(
        JSONB, default=list, server_default=text("'[]'::jsonb")
    )
    __table_args__ = (
        ForeignKeyConstraint(
            ["plan_id", "event_id"],
            ["event_plan_versions.id", "event_plan_versions.event_id"],
            name="task_plan_event",
            ondelete="RESTRICT",
        ),
        CheckConstraint("status IN ('todo','in_progress','done','cancelled')", name="task_status"),
        CheckConstraint("(status = 'done') = (completed_at IS NOT NULL)", name="task_completion"),
        CheckConstraint("length(trim(title)) > 0", name="task_title"),
        CheckConstraint("priority IN ('low','normal','high','critical')", name="task_priority"),
        CheckConstraint(
            "jsonb_typeof(depends_on) = 'array' AND jsonb_array_length(depends_on) <= 20",
            name="task_dependencies",
        ),
        Index("ix_tasks_event_due", "event_id", "due_at"),
    )


class Vendor(Record, Base):
    __tablename__ = "vendors"
    event_id: Mapped[UUID] = mapped_column(ForeignKey("events.id", ondelete="RESTRICT"))
    name: Mapped[str] = mapped_column(String(160))
    category: Mapped[str] = mapped_column(String(80))
    contact: Mapped[str] = mapped_column(String(300), default="")
    notes: Mapped[str] = mapped_column(String(2000), default="")
    provenance: Mapped[str] = mapped_column(String(32), default="user_provided")
    location: Mapped[str] = mapped_column(String(200), default="", server_default="")
    service_inclusions: Mapped[list[str]] = mapped_column(
        JSONB, default=list, server_default=text("'[]'::jsonb")
    )
    availability_evidence: Mapped[str | None] = mapped_column(String(500))
    cancellation_terms: Mapped[str | None] = mapped_column(String(1000))
    deposit_minor: Mapped[int | None] = mapped_column(BigInteger)
    source_label: Mapped[str] = mapped_column(
        String(120), default="User-provided", server_default="User-provided"
    )
    __table_args__ = (
        UniqueConstraint("id", "event_id", name="vendor_event"),
        CheckConstraint(
            "length(trim(name)) > 0 AND length(trim(category)) > 0", name="vendor_name_category"
        ),
        CheckConstraint(
            "provenance IN ('user_provided','demo_seeded','verified_evidence','ai_estimate')",
            name="vendor_provenance",
        ),
        CheckConstraint(
            "deposit_minor IS NULL OR deposit_minor BETWEEN 0 AND 9007199254740991",
            name="vendor_deposit",
        ),
        CheckConstraint(
            "jsonb_typeof(service_inclusions) = 'array' AND jsonb_array_length(service_inclusions) <= 20",
            name="vendor_inclusions",
        ),
        Index("ix_vendors_event", "event_id"),
    )


class VendorQuote(Record, Base):
    __tablename__ = "vendor_quotes"
    event_id: Mapped[UUID]
    vendor_id: Mapped[UUID]
    amount_minor: Mapped[int] = mapped_column(BigInteger)
    currency: Mapped[str] = mapped_column(String(3))
    issued_on: Mapped[date] = mapped_column(Date)
    valid_until: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(16), default="received")
    reference: Mapped[str] = mapped_column(String(300), default="")
    provenance: Mapped[str] = mapped_column(
        String(32), default="user_provided", server_default="user_provided"
    )
    inclusions: Mapped[list[str]] = mapped_column(
        JSONB, default=list, server_default=text("'[]'::jsonb")
    )
    cancellation_terms: Mapped[str | None] = mapped_column(String(1000))
    deposit_minor: Mapped[int | None] = mapped_column(BigInteger)
    availability_evidence: Mapped[str | None] = mapped_column(String(500))
    __table_args__ = (
        ForeignKeyConstraint(
            ["vendor_id", "event_id"],
            ["vendors.id", "vendors.event_id"],
            name="quote_vendor_event",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["event_id", "currency"],
            ["events.id", "events.currency"],
            name="quote_event_currency",
            ondelete="RESTRICT",
        ),
        CheckConstraint("amount_minor BETWEEN 0 AND 9007199254740991", name="quote_money"),
        CheckConstraint(
            "provenance IN ('user_provided','demo_seeded','verified_evidence','ai_estimate')",
            name="quote_provenance",
        ),
        CheckConstraint(
            "deposit_minor IS NULL OR deposit_minor BETWEEN 0 AND 9007199254740991",
            name="quote_deposit",
        ),
        CheckConstraint("valid_until IS NULL OR valid_until >= issued_on", name="quote_dates"),
        CheckConstraint(
            "status IN ('received','accepted','rejected','expired')", name="quote_status"
        ),
        Index("ix_quotes_event_vendor", "event_id", "vendor_id"),
    )


class Guest(Record, Base):
    __tablename__ = "guests"
    event_id: Mapped[UUID] = mapped_column(ForeignKey("events.id", ondelete="RESTRICT"))
    name: Mapped[str] = mapped_column(String(160))
    contact: Mapped[str] = mapped_column(String(300), default="")
    rsvp_status: Mapped[str] = mapped_column(String(16), default="pending")
    party_size: Mapped[int] = mapped_column(Integer, default=1)
    dietary_needs: Mapped[str | None] = mapped_column(String(2000))
    accessibility_needs: Mapped[str | None] = mapped_column(String(2000))
    __table_args__ = (
        CheckConstraint("length(trim(name)) > 0", name="guest_name"),
        CheckConstraint(
            "rsvp_status IN ('pending','attending','declined','tentative')", name="guest_rsvp"
        ),
        CheckConstraint("party_size BETWEEN 1 AND 100", name="guest_party_size"),
        Index("ix_guests_event_rsvp", "event_id", "rsvp_status"),
    )


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[UUID] = mapped_column(
        primary_key=True, default=uuid4, server_default=text("gen_random_uuid()")
    )
    actor_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    event_id: Mapped[UUID | None]
    action: Mapped[str] = mapped_column(String(32))
    request_id: Mapped[UUID]
    revision: Mapped[int] = mapped_column(Integer)
    changed_fields: Mapped[list[str]] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (
        ForeignKeyConstraint(
            ["event_id", "actor_id"],
            ["events.id", "events.owner_id"],
            name="audit_event_owner",
            ondelete="RESTRICT",
        ),
        CheckConstraint("revision >= 1", name="audit_revision"),
        CheckConstraint(
            "action IN ('event.created','event.updated','event.archived',"
            "'plan.generated','plan.saved')",
            name="audit_action",
        ),
        CheckConstraint(
            "jsonb_typeof(changed_fields) = 'array' AND jsonb_array_length(changed_fields) <= 30",
            name="audit_fields",
        ),
        Index("ix_audit_event_created", "event_id", "created_at"),
        Index("ix_audit_actor", "actor_id"),
    )


class GenerationRun(Record, Base):
    __tablename__ = "generation_runs"
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    event_id: Mapped[UUID]
    request_key: Mapped[UUID]
    input_hash: Mapped[str] = mapped_column(String(64))
    operation: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(16), default="running")
    expected_revision: Mapped[int] = mapped_column(Integer)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    model: Mapped[str] = mapped_column(String(100))
    call_count: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    error_code: Mapped[str | None] = mapped_column(String(64))
    extraction: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    plan_id: Mapped[UUID | None]
    __table_args__ = (
        ForeignKeyConstraint(
            ["event_id", "owner_id"],
            ["events.id", "events.owner_id"],
            name="generation_owner",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["plan_id", "event_id"],
            ["event_plan_versions.id", "event_plan_versions.event_id"],
            name="generation_plan_event",
            ondelete="RESTRICT",
        ),
        UniqueConstraint("event_id", "request_key", name="generation_idempotency"),
        CheckConstraint("operation IN ('intake','plan')", name="generation_operation"),
        CheckConstraint("status IN ('running','succeeded','failed')", name="generation_status"),
        CheckConstraint(
            "call_count BETWEEN 0 AND 2 AND expected_revision >= 1", name="generation_bounds"
        ),
        Index("ix_generation_owner_created", "owner_id", "created_at"),
        Index("ix_generation_event_created", "event_id", "created_at", "id"),
    )


class ReplanProposal(Record, Base):
    __tablename__ = "replan_proposals"
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    event_id: Mapped[UUID]
    base_plan_id: Mapped[UUID]
    base_event_revision: Mapped[int] = mapped_column(Integer)
    change_type: Mapped[str] = mapped_column(String(32))
    request: Mapped[dict[str, Any]] = mapped_column(JSONB)
    impact: Mapped[dict[str, Any]] = mapped_column(JSONB)
    alternative: Mapped[dict[str, Any]] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(16), default="pending", server_default="pending")
    rejection_reason: Mapped[str | None] = mapped_column(String(500))
    accepted_plan_id: Mapped[UUID | None]
    __table_args__ = (
        ForeignKeyConstraint(
            ["event_id", "owner_id"],
            ["events.id", "events.owner_id"],
            name="replan_owner",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["base_plan_id", "event_id"],
            ["event_plan_versions.id", "event_plan_versions.event_id"],
            name="replan_base_plan",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["accepted_plan_id", "event_id"],
            ["event_plan_versions.id", "event_plan_versions.event_id"],
            name="replan_accepted_plan",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "change_type IN ('guest_count','venue_change','quote_increase','date_change','task_delay','budget_constraint')",
            name="replan_change_type",
        ),
        CheckConstraint(
            "status IN ('pending','accepted','rejected','stale')", name="replan_status"
        ),
        CheckConstraint("base_event_revision >= 1", name="replan_base_revision"),
        Index("ix_replan_event_created", "event_id", "created_at", "id"),
    )
