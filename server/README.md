# server

FastAPI backend for the SportsDB monorepo.

## Local development (recommended)

### Requirements

- Python 3.12.12
- (Optional but recommended) a virtual environment tool

### Setup with `pyenv` + `requirements.txt`

```bash
# inside the /server directory
pyenv install 3.12.12
pyenv virtualenv 3.12.12 [venv name]
pip install -r requirements.txt
# this will be launched as a docker compose cmd
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### API - Local

- Health: `GET http://127.0.0.1:8000/health`
- DB check: `GET http://127.0.0.1:8000/db-check`

## Run via Docker Compose

```bash
# inside the /infra directory
docker compose up -d --build
```

### API - Docker

- Health: `GET http://localhost:8000/health`
- DB check: `GET http://localhost:8000/db-check`

## Configuration: environment variables

The server reads configuration from env vars:

- `DATABASE_URL` (required for DB features)
- `LOG_LEVEL` (default: `INFO`)

When running via Docker Compose, `DATABASE_URL` is provided by `infra/docker-compose.yml`.

### Example (local)

```bash
export LOG_LEVEL=DEBUG
export DATABASE_URL="postgresql+psycopg://[user]:[pw]@127.0.0.1:5432/sportsdb"
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## Notes

- Keep environment-specific values out of the repo. Use env files (e.g. `infra/.env`) or Compose env vars.
- Do not commit virtual environments (e.g. `.venv/`).
