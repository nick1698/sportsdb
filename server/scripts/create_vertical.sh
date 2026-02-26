#!/usr/bin/env bash
set -euo pipefail

# Interactive generator for a new vertical Django+Ninja service.
# - Creates server/verticals/<key>/ with Django project + api app + Dockerfile.dev + requirements.txt
# - DOES NOT edit compose/.env/sql/yaml automatically: prints what to change.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VERTICALS_DIR="${ROOT_DIR}/server/verticals"
BASE_REQ="${ROOT_DIR}/server/requirements.base.txt"

if [[ ! -f "$BASE_REQ" ]]; then
  echo "Missing: server/requirements.base.txt"
  echo "Create it first with Django + django-ninja + psycopg[binary]."
  exit 1
fi

echo "== SPDB: New Vertical Generator =="
echo

read -r -p "Vertical key (e.g. football) [a-z0-9_]: " VERTICAL
if [[ -z "${VERTICAL:-}" ]]; then
  echo "Aborted: empty key"
  exit 1
fi
if [[ ! "$VERTICAL" =~ ^[a-z0-9_]+$ ]]; then
  echo "Invalid key. Use only lowercase letters, numbers, underscore."
  exit 1
fi

DEFAULT_DB="${VERTICAL}_db"
DEFAULT_SUB="${VERTICAL}"

read -r -p "DB name [${DEFAULT_DB}]: " DB_NAME
DB_NAME="${DB_NAME:-$DEFAULT_DB}"

read -r -p "Subdomain (host prefix) [${DEFAULT_SUB}]: " SUBDOMAIN
SUBDOMAIN="${SUBDOMAIN:-$DEFAULT_SUB}"

SERVICE_PKG="${VERTICAL}_service"
API_APP="${VERTICAL}_api"
DB_ENV="${VERTICAL^^}_DB"

TARGET_DIR="${VERTICALS_DIR}/${VERTICAL}"

echo
echo "---- Summary ----"
echo "Vertical dir:   server/verticals/${VERTICAL}/"
echo "Django project: ${SERVICE_PKG}"
echo "Django app:     ${API_APP}"
echo "DB env var:     ${DB_ENV}"
echo "DB default:     ${DB_NAME}"
echo "Subdomain:      ${SUBDOMAIN}.\${DEV_DOMAIN}"
echo "Python image:   python:3.12-slim"
echo "-----------------"
echo

read -r -p "Proceed? [y/N]: " CONFIRM
if [[ "${CONFIRM:-}" != "y" && "${CONFIRM:-}" != "Y" ]]; then
  echo "Aborted."
  exit 0
fi

if [[ -e "$TARGET_DIR" ]]; then
  echo "Error: ${TARGET_DIR} already exists."
  exit 1
fi

mkdir -p "$TARGET_DIR"
cd "$TARGET_DIR"

echo
echo "==> Creating Django project: ${SERVICE_PKG}"
django-admin startproject "$SERVICE_PKG" .

echo "==> Creating Django app: ${API_APP}"
python manage.py startapp "$API_APP"

echo "==> Writing requirements.txt (includes base)"
cat > requirements.txt <<EOF
-r ../../requirements.base.txt
EOF

echo "==> Writing Dockerfile.dev"
cat > Dockerfile.dev <<'EOF'
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
EOF

echo "==> Patching settings.py (append SPDB block: UTC + env DB + ninja app)"
SETTINGS_FILE="${TARGET_DIR}/${SERVICE_PKG}/settings.py"
cat >> "$SETTINGS_FILE" <<EOF

# --- SPDB additions (generated) ---
import os

TIME_ZONE = "UTC"
USE_TZ = True

INSTALLED_APPS += [
    "ninja",
    "${API_APP}",
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("${DB_ENV}", "${DB_NAME}"),
        "USER": os.getenv("POSTGRES_USER", "spdb"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD", "spdb"),
        "HOST": os.getenv("POSTGRES_HOST", "postgres"),
        "PORT": os.getenv("POSTGRES_PORT", "5432"),
        "CONN_MAX_AGE": 60,
    }
}
EOF

echo "==> Replacing urls.py to mount Ninja at /api/"
URLS_FILE="${TARGET_DIR}/${SERVICE_PKG}/urls.py"
cat > "$URLS_FILE" <<EOF
from django.contrib import admin
from django.urls import path
from ${API_APP}.api import api

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", api.urls),
]
EOF

echo "==> Creating Ninja api.py with /health"
cat > "${TARGET_DIR}/${API_APP}/api.py" <<EOF
from ninja import NinjaAPI

api = NinjaAPI(title="SPDB ${VERTICAL} API")

@api.get("/health")
def health(request):
    return {"status": "ok", "service": "${VERTICAL}"}
EOF

echo
echo "✅ Created: server/verticals/${VERTICAL}/"
echo
echo "Now apply these MANUAL changes (copy/paste):"
echo
echo "1) infra/scripts/initdb.sql  (dev only; only needed if you want a new DB):"
echo "   CREATE DATABASE ${DB_NAME};"
echo
echo "2) .env"
echo "   ${DB_ENV}=${DB_NAME}"
echo
echo "3) infra/compose/docker-compose.dev.yml  (new service block):"
cat <<EOF
  ${VERTICAL}-api:
    build:
      context: ../../server/verticals/${VERTICAL}
      dockerfile: Dockerfile.dev
    container_name: spdb_${VERTICAL}_api
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
      ${DB_ENV}: \${${DB_ENV}:-${DB_NAME}}
    networks:
      - spdb
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.${VERTICAL}-api.rule=Host(\`${SUBDOMAIN}.\${DEV_DOMAIN}\`)"
      - "traefik.http.routers.${VERTICAL}-api.entrypoints=web"
      - "traefik.http.services.${VERTICAL}-api.loadbalancer.server.port=8000"
EOF