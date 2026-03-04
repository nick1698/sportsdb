#!/usr/bin/env bash

init_context() {
  ROOT_DIR="$(git rev-parse --show-toplevel)"
  VERTICALS_DIR="${ROOT_DIR}/server/verticals"
  BASE_REQ="${ROOT_DIR}/server/requirements.txt"
  INFRA_DIR="${ROOT_DIR}/infra"

  [[ -d "$VERTICALS_DIR" ]] || error "Missing directory: $VERTICALS_DIR"
  [[ -d "$INFRA_DIR" ]] || error "Missing directory: $INFRA_DIR"
  [[ -f "$BASE_REQ" ]] || error "Missing file: $BASE_REQ"
}

read_context_inputs() {
  VERTICAL="${1:-}"

  if [[ -z "${VERTICAL:-}" ]]; then
    read -r -p "+++> Vertical key-name [a-z0-9_]: " VERTICAL
  fi

  validate_vertical_key "$VERTICAL"

  TARGET_DIR="${VERTICALS_DIR}/${VERTICAL}"
  [[ ! -e "$TARGET_DIR" ]] || error "Target already exists: $TARGET_DIR"

  read -r -p "+++> Subdomain (host prefix, e.g. ${VERTICAL}.spdb) [${VERTICAL}]: " SUBDOMAIN
  SUBDOMAIN="${SUBDOMAIN:-$VERTICAL}"
}

build_context() {
  DB_NAME="${VERTICAL}_db"
  SERVICE_PKG="${VERTICAL}_service"
  API_APP="${VERTICAL}_api"

  SETTINGS_FILE="${TARGET_DIR}/${SERVICE_PKG}/settings.py"
  URLS_FILE="${TARGET_DIR}/${SERVICE_PKG}/urls.py"
  TESTS_FILE="${TARGET_DIR}/${API_APP}/tests.py"
  API_FILE="${TARGET_DIR}/${API_APP}/api.py"

  DB_INDEX_FILE="${INFRA_DIR}/db/verticals/_index_.sql"
  DB_GEN_FILE="${INFRA_DIR}/db/verticals/${VERTICAL}.sql"
  COMPOSE_FILE="${INFRA_DIR}/docker-compose.dev.yml"
}

print_context_summary() {
  cat <<EOF
---- Summary ----
Vertical dir:   server/verticals/${VERTICAL}/
Django project: ${SERVICE_PKG}
Django app:     ${API_APP}
DB default:     ${DB_NAME}
Subdomain:      ${SUBDOMAIN}.\${DEV_DOMAIN}
Python image:   python:3.12-slim
-----------------
EOF
}