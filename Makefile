COMPOSE_DEV=infra/compose/docker-compose.dev.yml

.PHONY: up down ps logs status tools

up:
	docker compose --env-file .env -f $(COMPOSE_DEV) up -d --remove-orphans

down:
	docker compose --env-file .env -f $(COMPOSE_DEV) down

status:
	docker compose --env-file .env -f $(COMPOSE_DEV) ps

logs:
	docker compose --env-file .env -f $(COMPOSE_DEV) logs -f --tail=200

# Avvia anche i container "tooling" (adminer, ecc.)
tools:
	docker compose --env-file .env -f $(COMPOSE_DEV) --profile tools up -d

ps:
	docker compose --env-file .env -f $(COMPOSE_DEV) exec postgres sh -lc 'psql -U "$$POSTGRES_USER" -d platform_db'
