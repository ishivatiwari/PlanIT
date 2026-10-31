"""Deterministic impact analysis for adaptive replan proposals."""
# ruff: noqa: E501

from collections.abc import Sequence
from copy import deepcopy
from typing import Any

CHANGE_TYPES = {
    "guest_count",
    "venue_change",
    "quote_increase",
    "date_change",
    "task_delay",
    "budget_constraint",
}


def _money(document: dict[str, Any]) -> int:
    return sum(
        int(row.get("estimated_amount_minor", 0)) for row in document.get("budget_categories", [])
    )


def analyze_replan(
    change_type: str,
    details: dict[str, Any],
    document: dict[str, Any],
    tasks: Sequence[Any],
    vendors: Sequence[Any],
    event: Any,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if change_type not in CHANGE_TYPES:
        raise ValueError("Unsupported replan change.")
    alternative = deepcopy(document)
    affected: list[str] = []
    warnings: list[str] = []
    assumptions: list[str] = []
    tradeoffs: list[str] = []
    old_guests = event.guest_count or 0
    if change_type == "guest_count":
        new_guests = int(details.get("guest_count", 0))
        if new_guests < 1:
            raise ValueError("Guest count must be positive.")
        affected = [
            r["category"]
            for r in alternative.get("budget_categories", [])
            if any(w in r["category"].lower() for w in ("cater", "food", "beverage"))
        ]
        ratio = new_guests / old_guests if old_guests else 1
        for row in alternative.get("budget_categories", []):
            if row["category"] in affected:
                row["estimated_amount_minor"] = int(row["estimated_amount_minor"] * ratio)
        assumptions.append(
            f"Catering-related estimates scale from {old_guests} to {new_guests} guests; other categories are unchanged."
        )
        tradeoffs.append(
            "A larger guest list may require additional seating and accessibility checks."
        )
    elif change_type == "venue_change":
        affected = ["venue requirements", "venue-related tasks", "accessibility checks"]
        warnings.append("Replacement venue availability is unknown until evidence is supplied.")
        assumptions.append(
            "The replacement venue must independently satisfy the recorded accessibility and capacity requirements."
        )
        tradeoffs.append(
            "A venue replacement may change transport, rentals, permissions and layout costs."
        )
    elif change_type == "quote_increase":
        category = str(details.get("category", ""))
        increase = int(details.get("increase_minor", 0))
        if increase < 0:
            raise ValueError("Quote increase must be non-negative.")
        for row in alternative.get("budget_categories", []):
            if category.lower() in row["category"].lower():
                row["estimated_amount_minor"] += increase
                affected.append(row["category"])
        if not affected:
            warnings.append(
                "No matching budget category was found; the quote increase remains unresolved."
            )
        assumptions.append("The supplied increase is treated as an estimate, not a verified quote.")
    elif change_type == "date_change":
        if not details.get("start_local"):
            raise ValueError("A replacement event start is required.")
        affected = ["all dated tasks", "vendor evidence", "guest communications"]
        warnings.append("Vendor and guest availability for the replacement date is unknown.")
        assumptions.append(
            "Existing task lead times are retained and must be reviewed against the new date."
        )
    elif change_type == "task_delay":
        task_id = str(details.get("task_id", ""))
        days = int(details.get("delay_days", 0))
        if days < 1:
            raise ValueError("Task delay must be at least one day.")
        affected = [task.title for task in tasks if str(task.id) == task_id]
        if not affected:
            raise ValueError("The delayed task was not found in this event.")
        warnings.append("Downstream tasks require rescheduling review.")
        tradeoffs.append("Protecting completed tasks may reduce available alternatives.")
    elif change_type == "budget_constraint":
        ceiling = int(details.get("budget_ceiling_minor", -1))
        if ceiling < 0:
            raise ValueError("Budget ceiling must be non-negative.")
        total = _money(alternative)
        if total > ceiling and total:
            for row in alternative.get("budget_categories", []):
                row["estimated_amount_minor"] = row["estimated_amount_minor"] * ceiling // total
            warnings.append(
                "Allocations were proportionally reduced; review every category before approval."
            )
        affected = ["budget allocations", "non-critical tasks"]
        tradeoffs.append(
            "A lower ceiling may require deferring non-critical tasks or reducing inclusions."
        )
    total = _money(alternative)
    impact = {
        "affected": affected,
        "warnings": warnings,
        "assumptions": assumptions,
        "tradeoffs": tradeoffs,
        "before_total_minor": _money(document),
        "after_total_minor": total,
        "feasible": not any("unknown" in w.lower() for w in warnings)
        and (event.budget_ceiling_minor is None or total <= event.budget_ceiling_minor),
    }
    if event.budget_ceiling_minor is not None and total > event.budget_ceiling_minor:
        impact["feasible"] = False
        warnings.append("The alternative exceeds the current event budget ceiling.")
    alternative.setdefault("assumptions", []).extend(assumptions)
    alternative.setdefault("unresolved_questions", []).extend(warnings)
    return impact, alternative
