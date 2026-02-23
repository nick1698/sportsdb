# server

FastAPI backend for the SportsDB monorepo.

## Local development (recommended)

### Requirements

- Python 3.12+
- (Optional but recommended) a virtual environment tool: `venv`, `uv`, or `poetry`

### Setup with `venv` + `requirements.txt`

From the repo root:

```bash
cd server
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

API:

- Health: `GET http://127.0.0.1:8000/health`

## Run via Docker Compose

From `infra/`:

```bash
docker compose up -d --build
```

API:

- Health: `GET http://localhost:8000/health`

## Configuration (env vars)

The server reads configuration from environment variables:

- `LOG_LEVEL` (default: `INFO`)
- `DATABASE_URL` (optional for now; used later for DB integration)

When running via Docker Compose, `DATABASE_URL` is provided by `infra/docker-compose.yml`.

### Example (local)

```bash
export LOG_LEVEL=DEBUG
export DATABASE_URL="postgresql+psycopg://user:pass@localhost:5432/sportsdb"
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## Notes

- Keep environment-specific values out of the repo. Use env files (e.g. `infra/.env`) or Compose env vars.
- Do not commit virtual environments (e.g. `.venv/`).
