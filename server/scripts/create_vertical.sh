#!/usr/bin/env bash
set -euo pipefail

# Interactive generator for a new vertical Django+Ninja service.
# Creates server/verticals/<key>/ with Django project + api app + Dockerfile.dev + requirements.txt

ROOT_DIR="$(git rev-parse --show-toplevel)"
VERTICALS_DIR="${ROOT_DIR}/server/verticals"
BASE_REQ="${ROOT_DIR}/server/requirements.txt"

if [[ ! -f "$BASE_REQ" ]]; then
  echo "Missing: server/requirements.txt"
  echo "Create it first with Django + django-ninja + psycopg[binary]."
  exit 1
fi

ENV_FILE="${ROOT_DIR}/.env"
INFRA_DIR="${ROOT_DIR}/infra"

echo "************ SPDB: Vertical generator ************"
echo

VERTICAL="${1:-}"

if [[ -z "$VERTICAL" ]]; then
  read -r -p "+++> Vertical key-name [a-z0-9_]: " VERTICAL
fi

if [[ -z "${VERTICAL:-}" ]]; then
  echo "Aborted: empty key"
  exit 1
fi

TARGET_DIR="${VERTICALS_DIR}/${VERTICAL}"

# check if Vertical does not exist already
if [[ -e "$TARGET_DIR" ]]; then
  echo "Error: ${TARGET_DIR} already exists."
  exit 1
fi

if [[ ! "$VERTICAL" =~ ^[a-z0-9_]+$ ]]; then
  echo "Invalid key. Use only lowercase letters, numbers, underscore."
  exit 1
fi

echo "***** SPDB: Generating ${VERTICAL}... *****"

# Constants using Vertical key
DB_NAME="${VERTICAL}_db"
SERVICE_PKG="${VERTICAL}_service"
API_APP="${VERTICAL}_api"

read -r -p "+++> Subdomain (host prefix, e.g.: ${VERTICAL}.spdb) [${VERTICAL}]: " SUBDOMAIN
SUBDOMAIN="${SUBDOMAIN:-$VERTICAL}"

SERVICE_BLOCK=$(cat <<EOF
  ${VERTICAL}-api:
    build:
      context: ../server
      dockerfile: ./verticals/${VERTICAL}/Dockerfile.dev
    container_name: spdb_api_${VERTICAL}
    restart: unless-stopped
    depends_on:
      postgres:
        condition: service_healthy
    environment:
      DJANGO_DEBUG: "1"
      DJANGO_SECRET_KEY: \${DJANGO_SECRET_KEY:-dev-insecure-secret-key}
      POSTGRES_HOST: postgres
      POSTGRES_PORT: "5432"
      POSTGRES_USER: \${POSTGRES_USER:-spdb}
      POSTGRES_PASSWORD: \${POSTGRES_PASSWORD:-spdb}
      PYTHONPATH: "/app"
    networks:
      - spdb
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.${VERTICAL}-api.rule=Host(\\\`${SUBDOMAIN}.\\\${DEV_DOMAIN}\\\`)"
      - "traefik.http.routers.${VERTICAL}-api.entrypoints=web"
      - "traefik.http.services.${VERTICAL}-api.loadbalancer.server.port=8000"
    volumes:
      - ../server/verticals/${VERTICAL}:/app/backend
      - ../server/shared:/app/shared
EOF
)

echo
echo "---- Summary ----"
echo "Vertical dir:   server/verticals/${VERTICAL}/"
echo "Django project: ${SERVICE_PKG}"
echo "Django app:     ${API_APP}"
echo "DB default:     ${DB_NAME}"
echo "Subdomain:      ${SUBDOMAIN}.\${DEV_DOMAIN}"
echo "Python image:   python:3.12-slim"
echo "-----------------"
echo

echo "==> 1) About to create vertical directory '${TARGET_DIR}'"
read -r -p "Proceed? [y/N]: " CONFIRM
if [[ "${CONFIRM:-}" != "y" && "${CONFIRM:-}" != "Y" ]]; then
  echo "Aborted."
  exit 1
fi

mkdir -p "$TARGET_DIR"
cd "$TARGET_DIR"

# --------------------------
# Creating vertical dir
# --------------------------
echo
echo "==> 2) Creating Django project: ${SERVICE_PKG}..."
django-admin startproject "$SERVICE_PKG" .

echo "==> 3) Creating Django app: ${API_APP}..."
python manage.py startapp "$API_APP"

echo "==> 4) Writing Dockerfile.dev..."
cat > Dockerfile.dev <<EOF
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates \
  && rm -rf /var/lib/apt/lists/*

COPY ./verticals/${VERTICAL} /app/backend
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

WORKDIR /app/backend
EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
EOF

echo "    ✓ Done!"
echo
read -r -p "Proceed? [Enter] "

# --------------------------
# Auto-patches (Django files)
# --------------------------
echo
echo "==> 5) Automatically update Django app..."

SETTINGS_FILE="${TARGET_DIR}/${SERVICE_PKG}/settings.py"
URLS_FILE="${TARGET_DIR}/${SERVICE_PKG}/urls.py"
TESTS_FILE="${TARGET_DIR}/${API_APP}/tests.py"
API_FILE="${TARGET_DIR}/${API_APP}/api.py"

echo "====> 5.1) Editing '${SERVICE_PKG}/settings.py'..."

# add import os if missing
if ! grep -qxF 'import os' "$SETTINGS_FILE"; then
  sed -i '/^from pathlib import Path$/a import os' "$SETTINGS_FILE"
fi

# fix ALLOWED_HOSTS
sed -i 's/^ALLOWED_HOSTS = .*/ALLOWED_HOSTS = ["*"]/' "$SETTINGS_FILE"

# add to INSTALLED_APPS before closing ]
sed -i "/^INSTALLED_APPS = \[/,/^]$/ {
  /'${API_APP//\//\\/}'/! {
    /^]$/i\    \"${API_APP}\",
  }
  /'ninja'/! {
    /^]$/i\    \"ninja\",
  }
  /'django_extensions'/! {
    /^]$/i\    \"django_extensions\",
  }
}" "$SETTINGS_FILE"

# remove from INSTALLED_APPS
sed -i "/^INSTALLED_APPS = \[/,/^]$/ {
  /django\.contrib\.admin/d
  /django\.contrib\.auth/d
  /django\.contrib\.sessions/d
  /django\.contrib\.messages/d
}" "$SETTINGS_FILE"

# remove from MIDDLEWARE
sed -i "/^MIDDLEWARE = \[/,/^]$/ {
  /django\.contrib\.auth\.middleware\.AuthenticationMiddleware/d
  /django\.contrib\.sessions\.middleware\.SessionMiddleware/d
  /django\.contrib\.messages\.middleware\.MessageMiddleware/d
  /django\.middleware\.csrf\.CsrfViewMiddleware/d
  /server\.libs\.spdb_shared\.api_contract\.request_id\.RequestIdMiddleware/d
}" "$SETTINGS_FILE"

# add to MIDDLEWARE
grep -q 'shared\.api_contract\.request_id\.RequestIdMiddleware' "$SETTINGS_FILE" || \
sed -i '/^MIDDLEWARE = \[/,/^]$/ {
  /^]$/i\    "shared.api_contract.request_id.RequestIdMiddleware",
}' "$SETTINGS_FILE"

# remove from TEMPLATES.OPTIONS.context_processors
sed -i "/'context_processors': \[/,/]/ {
  /django\.contrib\.auth\.context_processors\.auth/d
}" "$SETTINGS_FILE"

# replace whole DATABASES block
sed -i "/^DATABASES = {$/,/^}$/c\\
DATABASES = {\\
    \"default\": {\\
        \"ENGINE\": \"django.db.backends.postgresql\",\\
        \"NAME\": \"${DB_NAME}\",\\
        \"USER\": os.getenv(\"POSTGRES_USER\", \"spdb\"),\\
        \"PASSWORD\": os.getenv(\"POSTGRES_PASSWORD\", \"spdb\"),\\
        \"HOST\": os.getenv(\"POSTGRES_HOST\", \"postgres\"),\\
        \"PORT\": os.getenv(\"POSTGRES_PORT\", \"5432\"),\\
        \"CONN_MAX_AGE\": 60,\\
    }\\
}" "$SETTINGS_FILE"

# TIME_ZONE = "UTC"
sed -i "s/^TIME_ZONE = .*/TIME_ZONE = \"UTC\"/" "$SETTINGS_FILE"

# USE_TZ = True
sed -i "s/^USE_TZ = .*/USE_TZ = True/" "$SETTINGS_FILE"

# remove whole AUTH_PASSWORD_VALIDATORS block
sed -i '/^# Password validation$/,/^\]$/d' "$SETTINGS_FILE"
sed -i '/^AUTH_PASSWORD_VALIDATORS = \[$/,/^\]$/d' "$SETTINGS_FILE"

echo "      ✓ Done!"
echo "====> 5.2) Truncating '${SERVICE_PKG}/urls.py'..."

# cd "${TARGET_DIR}/${SERVICE_PKG}"

cat > "$URLS_FILE" <<EOF
from django.urls import path
from ${API_APP}.api import api

urlpatterns = [
    path("api/", api.urls),
]
EOF

echo "      ✓ Done!"
echo "====> 5.3) Deleting '${API_APP}/tests.py'..."
if [[ -f "$TESTS_FILE" ]]; then
  rm -f "$TESTS_FILE"
fi

echo "      ✓ Done!"
echo "====> 5.4) Creating '${API_APP}/api.py'..."

cat > "$API_FILE" <<EOF
from shared.api_contract.factory import build_api

api = build_api(title="SPDB ${VERTICAL} API")


@api.get("/health")
def health(request):
    return {"status": "ok", "service": "${VERTICAL}"}
EOF

echo "      ✓ Done!"
echo
read -r -p "Proceed? [Enter] "

# --------------------------
# Auto-patches (infra files)
# --------------------------
echo
echo "==> 6) Auto-patch infra files"

DB_INDEX_FILE="${INFRA_DIR}/db/verticals/_index_.sql"
DB_GEN_FILE="${INFRA_DIR}/db/verticals/${VERTICAL}.sql"

# db/verticals/_index_.sql — check existance or write the first line
echo "====> 6.1) Checking SQL index file clarity..."
if [[ ! -f "$DB_INDEX_FILE" ]] || [[ ! -s "$DB_INDEX_FILE" ]]; then
  echo "-- generated by server/scripts/create_vertical.sh - do not edit" > "$DB_INDEX_FILE"
  echo "      ✓ _index_.sql: generated bootstrap file"
else
  echo "      = _index_.sql: bootstrap file already present"

fi

# db/verticals/_index_.sql — write the db line
echo "====> 6.2) Writing on SQL index file..."
if ! grep -Eq "^\\i db\/verticals\/${VERTICAL}.sql$" "$DB_INDEX_FILE"; then
  echo "\i db/verticals/${VERTICAL}.sql" >> "$DB_INDEX_FILE"
  echo "      ✓ _index_.sql: added ${VERTICAL} to the list of dbs to bootstrap;"
else
  echo "      = _index_.sql: DB already present"
fi

# 1.3) db/verticals/[vertical].sql — generate the vertical file
echo "====> 6.3) Generating the ${DB_NAME} SQL bootstrap file..."
cat > "$DB_GEN_FILE" <<EOF
-- generated: do not edit

DO \$\$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_database WHERE datname = '${DB_NAME}') THEN
    CREATE DATABASE ${DB_NAME} OWNER spdb_bootstrap;
  END IF;
END \$\$;

\connect ${DB_NAME}
CREATE EXTENSION IF NOT EXISTS pgcrypto;

\connect postgres
GRANT CONNECT ON DATABASE ${DB_NAME} TO spdb_app;
EOF
echo "      ✓ ${VERTICAL}.sql generated"


# 2) docker-compose.dev.yml — inserisce il service block se manca
echo "====> 6.4) Updating docker compose file inserting the new ${VERTICAL} service block..."
COMPOSE_FILE="${INFRA_DIR}/docker-compose.dev.yml"
if [[ -f "$COMPOSE_FILE" ]]; then
  if grep -Eq "^\s*${VERTICAL}-api:" "$COMPOSE_FILE"; then
    echo "      = docker-compose: service ${VERTICAL}-api already present"
  else
    tmpfile="$(mktemp)"
    awk -v block="$SERVICE_BLOCK" '
      BEGIN{inserted=0}
      /^networks:/ && inserted==0 {print block; inserted=1}
      {print}
      END{
        if(inserted==0){
          print ""
          print block
        }
      }
    ' "$COMPOSE_FILE" > "$tmpfile" && mv "$tmpfile" "$COMPOSE_FILE"
    echo "      ✓ docker-compose: added service ${VERTICAL}-api"
  fi
else
  echo "      ! docker-compose: not found at ${COMPOSE_FILE} (skipped)"
fi

echo
echo "✅ Created: server/verticals/${VERTICAL}/ and patched infra files."
