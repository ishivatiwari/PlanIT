"""Local credentials and revocable opaque sessions; no identity supplied by clients."""

import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import Depends, Request, Response
from sqlalchemy import delete, text, update
from sqlalchemy.orm import Session as DBSession

from app.api.dependencies import DB
from app.core.errors import APIError
from app.core.settings import Settings
from app.db.models import Session, User

SCRYPT_N, SCRYPT_R, SCRYPT_P = 32768, 8, 3


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    result = hashlib.scrypt(
        password.encode(),
        salt=salt,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
        maxmem=64 * 1024 * 1024,
        dklen=32,
    )
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${salt.hex()}${result.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, n, r, p, salt, expected = encoded.split("$")
        if (algorithm, int(n), int(r), int(p)) != ("scrypt", SCRYPT_N, SCRYPT_R, SCRYPT_P):
            return False
        actual = hashlib.scrypt(
            password.encode(),
            salt=bytes.fromhex(salt),
            n=SCRYPT_N,
            r=SCRYPT_R,
            p=SCRYPT_P,
            maxmem=64 * 1024 * 1024,
            dklen=32,
        )
        return secrets.compare_digest(actual.hex(), expected)
    except ValueError, TypeError:
        return False


DUMMY_HASH = hash_password("unused timing equalization password")


def cookie_name(settings: Settings) -> str:
    return "__Host-eventora_session" if settings.app_env == "production" else "eventora_session"


def require_origin(request: Request) -> None:
    settings: Settings = request.app.state.settings
    if request.headers.get("origin") not in settings.allowed_origins:
        raise APIError(
            403,
            "ORIGIN_REJECTED",
            "Open this page from the configured PlanIT address and try again.",
        )
    if request.headers.get("x-requested-with") != "Eventora":
        raise APIError(403, "CSRF_REJECTED", "Refresh the page and try again.")


def rate_limit(request: Request, username: str) -> None:
    now = datetime.now(UTC)
    peer = request.client.host if request.client else "unknown"
    for label, maximum in ((f"account:{username}", 10), (f"peer:{peer}", 120)):
        # Separate committed transaction: failed credentials must still count.
        with request.app.state.database.engine.begin() as connection:
            connection.execute(
                text("DELETE FROM auth_limits WHERE window_start < :cutoff"),
                {"cutoff": now - timedelta(days=1)},
            )
            count = connection.execute(
                text("""
                INSERT INTO auth_limits (key, window_start, attempts) VALUES (:key, :now, 1)
                ON CONFLICT (key) DO UPDATE SET
                  attempts = CASE WHEN auth_limits.window_start < :cutoff
                    THEN 1 ELSE auth_limits.attempts + 1 END,
                  window_start = CASE WHEN auth_limits.window_start < :cutoff
                    THEN :now ELSE auth_limits.window_start END
                RETURNING attempts
            """),
                {"key": digest(label), "now": now, "cutoff": now - timedelta(minutes=15)},
            ).scalar_one()
        if count > maximum:
            raise APIError(
                429, "TOO_MANY_ATTEMPTS", "Too many sign-in attempts. Try again in 15 minutes."
            )


@dataclass
class Identity:
    user: User
    session: Session
    csrf_token: str


def current_identity(request: Request, db: DB) -> Identity:
    settings: Settings = request.app.state.settings
    token = request.cookies.get(cookie_name(settings), "")
    if not 40 <= len(token) <= 64:
        raise APIError(401, "AUTHENTICATION_REQUIRED", "Sign in to manage your events.")
    session = db.get(Session, digest(token))
    if session is None or session.revoked_at is not None or session.expires_at <= datetime.now(UTC):
        raise APIError(401, "AUTHENTICATION_REQUIRED", "Your session has ended. Sign in again.")
    user = db.get(User, session.user_id)
    if user is None:
        raise APIError(401, "AUTHENTICATION_REQUIRED", "Sign in to manage your events.")
    return Identity(user, session, digest("eventora-csrf:" + token))


Authenticated = Annotated[Identity, Depends(current_identity)]


def mutation_identity(request: Request, identity: Authenticated) -> Identity:
    require_origin(request)
    supplied = request.headers.get("x-csrf-token", "")
    if not supplied.isascii() or not secrets.compare_digest(supplied, identity.csrf_token):
        raise APIError(403, "CSRF_REJECTED", "Refresh the page and try again.")
    return identity


AuthorizedMutation = Annotated[Identity, Depends(mutation_identity)]


def start_session(db: DBSession, request: Request, response: Response, user: User) -> str:
    settings: Settings = request.app.state.settings
    now = datetime.now(UTC)
    old = request.cookies.get(cookie_name(settings))
    if old:
        db.execute(update(Session).where(Session.token_hash == digest(old)).values(revoked_at=now))
    db.execute(delete(Session).where(Session.expires_at < now - timedelta(days=1)))
    token = secrets.token_urlsafe(32)
    db.add(Session(token_hash=digest(token), user_id=user.id, expires_at=now + timedelta(hours=8)))
    db.commit()
    response.set_cookie(
        cookie_name(settings),
        token,
        max_age=8 * 3600,
        httponly=True,
        secure=settings.app_env == "production",
        samesite="strict",
        path="/",
    )
    return digest("eventora-csrf:" + token)
