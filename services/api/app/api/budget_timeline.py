from datetime import UTC, datetime

# mypy: ignore-errors
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Header, Query, Request
from sqlalchemy import select

from app.api.dependencies import DB
from app.api.events import audit, owned_event, precondition
from app.core.auth import Authenticated, AuthorizedMutation
from app.core.errors import APIError
from app.db.models import BudgetItem, EventPlanVersion, Task
from app.domain.budget_timeline import budget_summary, task_analysis, validate_dependencies
from app.domain.schemas import (
    BudgetItemPatch,
    BudgetItemWrite,
    BudgetSummary,
    TaskPatch,
    TaskRead,
    TaskWrite,
)

router = APIRouter(prefix="/api/v1/events/{event_id}", tags=["Budget and timeline"])


def _items(db, event_id, owner):
    owned_event(db, event_id, owner)
    return db.scalars(
        select(BudgetItem)
        .where(BudgetItem.event_id == event_id)
        .order_by(BudgetItem.created_at, BudgetItem.id)
    ).all()


@router.get("/budget", response_model=BudgetSummary)
def get_budget(
    event_id: UUID,
    db: DB,
    identity: Authenticated,
    scenario: Annotated[str, Query(pattern="^(economical|balanced|premium)$")] = "balanced",
):
    event = owned_event(db, event_id, identity.user.id)
    return budget_summary(
        _items(db, event_id, identity.user.id),
        event.budget_ceiling_minor,
        event.contingency_bps,
        scenario,
        event.currency,
    )


@router.post("/budget/items", response_model=BudgetSummary, status_code=201)
def add_budget(
    event_id: UUID,
    payload: BudgetItemWrite,
    request: Request,
    db: DB,
    identity: AuthorizedMutation,
    if_match: Annotated[str | None, Header()] = None,
    scenario: Annotated[str, Query(pattern="^(economical|balanced|premium)$")] = "balanced",
):
    event = owned_event(db, event_id, identity.user.id, lock=True)
    precondition(event, if_match)
    if event.status == "archived":
        raise APIError(409, "EVENT_ARCHIVED", "Archived events are read-only.")
    plan = db.scalar(
        select(EventPlanVersion)
        .where(EventPlanVersion.event_id == event_id)
        .order_by(EventPlanVersion.sequence.desc())
    )
    if not plan:
        raise APIError(409, "PLAN_REQUIRED", "Create an initial plan before adding budget items.")
    item = BudgetItem(
        event_id=event_id,
        plan_id=plan.id,
        currency=event.currency,
        quantity=1,
        unit_amount_minor=0,
        tax_minor=0,
        fee_minor=0,
        **payload.model_dump(),
    )
    db.add(item)
    event.revision += 1
    event.updated_at = datetime.now(UTC)
    audit(db, request, event, "event.updated", ["budget"])
    db.commit()
    return budget_summary(
        _items(db, event_id, identity.user.id),
        event.budget_ceiling_minor,
        event.contingency_bps,
        scenario,
        event.currency,
    )


@router.get("/timeline", response_model=list[TaskRead])
def get_timeline(event_id: UUID, db: DB, identity: Authenticated):
    event = owned_event(db, event_id, identity.user.id)
    rows = db.scalars(
        select(Task).where(Task.event_id == event_id).order_by(Task.due_at.nullslast(), Task.id)
    ).all()
    try:
        validate_dependencies(rows, event.starts_at, event.ends_at)
    except ValueError as exc:
        raise APIError(409, "INVALID_TIMELINE", str(exc)) from None
    critical, delayed, impact = task_analysis(rows)
    return [
        TaskRead.model_validate(
            {
                **{k: getattr(t, k) for k in TaskRead.model_fields if hasattr(t, k)},
                "critical": t.id in critical,
                "delayed": t.id in delayed,
                "impact": impact[t.id],
            }
        )
        for t in rows
    ]


@router.patch("/budget/items/{item_id}", response_model=BudgetSummary)
def edit_budget(
    event_id: UUID,
    item_id: UUID,
    payload: BudgetItemPatch,
    request: Request,
    db: DB,
    identity: AuthorizedMutation,
    if_match: Annotated[str | None, Header()] = None,
    scenario: Annotated[str, Query(pattern="^(economical|balanced|premium)$")] = "balanced",
) -> dict[str, Any]:
    event = owned_event(db, event_id, identity.user.id, lock=True)
    precondition(event, if_match)
    item = db.scalar(
        select(BudgetItem)
        .where(BudgetItem.id == item_id, BudgetItem.event_id == event_id)
        .with_for_update()
    )
    if not item:
        raise APIError(404, "BUDGET_ITEM_NOT_FOUND", "This budget item could not be found.")
    before = budget_summary(
        _items(db, event_id, identity.user.id),
        event.budget_ceiling_minor,
        event.contingency_bps,
        scenario,
        event.currency,
    )
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    event.revision += 1
    event.updated_at = datetime.now(UTC)
    audit(db, request, event, "event.updated", ["budget"])
    db.commit()
    after = budget_summary(
        _items(db, event_id, identity.user.id),
        event.budget_ceiling_minor,
        event.contingency_bps,
        scenario,
        event.currency,
    )
    after["before"] = {
        k: before[k] for k in ("estimated_minor", "planned_minor", "actual_minor", "reserve_minor")
    }
    after["after"] = {
        k: after[k] for k in ("estimated_minor", "planned_minor", "actual_minor", "reserve_minor")
    }
    return after


@router.post("/timeline/tasks", response_model=TaskRead, status_code=201)
def add_task(
    event_id: UUID,
    payload: TaskWrite,
    request: Request,
    db: DB,
    identity: AuthorizedMutation,
    if_match: Annotated[str | None, Header()] = None,
):
    event = owned_event(db, event_id, identity.user.id, lock=True)
    precondition(event, if_match)
    rows = db.scalars(select(Task).where(Task.event_id == event_id)).all()
    candidate = Task(
        event_id=event_id,
        title=payload.title,
        description=payload.description,
        owner=payload.owner,
        priority=payload.priority,
        due_at=payload.due_at,
        depends_on=[str(dep) for dep in payload.depends_on],
    )
    validate_dependencies([*rows, candidate], event.starts_at, event.ends_at)
    db.add(candidate)
    event.revision += 1
    event.updated_at = datetime.now(UTC)
    audit(db, request, event, "event.updated", ["timeline"])
    db.commit()
    return TaskRead.model_validate(
        {**{k: getattr(candidate, k) for k in TaskRead.model_fields if hasattr(candidate, k)}}
    )


@router.patch("/timeline/tasks/{task_id}", response_model=TaskRead)
def edit_task(
    event_id: UUID,
    task_id: UUID,
    payload: TaskPatch,
    request: Request,
    db: DB,
    identity: AuthorizedMutation,
    if_match: Annotated[str | None, Header()] = None,
):
    event = owned_event(db, event_id, identity.user.id, lock=True)
    precondition(event, if_match)
    task = db.scalar(
        select(Task).where(Task.id == task_id, Task.event_id == event_id).with_for_update()
    )
    if not task:
        raise APIError(404, "TASK_NOT_FOUND", "This task could not be found.")
    changes = payload.model_dump(exclude_unset=True)
    if changes.get("status") == "done":
        changes["completed_at"] = datetime.now(UTC)
    if changes.get("status") and changes["status"] != "done":
        changes["completed_at"] = None
    for k, v in changes.items():
        setattr(task, k, v)
    validate_dependencies(
        db.scalars(select(Task).where(Task.event_id == event_id)).all(),
        event.starts_at,
        event.ends_at,
    )
    event.revision += 1
    event.updated_at = datetime.now(UTC)
    audit(db, request, event, "event.updated", ["timeline"])
    db.commit()
    return TaskRead.model_validate(
        {**{k: getattr(task, k) for k in TaskRead.model_fields if hasattr(task, k)}}
    )
