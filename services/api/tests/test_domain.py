from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.api.auth import Registration
from app.core.auth import hash_password, verify_password
from app.domain.schemas import (
    AuditEventData,
    BudgetItemData,
    EventPlanVersionData,
    EventWrite,
    GuestData,
    OrganizationData,
    TaskData,
    VendorData,
    VendorQuoteData,
    local_instant,
)


@pytest.mark.parametrize(
    "field,value",
    [
        ("title", "  "),
        ("event_type", "unknown"),
        ("timezone", "Mars/Olympus"),
        ("currency", "BTC"),
        ("guest_count", True),
        ("guest_count", 1.5),
        ("guest_count", 0),
        ("budget_ceiling_minor", 0.5),
        ("budget_ceiling_minor", True),
        ("budget_ceiling_minor", -1),
        ("budget_ceiling_minor", 9007199254740992),
        ("preferences", ["a"] * 21),
        ("status", "archived"),
        ("owner_id", str(uuid4())),
    ],
)
def test_event_rejects_invalid_and_mass_assigned_fields(field, value):
    with pytest.raises(ValidationError):
        EventWrite.model_validate({"title": "A gathering", "event_type": "wedding", field: value})


def test_draft_unknown_needs_are_distinct_from_none_and_complete_requires_intake():
    draft = EventWrite(title="  A gathering  ", event_type="community")
    assert draft.title == "A gathering" and draft.dietary_needs is None
    with pytest.raises(ValidationError):
        EventWrite.model_validate({**draft.model_dump(), "status": "confirmed"})
    confirmed = EventWrite.model_validate(
        {
            **draft.model_dump(),
            "status": "confirmed",
            "start_local": "2027-03-10T18:00",
            "location": "Town hall",
            "guest_count": 25,
            "budget_ceiling_minor": 0,
            "dietary_needs": "",
            "accessibility_needs": "",
        }
    )
    assert confirmed.budget_ceiling_minor == 0 and confirmed.dietary_needs == ""


def test_dates_offsets_and_dst():
    assert local_instant(datetime(2027, 1, 1, 18), "Asia/Kolkata", None) == datetime(
        2027, 1, 1, 12, 30, tzinfo=UTC
    )
    with pytest.raises(ValueError, match="does not exist"):
        local_instant(datetime(2027, 3, 14, 2, 30), "America/New_York", None)
    with pytest.raises(ValueError, match="occurs twice"):
        local_instant(datetime(2027, 11, 7, 1, 30), "America/New_York", None)
    first = local_instant(datetime(2027, 11, 7, 1, 30), "America/New_York", 0)
    second = local_instant(datetime(2027, 11, 7, 1, 30), "America/New_York", 1)
    assert (second - first).total_seconds() == 3600
    with pytest.raises(ValidationError):
        EventWrite(
            title="Party",
            event_type="birthday",
            start_local=datetime(2027, 1, 2),
            end_local=datetime(2027, 1, 1),
        )
    with pytest.raises(ValueError, match="without an offset"):
        local_instant(datetime.now(UTC), "UTC", None)


def test_money_is_exact_and_line_total_is_bounded():
    data = dict(
        event_id=uuid4(),
        plan_id=uuid4(),
        category="Food",
        description="Dinner",
        currency="INR",
        quantity=3,
        unit_amount_minor=10001,
        tax_minor=7,
        fee_minor=2,
    )
    assert BudgetItemData(**data).total_minor == 30012
    with pytest.raises(ValidationError):
        BudgetItemData(**{**data, "unit_amount_minor": 9007199254740991})
    with pytest.raises(ValidationError):
        BudgetItemData(**{**data, "unit_amount_minor": 1.1})
    assert BudgetItemData(**{**data, "currency": "JPY"}).total_minor == 30012


def test_related_domain_contracts_validate_state_and_bounds():
    event_id = uuid4()
    OrganizationData(name="Community circle")
    VendorData(event_id=event_id, name="Local caterer", category="Food")
    GuestData(event_id=event_id, name="Guest", rsvp_status="attending", party_size=2)
    AuditEventData(
        event_id=event_id, actor_id=uuid4(), action="event.created", request_id=uuid4(), revision=1
    )
    with pytest.raises(ValidationError):
        OrganizationData(name=" ")
    with pytest.raises(ValidationError):
        GuestData(event_id=event_id, name="Guest", party_size=True)
    with pytest.raises(ValidationError):
        TaskData(event_id=event_id, title="Order cake", status="done")
    with pytest.raises(ValidationError):
        VendorQuoteData(
            event_id=event_id,
            vendor_id=uuid4(),
            amount_minor=10,
            currency="INR",
            issued_on="2027-02-02",
            valid_until="2027-02-01",
        )
    with pytest.raises(ValidationError):
        EventPlanVersionData(
            event_id=event_id, sequence=1, base_event_revision=1, title="Initial", status="approved"
        )


def test_passwords_are_salted_and_user_model_validates():
    password = "a private passphrase with spaces  "
    first, second = hash_password(password), hash_password(password)
    assert first != second and password not in first
    assert verify_password(password, first)
    assert not verify_password(password.strip(), first)
    assert not verify_password("incorrect passphrase", first)
    assert not verify_password(password, "malformed")
    account = Registration(username="  Alice_1 ", display_name=" Alice ", password=password)
    assert account.username == "alice_1" and account.display_name == "Alice"
    with pytest.raises(ValidationError):
        Registration(username="alice", display_name="Alice", password="short")
