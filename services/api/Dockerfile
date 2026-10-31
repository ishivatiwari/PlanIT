FROM python:3.14.4-slim-bookworm AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY services/api/requirements.lock ./requirements.lock
RUN python -m pip install --require-hashes -r requirements.lock
RUN groupadd --gid 10001 eventora && useradd --uid 10001 --gid eventora --create-home eventora
COPY services/api/app ./app
COPY services/api/migrations ./migrations
COPY services/api/alembic.ini ./alembic.ini
USER 10001:10001
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--no-access-log", "--no-proxy-headers"]
