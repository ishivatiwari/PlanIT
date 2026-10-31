"""Regression coverage for persisted budget and timeline mutations."""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import EventPlanVersion
from app.domain.schemas import MAX_MONEY
from app.main import create_app
from tests.test_events import HEADERS, account, new_event
from tests.test_planning import generate, planner  # noqa: F401

pytest_plugins = ["tests.test_events"]
pytestmark = pytest.mark.integration


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
