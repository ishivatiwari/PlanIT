r"""Seed an explicitly labelled PlanIT demonstration event and vendor set.

Usage (from the repository root):
  $env:DEMO_USERNAME='demo_wedding'; $env:DEMO_PASSWORD='use-a-long-local-password'
  .\services\api\.venv\Scripts\python.exe scripts/seed_demo.py

The command is idempotent for the same username/title. It never creates a shared
account or claims vendor availability. Use --fallback-plan when the configured
AI provider is unavailable; the resulting plan is clearly marked as a fallback.
"""
# ruff: noqa: E501

import argparse
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "api"))

from app.core.auth import hash_password  # noqa: E402
from app.core.settings import load_settings  # noqa: E402
from app.db.connection import Database  # noqa: E402
from app.db.models import BudgetItem, Event, EventPlanVersion, Task, User, Vendor, VendorQuote  # noqa: E402


def fallback_document():
    return {
        "summary": "A welcoming, elegant wedding celebration for 300 guests with a calm guest experience and a clearly bounded INR budget.",
        "budget_categories": [
            {
                "category": "Venue",
                "description": "Venue and core access",
                "estimated_amount_minor": 250000,
            },
            {
                "category": "Catering",
                "description": "Vegetarian menu and service",
                "estimated_amount_minor": 300000,
            },
            {
                "category": "Decor",
                "description": "Floral and table styling",
                "estimated_amount_minor": 150000,
            },
            {
                "category": "Photography",
                "description": "Ceremony and reception coverage",
                "estimated_amount_minor": 100000,
            },
            {
                "category": "Entertainment",
                "description": "Sound and music",
                "estimated_amount_minor": 80000,
            },
            {
                "category": "Contingency",
                "description": "Planning reserve",
                "estimated_amount_minor": 120000,
            },
        ],
        "preparation_tasks": [
            {
                "title": "Confirm venue requirements",
                "days_before_event": 120,
                "checklist": ["Capacity", "Access needs", "Cancellation terms"],
            },
            {
                "title": "Lock catering menu",
                "days_before_event": 60,
                "checklist": ["Dietary labels", "Headcount", "Service timing"],
            },
            {
                "title": "Final guest and vendor briefing",
                "days_before_event": 7,
                "checklist": ["Run sheet", "Emergency contacts", "Accessibility check"],
            },
        ],
        "vendor_requirements": [
            {
                "category": "Venue",
                "requirements": [
                    "Capacity for 300 guests",
                    "Accessible arrival",
                    "Rain contingency",
                ],
                "checklist": ["Ask for written quote", "Review cancellation terms"],
            },
            {
                "category": "Catering",
                "requirements": ["Vegetarian menu", "Dietary labelling", "Service for 300 guests"],
                "checklist": ["Confirm tasting", "Confirm staffing"],
            },
        ],
        "themes": ["Ivory and sage garden evening"],
        "menus": ["Vegetarian regional buffet with clearly labelled allergens"],
        "decor": ["Low-waste florals, warm table lighting and step-free aisles"],
        "activities": ["Welcome toast", "Family photo hour", "Quiet seating area"],
        "assumptions": [
            "All costs are planning estimates in INR minor units.",
            "Vendor availability is unknown until evidenced.",
        ],
        "unresolved_questions": ["Which venue quote will the couple provide?"],
        "conflicts": [],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--fallback-plan",
        action="store_true",
        help="Seed a clearly labelled non-AI fallback draft.",
    )
    args = parser.parse_args()
    username = os.environ.get("DEMO_USERNAME", "demo_wedding").strip().lower()
    password = os.environ.get("DEMO_PASSWORD", "")
    if len(username) < 3 or len(username) > 32 or not password or len(password) < 15:
        raise SystemExit("Set DEMO_USERNAME and DEMO_PASSWORD (at least 15 characters) first.")
    settings = load_settings()
    database = Database(settings)
    event_date = datetime(2027, 2, 20, 11, 30, tzinfo=UTC)
    with Session(database.engine, expire_on_commit=False) as db:
        user = db.scalar(select(User).where(User.username == username))
        if user is None:
            user = User(
                username=username,
                display_name="PlanIT demo owner",
                password_hash=hash_password(password),
            )
            db.add(user)
            db.flush()
        event = db.scalar(
            select(Event).where(
                Event.owner_id == user.id, Event.title == "Demo Wedding — 300 Guests"
            )
        )
        if event is None:
            event = Event(
                owner_id=user.id,
                title="Demo Wedding — 300 Guests",
                event_type="wedding",
                timezone="Asia/Kolkata",
                currency="INR",
                starts_at=event_date,
                ends_at=event_date + timedelta(hours=6),
                location="Bengaluru Garden Hall (demo)",
                guest_count=300,
                budget_ceiling_minor=100000000,
                contingency_bps=1000,
                preferences=["sage and ivory", "step-free access"],
                dietary_needs="Vegetarian menu; label allergens",
                accessibility_needs="Step-free arrival and quiet seating",
                status="draft",
            )
            db.add(event)
            db.flush()
        vendors = [
            ("Demo Garden Hall", "venue", 25000000, ["300 guest capacity", "Step-free entrance"]),
            ("Demo Table & Tiffin", "catering", 30000000, ["Vegetarian buffet", "Allergen labels"]),
            (
                "Demo Lens Collective",
                "photography",
                10000000,
                ["Ceremony coverage", "Reception coverage"],
            ),
        ]
        existing_names = {
            row.name for row in db.scalars(select(Vendor).where(Vendor.event_id == event.id)).all()
        }
        for name, category, amount, inclusions in vendors:
            if name in existing_names:
                continue
            vendor = Vendor(
                event_id=event.id,
                name=name,
                category=category,
                location="Bengaluru (demo)",
                provenance="demo_seeded",
                source_label="Demo dataset — not verified",
                service_inclusions=inclusions,
                availability_evidence=None,
                cancellation_terms=None,
            )
            db.add(vendor)
            db.flush()
            db.add(
                VendorQuote(
                    event_id=event.id,
                    vendor_id=vendor.id,
                    amount_minor=amount,
                    currency="INR",
                    issued_on=event_date.date(),
                    status="received",
                    reference="DEMO-ONLY",
                    provenance="demo_seeded",
                    inclusions=inclusions,
                    availability_evidence=None,
                )
            )
        if (
            args.fallback_plan
            and db.scalar(select(EventPlanVersion).where(EventPlanVersion.event_id == event.id))
            is None
        ):
            document = fallback_document()
            intake = {
                "title": event.title,
                "event_type": "wedding",
                "start_local": "2027-02-20T17:00:00",
                "end_local": "2027-02-20T23:00:00",
                "start_fold": None,
                "end_fold": None,
                "duration_minutes": 360,
                "timezone": "Asia/Kolkata",
                "location": event.location,
                "guest_count": 300,
                "currency": "INR",
                "budget_amount": "1000000",
                "preferences": event.preferences,
                "constraints": [],
                "dietary_needs": event.dietary_needs,
                "accessibility_needs": event.accessibility_needs,
            }
            plan = EventPlanVersion(
                event_id=event.id,
                sequence=1,
                base_event_revision=event.revision,
                title="Fallback wedding plan (demo)",
                status="draft",
                intake=intake,
                document=document,
                saved_at=datetime.now(UTC),
                prompt_version="fallback-demo",
            )
            db.add(plan)
            db.flush()
            for category in document["budget_categories"]:
                db.add(
                    BudgetItem(
                        event_id=event.id,
                        plan_id=plan.id,
                        category=category["category"],
                        description=category["description"],
                        currency="INR",
                        unit_amount_minor=category["estimated_amount_minor"],
                        estimated_minor=category["estimated_amount_minor"],
                        planned_minor=category["estimated_amount_minor"],
                        scenario="balanced",
                    )
                )
            for index, task in enumerate(document["preparation_tasks"]):
                db.add(
                    Task(
                        event_id=event.id,
                        plan_id=plan.id,
                        title=task["title"],
                        description="Fallback demo checklist",
                        priority="high" if index == 0 else "normal",
                        due_at=event_date - timedelta(days=task["days_before_event"]),
                    )
                )
        db.commit()
        print(f"Demo event ready: {event.id}")
        print("Sample vendors are labelled Demo dataset — not verified.")
        print("Open /events, sign in with the supplied demo account, and use Plan with AI.")
        if args.fallback_plan:
            print("A fallback draft was seeded; it is an estimate and not an AI provider result.")


if __name__ == "__main__":
    main()
