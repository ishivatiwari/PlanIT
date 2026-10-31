"""Pure deterministic budget and dependency scheduling rules."""

from collections import defaultdict, deque
from collections.abc import Iterable, Sequence
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID

from app.domain.schemas import MAX_MONEY

SCENARIOS = {"economical", "balanced", "premium"}


class BudgetRow(Protocol):
    @property
    def scenario(self) -> str: ...
    @property
    def estimated_minor(self) -> int: ...
    @property
    def planned_minor(self) -> int: ...
    @property
    def actual_minor(self) -> int: ...


class ScheduledTask(Protocol):
    @property
    def id(self) -> UUID: ...
    @property
    def depends_on(self) -> Sequence[str | UUID]: ...
    @property
    def due_at(self) -> datetime | None: ...
    @property
    def priority(self) -> str: ...
    @property
    def status(self) -> str: ...


def budget_summary(
    items: Iterable[BudgetRow],
    ceiling: int | None,
    reserve_bps: int,
    scenario: str,
    currency: str,
    before: dict[str, int] | None = None,
) -> dict[str, Any]:
    if scenario not in SCENARIOS or not 0 <= reserve_bps <= 5000:
        raise ValueError("Invalid scenario or contingency reserve.")
    rows = [i for i in items if i.scenario == scenario]
    by_category: dict[str, int] = defaultdict(int)
    for item in rows:
        by_category[getattr(item, "category", "Uncategorized")] += item.planned_minor
    estimated = sum(i.estimated_minor for i in rows)
    planned = sum(i.planned_minor for i in rows)
    actual = sum(i.actual_minor for i in rows)
    reserve = (planned * reserve_bps + 9999) // 10000
    projected = planned + reserve
    if any(x > MAX_MONEY for x in (estimated, planned, actual, reserve, projected)):
        raise ValueError("Budget totals exceed supported limits.")
    remaining = None if ceiling is None else ceiling - projected
    result = {
        "estimated_minor": estimated,
        "planned_minor": planned,
        "actual_minor": actual,
        "reserve_minor": reserve,
    }
    return {
        "currency": currency,
        "ceiling_minor": ceiling,
        "scenario": scenario,
        "savings_alternatives": (
            [
                "Replace premium selections with economical alternatives.",
                "Defer non-critical items until quotes are confirmed.",
            ]
            if remaining is not None and remaining < 0
            else []
        ),
        "category_totals": [
            {"category": category, "planned_minor": amount}
            for category, amount in sorted(by_category.items())
        ],
        **result,
        "remaining_minor": remaining,
        "projected_overrun_minor": max(0, -remaining) if remaining is not None else 0,
        "before": before,
        "after": result,
    }


def validate_dependencies(
    tasks: Iterable[ScheduledTask], event_start: datetime | None, event_end: datetime | None
) -> list[UUID]:
    rows = list(tasks)
    ids = {t.id for t in rows}
    graph = {t.id: [UUID(str(dep)) for dep in (t.depends_on or [])] for t in rows}
    for task_id, deps in graph.items():
        if any(dep not in ids or dep == task_id for dep in deps):
            raise ValueError("Task dependency references a missing task or itself.")
    indegree = {i: 0 for i in ids}
    outgoing: dict[UUID, list[UUID]] = defaultdict(list)
    for task_id, deps in graph.items():
        for dep in deps:
            indegree[task_id] += 1
            outgoing[dep].append(task_id)
    queue = deque(i for i, v in indegree.items() if v == 0)
    ordered = []
    while queue:
        node = queue.popleft()
        ordered.append(node)
        for child in outgoing[node]:
            indegree[child] -= 1
            if indegree[child] == 0:
                queue.append(child)
    if len(ordered) != len(ids):
        raise ValueError("Task dependencies contain a cycle.")
    for task in rows:
        if task.due_at and event_start and task.due_at > event_start:
            raise ValueError("A task deadline cannot fall after the event starts.")
        if task.due_at and event_end and task.due_at > event_end:
            raise ValueError("A task deadline cannot fall after the event ends.")
    return ordered


def task_analysis(
    tasks: Iterable[ScheduledTask], now: datetime | None = None
) -> tuple[set[UUID], set[UUID], dict[UUID, list[UUID]]]:
    rows = list(tasks)
    now = now or datetime.now(UTC)
    ids = {t.id for t in rows}
    outgoing: dict[UUID, list[UUID]] = defaultdict(list)
    for t in rows:
        for dep in t.depends_on or []:
            outgoing[UUID(str(dep))].append(t.id)
    critical = {
        t.id
        for t in rows
        if t.priority == "critical" or t.status in {"todo", "in_progress"} and bool(outgoing[t.id])
    }
    delayed = {
        t.id for t in rows if t.due_at and t.due_at < now and t.status not in {"done", "cancelled"}
    }
    impact: dict[UUID, list[UUID]] = {i: [] for i in ids}
    for root in delayed:
        stack = list(outgoing[root])
        seen = set(stack)
        while stack:
            node = stack.pop()
            impact[root].append(node)
            for child in outgoing[node]:
                if child not in seen:
                    seen.add(child)
                    stack.append(child)
    return critical, delayed, impact
