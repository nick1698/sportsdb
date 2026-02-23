# infra

Infrastructure and deployment files (docker-compose, env examples, etc.).

## Development DB

### Start

```bash
cp .env.example .env
docker compose --env-file .env up -d
```

### Stop

```bash
docker compose down
```
