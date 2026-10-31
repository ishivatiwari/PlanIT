from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse

from app.ai.provider import GeminiProvider
from app.api.auth import router as auth_router
from app.api.budget_timeline import router as budget_timeline_router
from app.api.events import router as events_router
from app.api.exports import router as exports_router
from app.api.health import router
from app.api.planning import router as planning_router
from app.api.replanning import router as replanning_router
from app.api.vendors import router as vendors_router
from app.core.errors import APIError, validation_fields
from app.core.observability import RequestBodyLimit, RequestContextMiddleware, configure_logging
from app.core.settings import Settings, load_settings
from app.db.connection import Database


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.database = Database(settings)
        try:
            yield
        finally:
            app.state.database.close()

    app = FastAPI(
        title="PlanIT API",
        version="0.3.0",
        docs_url="/api/docs" if settings.app_env != "production" else None,
        redoc_url=None,
        openapi_url="/api/openapi.json" if settings.app_env != "production" else None,
        lifespan=lifespan,
        debug=False,
    )
    app.add_middleware(RequestBodyLimit)
    app.add_middleware(RequestContextMiddleware)
    app.state.settings = settings
    app.state.ai_provider = GeminiProvider(settings)
    app.include_router(router)
    app.include_router(auth_router)
    app.include_router(events_router)
    app.include_router(exports_router)
    app.include_router(planning_router)
    app.include_router(budget_timeline_router)
    app.include_router(vendors_router)
    app.include_router(replanning_router)

    @app.exception_handler(APIError)
    async def api_error(request: Request, exc: APIError) -> JSONResponse:
        return JSONResponse(
            {
                "error": {"code": exc.code, "message": exc.message, "fields": exc.fields},
                "request_id": request.state.request_id,
            },
            status_code=exc.status,
            headers={"Retry-After": "86400" if exc.code == "AI_DAILY_LIMIT" else "900"}
            if exc.status == 429
            else None,
        )

    @app.exception_handler(IntegrityError)
    async def conflict_error(request: Request, exc: IntegrityError) -> JSONResponse:
        return await api_error(
            request,
            APIError(
                409,
                "RESOURCE_CONFLICT",
                "This change conflicts with related records. Reload the event and try again.",
            ),
        )

    @app.exception_handler(SQLAlchemyError)
    async def database_error(request: Request, exc: SQLAlchemyError) -> JSONResponse:
        return await api_error(
            request,
            APIError(
                503,
                "DEPENDENCY_UNAVAILABLE",
                "The service is temporarily unavailable. Please try again.",
            ),
        )

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse(
            {
                "error": {"code": "HTTP_ERROR", "message": "The request could not be completed."},
                "request_id": request.state.request_id,
            },
            status_code=exc.status_code,
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            {
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Check the request fields.",
                    "fields": validation_fields(exc.errors()),
                },
                "request_id": request.state.request_id,
            },
            status_code=422,
        )

    return app
