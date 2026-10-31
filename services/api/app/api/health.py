from typing import Literal

from fastapi import APIRouter, Request
from pydantic import BaseModel
from starlette.responses import JSONResponse

router = APIRouter(prefix="/api/v1/health", tags=["Health"])


class HealthStatus(BaseModel):
    status: Literal["ok", "ready"]


@router.get("/live", response_model=HealthStatus)
def live() -> HealthStatus:
    return HealthStatus(status="ok")


@router.get("/ready", response_model=HealthStatus, responses={503: {"description": "Not ready"}})
def ready(request: Request) -> HealthStatus | JSONResponse:
    if request.app.state.database.ready():
        return HealthStatus(status="ready")
    return JSONResponse(
        {
            "error": {
                "code": "DEPENDENCY_UNAVAILABLE",
                "message": "The service is not ready. Please try again shortly.",
            },
            "request_id": request.state.request_id,
        },
        status_code=503,
    )
