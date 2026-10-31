from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.dependencies import DB
from app.core.auth import (
    DUMMY_HASH,
    Authenticated,
    AuthorizedMutation,
    cookie_name,
    hash_password,
    rate_limit,
    require_origin,
    start_session,
    verify_password,
)
from app.core.errors import APIError
from app.db.models import User
from app.domain.schemas import UserProfile

router = APIRouter(prefix="/api/v1", tags=["Accounts"])


class Credentials(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: Annotated[str, Field(min_length=3, max_length=32, pattern=r"^[a-z0-9_]+$")]
    password: SecretStr = Field(min_length=15, max_length=128)

    @field_validator("username", mode="before")
    @classmethod
    def normalize_username(cls, value: object) -> object:
        return value.strip().lower() if isinstance(value, str) else value


class Registration(Credentials):
    display_name: Annotated[str, Field(min_length=1, max_length=100)]

    @field_validator("display_name", mode="before")
    @classmethod
    def clean_name(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class AccountSession(BaseModel):
    user: UserProfile
    csrf_token: str


@router.post("/auth/register", response_model=AccountSession, status_code=201)
def register(payload: Registration, request: Request, response: Response, db: DB) -> AccountSession:
    require_origin(request)
    rate_limit(request, payload.username)
    user = User(
        username=payload.username,
        display_name=payload.display_name,
        password_hash=hash_password(payload.password.get_secret_value()),
    )
    db.add(user)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise APIError(
            409,
            "USERNAME_UNAVAILABLE",
            "Choose another username or sign in to your existing account.",
        ) from None
    csrf = start_session(db, request, response, user)
    return AccountSession(user=UserProfile.model_validate(user), csrf_token=csrf)


@router.post("/auth/login", response_model=AccountSession)
def login(payload: Credentials, request: Request, response: Response, db: DB) -> AccountSession:
    require_origin(request)
    rate_limit(request, payload.username)
    user = db.scalar(select(User).where(User.username == payload.username))
    valid = verify_password(
        payload.password.get_secret_value(), user.password_hash if user else DUMMY_HASH
    )
    if not user or not valid:
        raise APIError(401, "INVALID_CREDENTIALS", "The username or password is incorrect.")
    csrf = start_session(db, request, response, user)
    return AccountSession(user=UserProfile.model_validate(user), csrf_token=csrf)


@router.get("/me", response_model=AccountSession)
def me(identity: Authenticated) -> AccountSession:
    return AccountSession(
        user=UserProfile.model_validate(identity.user), csrf_token=identity.csrf_token
    )


@router.post("/auth/logout", status_code=204)
def logout(request: Request, response: Response, db: DB, identity: AuthorizedMutation) -> None:
    identity.session.revoked_at = datetime.now(UTC)
    db.commit()
    response.delete_cookie(
        cookie_name(request.app.state.settings),
        path="/",
        secure=request.app.state.settings.app_env == "production",
        httponly=True,
        samesite="strict",
    )
