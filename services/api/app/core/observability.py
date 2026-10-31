import json
import logging
from datetime import UTC, datetime
from time import perf_counter
from uuid import UUID, uuid4

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class RequestBodyLimit:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            body.extend(message.get("body", b""))
            if len(body) > 65536:
                response = JSONResponse(
                    {
                        "error": {
                            "code": "REQUEST_TOO_LARGE",
                            "message": "The request is too large.",
                        },
                        "request_id": scope["state"]["request_id"],
                    },
                    status_code=413,
                )
                await response(scope, receive, send)
                return
            if not message.get("more_body", False):
                break
        delivered = False

        async def replay() -> Message:
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()

        await self.app(scope, replay, send)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        fields = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "event": record.getMessage(),
        }
        for key in (
            "request_id",
            "method",
            "route",
            "status_code",
            "duration_ms",
            "run_id",
            "operation",
            "call_count",
            "error_code",
            "input_tokens",
            "output_tokens",
        ):
            if hasattr(record, key):
                fields[key] = getattr(record, key)
        return json.dumps(fields)


def configure_logging(level: str) -> None:
    logger = logging.getLogger("eventora")
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logger.handlers = [handler]
    logger.setLevel(level)
    logger.propagate = False


class RequestContextMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        supplied = (
            dict(scope.get("headers", []))
            .get(b"x-request-id", b"")
            .decode("ascii", errors="ignore")
        )
        try:
            request_id = str(UUID(supplied))
        except ValueError:
            request_id = str(uuid4())
        scope.setdefault("state", {})["request_id"] = request_id
        start = perf_counter()
        status = 500
        started = False

        async def safe_send(message: Message) -> None:
            nonlocal status, started
            if message["type"] == "http.response.start":
                started = True
                status = message["status"]
                headers = list(message.get("headers", []))
                headers.extend(
                    [
                        (b"x-request-id", request_id.encode()),
                        (b"cache-control", b"no-store"),
                        (b"x-content-type-options", b"nosniff"),
                    ]
                )
                message = {**message, "headers": headers}
            await send(message)

        try:
            await self.app(scope, receive, safe_send)
        except Exception:
            # Never log exception strings: driver errors can contain credentials.
            if not started:
                response = JSONResponse(
                    {
                        "error": {
                            "code": "INTERNAL_ERROR",
                            "message": "Something went wrong. Please try again.",
                        },
                        "request_id": request_id,
                    },
                    status_code=500,
                )
                await response(scope, receive, safe_send)
        finally:
            route = getattr(scope.get("route"), "path", "<unmatched>")
            logging.getLogger("eventora").info(
                "http_request",
                extra={
                    "request_id": request_id,
                    "method": scope["method"],
                    "route": route,
                    "status_code": status,
                    "duration_ms": round((perf_counter() - start) * 1000, 2),
                },
            )
