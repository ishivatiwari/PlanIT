from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.domain.replanning import analyze_replan


def document():
    return {
        "summary": "Plan",
        "budget_categories": [
            {"category": "Catering", "description": "Food", "estimated_amount_minor": 1000},
            {"category": "Decor", "description": "Decor", "estimated_amount_minor": 500},
        ],
        "preparation_tasks": [],
        "vendor_requirements": [],
        "themes": [],
        "menus": [],
        "decor": [],
        "activities": [],
        "assumptions": [],
        "unresolved_questions": [],
        "conflicts": [],
    }


def event():
    return SimpleNamespace(guest_count=10, budget_ceiling_minor=2000)


def test_guest_change_scales_catering_and_explains_tradeoff():
    impact, alternative = analyze_replan(
        "guest_count", {"guest_count": 20}, document(), [], [], event()
    )
    assert impact["affected"] == ["Catering"]
    assert alternative["budget_categories"][0]["estimated_amount_minor"] == 2000
    assert impact["assumptions"]


def test_quote_increase_can_be_flagged_infeasible():
    impact, _ = analyze_replan(
        "quote_increase",
        {"category": "Catering", "increase_minor": 1500},
        document(),
        [],
        [],
        event(),
    )
    assert impact["feasible"] is False
    assert any("ceiling" in warning for warning in impact["warnings"])


def test_task_delay_requires_existing_task():
    with pytest.raises(ValueError, match="not found"):
        analyze_replan(
            "task_delay", {"task_id": str(uuid4()), "delay_days": 2}, document(), [], [], event()
        )


def test_budget_constraint_is_deterministic():
    impact, alternative = analyze_replan(
        "budget_constraint", {"budget_ceiling_minor": 750}, document(), [], [], event()
    )
    assert impact["after_total_minor"] == 750
    assert sum(row["estimated_amount_minor"] for row in alternative["budget_categories"]) == 750
