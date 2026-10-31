from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from app.core.settings import Settings

EXPECTED_REVISION = "0006_replanning"


class Database:
    def __init__(self, settings: Settings) -> None:
        self.engine = create_engine(
            settings.database_url.get_secret_value(),
            pool_size=3,
            max_overflow=2,
            pool_timeout=2,
            pool_pre_ping=True,
            hide_parameters=True,
            connect_args={"connect_timeout": 3, "options": "-c statement_timeout=5000"},
        )

    def ready(self) -> bool:
        try:
            with self.engine.connect() as connection:
                connection.execute(text("SET LOCAL statement_timeout = 1000"))
                connection.execute(text("SELECT 1"))
                revision: object = connection.execute(
                    text("SELECT version_num FROM alembic_version")
                ).scalar_one()
                return bool(revision == EXPECTED_REVISION)
        except SQLAlchemyError:
            return False

    def close(self) -> None:
        self.engine.dispose()
