# infra

Infrastructure and deployment files (docker-compose, env examples, etc.).

## Development DB

### Start

This will start Postgres and the API at `http://localhost:8000`

```bash
cp .env.example .env
docker compose --env-file .env up -d
```

### Stop

```bash
docker compose down
```
