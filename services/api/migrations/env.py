from alembic import context
from sqlalchemy import create_engine, pool

from app.core.settings import load_settings
from app.db.models import Base

settings = load_settings()
url = settings.migration_database_url or settings.database_url

if context.is_offline_mode():
    context.configure(url=url.get_secret_value(), literal_binds=True, target_metadata=Base.metadata)
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = create_engine(url.get_secret_value(), poolclass=pool.NullPool, hide_parameters=True)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=Base.metadata)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()
