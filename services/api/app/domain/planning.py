"""Provider contracts and deterministic intake, money and scheduling rules."""

import re
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation, localcontext
from typing import Annotated, Literal
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, StrictInt, model_validator

from app.domain.schemas import (
    MAX_MONEY,
    Contract,
    Currency,
    EventType,
    EventWrite,
    Money,
    local_instant,
)

Short = Annotated[str, Field(min_length=1, max_length=200)]
Notes = Annotated[list[Short], Field(max_length=12)]


class IntakeDetails(Contract):
    title: Annotated[str, Field(min_length=1, max_length=160)] | None
    event_type: EventType | None
    start_local: Annotated[str, Field(max_length=30)] | None
    end_local: Annotated[str, Field(max_length=30)] | None
    start_fold: Literal[0, 1] | None
    end_fold: Literal[0, 1] | None
    duration_minutes: Annotated[StrictInt, Field(ge=1, le=10080)] | None
    timezone: Annotated[str, Field(max_length=64)] | None
    location: Annotated[str, Field(max_length=300)] | None
    guest_count: Annotated[StrictInt, Field(ge=1, le=1000000)] | None
    currency: Currency | None
    budget_amount: Annotated[str, Field(max_length=64)] | None
    preferences: Annotated[
        list[Annotated[str, Field(min_length=1, max_length=120)]], Field(max_length=20)
    ]
    constraints: Notes
    dietary_needs: Annotated[str, Field(max_length=2000)] | None
    accessibility_needs: Annotated[str, Field(max_length=2000)] | None


class Extraction(Contract):
    details: IntakeDetails
    questions: Notes
    conflicts: Notes
    assumptions: Notes


def budget_minor(value: str, currency: Currency) -> int:
    """Parse amounts and common magnitude suffixes without model arithmetic or floats."""
    raw = value.strip().lower().replace(",", "")
    for code, symbol in (("INR", "₹"), ("USD", "$"), ("EUR", "€"), ("GBP", "£"), ("JPY", "¥")):
        if symbol in raw or code.lower() in raw:
            if code != currency:
                raise ValueError("The budget currency conflicts with the selected currency.")
            raw = raw.replace(symbol, "").replace(code.lower(), "").strip()
    match = re.fullmatch(r"(\d+(?:\.\d+)?)\s*(k|thousand|lakh|lac|million)?", raw)
    if not match:
        raise ValueError("Enter one budget amount, without a range or calculation.")
    multiplier = {
        None: 1,
        "k": 1000,
        "thousand": 1000,
        "lakh": 100000,
        "lac": 100000,
        "million": 1000000,
    }[match[2]]
    try:
        with localcontext() as context:
            context.prec = max(100, len(match[1]) + 10)
            amount = Decimal(match[1]) * multiplier * (1 if currency == "JPY" else 100)
    except InvalidOperation:
        raise ValueError("Enter a valid budget amount.") from None
    if amount != amount.to_integral_value() or not 0 <= amount <= MAX_MONEY:
        raise ValueError("The budget exceeds currency precision or supported limits.")
    return int(amount)


ESSENTIAL = {
    "title": "What should this event be called?",
    "event_type": "Is this a wedding, birthday or community event?",
    "start_local": "What is the event's local start date and time?",
    "timezone": "Which IANA timezone applies to the event?",
    "location": "Where will the event take place?",
    "guest_count": "How many guests should the plan accommodate?",
    "currency": "Which currency should the budget use?",
    "budget_amount": "What is the total budget ceiling?",
    "dietary_needs": "What dietary needs apply? Enter none if there are none.",
    "accessibility_needs": "What accessibility needs apply? Enter none if there are none.",
}


def questions(details: IntakeDetails) -> list[str]:
    result = [
        question
        for field, question in ESSENTIAL.items()
        if getattr(details, field) is None
        or (getattr(details, field) == "" and field not in {"dietary_needs", "accessibility_needs"})
    ]
    if not details.duration_minutes and not details.end_local:
        result.append("How long will the event last, or when will it end?")
    return result


def event_input(details: IntakeDetails) -> EventWrite:
    missing = questions(details)
    if missing:
        raise ValueError("Complete the essential details before generating: " + " ".join(missing))
    assert details.currency and details.budget_amount and details.timezone and details.start_local
    try:
        ZoneInfo(details.timezone)
    except ZoneInfoNotFoundError, ValueError:
        raise ValueError("Choose a valid IANA timezone.") from None
    data = details.model_dump(exclude={"budget_amount", "duration_minutes", "constraints"})
    data["budget_ceiling_minor"] = budget_minor(details.budget_amount, details.currency)
    start = local_instant(
        datetime.fromisoformat(details.start_local), details.timezone, details.start_fold
    )
    assert start is not None
    if details.duration_minutes:
        calculated = start + timedelta(minutes=details.duration_minutes)
        if details.end_local:
            end = local_instant(
                datetime.fromisoformat(details.end_local), details.timezone, details.end_fold
            )
            if end != calculated:
                raise ValueError(
                    "The end time and duration conflict. Correct one before generating."
                )
        local_end = calculated.astimezone(ZoneInfo(details.timezone))
        data["end_local"] = local_end.replace(tzinfo=None)
        data["end_fold"] = local_end.fold
    validated = EventWrite.model_validate(data)
    end = local_instant(validated.end_local, validated.timezone, validated.end_fold)
    if end is None or end - start > timedelta(days=7):
        raise ValueError("Choose an event duration of at most seven days.")
    if start <= datetime.now(UTC):
        raise ValueError("Choose a future start date for an initial event plan.")
    return validated


class CategoryProposal(Contract):
    category: Annotated[str, Field(min_length=1, max_length=80)]
    description: Annotated[str, Field(min_length=1, max_length=160)]
    weight: Annotated[StrictInt, Field(ge=1, le=100)]


class PreparationTask(Contract):
    title: Annotated[str, Field(min_length=1, max_length=160)]
    days_before_event: Annotated[StrictInt, Field(ge=0, le=365)]
    checklist: Notes


class VendorRequirement(Contract):
    category: Annotated[str, Field(min_length=1, max_length=80)]
    requirements: Notes
    checklist: Notes


class PlanIdeas(Contract):
    summary: Annotated[str, Field(min_length=1, max_length=1500)]
    preparation_tasks: Annotated[list[PreparationTask], Field(min_length=1, max_length=20)]
    vendor_requirements: Annotated[list[VendorRequirement], Field(max_length=10)]
    themes: Notes
    menus: Notes
    decor: Notes
    activities: Notes
    assumptions: Notes
    unresolved_questions: Notes
    conflicts: Notes

    @model_validator(mode="after")
    def no_verified_claims(self) -> PlanIdeas:
        text = self.model_dump_json()
        if re.search(
            r"https?://|\bverified (?:quote|quotation|vendor)\b|\bconfirmed availability\b|"
            r"\bbooking confirmed\b|\bguaranteed (?:price|availability)\b",
            text,
            re.I,
        ):
            raise ValueError(
                "Draft suggestions cannot claim external verification or availability."
            )
        return self


class ModelPlan(PlanIdeas):
    budget_categories: Annotated[list[CategoryProposal], Field(min_length=1, max_length=12)]


class EstimatedCategory(Contract):
    category: Annotated[str, Field(min_length=1, max_length=80)]
    description: Annotated[str, Field(min_length=1, max_length=160)]
    estimated_amount_minor: Money


class PlanDocument(PlanIdeas):
    budget_categories: Annotated[list[EstimatedCategory], Field(min_length=1, max_length=12)]

    @model_validator(mode="after")
    def exact_total(self) -> PlanDocument:
        if len(self.model_dump_json().encode()) > 48000:
            raise ValueError("The draft is too large. Shorten its notes before saving.")
        if sum(row.estimated_amount_minor for row in self.budget_categories) > MAX_MONEY:
            raise ValueError("The total exceeds supported monetary limits.")
        return self


def allocate(proposal: ModelPlan, ceiling: int) -> PlanDocument:
    weights = sum(row.weight for row in proposal.budget_categories)
    amounts = [ceiling * row.weight // weights for row in proposal.budget_categories]
    remaining = ceiling - sum(amounts)
    order = sorted(
        range(len(amounts)),
        key=lambda i: (-(ceiling * proposal.budget_categories[i].weight % weights), i),
    )
    for index in order[:remaining]:
        amounts[index] += 1
    return PlanDocument(
        **proposal.model_dump(exclude={"budget_categories"}),
        budget_categories=[
            EstimatedCategory(
                category=row.category,
                description=row.description,
                estimated_amount_minor=amounts[index],
            )
            for index, row in enumerate(proposal.budget_categories)
        ],
    )


class IntakeRequest(Contract):
    description: Annotated[str, Field(min_length=10, max_length=6000)]
    consent: Literal[True]


class GenerateRequest(Contract):
    details: IntakeDetails
    confirmed: Literal[True]
    consent: Literal[True]


class PlanEdit(Contract):
    document: PlanDocument


class ScheduledTask(Contract):
    title: str
    due_on: str
    needs_rescheduling: bool


class PlanRead(Contract):
    id: UUID
    event_id: UUID
    sequence: int
    revision: int
    base_event_revision: int
    title: str
    status: str
    saved_at: datetime | None
    created_at: datetime
    intake: IntakeDetails
    document: PlanDocument
    currency: Currency
    budget_ceiling_minor: int
    estimated_total_minor: int
    remaining_minor: int
    schedule: list[ScheduledTask]
    warnings: list[str]
    explanations: list[str] = []


class RunRead(Contract):
    id: UUID
    operation: str
    status: str
    error_code: str | None
    call_count: int
    latency_ms: int | None
    extraction: Extraction | None
    plan_id: UUID | None


class AIStatus(Contract):
    enabled: bool
    provider: str
    timeout_seconds: int
