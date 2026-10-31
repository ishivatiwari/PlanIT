"""Regression coverage for persisted budget and timeline mutations."""

from datetime import datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event as sqlalchemy_event
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import BudgetItem, EventPlanVersion, Task
from app.domain.schemas import MAX_MONEY
from app.main import create_app
from tests.test_events import HEADERS, account, new_event
from tests.test_planning import generate, planner  # noqa: F401

pytest_plugins = ["tests.test_events"]
pytestmark = pytest.mark.integration


@pytest.mark.parametrize("records", [100, 1000])
def test_planning_query_and_materialization_budgets(planner, records):  # noqa: F811
    client, headers, event, _, engine, _ = planner
    assert generate(client, headers, event).status_code == 200
    root = f"/api/v1/events/{event['id']}"
    with Session(engine) as db:
        plan = db.scalar(select(EventPlanVersion))
        db.add_all(
            [
                BudgetItem(
                    event_id=plan.event_id,
                    plan_id=plan.id,
                    category="Venue",
                    description="Synthetic cost",
                    currency="INR",
                    unit_amount_minor=0,
                    planned_minor=100,
                    scenario="balanced",
                )
                for _ in range(records)
            ]
        )
        tasks = [Task(event_id=plan.event_id, title=f"Task {i}") for i in range(records)]
        db.add_all(tasks)
        db.commit()
        task_id = tasks[0].id

    statements = []
    loaded = []
    api_engine = client.app.state.database.engine

    def record_query(connection, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("SELECT"):
            statements.append(statement)

    def record_load(instance, context):
        loaded.append(type(instance).__name__)

    sqlalchemy_event.listen(api_engine, "before_cursor_execute", record_query)
    sqlalchemy_event.listen(BudgetItem, "load", record_load)
    sqlalchemy_event.listen(Task, "load", record_load)
    try:
        summary = client.get(root + "/budget")
        assert summary.status_code == 200
        assert summary.json()["planned_minor"] == records * 100
        budget_queries = sum("FROM events" in s or "FROM budget_items" in s for s in statements)
        budget_rows = loaded.count("BudgetItem")
        statements.clear()
        loaded.clear()
        revision = client.get(root).json()["revision"]
        changed = client.patch(
            root + f"/timeline/tasks/{task_id}",
            json={"status": "done"},
            headers={**headers, "If-Match": f'"{revision}"'},
        )
        assert changed.status_code == 200
        task_queries = sum("FROM tasks" in s for s in statements)
        task_rows = loaded.count("Task")
        print(
            f"records={records}: budget SELECTs={budget_queries}, budget ORM rows={budget_rows}; "
            f"task status SELECTs={task_queries}, task ORM rows={task_rows}"
        )
        assert (budget_queries, budget_rows, task_queries, task_rows) == (2, 0, 1, 1)
        statements.clear()
        response = client.post(
            root + "/replans",
            json={"change_type": "guest_count", "details": {"guest_count": 40}},
            headers={**headers, "If-Match": f'"{revision + 1}"'},
        )
        assert response.status_code == 201
        assert not any(
            "FROM tasks" in statement or "FROM vendors" in statement for statement in statements
        )
        statements.clear()
        delayed = client.post(
            root + "/replans",
            json={
                "change_type": "task_delay",
                "details": {"task_id": str(task_id), "delay_days": 2},
            },
            headers={**headers, "If-Match": f'"{revision + 1}"'},
        )
        assert delayed.status_code == 201
        assert sum("FROM tasks" in statement for statement in statements) == 1
    finally:
        sqlalchemy_event.remove(api_engine, "before_cursor_execute", record_query)
        sqlalchemy_event.remove(BudgetItem, "load", record_load)
        sqlalchemy_event.remove(Task, "load", record_load)


def test_task_security_validation_and_persistence(store):
    _, settings = store
    with TestClient(create_app(settings)) as client:
        headers = account(client)
        event = new_event(client, headers, start_local="2030-05-20T18:00:00").json()
        root = f"/api/v1/events/{event['id']}"

        def revision():
            return {**headers, "If-Match": f'"{client.get(root).json()["revision"]}"'}

        assert (
            client.post(
                root + "/timeline/tasks",
                json={"title": "Missing CSRF"},
                headers={**HEADERS, "If-Match": '"1"'},
            ).status_code
            == 403
        )
        invalid = client.post(
            root + "/timeline/tasks",
            json={"title": "Impossible deadline", "due_at": "2031-01-01T00:00:00Z"},
            headers=revision(),
        )
        assert invalid.status_code == 422
        assert client.get(root).json()["revision"] == 1
        first = client.post(
            root + "/timeline/tasks", json={"title": "Confirm venue"}, headers=revision()
        )
        assert first.status_code == 201
        task = first.json()
        path = root + f"/timeline/tasks/{task['id']}"
        second = client.post(
            root + "/timeline/tasks", json={"title": "Send invitations"}, headers=revision()
        ).json()
        linked = client.patch(path, json={"depends_on": [second["id"]]}, headers=revision())
        assert linked.status_code == 200
        assert linked.json()["depends_on"] == [second["id"]]
        cycle = client.patch(
            root + f"/timeline/tasks/{second['id']}",
            json={"depends_on": [task["id"]]},
            headers=revision(),
        )
        assert cycle.status_code == 422
        assert (
            client.patch(
                path, json={"due_at": "2030-01-01T12:00:00"}, headers=revision()
            ).status_code
            == 422
        )
        assert client.patch(path, json={"status": None}, headers=revision()).status_code == 422
        done = client.patch(path, json={"status": "done"}, headers=revision()).json()
        repeated = client.patch(path, json={"status": "done"}, headers=revision()).json()
        assert datetime.fromisoformat(repeated["completed_at"]) == datetime.fromisoformat(
            done["completed_at"]
        )
        stale = client.patch(path, json={"status": "todo"}, headers={**headers, "If-Match": '"1"'})
        assert stale.status_code == 412
        assert client.post(root + "/archive", headers=revision()).status_code == 200
        assert (
            client.post(
                root + "/timeline/tasks", json={"title": "Blocked"}, headers=revision()
            ).status_code
            == 409
        )
        assert client.patch(path, json={"status": "todo"}, headers=revision()).status_code == 409
        assert client.get(root + "/timeline").json()[0]["id"]
        account(client, "another_owner")
        assert client.get(root + "/timeline").status_code == 404


def test_budget_saved_scenarios_and_archived_edits(planner):  # noqa: F811
    client, headers, event, _, engine, _ = planner
    assert generate(client, headers, event).status_code == 200
    root = f"/api/v1/events/{event['id']}"

    def revision():
        return {**headers, "If-Match": f'"{client.get(root).json()["revision"]}"'}

    payload = {"category": "Venue", "description": "Rental", "planned_minor": 12345}
    created = client.post(root + "/budget/items", json=payload, headers=revision())
    assert created.status_code == 201
    assert created.json()["planned_minor"] == 12345
    assert client.get(root + "/budget?scenario=premium").json()["planned_minor"] == 0
    from app.db.models import BudgetItem

    with Session(engine) as db:
        item = db.scalar(select(BudgetItem))
        item_id = str(item.id)
        assert db.scalar(select(EventPlanVersion)) is not None
    path = root + f"/budget/items/{item_id}"
    assert client.patch(path, json={"actual_minor": 12000}, headers=revision()).status_code == 200
    assert client.patch(path, json={"planned_minor": None}, headers=revision()).status_code == 422
    before = client.get(root).json()["revision"]
    overflow = client.post(
        root + "/budget/items",
        json={**payload, "planned_minor": MAX_MONEY},
        headers=revision(),
    )
    assert overflow.status_code == 422
    assert overflow.json()["error"]["code"] == "INVALID_BUDGET"
    assert client.get(root).json()["revision"] == before
    assert client.get(root + "/budget").json()["planned_minor"] == 12345
    premium = {**payload, "scenario": "premium"}
    assert client.post(root + "/budget/items", json=premium, headers=revision()).status_code == 201
    assert (
        client.post(
            root + "/budget/items",
            json={**premium, "planned_minor": MAX_MONEY},
            headers=revision(),
        ).status_code
        == 422
    )
    assert client.get(root + "/budget?scenario=premium").json()["planned_minor"] == 12345
    assert client.post(root + "/archive", headers=revision()).status_code == 200
    assert client.patch(path, json={"actual_minor": 1}, headers=revision()).status_code == 409
    assert client.get(root + "/budget").json()["actual_minor"] == 12000


def test_quote_persistence_and_archived_replan_guards(planner):  # noqa: F811
    client, headers, event, _, _, _ = planner
    assert generate(client, headers, event).status_code == 200
    root = f"/api/v1/events/{event['id']}"

    def revision():
        return {**headers, "If-Match": f'"{client.get(root).json()["revision"]}"'}

    created = client.post(
        root + "/vendors", json={"name": "Garden Hall", "category": "venue"}, headers=revision()
    )
    assert created.status_code == 201
    vendor_id = created.json()["id"]
    path = root + f"/vendors/{vendor_id}/quotes"
    quote = {"vendor_id": vendor_id, "amount_minor": 125050, "issued_on": "2030-01-01"}
    assert (
        client.post(path, json={**quote, "vendor_id": str(uuid4())}, headers=revision()).status_code
        == 422
    )
    assert client.post(path, json=quote, headers=revision()).status_code == 201
    persisted = client.get(root + "/vendors?category=venue").json()
    assert persisted[0]["quotes"][0]["amount_minor"] == 125050
    assert client.get(root + "/vendors?category=catering").json() == []
    proposal = client.post(
        root + "/replans",
        json={"change_type": "guest_count", "details": {"guest_count": 40}},
        headers=revision(),
    )
    assert proposal.status_code == 201
    assert client.post(root + "/archive", headers=revision()).status_code == 200
    assert client.post(path, json=quote, headers=revision()).status_code == 409
    for action in ("approve", "reject"):
        result = client.post(
            root + f"/replans/{proposal.json()['id']}/{action}", json={}, headers=revision()
        )
        assert result.status_code == 409
    assert client.get(root + "/replans").json()[0]["status"] == "pending"
