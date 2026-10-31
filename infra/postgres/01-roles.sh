#!/bin/bash
set -euo pipefail
psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" --set=ON_ERROR_STOP=1 \
  --set=app_password="$APP_DB_PASSWORD" --set=migration_password="$MIGRATION_DB_PASSWORD" <<'SQL'
CREATE ROLE eventora_app LOGIN PASSWORD :'app_password' NOSUPERUSER NOCREATEDB NOCREATEROLE;
CREATE ROLE eventora_migrator LOGIN PASSWORD :'migration_password' NOSUPERUSER NOCREATEDB NOCREATEROLE;
ALTER SCHEMA public OWNER TO eventora_migrator;
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO eventora_app;
ALTER DEFAULT PRIVILEGES FOR ROLE eventora_migrator IN SCHEMA public GRANT SELECT ON TABLES TO eventora_app;
SQL
