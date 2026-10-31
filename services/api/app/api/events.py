import base64
import binascii
import json
from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Header, Query, Request, Response
from pydantic import ValidationError
from sqlalchemy import select, tuple_

from app.api.dependencies import DB
from app.core.auth import Authenticated, AuthorizedMutation
from app.core.errors import APIError, validation_fields
from app.db.models import AuditEvent, Event
from app.domain.schemas import EventPage, EventPatch, EventRead, EventWrite, local_instant

router = APIRouter(prefix="/api/v1/events", tags=["Events"])


def values(payload: EventWrite) -> dict[str, object]:
    result = payload.model_dump(exclude={"start_local", "end_local", "start_fold", "end_fold"})
    result["starts_at"] = local_instant(payload.start_local, payload.timezone, payload.start_fold)
    result["ends_at"] = local_instant(payload.end_local, payload.timezone, payload.end_fold)
    return result


def event_view(event: Event) -> EventRead:
    data = {
        name: getattr(event, name)
        for name in EventRead.model_fields
        if name not in {"start_local", "end_local", "start_fold", "end_fold"}
    }
    for prefix, instant in (("start", event.starts_at), ("end", event.ends_at)):
        local = instant.astimezone(ZoneInfo(event.timezone)) if instant else None
        data[f"{prefix}_local"] = local.replace(tzinfo=None) if local else None
        data[f"{prefix}_fold"] = local.fold if local else None
    return EventRead.model_validate(data)


def owned_event(db: DB, event_id: UUID, owner_id: UUID, *, lock: bool = False) -> Event:
    query = select(Event).where(Event.id == event_id, Event.owner_id == owner_id)
    if lock:
        query = query.with_for_update()
    event = db.scalar(query)
    if event is None:
        raise APIError(404, "EVENT_NOT_FOUND", "This event could not be found.")
    return event


def precondition(event: Event, if_match: str | None) -> None:
    if if_match is None:
        raise APIError(428, "REVISION_REQUIRED", "Reload the event before changing it.")
    if if_match != f'"{event.revision}"':
        raise APIError(
            412,
            "REVISION_CONFLICT",
            "This event changed in another window. Reload it before saving.",
        )


def audit(db: DB, request: Request, event: Event, action: str, fields: list[str]) -> None:
    db.add(
        AuditEvent(
            actor_id=event.owner_id,
            event_id=event.id,
            action=action,
            request_id=UUID(request.state.request_id),
            revision=event.revision,
            changed_fields=sorted(fields),
        )
    )


def response_event(response: Response, event: Event) -> EventRead:
    response.headers["ETag"] = f'"{event.revision}"'
    return event_view(event)


@router.post("", response_model=EventRead, status_code=201)
def create_event(
    payload: EventWrite, request: Request, response: Response, db: DB, identity: AuthorizedMutation
) -> EventRead:
    event = Event(owner_id=identity.user.id, **values(payload))
    db.add(event)
    db.flush()
    audit(db, request, event, "event.created", list(payload.model_fields_set))
    db.commit()
    response.headers["Location"] = f"/api/v1/events/{event.id}"
    return response_event(response, event)


@router.get("", response_model=EventPage)
def list_events(
    db: DB,
    identity: Authenticated,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: Annotated[str | None, Query(max_length=256)] = None,
    status: Literal["active", "archived", "all"] = "active",
) -> EventPage:
    query = select(Event).where(Event.owner_id == identity.user.id)
    if status == "active":
        query = query.where(Event.status != "archived")
    elif status == "archived":
        query = query.where(Event.status == "archived")
    if cursor:
        try:
            decoded = json.loads(base64.b64decode(cursor, altchars=b"-_", validate=True))
            if not isinstance(decoded, list) or len(decoded) != 2:
                raise ValueError
            stamp, identifier = datetime.fromisoformat(decoded[0]), UUID(decoded[1])
            if stamp.tzinfo is None:
                raise ValueError
        except ValueError, TypeError, binascii.Error, OverflowError:
            raise APIError(422, "VALIDATION_ERROR", "The page cursor is invalid.") from None
        query = query.where(tuple_(Event.created_at, Event.id) < tuple_(stamp, identifier))
    rows = db.scalars(
        query.order_by(Event.created_at.desc(), Event.id.desc()).limit(limit + 1)
    ).all()
    items = rows[:limit]
    next_cursor = None
    if len(rows) > limit:
        last = items[-1]
        next_cursor = base64.urlsafe_b64encode(
            json.dumps([last.created_at.isoformat(), str(last.id)]).encode()
        ).decode()
    return EventPage(items=[event_view(event) for event in items], next_cursor=next_cursor)


@router.get("/{event_id}", response_model=EventRead)
def get_event(event_id: UUID, response: Response, db: DB, identity: Authenticated) -> EventRead:
    return response_event(response, owned_event(db, event_id, identity.user.id))


@router.patch("/{event_id}", response_model=EventRead)
def edit_event(
    event_id: UUID,
    payload: EventPatch,
    request: Request,
    response: Response,
    db: DB,
    identity: AuthorizedMutation,
    if_match: Annotated[str | None, Header()] = None,
) -> EventRead:
    event = owned_event(db, event_id, identity.user.id, lock=True)
    precondition(event, if_match)
    if event.status == "archived":
        raise APIError(409, "EVENT_ARCHIVED", "Archived events are read-only.")
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise APIError(422, "VALIDATION_ERROR", "Supply at least one field to update.")
    existing = event_view(event).model_dump(include=set(EventWrite.model_fields))
    try:
        validated = EventWrite.model_validate({**existing, **changes})
    except ValidationError as exc:
        raise APIError(
            422,
            "VALIDATION_ERROR",
            "Some event details need attention.",
            validation_fields(exc.errors()),
        ) from None
    for key, value in values(validated).items():
        setattr(event, key, value)
    event.revision += 1
    event.updated_at = datetime.now(UTC)
    audit(db, request, event, "event.updated", list(changes))
    db.commit()
    return response_event(response, event)


@router.post("/{event_id}/archive", response_model=EventRead)
def archive_event(
    event_id: UUID,
    request: Request,
    response: Response,
    db: DB,
    identity: AuthorizedMutation,
    if_match: Annotated[str | None, Header()] = None,
) -> EventRead:
    event = owned_event(db, event_id, identity.user.id, lock=True)
    precondition(event, if_match)
    if event.status != "archived":
        event.status = "archived"
        event.archived_at = datetime.now(UTC)
        event.updated_at = event.archived_at
        event.revision += 1
        audit(db, request, event, "event.archived", ["status", "archived_at"])
        db.commit()
    return response_event(response, event)
