"""Deterministic provider doubles. These are not model-quality or live-AI evidence."""

from copy import deepcopy

from app.ai.provider import ProviderFailure

DETAILS = {
    "title": "A garden birthday",
    "event_type": "birthday",
    "start_local": "2030-05-20T18:00",
    "end_local": None,
    "start_fold": None,
    "end_fold": None,
    "duration_minutes": 180,
    "timezone": "Asia/Kolkata",
    "location": "Community garden",
    "guest_count": 30,
    "currency": "INR",
    "budget_amount": "30000.01",
    "preferences": ["Natural colours"],
    "constraints": ["No amplified music"],
    "dietary_needs": "Vegetarian",
    "accessibility_needs": "Step-free access",
}
PROPOSAL = {
    "summary": "A welcoming garden birthday with vegetarian food and gentle activities.",
    "budget_categories": [
        {"category": "Food", "description": "Vegetarian menu allocation", "weight": 2},
        {
            "category": "Venue and decor",
            "description": "A planning allocation requiring quotes",
            "weight": 1,
        },
    ],
    "preparation_tasks": [
        {
            "title": "Review venue access",
            "days_before_event": 14,
            "checklist": ["Check step-free entry", "Confirm an accessible toilet"],
        },
        {
            "title": "Confirm menu needs",
            "days_before_event": 7,
            "checklist": ["Ask about dietary requirements"],
        },
    ],
    "vendor_requirements": [
        {
            "category": "Catering",
            "requirements": ["Vegetarian options", "Clearly label allergens"],
            "checklist": ["Request an itemized quote", "Ask about service equipment"],
        }
    ],
    "themes": ["A relaxed garden gathering"],
    "menus": ["Seasonal vegetarian dishes"],
    "decor": ["Reusable table decorations"],
    "activities": ["Quiet conversation games"],
    "assumptions": ["The host will confirm venue access and actual supplier prices."],
    "unresolved_questions": ["Is indoor shelter available if it rains?"],
    "conflicts": [],
}


class FixtureProvider:
    kind = "test_fixture"

    def __init__(self):
        self.calls = 0
        self.failure = None
        self.callback = None

    def generate(self, operation, context, metrics):
        self.calls += 1
        metrics.calls += 1
        if metrics.on_call:
            metrics.on_call(metrics.calls)
        metrics.input_tokens, metrics.output_tokens = 100, 200
        if self.callback:
            self.callback()
        if self.failure or "simulate failure" in context.get("description", "").lower():
            raise ProviderFailure(self.failure or "AI_TIMEOUT")
        if operation == "intake":
            details = deepcopy(DETAILS)
            if "incomplete" in context.get("description", "").lower():
                for key in ("location", "guest_count", "budget_amount", "duration_minutes"):
                    details[key] = None
            return {"details": details, "questions": [], "conflicts": [], "assumptions": []}
        return deepcopy(PROPOSAL)
