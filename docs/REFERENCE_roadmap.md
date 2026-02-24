# Roadmap operativa: Platform → Sport 1 → Sport 2 → Templating → Nuovi sport

Questo documento è una checklist operativa per costruire:

1. Platform (account unico + registry)
2. Sport 1 end-to-end (es. Volleyball)
3. Sport 2 (es. Football) replicando il modello
4. Templating + runbook per rendere “aggiungi sport” una procedura

---

## Fase 0 — Preparazione repository (monorepo)

### 0.1 Struttura iniziale

- Crea lo scheletro monorepo:
  - `server/packages/core`
  - `server/packages/platform_app`
  - `server/packages/sports/volleyball`
  - `client/packages/ui`
  - `client/packages/api-client`
  - `client/apps/platform`
  - `client/apps/volleyball`
  - `infra/nginx`
- Inserisci `README.md`, `docs/architecture.md`, `.env.example`

### 0.2 Standard tecnici (subito)

- Backend:
  - lint/format (ruff)
  - logging su file + rotazione (core)
  - error model coerente (Problem Details o simile)
- Frontend:
  - workspace (pnpm consigliato)
  - eslint + prettier + tsconfig base
  - TanStack Query + React Hook Form + Zod
- Convenzioni:
  - namespace API: `/api/platform/*`, `/api/volleyball/*`, `/api/football/*`
  - env vars: `PLATFORM_DATABASE_URL`, `VOLLEYBALL_DATABASE_URL`, `FOOTBALL_DATABASE_URL`, ecc.

Deliverable: repo avviabile con servizi “vuoti” + reverse proxy funzionante.

---

## Fase 1 — Platform (fondamenta comuni)

Obiettivo: account unico + preferenze sport + registry società per cross-link.

### 1.1 Platform DB schema (platform_db)

Migrazioni Alembic per:

- `users`
- `refresh_tokens` / `sessions` (a scelta)
- `user_sport_preferences`
- `org_registry`
- `org_sport_presence`

Note:

- `org_sport_presence` contiene `sport_key` + `sport_ref` (slug o id locale sport).
- Matching **manuale**.

### 1.2 Platform API

Endpoint minimi:

- Auth:
  - `POST /api/platform/auth/register`
  - `POST /api/platform/auth/login`
  - `POST /api/platform/auth/refresh`
- Preferenze:
  - `GET/PUT /api/platform/preferences/sports`
- Registry:
  - `GET /api/platform/orgs/{slug|id}` (include presence)
  - Admin:
    - `POST /api/platform/orgs`
    - `PUT /api/platform/orgs/{id}`
    - `PUT /api/platform/orgs/{id}/presence/{sport_key}`

### 1.3 Token strategy per sport apps

- JWT firmato dal platform.
- Sport apps verificano token localmente (consigliato).

### 1.4 Platform Frontend

- Login / Register
- Dashboard account:
  - selezione sport da seguire
  - link ai subdomain degli sport seguiti

Deliverable: utente crea account, seleziona sport, token valido.

---

## Fase 2 — Sport 1 (es. Volleyball) end-to-end

Obiettivo: prima piattaforma sportiva completa (skin propria + DB proprio).

### 2.1 Volleyball DB schema (volleyball_db)

Migrazioni per “core locale sport”:

- `person`
- `person_nationality`
- `club` (con `registry_org_id UUID NULL`)
- `team`
- `competition`
- `season`
- `engagement`

Volley-specific (se serve in v1):

- `volleyball_match` / `volleyball_set` / `volleyball_team_stats` (posticipabili)

### 2.2 Volleyball API

- Verify token platform su ogni request
- CRUD base:
  - `/api/volleyball/people`
  - `/api/volleyball/clubs`
  - `/api/volleyball/competitions`
  - `/api/volleyball/seasons`
  - `/api/volleyball/engagements`

### 2.3 Cross-link società

- Nel volley: `club.registry_org_id`
- Nel platform: presence `sport_key='volleyball'` con `sport_ref` (slug/id club)

### 2.4 Volleyball Frontend

- Skin volley
- Club list + Club detail
- Club detail: se `registry_org_id` presente → fetch platform org → mostra link ad altri sport presenti

Deliverable: volleyball subdomain usabile, isolato, cross-link pronto.

---

## Fase 3 — Sport 2 (es. Football) replicando il modello

Obiettivo: aggiungere un secondo sport senza refactor del primo.

### 3.1 Football DB schema (football_db)

Replica core locale sport + calcio-specific:

- base: person/club/team/competition/season/engagement
- calcio-specific:
  - `football_profile`
  - `football_match`
  - `football_event`
  - `football_player_stats`

### 3.2 Football API

- verify token platform
- `/api/football/*` CRUD base + match/events/stats (anche incrementale)

### 3.3 Football Frontend

- skin football
- Club detail con cross-link via registry

### 3.4 Platform: abilita sport “football”

- sport tra quelli selezionabili
- mapping presence per società multi-sport

Deliverable: due sport indipendenti, account unico, registry funzionante.

---

## Fase 4 — Templating

Obiettivo: rendere “aggiungere uno sport” una procedura ripetibile.

### 4.1 Backend template sport app

Standardizzare:

- `main.py`, `deps.py`, `settings.py`
- `api/`, `domain/`, `db/models`, `repositories`, `migrations`

### 4.2 Frontend template sport app

Standardizzare:

- routing base
- theme folder
- api wrapper (base URL `api.<sport>.<domain>`)
- auth guard (token platform)

### 4.3 Infra template

Standardizzare:

- routing nginx per `sport.<domain>` e `api.sport.<domain>`
- docker-compose service template: `<sport>_db`, `<sport>_api`, `<sport>_web`

Deliverable: aggiungere sport = copia template + 5-10 configurazioni note.

---

## Fase 5 — Runbook: aggiungere un nuovo sport (Sport 3+)

### Backend

1. Crea: `server/packages/sports/<sport_key>/...`
2. Copia template app
3. Aggiungi env var: `<SPORT>_DATABASE_URL`
4. Configura verify token platform
5. Migrazioni: `0001_<sport>_init.py` (core locale sport)
6. Espone `/api/<sport_key>/*`

### Frontend

1. Crea: `client/apps/<sport_key>/` da template
2. Imposta tema/branding
3. Configura API base `api.<sport_key>.<domain>`
4. Cross-link club via `registry_org_id`

### Platform

1. Aggiungi sport alla lista selezionabile (preferenze utente)
2. Admin: set presence per società multi-sport (`org_sport_presence`)

### Infra/Deploy

1. Aggiungi subdomain web + api
2. Aggiungi servizi docker/helm
3. QA minimo: login → sport app → club detail → cross-link

---

## Milestone logiche

- M1: Platform auth + preferenze + org_registry/presence
- M2: Sport 1 (volleyball) CRUD base + cross-link club
- M3: Sport 2 (football) CRUD base + match/events minimi + cross-link
- M4: Template + runbook + (opzionale) script scaffolding
