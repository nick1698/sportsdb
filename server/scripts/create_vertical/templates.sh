#!/usr/bin/env bash

render_dockerfile_dev() {
  cat <<EOF
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \\
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates \\
  && rm -rf /var/lib/apt/lists/*

COPY ./verticals/${VERTICAL} /app/backend
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

WORKDIR /app/backend
EXPOSE 8000
CMD ["python", "manage.py", "runserver_plus", "0.0.0.0:8000"]
EOF
}

render_urls_py() {
  cat <<EOF
from django.urls import path
from ${API_APP}.api import api

urlpatterns = [
    path("api/", api.urls),
]
EOF
}

render_api_py() {
  cat <<EOF
from shared.api_contract.factory import build_api

api = build_api(title="SPDB ${VERTICAL} API")


@api.get("/health")
def health(request):
    return {"status": "ok", "service": "${VERTICAL}"}
EOF
}

render_service_block() {
  cat <<EOF
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
      - ../server/shared:/app/shared:z
EOF
}

render_vertical_sql() {
  cat <<EOF
-- generated: do not edit

SELECT 'CREATE DATABASE ${DB_NAME} OWNER spdb_bootstrap'
WHERE NOT EXISTS (
  SELECT FROM pg_database WHERE datname = '${DB_NAME}'
)\\gexec

\\connect ${DB_NAME}
CREATE EXTENSION IF NOT EXISTS pgcrypto;

\\connect postgres
GRANT CONNECT ON DATABASE ${DB_NAME} TO spdb_app;
EOF
}