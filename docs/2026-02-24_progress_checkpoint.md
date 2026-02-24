# SportsDB — 2026-02-24 checkpoint

Questo documento descrive **com’è strutturato il repo oggi** e **come si usa** (dev/prod, migrazioni, entrypoint)

## 1. Situazione Git

Branch: `main`  
Ultimi commit rilevanti:

- `30630e0` — comandi Alembic nel Makefile
- `e8769de` — prima tabella `app_variable` nel DB
- `0d1b712` — compose dev override + Makefile
- `13798f8` — wire Alembic metadata + models package

## 2. Struttura del repository (monorepo)

- `infra/` — Docker Compose + env
- `server/` — FastAPI + SQLAlchemy + Alembic + Dockerfile
- `web/` — placeholder/documentazione (solo README per ora)
- `docs/` — documentazione di supporto
- `Makefile` — comandi operativi
- `README.md` — readme root

### Dettagli principali

#### `infra/`

- `docker-compose.yml` (base)
- `docker-compose.dev.yml` (override dev: bind mount)
- `.env` e `.env.example`
- `README.md` (documentazione infra)

Servizi:

- `db`: Postgres 16-alpine, volume `db_data`, healthcheck `pg_isready`
- `api`: build da `server/Dockerfile`, porta `8000`, dipende da `db`

#### `server/`

- `Dockerfile` + `requirements.txt`
- `app/`
  - `main.py` (entrypoint FastAPI)
  - `settings.py` (config; usa `DATABASE_URL` da env)
  - `db.py` (layer DB)
  - `logging_config.py`
  - `models/`
    - `base.py` (SQLAlchemy Declarative Base)
    - `__init__.py` (export/import dei modelli)
- `alembic.ini`
- `migrations/` (Alembic)
  - `env.py` (config + target_metadata)
  - `versions/` (revision scripts)

## 3. Esecuzione: standard vs dev

### 3.1 Standard (senza bind mount)

Usare solo `infra/docker-compose.yml`:

```bash
docker compose -f infra/docker-compose.yml up -d --build
```

Caratteristiche:

- il container `api` usa il codice “copiato/buildato” in immagine;
- ogni modifica al codice richiede rebuild/restart (o almeno rebuild).

### 3.2 Dev (con bind mount)

Usare base + override `infra/docker-compose.dev.yml`:

```bash
docker compose -f infra/docker-compose.yml -f infra/docker-compose.dev.yml up -d --build
```

Caratteristiche:

- bind mount: `server/` → `/app` nel container `api`
- modifiche al codice riflettono immediatamente la sorgente montata (utile per iterare velocemente)

## 4. Database & migrazioni (Alembic)

### 4.1 Migrations presenti

In `server/migrations/versions/` risultano:

- `e7eea473be7b_baseline.py` — baseline
- `23c1ffc409ae_smoke_autogen.py` — smoke test autogenerate

### 4.2 Alembic autogenerate “sbloccato”

`server/migrations/env.py` è configurato per usare `target_metadata` dal modello SQLAlchemy (`Base.metadata`), quindi:

- aggiungi/aggiorni modelli in `server/app/models/`
- generi revision con `--autogenerate`
- applichi con `upgrade head`

## 5. Makefile: comandi operativi

Il repo include un `Makefile` usato per:

- avvio stack standard/dev
- logs e shell nel container
- accesso a psql nel container DB
- comandi Alembic (e shortcut per creare migrations in dev)

Obiettivo: evitare di ricordare ogni volta i flag `-f ...` di compose e standardizzare il workflow.

## 6. Stato “funzionale” attuale

Quello che risulta “già funzionante”:

- stack `db` + `api` avviabili via Docker Compose
- `DATABASE_URL` configurata via environment in compose
- Alembic migrations presenti e pipeline autogenerate verificata (smoke test)
- modello base SQLAlchemy presente e package `models` esistente
