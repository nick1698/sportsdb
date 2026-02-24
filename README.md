# SportsDB

A monorepo for a sports platform with:

- a shared **Platform** (single account system + club registry)
- multiple **sport apps** (e.g. volleyball, football) with **separate databases per sport**

## First steps (dev)

### Requirements

- Git
- Docker + Docker Compose

## Repository layout

- `server/` backend services
- `web/` frontend app(s)
- `infra/` infrastructure (Docker, env, deploy)
- `docs/` documentation

## Run

### Docker compose

You can run the stack either with Docker Compose directly, or via the included `Makefile`.

**Standard (no bind mounts):**

```bash
docker compose -f infra/docker-compose.yml up -d --build
```

**Dev (bind mounts / live code):**

```bash
docker compose -f infra/docker-compose.yml -f infra/docker-compose.dev.yml up -d --build
```

The same `-f ...` flags apply to other commands (`logs`, `exec`, etc.).

### Makefile

```bash
make up        # standard
make up-dev    # dev (bind mounts)
make logs      # tail logs (standard)
make logs-dev  # tail logs (dev)
make sh-api-dev
make alembic-dev ARGS="upgrade head"
```
