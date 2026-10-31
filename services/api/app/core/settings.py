from pathlib import Path
from typing import Literal, Self
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url

ROOT = next(
    (parent for parent in Path(__file__).resolve().parents if (parent / ".env.example").is_file()),
    Path.cwd(),
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT / ".env", extra="ignore", hide_input_in_errors=True
    )

    app_env: Literal["development", "test", "production"] = "development"
    database_url: SecretStr
    migration_database_url: SecretStr | None = None
    log_level: Literal["INFO", "WARNING", "ERROR"] = "INFO"
    ai_enabled: bool = False
    gemini_api_key: SecretStr | None = None
    gemini_model: str = Field(
        default="gemini-2.5-flash", max_length=100, pattern=r"^[a-zA-Z0-9._:/-]*$"
    )
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta"
    ai_timeout_seconds: int = Field(default=45, ge=5, le=60)
    ai_max_retries: int = Field(default=1, ge=0, le=1)
    ai_max_output_tokens: int = Field(default=6000, ge=1000, le=10000)
    ai_daily_requests: int = Field(default=20, ge=1, le=100)
    app_url: str = "http://127.0.0.1:3000"

    @model_validator(mode="after")
    def validate_origin(self) -> Self:
        url = urlsplit(self.app_url)
        if url.port is not None and not 1 <= url.port <= 65535:
            raise ValueError("APP_URL has an invalid port.")
        if (
            url.scheme not in {"http", "https"}
            or not url.hostname
            or url.username
            or url.password
            or url.path not in {"", "/"}
            or url.query
            or url.fragment
        ):
            raise ValueError("APP_URL must be the web origin.")
        if self.app_env == "production" and url.scheme != "https":
            raise ValueError("Production sessions require an HTTPS APP_URL.")
        if url.scheme == "http" and url.hostname not in {"localhost", "127.0.0.1", "[::1]", "::1"}:
            raise ValueError("HTTP sessions are permitted only for loopback development.")
        self.app_url = self.app_url.rstrip("/")
        return self

    @property
    def allowed_origins(self) -> set[str]:
        origins = {self.app_url}
        url = urlsplit(self.app_url)
        if self.app_env != "production" and url.hostname in {"localhost", "127.0.0.1"}:
            port = f":{url.port}" if url.port else ""
            origins.update({f"{url.scheme}://localhost{port}", f"{url.scheme}://127.0.0.1{port}"})
        return origins

    @model_validator(mode="after")
    def validate_ai(self) -> Self:
        url = urlsplit(self.gemini_base_url)
        if (
            url.scheme != "https"
            or not url.hostname
            or url.username
            or url.password
            or url.query
            or url.fragment
            or url.port not in (None, 443)
        ):
            raise ValueError("GEMINI_BASE_URL must be a trusted HTTPS API endpoint.")
        self.gemini_base_url = self.gemini_base_url.rstrip("/")
        if self.ai_enabled and (
            not self.gemini_api_key
            or not self.gemini_api_key.get_secret_value().strip()
            or not self.gemini_model
        ):
            raise ValueError("AI requires an API key and explicitly selected model.")
        return self

    @field_validator("database_url", "migration_database_url")
    @classmethod
    def validate_database_url(cls, value: SecretStr | None) -> SecretStr | None:
        if value is None:
            return value
        try:
            url = make_url(value.get_secret_value())
            valid = (
                url.drivername == "postgresql+psycopg"
                and url.username
                and url.password
                and url.host
                and url.database
                and (url.port is None or 1 <= url.port <= 65535)
            )
        except ValueError, TypeError:
            valid = False
        except Exception:
            valid = False
        if not valid:
            raise ValueError("Use a complete PostgreSQL psycopg connection URL.")
        return value


def load_settings() -> Settings:
    try:
        return Settings()
    except ValueError:
        raise RuntimeError(
            "Invalid configuration. Check DATABASE_URL, APP_ENV, APP_URL, "
            "LOG_LEVEL and AI_ENABLED. "
            "Check backend Gemini settings if AI is enabled. See .env.example."
        ) from None
