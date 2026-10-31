from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.domain.budget_timeline import budget_summary, task_analysis, validate_dependencies


def item(scenario="balanced", estimated=100, planned=200, actual=50):
    return SimpleNamespace(scenario=scenario, estimated_minor=estimated, planned_minor=planned, actual_minor=actual)


def test_budget_scenarios_reserve_and_overrun_are_exact():
    result = budget_summary([item(), item("economical", 10, 20, 5)], 210, 500, "balanced", "INR")
    assert result["planned_minor"] == 200
    assert result["reserve_minor"] == 10
    assert result["remaining_minor"] == 0
    assert result["projected_overrun_minor"] == 0
    over = budget_summary([item(planned=300)], 200, 0, "balanced", "INR")
    assert over["projected_overrun_minor"] == 100
    assert over["savings_alternatives"]


def test_budget_rejects_invalid_reserve_and_scenario():
    with pytest.raises(ValueError):
        budget_summary([item()], 100, 5001, "balanced", "INR")
    with pytest.raises(ValueError):
        budget_summary([item()], 100, 0, "custom", "INR")


def test_dependencies_detect_cycle_and_impossible_deadline():
    first, second = uuid4(), uuid4()
    tasks = [SimpleNamespace(id=first, depends_on=[second], due_at=None), SimpleNamespace(id=second, depends_on=[first], due_at=None)]
    with pytest.raises(ValueError, match="cycle"):
        validate_dependencies(tasks, None, None)
    task = SimpleNamespace(id=first, depends_on=[], due_at=datetime(2030, 1, 2, tzinfo=UTC))
    with pytest.raises(ValueError, match="starts"):
        validate_dependencies([task], datetime(2030, 1, 1, tzinfo=UTC), None)


def test_delayed_task_impact_preserves_completed_tasks():
    root, child, done = uuid4(), uuid4(), uuid4()
    now = datetime.now(UTC)
    tasks = [
        SimpleNamespace(id=root, depends_on=[], priority="critical", status="todo", due_at=now - timedelta(days=1)),
        SimpleNamespace(id=child, depends_on=[root], priority="normal", status="todo", due_at=now + timedelta(days=1)),
        SimpleNamespace(id=done, depends_on=[root], priority="normal", status="done", due_at=now - timedelta(days=1)),
    ]
    critical, delayed, impact = task_analysis(tasks, now)
    assert root in critical and root in delayed and child in impact[root]
    assert done not in delayed  # completed work is preserved and never marked late
