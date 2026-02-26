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
INITDB_FILE="${ROOT_DIR}/infra/scripts/initdb.sql"
COMPOSE_FILE="${ROOT_DIR}/infra/compose/docker-compose.dev.yml"

echo "************ SPDB: Vertical generator ************"
echo

# reading VERTICAL key from stdin
read -r -p "+++> Vertical key-name [a-z0-9_]: " VERTICAL
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

# Constants using Vertical key
DB_NAME="${VERTICAL}_db"
SERVICE_PKG="${VERTICAL}_service"
API_APP="${VERTICAL}_api"
DB_ENV="${VERTICAL^^}_DB"

read -r -p "+++> Subdomain (host prefix, e.g.: ${VERTICAL}.spdb) [${VERTICAL}]: " SUBDOMAIN
SUBDOMAIN="${SUBDOMAIN:-$VERTICAL}"

SERVICE_BLOCK=$(cat <<EOF
  ${VERTICAL}-api:
    build:
      context: ../../server
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
      ${DB_ENV}: \${${DB_ENV}:-${DB_NAME}}
    networks:
      - spdb
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.${VERTICAL}-api.rule=Host(\\\`${SUBDOMAIN}.\\\${DEV_DOMAIN}\\\`)"
      - "traefik.http.routers.${VERTICAL}-api.entrypoints=web"
      - "traefik.http.services.${VERTICAL}-api.loadbalancer.server.port=8000"
    volumes:
      - ../../server/verticals/${VERTICAL}:/app
EOF
)

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

echo "==> Creating directory '${TARGET_DIR}'..."
read -r -p "+++> Proceed? [y/N]: " CONFIRM
if [[ "${CONFIRM:-}" != "y" && "${CONFIRM:-}" != "Y" ]]; then
  echo "Aborted."
  exit 1
fi

mkdir -p "$TARGET_DIR"
cd "$TARGET_DIR"

echo
echo "==> Creating Django project: ${SERVICE_PKG}..."
django-admin startproject "$SERVICE_PKG" .

echo "==> Creating Django app: ${API_APP}..."
python manage.py startapp "$API_APP"

echo "==> Writing Dockerfile.dev..."
cat > Dockerfile.dev <<EOF
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates \
  && rm -rf /var/lib/apt/lists/*

COPY ./verticals/${VERTICAL} /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
EOF

echo "==> Deleting ${API_APP}/tests.py..."
FILE="${VERTICALS_DIR}/${VERTICAL}/${API_APP}/tests.py"
if [[ -f "$FILE" ]]; then
  rm -f "$FILE"
fi

VERTICAL_DJ="server/verticals/${VERTICAL}"
SETTINGS_FILE="${VERTICAL_DJ}/${SERVICE_PKG}/settings.py"
URLS_FILE="${VERTICAL_DJ}/${SERVICE_PKG}/urls.py"
API_FILE="${VERTICAL_DJ}/${API_APP}/urls.py"

echo
echo "+++> Manual steps <+++"
echo

read -r -p "STEP 0: Is the variable '${DB_ENV}' present in the '.env' file? [y/N]: " CONFIRM
if [[ "${CONFIRM:-}" != "y" && "${CONFIRM:-}" != "Y" ]]; then
  echo "Aborted."
  exit 0
fi

cat <<EOF

##### STEP 1: edit '${SETTINGS_FILE}' #####

· add among imports:
import os

· fix this:
ALLOWED_HOSTS = ["*"]

· add to INSTALLED_APPS:
    "ninja",
    "${API_APP}",

· override:
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

· check:
TIME_ZONE = "UTC"
USE_TZ = True


· remove:
from INSTALLED_APPS:
-    'django.contrib.admin',
-    'django.contrib.auth',
-    'django.contrib.sessions',
-    'django.contrib.messages',
from MIDDLEWARE
-    'django.contrib.auth.middleware.AuthenticationMiddleware',
-    'django.contrib.sessions.middleware.SessionMiddleware',
-    'django.contrib.messages.middleware.MessageMiddleware',
-    'django.middleware.csrf.CsrfViewMiddleware',
from TEMPLATES.OPTIONS.context_processors:
-    'django.contrib.auth.context_processors.auth'
the whole AUTH_PASSWORD_VALIDATORS


EOF

read -r -p "Move on to step 2? [click Enter] "

cat <<EOF


##### STEP 2: create '${API_FILE}' with content: [copy] #####


from ninja import NinjaAPI

api = NinjaAPI(title="SPDB ${VERTICAL} API")


@api.get("/health")
def health(request):
    return {"status": "ok", "service": "${VERTICAL}"}


EOF

read -r -p "Move on to step 3? [click Enter] "

cat <<EOF

##### STEP 3: replace the whole content of '${URLS_FILE}' with: [copy] #####

from django.urls import path
from ${API_APP}.api import api

urlpatterns = [
    path("api/", api.urls),
]

EOF

read -r -p "Manual patches done! Move on to infra files auto-patching: [click Enter] "

# --------------------------
# Auto-patches (infra files)
# --------------------------
echo
echo "==> Auto-patching infra files"

# 1) initdb.sql — aggiunge CREATE DATABASE se manca
if [[ -f "$INITDB_FILE" ]]; then
  if ! grep -Eq "^\s*CREATE\s+DATABASE\s+${DB_NAME}\s*;" "$INITDB_FILE"; then
    {
      echo ""
      echo "-- added by create_vertical.sh (${VERTICAL})"
      echo "CREATE DATABASE ${DB_NAME};"
    } >> "$INITDB_FILE"
    echo "   ✓ initdb.sql: added CREATE DATABASE ${DB_NAME};"
  else
    echo "   = initdb.sql: DB already present"
  fi
else
  echo "   ! initdb.sql not found at: ${INITDB_FILE} (skipped)"
fi

# 2) .env — aggiunge o aggiorna <VERTICAL>_DB=<db>
if [[ -f "$ENV_FILE" ]]; then
  if grep -Eq "^${DB_ENV}=" "$ENV_FILE"; then
    sed -i "s|^${DB_ENV}=.*|${DB_ENV}=${DB_NAME}|" "$ENV_FILE"
    echo "   ✓ .env: updated ${DB_ENV}=${DB_NAME}"
  else
    echo "${DB_ENV}=${DB_NAME}" >> "$ENV_FILE"
    echo "   ✓ .env: appended ${DB_ENV}=${DB_NAME}"
  fi
else
  echo "   ! .env not found at: ${ENV_FILE} (skipped)"
fi

# 3) docker-compose.dev.yml — inserisce il service block se manca
if [[ -f "$COMPOSE_FILE" ]]; then
  if grep -Eq "^\s*${VERTICAL}-api:" "$COMPOSE_FILE"; then
    echo "   = compose: service ${VERTICAL}-api already present"
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
    echo "   ✓ compose: added service ${VERTICAL}-api"
  fi
else
  echo "   ! compose not found at: ${COMPOSE_FILE} (skipped)"
fi

echo
echo "✅ Created: server/verticals/${VERTICAL}/ and patched infra files."
