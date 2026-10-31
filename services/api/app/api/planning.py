"""Owner-scoped intake/generation and editable drafts. Provider I/O holds no DB lock."""
# ruff: noqa: E501

import hashlib
import json
import logging
from datetime import UTC, datetime, timedelta
from time import perf_counter
from typing import Annotated, Any, cast
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Header, Query, Request, Response
from pydantic import ValidationError
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.ai.provider import PROMPT_VERSION, Metrics, Provider, ProviderFailure
from app.api.dependencies import DB
from app.api.events import audit, event_view, owned_event, precondition, values
from app.core.auth import Authenticated, AuthorizedMutation
from app.core.errors import APIError
from app.db.models import Event, EventPlanVersion, GenerationRun, User
from app.domain.planning import (
    AIStatus,
    Extraction,
    GenerateRequest,
    IntakeDetails,
    IntakeRequest,
    ModelPlan,
    PlanDocument,
    PlanEdit,
    PlanRead,
    RunRead,
    ScheduledTask,
    allocate,
    event_input,
    questions,
)
from app.domain.schemas import Contract, EventWrite

router = APIRouter(prefix="/api/v1", tags=["AI intake and drafts"])
logger = logging.getLogger("eventora")


class PlanPage(Contract):
    items: list[PlanRead]
    next_before: int | None


def run_view(run: GenerationRun) -> RunRead:
    return RunRead(
        id=run.id,
        operation=run.operation,
        status=run.status,
        error_code=run.error_code,
        call_count=run.call_count,
        latency_ms=run.latency_ms,
        plan_id=run.plan_id,
        extraction=Extraction.model_validate(run.extraction) if run.extraction else None,
    )


def intake_context(event: Event) -> dict[str, Any]:
    data = event_view(event).model_dump(mode="json", include=set(EventWrite.model_fields))
    amount = data.pop("budget_ceiling_minor")
    data["budget_amount"] = (
        None
        if amount is None
        else (str(amount) if event.currency == "JPY" else f"{amount // 100}.{amount % 100:02d}")
    )
    data["duration_minutes"] = (
        int((event.ends_at - event.starts_at).total_seconds() // 60)
        if event.starts_at and event.ends_at
        else None
    )
    data["constraints"] = []
    data.pop("status", None)
    return data


def plan_view(plan: EventPlanVersion, event: Event) -> PlanRead:
    if plan.document is None or plan.intake is None:
        raise APIError(409, "LEGACY_PLAN", "This plan has no reviewable draft content.")
    details = IntakeDetails.model_validate(plan.intake)
    document = PlanDocument.model_validate(plan.document)
    # Historical plans remain readable after their event date passes.
    from app.domain.planning import budget_minor

    assert details.currency and details.budget_amount and details.timezone and details.start_local
    ceiling = budget_minor(details.budget_amount, details.currency)
    total = sum(row.estimated_amount_minor for row in document.budget_categories)
    day = datetime.fromisoformat(details.start_local).date()
    today = datetime.now(ZoneInfo(details.timezone)).date()
    schedule = [
        ScheduledTask(
            title=task.title,
            due_on=(day - timedelta(days=task.days_before_event)).isoformat(),
            needs_rescheduling=day - timedelta(days=task.days_before_event) < today,
        )
        for task in document.preparation_tasks
    ]
    warnings = ["Planning allocations are estimates, not quotations or verified market prices."]
    if total > ceiling:
        warnings.append(
            "These estimates exceed the budget ceiling. Review the amounts before using this draft."
        )
    if any(task.needs_rescheduling for task in schedule):
        warnings.append("Some preparation dates have passed and need rescheduling.")
    if plan.base_event_revision != event.revision:
        warnings.append(
            "Event details changed after this draft. It remains readable; "
            "saving against stale details is blocked."
        )
    return PlanRead(
        id=plan.id,
        event_id=plan.event_id,
        sequence=plan.sequence,
        revision=plan.revision,
        base_event_revision=plan.base_event_revision,
        title=plan.title,
        status=plan.status,
        saved_at=plan.saved_at,
        created_at=plan.created_at,
        intake=details,
        document=document,
        currency=details.currency,
        budget_ceiling_minor=ceiling,
        estimated_total_minor=total,
        remaining_minor=ceiling - total,
        schedule=schedule,
        warnings=warnings,
        explanations=[
            *(
                [f"Ideas respect the recorded dietary requirement: {details.dietary_needs}."]
                if details.dietary_needs
                else []
            ),
            *(
                [
                    f"Ideas respect the recorded accessibility requirement: {details.accessibility_needs}."
                ]
                if details.accessibility_needs
                else []
            ),
            *(
                [
                    f"Budget allocations were calculated against the {details.currency} {details.budget_amount} ceiling by deterministic application code."
                ]
                if details.budget_amount
                else []
            ),
            "Themes, menus, decor and activities are editable suggestions; they are not verified supplier facts.",
        ],
    )


@router.get("/ai/status", response_model=AIStatus)
def ai_status(request: Request, identity: Authenticated) -> AIStatus:
    settings = request.app.state.settings
    return AIStatus(
        enabled=settings.ai_enabled,
        provider=request.app.state.ai_provider.kind,
        timeout_seconds=settings.ai_timeout_seconds,
    )


def execute_run(
    event_id: UUID,
    payload: IntakeRequest | GenerateRequest,
    operation: str,
    request: Request,
    db: DB,
    owner: UUID,
    if_match: str | None,
    key: UUID,
) -> RunRead:
    settings = request.app.state.settings
    event = owned_event(db, event_id, owner)
    input_hash = hashlib.sha256(
        json.dumps(
            {
                "operation": operation,
                "payload": payload.model_dump(mode="json"),
                "if_match": if_match,
            },
            sort_keys=True,
        ).encode()
    ).hexdigest()
    # Serialize admission per user, preventing duplicate requests and quota races.
    db.scalar(select(User).where(User.id == owner).with_for_update())
    existing = db.scalar(
        select(GenerationRun).where(
            GenerationRun.event_id == event_id, GenerationRun.request_key == key
        )
    )
    now = datetime.now(UTC)
    if existing:
        if existing.input_hash != input_hash:
            raise APIError(
                409, "IDEMPOTENCY_CONFLICT", "This request key was used for different details."
            )
        if existing.status == "running" and existing.expires_at < now:
            existing.status, existing.error_code = "failed", "AI_INTERRUPTED"
        db.commit()
        return run_view(existing)
    precondition(event, if_match)
    if event.status == "archived":
        raise APIError(409, "EVENT_ARCHIVED", "Archived events are read-only.")
    if not settings.ai_enabled:
        raise APIError(
            503, "AI_DISABLED", "AI planning is not configured. Your saved events remain available."
        )
    validated: EventWrite | None = None
    if isinstance(payload, GenerateRequest):
        if event.status not in {"draft", "confirmed"}:
            raise APIError(
                409, "EVENT_NOT_PLANNABLE", "Only draft or confirmed events can be planned."
            )
        if db.scalar(
            select(EventPlanVersion.id).where(
                EventPlanVersion.event_id == event_id, EventPlanVersion.status == "approved"
            )
        ):
            raise APIError(
                409,
                "APPROVED_PLAN_EXISTS",
                "An approved plan cannot be replaced by initial generation.",
            )
        try:
            validated = event_input(payload.details)
            validated = validated.model_copy(update={"status": event.status})
        except ValueError, KeyError, OverflowError:
            raise APIError(
                422,
                "INTAKE_INCOMPLETE",
                "Check required details, budget, timezone, dates and duration. "
                "Resolve conflicting values before generating.",
            ) from None
    db.execute(
        update(GenerationRun)
        .where(
            GenerationRun.owner_id == owner,
            GenerationRun.status == "running",
            GenerationRun.expires_at < now,
        )
        .values(status="failed", error_code="AI_INTERRUPTED")
    )
    if db.scalar(
        select(GenerationRun.id).where(
            GenerationRun.owner_id == owner, GenerationRun.status == "running"
        )
    ):
        raise APIError(
            409,
            "AI_ALREADY_RUNNING",
            "A planning request is already running. Check its result before trying again.",
        )
    count = (
        db.scalar(
            select(func.count())
            .select_from(GenerationRun)
            .where(
                GenerationRun.owner_id == owner, GenerationRun.created_at >= now - timedelta(days=1)
            )
        )
        or 0
    )
    if count >= settings.ai_daily_requests:
        raise APIError(
            429,
            "AI_DAILY_LIMIT",
            "Your daily planning request limit has been reached. Try again tomorrow.",
        )
    snapshot = intake_context(event)
    reference = datetime.now(ZoneInfo(event.timezone)).isoformat()
    run = GenerationRun(
        owner_id=owner,
        event_id=event_id,
        request_key=key,
        input_hash=input_hash,
        operation=operation,
        expected_revision=event.revision,
        model=settings.gemini_model,
        expires_at=now + timedelta(seconds=settings.ai_timeout_seconds + 15),
    )
    db.add(run)
    db.commit()
    run_id = run.id
    started = perf_counter()

    def attempted(calls: int) -> None:
        with Session(request.app.state.database.engine) as metrics_db:
            metrics_db.execute(
                update(GenerationRun)
                .where(GenerationRun.id == run_id, GenerationRun.owner_id == owner)
                .values(call_count=calls)
            )
            metrics_db.commit()
        logger.info(
            "ai_call",
            extra={
                "request_id": request.state.request_id,
                "run_id": str(run_id),
                "operation": operation,
                "call_count": calls,
            },
        )

    metrics = Metrics(on_call=attempted)
    try:
        context = (
            {
                "reference_time": reference,
                "saved_event": snapshot,
                "description": payload.description,
            }
            if isinstance(payload, IntakeRequest)
            else {
                "reviewed_intake": payload.details.model_dump(mode="json"),
                "reference_time": reference,
            }
        )
        result = cast(Provider, request.app.state.ai_provider).generate(operation, context, metrics)
        extraction: Extraction | None = None
        document: PlanDocument | None = None
        if operation == "intake":
            extraction = Extraction.model_validate(result)
            extraction.questions = list(
                dict.fromkeys(questions(extraction.details) + extraction.questions)
            )[:12]
        else:
            assert validated is not None and validated.budget_ceiling_minor is not None
            document = allocate(ModelPlan.model_validate(result), validated.budget_ceiling_minor)
        db.expire_all()
        current = db.scalar(
            select(GenerationRun).where(GenerationRun.id == run_id).with_for_update()
        )
        assert current is not None
        event = owned_event(db, event_id, owner, lock=True)
        if current.status != "running" or current.expires_at < datetime.now(UTC):
            raise ProviderFailure("AI_INTERRUPTED")
        if event.revision != current.expected_revision or event.status == "archived":
            raise ProviderFailure("EVENT_CHANGED")
        if extraction:
            current.extraction = extraction.model_dump(mode="json")
        else:
            assert document and validated and isinstance(payload, GenerateRequest)
            if db.scalar(
                select(EventPlanVersion.id).where(
                    EventPlanVersion.event_id == event_id, EventPlanVersion.status == "approved"
                )
            ):
                raise ProviderFailure("APPROVED_PLAN_EXISTS")
            for name, value in values(validated).items():
                setattr(event, name, value)
            event.revision += 1
            event.updated_at = datetime.now(UTC)
            sequence = (
                db.scalar(
                    select(func.max(EventPlanVersion.sequence)).where(
                        EventPlanVersion.event_id == event_id
                    )
                )
                or 0
            ) + 1
            plan = EventPlanVersion(
                event_id=event_id,
                sequence=sequence,
                base_event_revision=event.revision,
                title=validated.title,
                intake=payload.details.model_dump(mode="json"),
                document=document.model_dump(mode="json"),
                prompt_version=PROMPT_VERSION,
            )
            db.add(plan)
            db.flush()
            current.plan_id = plan.id
            audit(db, request, event, "plan.generated", ["plan_document", "event_intake"])
        current.status = "succeeded"
        current.call_count, current.input_tokens, current.output_tokens = (
            metrics.calls,
            metrics.input_tokens,
            metrics.output_tokens,
        )
        current.latency_ms = round((perf_counter() - started) * 1000)
        db.commit()
    except Exception as failure:
        db.rollback()
        code = (
            failure.code
            if isinstance(failure, ProviderFailure)
            else "AI_INVALID_OUTPUT"
            if isinstance(failure, (ValidationError, ValueError, TypeError))
            else "AI_FAILED"
        )
        current = db.get(GenerationRun, run_id)
        assert current is not None
        current.status, current.error_code = "failed", code
        current.call_count, current.input_tokens, current.output_tokens = (
            metrics.calls,
            metrics.input_tokens,
            metrics.output_tokens,
        )
        current.latency_ms = round((perf_counter() - started) * 1000)
        db.commit()
    logger.info(
        "ai_run_completed",
        extra={
            "request_id": request.state.request_id,
            "run_id": str(run_id),
            "operation": operation,
            "call_count": current.call_count,
            "duration_ms": current.latency_ms,
            "error_code": current.error_code,
            "input_tokens": current.input_tokens,
            "output_tokens": current.output_tokens,
        },
    )
    return run_view(current)


@router.post("/events/{event_id}/intake", response_model=RunRead)
def extract_intake(
    event_id: UUID,
    payload: IntakeRequest,
    request: Request,
    db: DB,
    identity: AuthorizedMutation,
    idempotency_key: Annotated[UUID, Header()],
    if_match: Annotated[str | None, Header()] = None,
) -> RunRead:
    return execute_run(
        event_id, payload, "intake", request, db, identity.user.id, if_match, idempotency_key
    )


@router.post("/events/{event_id}/generations", response_model=RunRead)
def generate_plan(
    event_id: UUID,
    payload: GenerateRequest,
    request: Request,
    db: DB,
    identity: AuthorizedMutation,
    idempotency_key: Annotated[UUID, Header()],
    if_match: Annotated[str | None, Header()] = None,
) -> RunRead:
    return execute_run(
        event_id, payload, "plan", request, db, identity.user.id, if_match, idempotency_key
    )


@router.get("/events/{event_id}/generations", response_model=list[RunRead])
def recent_runs(event_id: UUID, db: DB, identity: Authenticated) -> list[RunRead]:
    owned_event(db, event_id, identity.user.id)
    rows = db.scalars(
        select(GenerationRun)
        .where(GenerationRun.event_id == event_id, GenerationRun.owner_id == identity.user.id)
        .order_by(GenerationRun.created_at.desc())
        .limit(10)
    ).all()
    for row in rows:
        if row.status == "running" and row.expires_at < datetime.now(UTC):
            row.status, row.error_code = "failed", "AI_INTERRUPTED"
    db.commit()
    return [run_view(row) for row in rows]


@router.get("/events/{event_id}/plans", response_model=PlanPage)
def list_plans(
    event_id: UUID,
    db: DB,
    identity: Authenticated,
    before: Annotated[int | None, Query(ge=1)] = None,
) -> PlanPage:
    event = owned_event(db, event_id, identity.user.id)
    query = select(EventPlanVersion).where(
        EventPlanVersion.event_id == event_id, EventPlanVersion.document.is_not(None)
    )
    if before:
        query = query.where(EventPlanVersion.sequence < before)
    rows = db.scalars(query.order_by(EventPlanVersion.sequence.desc()).limit(11)).all()
    return PlanPage(
        items=[plan_view(row, event) for row in rows[:10]],
        next_before=rows[9].sequence if len(rows) > 10 else None,
    )


def owned_plan(db: DB, event_id: UUID, plan_id: UUID, lock: bool = False) -> EventPlanVersion:
    query = select(EventPlanVersion).where(
        EventPlanVersion.id == plan_id, EventPlanVersion.event_id == event_id
    )
    plan = db.scalar(query.with_for_update() if lock else query)
    if plan is None:
        raise APIError(404, "PLAN_NOT_FOUND", "This draft could not be found.")
    return plan


@router.get("/events/{event_id}/plans/{plan_id}", response_model=PlanRead)
def get_plan(
    event_id: UUID, plan_id: UUID, response: Response, db: DB, identity: Authenticated
) -> PlanRead:
    event = owned_event(db, event_id, identity.user.id)
    plan = owned_plan(db, event_id, plan_id)
    response.headers["ETag"] = f'"{plan.revision}"'
    return plan_view(plan, event)


@router.patch("/events/{event_id}/plans/{plan_id}", response_model=PlanRead)
def save_plan(
    event_id: UUID,
    plan_id: UUID,
    payload: PlanEdit,
    request: Request,
    response: Response,
    db: DB,
    identity: AuthorizedMutation,
    if_match: Annotated[str | None, Header()] = None,
) -> PlanRead:
    event = owned_event(db, event_id, identity.user.id, lock=True)
    plan = owned_plan(db, event_id, plan_id, lock=True)
    if if_match is None:
        raise APIError(428, "REVISION_REQUIRED", "Reload this draft before saving.")
    if if_match != f'"{plan.revision}"':
        raise APIError(
            412, "REVISION_CONFLICT", "This draft changed elsewhere. Reload before saving."
        )
    if (
        plan.status != "draft"
        or event.status == "archived"
        or plan.base_event_revision != event.revision
    ):
        raise APIError(
            409, "PLAN_READ_ONLY", "This draft cannot be edited against the current event details."
        )
    if plan.document is None:
        raise APIError(409, "LEGACY_PLAN", "This plan has no editable draft content.")
    plan.document = payload.document.model_dump(mode="json")
    plan.revision += 1
    plan.saved_at = datetime.now(UTC)
    plan.updated_at = plan.saved_at
    audit(db, request, event, "plan.saved", ["plan_document"])
    db.commit()
    response.headers["ETag"] = f'"{plan.revision}"'
    return plan_view(plan, event)
