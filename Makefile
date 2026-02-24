# SportsDB Makefile
# Usage:
#   make help
#   make up            # standard stack
#   make up-dev        # dev stack (bind mounts)
#
# Notes:
# - This Makefile assumes Docker Compose V2 ("docker compose", not "docker-compose").
# - Run from repo root.

SHELL := /usr/bin/bash
.ONESHELL:
.SHELLFLAGS := -eu -o pipefail -c

COMPOSE_BASE := docker compose -f infra/docker-compose.yml
COMPOSE_DEV  := $(COMPOSE_BASE) -f infra/docker-compose.dev.yml

# Pick a default compose context for generic commands (standard by default).
COMPOSE ?= $(COMPOSE_BASE)

.PHONY: help
help: ## Show available commands
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z0-9_\-]+:.*##/ {printf "\033[36m%-18s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# --- Stack lifecycle ---------------------------------------------------------

.PHONY: up
up: ## Build (if needed) and start the standard stack in background
	$(COMPOSE_BASE) up -d --build

.PHONY: up-dev
up-dev: ## Build (if needed) and start the dev stack (bind mounts) in background
	$(COMPOSE_DEV) up -d --build

.PHONY: down
down: ## Stop and remove containers (standard stack definition)
	$(COMPOSE_BASE) down

.PHONY: down-dev
down-dev: ## Stop and remove containers (dev stack definition)
	$(COMPOSE_DEV) down

.PHONY: restart
restart: ## Restart services (standard stack)
	$(COMPOSE_BASE) restart

.PHONY: restart-dev
restart-dev: ## Restart services (dev stack)
	$(COMPOSE_DEV) restart

# --- Logs & status -----------------------------------------------------------

.PHONY: ps
ps: ## Show running containers (standard stack)
	$(COMPOSE_BASE) ps

.PHONY: ps-dev
ps-dev: ## Show running containers (dev stack)
	$(COMPOSE_DEV) ps

.PHONY: logs
logs: ## Tail logs (standard stack). Pass SERVICE=api (optional)
	if [[ -n "${SERVICE:-}" ]]; then $(COMPOSE_BASE) logs -f --tail=200 "$$SERVICE"; else $(COMPOSE_BASE) logs -f --tail=200; fi

.PHONY: logs-dev
logs-dev: ## Tail logs (dev stack). Pass SERVICE=api (optional)
	if [[ -n "${SERVICE:-}" ]]; then $(COMPOSE_DEV) logs -f --tail=200 "$$SERVICE"; else $(COMPOSE_DEV) logs -f --tail=200; fi

# --- Exec helpers ------------------------------------------------------------

.PHONY: sh-api
sh-api: ## Open a shell inside the api container (standard)
	$(COMPOSE_BASE) exec api sh

.PHONY: sh-api-dev
sh-api-dev: ## Open a shell inside the api container (dev)
	$(COMPOSE_DEV) exec api sh

.PHONY: psql
psql: ## Open psql inside db container (standard). Override DB_USER/DB_NAME if needed.
	$(COMPOSE_BASE) exec db psql -U $${DB_USER:-sportsdb} -d $${DB_NAME:-sportsdb}

.PHONY: psql-dev
psql-dev: ## Open psql inside db container (dev). Override DB_USER/DB_NAME if needed.
	$(COMPOSE_DEV) exec db psql -U $${DB_USER:-sportsdb} -d $${DB_NAME:-sportsdb}

# --- Alembic ----------------------------------------------------------------

.PHONY: alembic
alembic: ## Run an alembic command in api (standard). Example: make alembic ARGS="upgrade head"
	$(COMPOSE_BASE) exec api alembic $${ARGS:?Set ARGS, e.g. ARGS="upgrade head"}

.PHONY: alembic-dev
alembic-dev: ## Run an alembic command in api (dev). Example: make alembic-dev ARGS="revision --autogenerate -m 'msg'"
	$(COMPOSE_DEV) exec api alembic $${ARGS:?Set ARGS, e.g. ARGS="upgrade head"}

.PHONY: mig
mig: ## Create an autogenerate migration (standard). Usage: make mig MSG=add_users_table
	$(COMPOSE_BASE) exec api alembic revision --autogenerate -m $${MSG:?Set MSG, e.g. MSG=add_users_table}

.PHONY: mig-dev
mig-dev: ## Create an autogenerate migration (dev). Usage: make mig-dev MSG=add_users_table
	$(COMPOSE_DEV) exec api alembic revision --autogenerate -m $${MSG:?Set MSG, e.g. MSG=add_users_table}

.PHONY: upg-dev
upg-dev: ## Alembic upgrade head (dev)
	$(COMPOSE_DEV) exec api alembic upgrade head

# --- Quality of life ---------------------------------------------------------

.PHONY: config
config: ## Print the merged compose config (standard only)
	$(COMPOSE_BASE) config

.PHONY: config-dev
config-dev: ## Print the merged compose config (base + dev override)
	$(COMPOSE_DEV) config
