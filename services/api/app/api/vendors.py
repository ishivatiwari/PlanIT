from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header, Query, Request
from sqlalchemy import select

from app.api.dependencies import DB
from app.api.events import audit, editable_event, owned_event
from app.core.auth import Authenticated, AuthorizedMutation
from app.core.errors import APIError
from app.db.models import Vendor, VendorQuote
from app.domain.schemas import QuoteWrite, VendorRead, VendorWrite

router = APIRouter(prefix="/api/v1/events/{event_id}/vendors", tags=["Vendor intelligence"])


def view(v: Vendor, quotes: list[VendorQuote]) -> VendorRead:
    return VendorRead.model_validate(
        {
            **{k: getattr(v, k) for k in VendorRead.model_fields if hasattr(v, k)},
            "quotes": [
                {
                    k: getattr(q, k)
                    for k in (
                        "id",
                        "amount_minor",
                        "currency",
                        "issued_on",
                        "valid_until",
                        "status",
                        "reference",
                        "provenance",
                        "inclusions",
                        "cancellation_terms",
                        "deposit_minor",
                        "availability_evidence",
                    )
                }
                for q in quotes
            ],
        }
    )


@router.get("", response_model=list[VendorRead])
def list_vendors(
    event_id: UUID,
    db: DB,
    identity: Authenticated,
    category: str | None = None,
    provenance: str | None = None,
    sort: Annotated[str, Query(pattern="^(name|price|category)$")] = "name",
) -> list[VendorRead]:
    owned_event(db, event_id, identity.user.id)
    query = select(Vendor).where(Vendor.event_id == event_id)
    if category:
        query = query.where(Vendor.category.ilike(category))
    if provenance:
        query = query.where(Vendor.provenance == provenance)
    rows = db.scalars(query.order_by(Vendor.category if sort == "category" else Vendor.name)).all()
    if not rows:
        return []
    quotes = db.scalars(
        select(VendorQuote).where(
            VendorQuote.event_id == event_id,
            VendorQuote.vendor_id.in_(query.with_only_columns(Vendor.id)),
        )
    ).all()
    by: dict[UUID, list[VendorQuote]] = {}
    for q in quotes:
        by.setdefault(q.vendor_id, []).append(q)
    if sort == "price":
        rows = sorted(
            rows, key=lambda v: min((q.amount_minor for q in by.get(v.id, [])), default=10**18)
        )
    return [view(v, by.get(v.id, [])) for v in rows]


@router.post("", response_model=VendorRead, status_code=201)
def create_vendor(
    event_id: UUID,
    payload: VendorWrite,
    request: Request,
    db: DB,
    identity: AuthorizedMutation,
    if_match: Annotated[str | None, Header()] = None,
) -> VendorRead:
    event = editable_event(db, event_id, identity.user.id, if_match)
    if payload.provenance == "demo_seeded" and not payload.source_label.lower().startswith("demo"):
        raise APIError(
            422, "PROVENANCE_REQUIRED", "Demonstration records need a demonstration source label."
        )
    vendor = Vendor(event_id=event_id, **payload.model_dump())
    db.add(vendor)
    event.revision += 1
    event.updated_at = datetime.now(UTC)
    audit(db, request, event, "event.updated", ["vendor"])
    db.commit()
    return view(vendor, [])


@router.post("/{vendor_id}/quotes", response_model=VendorRead, status_code=201)
def add_quote(
    event_id: UUID,
    vendor_id: UUID,
    payload: QuoteWrite,
    request: Request,
    db: DB,
    identity: AuthorizedMutation,
    if_match: Annotated[str | None, Header()] = None,
) -> VendorRead:
    event = editable_event(db, event_id, identity.user.id, if_match)
    if payload.vendor_id != vendor_id:
        raise APIError(422, "VENDOR_MISMATCH", "The quote must reference the selected vendor.")
    vendor = db.scalar(
        select(Vendor).where(Vendor.id == vendor_id, Vendor.event_id == event_id).with_for_update()
    )
    if not vendor:
        raise APIError(404, "VENDOR_NOT_FOUND", "This vendor could not be found.")
    quote = VendorQuote(event_id=event_id, currency=event.currency, **payload.model_dump())
    db.add(quote)
    event.revision += 1
    event.updated_at = datetime.now(UTC)
    audit(db, request, event, "event.updated", ["vendor_quote"])
    db.commit()
    return view(vendor, [quote])
