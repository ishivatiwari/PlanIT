from collections.abc import Sequence
from typing import Any


class APIError(Exception):
    def __init__(
        self, status: int, code: str, message: str, fields: list[dict[str, str]] | None = None
    ) -> None:
        self.status = status
        self.code = code
        self.message = message
        self.fields = fields or []


def validation_fields(errors: Sequence[Any]) -> list[dict[str, str]]:
    """Never return submitted values, exception context, or unrecognized field names."""
    allowed = {
        "title",
        "event_type",
        "timezone",
        "currency",
        "start_local",
        "end_local",
        "start_fold",
        "end_fold",
        "location",
        "guest_count",
        "budget_ceiling_minor",
        "preferences",
        "dietary_needs",
        "accessibility_needs",
        "status",
        "username",
        "password",
        "display_name",
        "cursor",
        "limit",
        "event_id",
    }
    fields = []
    for error in errors[:20]:
        path = next((str(part) for part in error["loc"] if part in allowed), "form")
        message = str(error["msg"]).removeprefix("Value error, ")
        if error["type"] == "extra_forbidden":
            message = "An unsupported field was supplied."
        fields.append({"path": path, "message": message})
    return fields
