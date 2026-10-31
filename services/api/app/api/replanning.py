from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header, Request
from sqlalchemy import func, select

from app.api.dependencies import DB
from app.api.events import audit, editable_event, owned_event
from app.core.auth import Authenticated, AuthorizedMutation
from app.core.errors import APIError
from app.db.models import EventPlanVersion, ReplanProposal, Task
from app.domain.planning import PlanDocument
from app.domain.replanning import analyze_replan
from app.domain.schemas import ReplanRead, ReplanRequest

router = APIRouter(prefix="/api/v1/events/{event_id}/replans", tags=["Adaptive replanning"])


def view(row: ReplanProposal) -> ReplanRead:
    return ReplanRead.model_validate({k: getattr(row, k) for k in ReplanRead.model_fields})


def base_plan(db: DB, event_id: UUID) -> EventPlanVersion:
    row = db.scalar(
        select(EventPlanVersion)
        .where(EventPlanVersion.event_id == event_id, EventPlanVersion.document.is_not(None))
        .order_by(EventPlanVersion.sequence.desc())
        .limit(1)
    )
    if row is None:
        raise APIError(409, "PLAN_REQUIRED", "Create a reviewable plan before requesting a replan.")
    return row


@router.get("", response_model=list[ReplanRead])
def list_replans(event_id: UUID, db: DB, identity: Authenticated) -> list[ReplanRead]:
    owned_event(db, event_id, identity.user.id)
    return [
        view(row)
        for row in db.scalars(
            select(ReplanProposal)
            .where(ReplanProposal.event_id == event_id, ReplanProposal.owner_id == identity.user.id)
            .order_by(ReplanProposal.created_at.desc())
            .limit(20)
        ).all()
    ]


@router.post("", response_model=ReplanRead, status_code=201)
def propose_replan(
    event_id: UUID,
    payload: ReplanRequest,
    request: Request,
    db: DB,
    identity: AuthorizedMutation,
    if_match: Annotated[str | None, Header()] = None,
) -> ReplanRead:
    event = editable_event(db, event_id, identity.user.id, if_match)
    plan = base_plan(db, event_id)
    tasks = []
    if payload.change_type == "task_delay":
        try:
            task_id = UUID(str(payload.details.get("task_id", "")))
        except ValueError:
            raise APIError(422, "INFEASIBLE_REPLAN", "Choose a task from this event.") from None
        tasks = list(db.scalars(select(Task).where(Task.event_id == event_id, Task.id == task_id)))
    try:
        impact, alternative = analyze_replan(
            payload.change_type, payload.details, plan.document or {}, tasks, [], event
        )
        PlanDocument.model_validate(alternative)
    except (ValueError, TypeError) as exc:
        raise APIError(422, "INFEASIBLE_REPLAN", str(exc)) from None
    row = ReplanProposal(
        owner_id=identity.user.id,
        event_id=event_id,
        base_plan_id=plan.id,
        base_event_revision=event.revision,
        change_type=payload.change_type,
        request=payload.model_dump(mode="json"),
        impact=impact,
        alternative=alternative,
    )
    db.add(row)
    db.flush()
    audit(db, request, event, "replan.proposed", ["replan"])
    db.commit()
    return view(row)


@router.post("/{proposal_id}/reject", response_model=ReplanRead)
def reject_replan(
    event_id: UUID,
    proposal_id: UUID,
    request: Request,
    db: DB,
    identity: AuthorizedMutation,
    if_match: Annotated[str | None, Header()] = None,
) -> ReplanRead:
    event = editable_event(db, event_id, identity.user.id, if_match)
    row = db.scalar(
        select(ReplanProposal)
        .where(
            ReplanProposal.id == proposal_id,
            ReplanProposal.event_id == event_id,
            ReplanProposal.owner_id == identity.user.id,
        )
        .with_for_update()
    )
    if not row:
        raise APIError(404, "REPLAN_NOT_FOUND", "This proposal could not be found.")
    if row.status != "pending":
        raise APIError(409, "REPLAN_CLOSED", "This proposal is already closed.")
    row.status = "rejected"
    row.rejection_reason = "Rejected by the event owner."
    audit(db, request, event, "replan.rejected", ["replan"])
    db.commit()
    return view(row)


@router.post("/{proposal_id}/approve", response_model=ReplanRead)
def approve_replan(
    event_id: UUID,
    proposal_id: UUID,
    request: Request,
    db: DB,
    identity: AuthorizedMutation,
    if_match: Annotated[str | None, Header()] = None,
) -> ReplanRead:
    event = editable_event(db, event_id, identity.user.id, if_match)
    row = db.scalar(
        select(ReplanProposal)
        .where(
            ReplanProposal.id == proposal_id,
            ReplanProposal.event_id == event_id,
            ReplanProposal.owner_id == identity.user.id,
        )
        .with_for_update()
    )
    if not row:
        raise APIError(404, "REPLAN_NOT_FOUND", "This proposal could not be found.")
    plan = db.scalar(
        select(EventPlanVersion)
        .where(EventPlanVersion.id == row.base_plan_id, EventPlanVersion.event_id == event_id)
        .with_for_update()
    )
    if row.status != "pending":
        raise APIError(409, "REPLAN_CLOSED", "This proposal is already closed.")
    if (
        not plan
        or plan.id != base_plan(db, event_id).id
        or row.base_event_revision != event.revision
    ):
        row.status = "stale"
        db.commit()
        raise APIError(412, "REPLAN_STALE", "The event or plan changed. Review a new proposal.")
    document = PlanDocument.model_validate(row.alternative)
    sequence = (
        db.scalar(
            select(func.max(EventPlanVersion.sequence)).where(EventPlanVersion.event_id == event_id)
        )
        or 0
    ) + 1
    new_plan = EventPlanVersion(
        event_id=event_id,
        sequence=sequence,
        base_event_revision=event.revision + 1,
        parent_id=plan.id,
        title=plan.title,
        status="approved",
        approved_by=identity.user.id,
        approved_at=datetime.now(UTC),
        intake=plan.intake,
        document=document.model_dump(mode="json"),
        prompt_version=plan.prompt_version,
    )
    db.add(new_plan)
    db.flush()
    event.revision += 1
    event.updated_at = datetime.now(UTC)
    row.status = "accepted"
    row.accepted_plan_id = new_plan.id
    audit(db, request, event, "replan.approved", ["replan", "plan_version"])
    db.commit()
    return view(row)
