COMPOSE_DEV = infra/compose/docker-compose.dev.yml
COMPOSE = docker compose --env-file .env -f $(COMPOSE_DEV)

# service: platform | volley | football ...
SVC ?= platform

.PHONY: build up down ps logs status tools-up tools-down manage makemigrations migrate showmigrations create-vertical

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

manage:
	$(COMPOSE) exec $(SVC)-api python manage.py ${ARGS}

makemigrations:
	$(COMPOSE) exec $(SVC)-api python manage.py makemigrations

migrate:
	$(COMPOSE) exec $(SVC)-api python manage.py migrate

showmigrations:
	$(COMPOSE) exec $(SVC)-api python manage.py showmigrations

create-vertical:
	@bash server/scripts/create_vertical.sh