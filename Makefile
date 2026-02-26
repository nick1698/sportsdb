COMPOSE_DEV = infra/compose/docker-compose.dev.yml
COMPOSE = docker compose --env-file .env -f $(COMPOSE_DEV)

# service: platform | volley | football ...
SVC ?= platform

.PHONY: build up down ps logs status tools-up tools-down manage makemigrations migrate showmigrations create-vertical reset-db

build:
	${COMPOSE} up -d --build

up:
	${COMPOSE} up -d --remove-orphans

down:
	${COMPOSE} down

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

# e.g.: mk manage SVC=[platform] ARGS="..."
manage:
	$(COMPOSE) exec $(SVC)-api python manage.py ${ARGS}

# e.g.: mk makemigrations SVC=[platform]
makemigrations:
	$(COMPOSE) exec $(SVC)-api python manage.py makemigrations

# e.g.: mk migrate SVC=[platform]
migrate:
	$(COMPOSE) exec $(SVC)-api python manage.py migrate

# e.g.: mk showmigrations SVC=[platform]
showmigrations:
	$(COMPOSE) exec $(SVC)-api python manage.py showmigrations

create-vertical:
	@bash server/scripts/create_vertical.sh

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