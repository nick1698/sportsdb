COMPOSE_DEV = infra/docker-compose.dev.yml
COMPOSE = docker compose --env-file .env -f $(COMPOSE_DEV)

# service: platform | volley | football ...
SVC ?= platform

.PHONY: help build up down down-v ps logs status tools-up tools-down enter manage makemigrations migrate showmigrations test create-vertical reset-db

help:
	@echo "Available commands:"
	@echo "  mk help              - List all available commands"
	@echo "  mk build             - Start the containers and rebuild images"
	@echo "  mk up                - Start the containers"
	@echo "  mk down              - Stop and remove the containers"
	@echo "  mk down-v            - Stop and remove containers and DB volume"
	@echo "  mk status            - Show container status"
	@echo "  mk logs              - Show container logs"
	@echo "  mk tools-up          - Start tooling containers"
	@echo "  mk tools-down        - Stop tooling containers"
	@echo "  mk ps                - Open psql on the SVC database"
	@echo "  mk enter SVC=...     - Enter the service API container"
	@echo '  mk manage SVC=... ARGS="..." - Run manage.py'
	@echo "  mk makemigrations    - Run makemigrations"
	@echo "  mk migrate           - Run migrate"
	@echo "  mk showmigrations    - Show migrations"
	@echo "  mk create-vertical   - Create a new vertical"
	@echo "  mk reset-db SVC=...  - Fully reset the service database"

build:
	${COMPOSE} up -d --build ${ARGS}

up:
	${COMPOSE} up -d --remove-orphans

down:
	${COMPOSE} down

down-v:
	${COMPOSE} down -v
	docker volume rm -f spdb_postgres_data || true

status:
	${COMPOSE} ps

logs:
	${COMPOSE} logs -f --tail=200

# Avvia anche i container "tooling" (adminer, ecc.)
tools-up:
	${COMPOSE} --profile tools up -d

tools-down:
	${COMPOSE} stop adminer

ps:
	${COMPOSE} exec postgres sh -lc 'psql -U "$$POSTGRES_USER" -d $(SVC)_db'

# e.g.: mk enter SVC=[platform]
enter:
	$(COMPOSE) exec $(SVC)-api bash

# e.g.: mk manage SVC=[platform] ARGS="..."
manage:
	$(COMPOSE) exec $(SVC)-api python manage.py ${ARGS}

# e.g.: mk makemigrations SVC=[platform] {NAME=[test_migration] EMPTY=[1]}
makemigrations:
	$(COMPOSE) exec $(SVC)-api python manage.py makemigrations $(SVC)_api $(if $(NAME),--name $(NAME)) $(if $(EMPTY),--empty) ${ARGS}

# e.g.: mk migrate SVC=[platform] {TARGET=[0xxx]}
migrate:
	$(COMPOSE) exec $(SVC)-api python manage.py migrate $(SVC)_api $(TARGET) ${ARGS}

# e.g.: mk showmigrations SVC=[platform]
showmigrations:
	$(COMPOSE) exec $(SVC)-api python manage.py showmigrations ${ARGS}

# e.g.: mk test SVC=[platform]
test:
	$(COMPOSE) exec $(SVC)-api python manage.py test --shuffle --failfast ${ARGS}

# e.g.: mk create-vertical SVC=[new_vertical]
create-vertical:
	@server/scripts/bin/create-vertical $(SVC)

# e.g.: mk reset-db SVC=[platform]
reset-db:
	@set -e; \
	DB="$(SVC)_db"; \
	echo "🔥 Reset database $$DB (service: $(SVC)-api)"; \
	$(COMPOSE) stop $(SVC)-api; \
	$(COMPOSE) exec postgres sh -lc 'psql -U "$$POSTGRES_USER" -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='\'''"$$DB"''\'' AND pid <> pg_backend_pid();"' ; \
	$(COMPOSE) exec postgres sh -lc 'psql -U "$$POSTGRES_USER" -d postgres -c "DROP DATABASE IF EXISTS \"'"$$DB"'\";"' ; \
	$(COMPOSE) exec postgres sh -lc 'psql -U "$$POSTGRES_USER" -d postgres -c "CREATE DATABASE \"'"$$DB"'\" OWNER \"$$POSTGRES_USER\";"' ; \
	$(COMPOSE) up -d $(SVC)-api; \
	$(COMPOSE) exec $(SVC)-api python manage.py migrate
