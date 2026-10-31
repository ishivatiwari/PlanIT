"""Owner-scoped, evidence-preserving event exports."""
# ruff: noqa: E501

import json
from datetime import date, datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Query, Response
from sqlalchemy import select

from app.api.dependencies import DB
from app.api.events import owned_event
from app.core.auth import Authenticated
from app.db.models import BudgetItem, EventPlanVersion, Task, Vendor, VendorQuote
from app.domain.budget_timeline import budget_summary

router = APIRouter(prefix="/api/v1/events/{event_id}", tags=["Exports"])


def _json_value(value: object) -> object:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    return value


def _payload(db: Any, event: Any) -> dict[str, Any]:
    plan = db.scalar(
        select(EventPlanVersion)
        .where(EventPlanVersion.event_id == event.id)
        .order_by(EventPlanVersion.sequence.desc())
    )
    items = db.scalars(
        select(BudgetItem).where(BudgetItem.event_id == event.id).order_by(BudgetItem.created_at)
    ).all()
    tasks = db.scalars(
        select(Task).where(Task.event_id == event.id).order_by(Task.due_at.nullslast(), Task.id)
    ).all()
    vendors = db.scalars(
        select(Vendor).where(Vendor.event_id == event.id).order_by(Vendor.category, Vendor.name)
    ).all()
    quotes = db.scalars(select(VendorQuote).where(VendorQuote.event_id == event.id)).all()
    quotes_by_vendor: dict[UUID, list[dict[str, object]]] = {}
    for quote in quotes:
        quotes_by_vendor.setdefault(quote.vendor_id, []).append(
            {
                "amount_minor": quote.amount_minor,
                "currency": quote.currency,
                "status": quote.status,
                "provenance": quote.provenance,
                "reference": quote.reference,
                "inclusions": quote.inclusions,
                "availability_evidence": quote.availability_evidence,
                "cancellation_terms": quote.cancellation_terms,
                "deposit_minor": quote.deposit_minor,
            }
        )
    summary = budget_summary(
        items,
        event.budget_ceiling_minor,
        event.contingency_bps,
        "balanced",
        event.currency,
    )
    return {
        "export_version": 1,
        "exported_at": datetime.now().astimezone().isoformat(),
        "event": {
            "id": event.id,
            "title": event.title,
            "event_type": event.event_type,
            "timezone": event.timezone,
            "currency": event.currency,
            "starts_at": event.starts_at,
            "ends_at": event.ends_at,
            "location": event.location,
            "guest_count": event.guest_count,
            "budget_ceiling_minor": event.budget_ceiling_minor,
            "preferences": event.preferences,
            "dietary_needs": event.dietary_needs,
            "accessibility_needs": event.accessibility_needs,
            "status": event.status,
        },
        "plan": (
            {
                "id": plan.id,
                "sequence": plan.sequence,
                "title": plan.title,
                "status": plan.status,
                "saved_at": plan.saved_at,
                "document": plan.document,
            }
            if plan
            else None
        ),
        "budget": {
            "summary": summary,
            "items": [
                {
                    "category": item.category,
                    "description": item.description,
                    "currency": item.currency,
                    "quantity": item.quantity,
                    "estimated_minor": item.estimated_minor,
                    "planned_minor": item.planned_minor,
                    "actual_minor": item.actual_minor,
                    "total_minor": item.total_minor,
                    "scenario": item.scenario,
                }
                for item in items
            ],
        },
        "checklist": [
            {
                "id": task.id,
                "title": task.title,
                "description": task.description,
                "status": task.status,
                "owner": task.owner,
                "priority": task.priority,
                "due_at": task.due_at,
                "depends_on": task.depends_on,
            }
            for task in tasks
        ],
        "vendors": [
            {
                "name": vendor.name,
                "category": vendor.category,
                "location": vendor.location,
                "provenance": vendor.provenance,
                "source_label": vendor.source_label,
                "service_inclusions": vendor.service_inclusions,
                "availability_evidence": vendor.availability_evidence,
                "cancellation_terms": vendor.cancellation_terms,
                "quotes": quotes_by_vendor.get(vendor.id, []),
            }
            for vendor in vendors
        ],
    }


def _markdown(payload: dict[str, Any]) -> str:
    event = payload["event"]
    lines = [
        f"# {event['title']}",
        "",
        f"**Type:** {event['event_type']}  ",
        f"**Date:** {event.get('starts_at') or 'Not set'}  ",
        f"**Guests:** {event.get('guest_count') or 'Not set'}  ",
        f"**Budget ceiling:** {event.get('currency')} minor units {event.get('budget_ceiling_minor') or 'Not set'}  ",
        f"**Location:** {event.get('location') or 'Not set'}",
        "",
        "## Budget",
    ]
    budget = payload["budget"]
    assert isinstance(budget, dict)
    summary = budget["summary"]
    assert isinstance(summary, dict)
    lines.extend(
        [
            f"Balanced estimate: {summary['estimated_minor']} {summary['currency']} minor units.",
            f"Planned: {summary['planned_minor']}; reserve: {summary['reserve_minor']}; projected overrun: {summary['projected_overrun_minor']}.",
            "",
            "| Category | Description | Planned minor units | Scenario |",
            "| --- | --- | ---: | --- |",
        ]
    )
    for item in budget["items"]:
        lines.append(
            f"| {item['category']} | {item['description']} | {item['planned_minor']} | {item['scenario']} |"
        )
    lines.extend(["", "## Preparation checklist"])
    for task in payload["checklist"]:
        lines.append(
            f"- [{'x' if task['status'] == 'done' else ' '}] {task['title']} — {task['due_at'] or 'date to be set'}"
        )
    lines.extend(["", "## Vendor requirements and evidence"])
    for vendor in payload["vendors"]:
        lines.append(
            f"- **{vendor['name']}** ({vendor['category']}) — {vendor['provenance']}; source: {vendor['source_label']}."
        )
    lines.extend(
        [
            "",
            "_Estimates and provenance labels are preserved; this export does not confirm availability or bookings._",
        ]
    )
    return "\n".join(lines) + "\n"


@router.get("/export")
def export_event(
    event_id: UUID,
    db: DB,
    identity: Authenticated,
    format: Annotated[str, Query(pattern="^(json|markdown)$")] = "json",
) -> Response:
    event = owned_event(db, event_id, identity.user.id)
    payload = _payload(db, event)
    filename = f"planit-{event.id}.{'md' if format == 'markdown' else 'json'}"
    if format == "markdown":
        return Response(
            content=_markdown(payload),
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    return Response(
        content=json.dumps(payload, default=_json_value, ensure_ascii=False),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
