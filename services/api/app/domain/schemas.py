"""Validated transport/domain contracts. Monetary amounts are integer minor units."""

from datetime import UTC, date, datetime
from typing import Annotated, Any, Literal, Self
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator, model_validator

MAX_MONEY = 9_007_199_254_740_991
Money = Annotated[StrictInt, Field(ge=0, le=MAX_MONEY)]
Count = Annotated[StrictInt, Field(ge=1, le=1_000_000)]
Title = Annotated[str, Field(min_length=1, max_length=160)]
Note = Annotated[str, Field(max_length=2000)]
Currency = Literal["INR", "USD", "EUR", "GBP", "JPY"]
EventType = Literal["wedding", "birthday", "community"]
EventStatus = Literal["draft", "confirmed", "completed", "cancelled"]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, from_attributes=True)


def local_instant(value: datetime | None, zone: str, fold: int | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is not None:
        raise ValueError("Use a local date and time without an offset, and an IANA timezone.")
    timezone = ZoneInfo(zone)
    candidates = [value.replace(tzinfo=timezone, fold=n) for n in (0, 1)]
    valid = [
        item
        for item in candidates
        if item.astimezone(UTC).astimezone(timezone).replace(tzinfo=None) == value
    ]
    if not valid:
        raise ValueError(
            "This local time does not exist because the clocks change. Choose another time."
        )
    if len({item.utcoffset() for item in valid}) > 1 and fold is None:
        raise ValueError("This local time occurs twice. Choose the first or second occurrence.")
    return candidates[fold or 0].astimezone(UTC)


class EventWrite(Contract):
    title: Title
    event_type: EventType
    timezone: Annotated[str, Field(min_length=1, max_length=64)] = "Asia/Kolkata"
    currency: Currency = "INR"
    start_local: datetime | None = None
    end_local: datetime | None = None
    start_fold: Literal[0, 1] | None = None
    end_fold: Literal[0, 1] | None = None
    location: Annotated[str, Field(max_length=300)] | None = None
    guest_count: Count | None = None
    budget_ceiling_minor: Money | None = None
    contingency_bps: Annotated[StrictInt, Field(ge=0, le=5000)] = 0
    preferences: Annotated[
        list[Annotated[str, Field(min_length=1, max_length=120)]], Field(max_length=20)
    ] = Field(default_factory=list)
    dietary_needs: Note | None = None
    accessibility_needs: Note | None = None
    status: EventStatus = "draft"

    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError, ValueError:
            raise ValueError("Choose a valid IANA timezone, such as Asia/Kolkata.") from None
        return value

    @model_validator(mode="after")
    def valid_dates_and_status(self) -> Self:
        start = local_instant(self.start_local, self.timezone, self.start_fold)
        end = local_instant(self.end_local, self.timezone, self.end_fold)
        if end is not None and (start is None or end <= start):
            raise ValueError("The end must be after the start.")
        if self.status in {"confirmed", "completed"}:
            if (
                start is None
                or not self.location
                or self.guest_count is None
                or self.budget_ceiling_minor is None
            ):
                raise ValueError(
                    "Confirmed or completed events require a start, location, "
                    "guest count, and budget ceiling."
                )
            if self.dietary_needs is None or self.accessibility_needs is None:
                raise ValueError(
                    "Confirm dietary and accessibility needs, "
                    "using an empty response when there are none."
                )
        return self


class EventPatch(Contract):
    # Nullable transport fields permit partial updates; merged EventWrite validation
    # rejects null for required fields and checks cross-field invariants atomically.
    title: Title | None = None
    event_type: EventType | None = None
    timezone: Annotated[str, Field(min_length=1, max_length=64)] | None = None
    currency: Currency | None = None
    start_local: datetime | None = None
    end_local: datetime | None = None
    start_fold: Literal[0, 1] | None = None
    end_fold: Literal[0, 1] | None = None
    location: Annotated[str, Field(max_length=300)] | None = None
    guest_count: Count | None = None
    budget_ceiling_minor: Money | None = None
    contingency_bps: Annotated[StrictInt, Field(ge=0, le=5000)] | None = None
    preferences: (
        Annotated[list[Annotated[str, Field(min_length=1, max_length=120)]], Field(max_length=20)]
        | None
    ) = None
    dietary_needs: Note | None = None
    accessibility_needs: Note | None = None
    status: EventStatus | None = None


class EventRead(Contract):
    id: UUID
    title: str
    event_type: EventType
    timezone: str
    currency: Currency
    start_local: datetime | None
    end_local: datetime | None
    start_fold: int | None
    end_fold: int | None
    starts_at: datetime | None
    ends_at: datetime | None
    location: str | None
    guest_count: int | None
    budget_ceiling_minor: int | None
    contingency_bps: int
    preferences: list[str]
    dietary_needs: str | None
    accessibility_needs: str | None
    status: Literal["draft", "confirmed", "completed", "cancelled", "archived"]
    revision: int
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None


class EventPage(Contract):
    items: list[EventRead]
    next_cursor: str | None


class UserProfile(Contract):
    id: UUID
    username: str
    display_name: Annotated[str, Field(min_length=1, max_length=100)]


class OrganizationData(Contract):
    name: Title


class EventPlanVersionData(Contract):
    event_id: UUID
    sequence: Annotated[StrictInt, Field(ge=1)]
    base_event_revision: Annotated[StrictInt, Field(ge=1)]
    parent_id: UUID | None = None
    title: Title
    status: Literal["draft", "proposed", "approved", "rejected"] = "draft"
    approved_by: UUID | None = None
    approved_at: datetime | None = None

    @model_validator(mode="after")
    def approval_metadata(self) -> Self:
        if (self.status == "approved") != (
            self.approved_by is not None and self.approved_at is not None
        ):
            raise ValueError("Approved versions require an approving user and timestamp.")
        if self.status != "approved" and (self.approved_by or self.approved_at):
            raise ValueError("Approval metadata belongs only to approved versions.")
        return self


class BudgetItemData(Contract):
    event_id: UUID
    plan_id: UUID
    category: Annotated[str, Field(min_length=1, max_length=80)]
    description: Title
    currency: Currency
    quantity: Count = 1
    unit_amount_minor: Money
    tax_minor: Money = 0
    fee_minor: Money = 0
    estimated_minor: Money = 0
    planned_minor: Money = 0
    actual_minor: Money = 0
    scenario: Literal["economical", "balanced", "premium"] = "balanced"

    @property
    def total_minor(self) -> int:
        return self.quantity * self.unit_amount_minor + self.tax_minor + self.fee_minor

    @model_validator(mode="after")
    def safe_total(self) -> Self:
        if self.total_minor > MAX_MONEY:
            raise ValueError("The line total exceeds the supported monetary range.")
        return self


class TaskData(Contract):
    event_id: UUID
    plan_id: UUID | None = None
    title: Title
    description: Note = ""
    status: Literal["todo", "in_progress", "done", "cancelled"] = "todo"
    due_at: datetime | None = None
    completed_at: datetime | None = None
    owner: Annotated[str, Field(max_length=100)] = ""
    priority: Literal["low", "normal", "high", "critical"] = "normal"
    depends_on: list[UUID] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def completion(self) -> Self:
        if (self.status == "done") != (self.completed_at is not None):
            raise ValueError("Only a completed task has a completion timestamp.")
        for value in (self.due_at, self.completed_at):
            if value is not None and value.tzinfo is None:
                raise ValueError("Task timestamps must include a UTC offset.")
        return self


class BudgetItemWrite(Contract):
    category: Annotated[str, Field(min_length=1, max_length=80)]
    description: Title
    estimated_minor: Money = 0
    planned_minor: Money = 0
    actual_minor: Money = 0
    scenario: Literal["economical", "balanced", "premium"] = "balanced"


class BudgetItemPatch(Contract):
    category: Annotated[str, Field(min_length=1, max_length=80)] | None = None
    description: Title | None = None
    estimated_minor: Money | None = None
    planned_minor: Money | None = None
    actual_minor: Money | None = None
    scenario: Literal["economical", "balanced", "premium"] | None = None

    @model_validator(mode="after")
    def non_null_changes(self) -> Self:
        if any(getattr(self, name) is None for name in self.model_fields_set):
            raise ValueError(
                "Budget fields cannot be null; omit fields that should stay unchanged."
            )
        return self


class BudgetSummary(Contract):
    currency: Currency
    ceiling_minor: int | None
    estimated_minor: int
    planned_minor: int
    actual_minor: int
    reserve_minor: int
    remaining_minor: int | None
    projected_overrun_minor: int
    scenario: Literal["economical", "balanced", "premium"]
    savings_alternatives: list[str]
    category_totals: list[dict[str, int | str]] = Field(default_factory=list)
    before: dict[str, int] | None = None
    after: dict[str, int] | None = None


class TaskWrite(Contract):
    title: Title
    description: Note = ""
    owner: Annotated[str, Field(max_length=100)] = ""
    priority: Literal["low", "normal", "high", "critical"] = "normal"
    due_at: datetime | None = None
    depends_on: list[UUID] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def due_offset(self) -> Self:
        if self.due_at is not None and self.due_at.tzinfo is None:
            raise ValueError("Task deadlines must include a timezone offset.")
        return self


class TaskPatch(Contract):
    title: Title | None = None
    description: Note | None = None
    owner: Annotated[str, Field(max_length=100)] | None = None
    priority: Literal["low", "normal", "high", "critical"] | None = None
    due_at: datetime | None = None
    status: Literal["todo", "in_progress", "done", "cancelled"] | None = None
    depends_on: list[UUID] | None = Field(default=None, max_length=20)

    @model_validator(mode="after")
    def valid_changes(self) -> Self:
        if any(getattr(self, name) is None for name in self.model_fields_set - {"due_at"}):
            raise ValueError("Only the deadline can be cleared; other task fields cannot be null.")
        if self.due_at is not None and self.due_at.tzinfo is None:
            raise ValueError("Task deadlines must include a timezone offset.")
        return self


class TaskRead(Contract):
    id: UUID
    event_id: UUID
    plan_id: UUID | None
    title: str
    description: str
    owner: str
    priority: str
    status: str
    due_at: datetime | None
    completed_at: datetime | None
    depends_on: list[UUID]
    critical: bool = False
    delayed: bool = False
    impact: list[UUID] = Field(default_factory=list)


ReplanType = Literal[
    "guest_count",
    "venue_change",
    "quote_increase",
    "date_change",
    "task_delay",
    "budget_constraint",
]


class ReplanRequest(Contract):
    change_type: ReplanType
    details: dict[str, Any] = Field(default_factory=dict)
    note: Annotated[str, Field(max_length=1000)] = ""


class ReplanRead(Contract):
    id: UUID
    event_id: UUID
    base_plan_id: UUID
    base_event_revision: int
    change_type: ReplanType
    request: dict[str, Any]
    impact: dict[str, Any]
    alternative: dict[str, Any]
    status: Literal["pending", "accepted", "rejected", "stale"]
    rejection_reason: str | None
    accepted_plan_id: UUID | None


class VendorData(Contract):
    event_id: UUID
    name: Title
    category: Annotated[str, Field(min_length=1, max_length=80)]
    contact: Annotated[str, Field(max_length=300)] = ""
    notes: Note = ""
    provenance: Literal["user_provided", "demo_seeded", "verified_evidence", "ai_estimate"] = (
        "user_provided"
    )
    location: Annotated[str, Field(max_length=200)] = ""
    service_inclusions: list[Annotated[str, Field(max_length=200)]] = Field(
        default_factory=list, max_length=20
    )
    availability_evidence: Annotated[str, Field(max_length=500)] | None = None
    cancellation_terms: Annotated[str, Field(max_length=1000)] | None = None
    deposit_minor: Money | None = None
    source_label: Annotated[str, Field(max_length=120)] = "User-provided"


class VendorQuoteData(Contract):
    event_id: UUID
    vendor_id: UUID
    amount_minor: Money
    currency: Currency
    issued_on: date
    valid_until: date | None = None
    status: Literal["received", "accepted", "rejected", "expired"] = "received"
    reference: Annotated[str, Field(max_length=300)] = ""
    provenance: Literal["user_provided", "demo_seeded", "verified_evidence", "ai_estimate"] = (
        "user_provided"
    )
    inclusions: list[Annotated[str, Field(max_length=200)]] = Field(
        default_factory=list, max_length=20
    )
    cancellation_terms: Annotated[str, Field(max_length=1000)] | None = None
    deposit_minor: Money | None = None
    availability_evidence: Annotated[str, Field(max_length=500)] | None = None

    @model_validator(mode="after")
    def expiry(self) -> Self:
        if self.valid_until is not None and self.valid_until < self.issued_on:
            raise ValueError("A quote cannot expire before its issue date.")
        return self


class VendorWrite(Contract):
    name: Title
    category: Annotated[str, Field(min_length=1, max_length=80)]
    location: Annotated[str, Field(max_length=200)] = ""
    contact: Annotated[str, Field(max_length=300)] = ""
    notes: Note = ""
    provenance: Literal["user_provided", "demo_seeded", "verified_evidence", "ai_estimate"] = (
        "user_provided"
    )
    service_inclusions: list[Annotated[str, Field(max_length=200)]] = Field(
        default_factory=list, max_length=20
    )
    availability_evidence: Annotated[str, Field(max_length=500)] | None = None
    cancellation_terms: Annotated[str, Field(max_length=1000)] | None = None
    deposit_minor: Money | None = None
    source_label: Annotated[str, Field(max_length=120)] = "User-provided"


class QuoteWrite(Contract):
    vendor_id: UUID
    amount_minor: Money
    issued_on: date
    valid_until: date | None = None
    status: Literal["received", "accepted", "rejected", "expired"] = "received"
    reference: Annotated[str, Field(max_length=300)] = ""
    provenance: Literal["user_provided", "demo_seeded", "verified_evidence", "ai_estimate"] = (
        "user_provided"
    )
    inclusions: list[Annotated[str, Field(max_length=200)]] = Field(
        default_factory=list, max_length=20
    )
    cancellation_terms: Annotated[str, Field(max_length=1000)] | None = None
    deposit_minor: Money | None = None
    availability_evidence: Annotated[str, Field(max_length=500)] | None = None

    @model_validator(mode="after")
    def valid_dates(self) -> Self:
        if self.valid_until is not None and self.valid_until < self.issued_on:
            raise ValueError("A quote cannot expire before its issue date.")
        return self


class VendorRead(Contract):
    id: UUID
    event_id: UUID
    name: str
    category: str
    location: str
    contact: str
    notes: str
    provenance: str
    source_label: str
    service_inclusions: list[str]
    availability_evidence: str | None
    cancellation_terms: str | None
    deposit_minor: int | None
    quotes: list[dict[str, Any]]


class GuestData(Contract):
    event_id: UUID
    name: Title
    contact: Annotated[str, Field(max_length=300)] = ""
    rsvp_status: Literal["pending", "attending", "declined", "tentative"] = "pending"
    party_size: Annotated[StrictInt, Field(ge=1, le=100)] = 1
    dietary_needs: Note | None = None
    accessibility_needs: Note | None = None


class AuditEventData(Contract):
    actor_id: UUID
    event_id: UUID | None = None
    action: Literal["event.created", "event.updated", "event.archived"]
    request_id: UUID
    revision: Annotated[StrictInt, Field(ge=1)]
    changed_fields: Annotated[list[Annotated[str, Field(max_length=64)]], Field(max_length=30)] = (
        Field(default_factory=list)
    )
