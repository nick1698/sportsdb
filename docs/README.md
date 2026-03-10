# SportsDB — Multi-Vertical Platform (Platform + Verticali)

Piattaforma che raccoglie e mostra dati su più sport, con una **Platform/Core** centrale (identity, governance, auth, registry) e **verticali** per sport o eventi multi-sport, ciascuno con API+Web+DB separati.

## 1. Obiettivo e principi

### Obiettivo prodotto - fase 0 (MVP)

Consultazione data-heavy divisa per sport: pagine profilo di atlete/staff, club/squadre, leghe/campionati, federazioni/nazionali, con filtri/facet e ricerca testuale.

### Idee di implementazioni future

Per singolo sport:

- Calendari, risultati, classifiche
- Statistiche avanzate

Per utente:

- personalizzazione dashboard personale cross-sport
- editing dati (editor)

### Principi chiave

- **Separazione netta**: Core/Platform = control plane; Vertical = dominio specifico.
- **Hard refs**: nel dominio vertical non esiste “entità vera” senza identity core valida.
- **Governance**: create/link/merge di identity passano dall’**inbox core**.
- **Scalabilità per aggiunta sport**: aggiungere un nuovo sport deve essere (quasi) una procedura ripetibile.

## 2. Architettura (decisioni consolidate)

### 2.1 Concetti

- **Platform/Core**: registry + identity + auth + governance.
- **Vertical**: unità deployabile con `api + web + db` di diversi tipi (ognuno con DB proprio):
  - `sport` (volley, football, …)
  - `event` multi-sport (olympics, …)
- **Presence**: relazione identity↔vertical (Org/Person “presenti” nel vertical con uno status).
- **Inbox**: staging/governance per proposte: `create/link/merge/reject`
  - MVP: tabella centrale nel core DB (solo per modifiche a tabelle core)
  - Target: tabella core + tabella vertical (con blocco in caso di modifica a tabella core)

### 2.2 Resilienza / platform down

- MVP: se `platform/core db` è down, si accetta anche maintenance generale.
- Target: se `platform` è down:
  - i vertical restano **consultabili read-only** (pubblico)
  - tutte le funzioni protette vanno **fail-closed** (503)
  - nessun grace period auth: rotte protette vanno in 503

### 2.3 Ingress / routing

- Un **ingress “stupido”** (reverse proxy) fa TLS + routing per host/subdomain verso web/api.
- Niente logica di autorizzazione nell’ingress.

### 2.4 Repo e dipendenze

- **Monorepo** con unità deployabili indipendenti.
- Piramide dipendenze:
  - `shared/*` non dipende da niente
  - `platform/*` dipende solo da `shared/*`
  - `vertical/*` dipendono solo da `shared/*` (mai vertical - vertical)

### 2.5 Contratti API e standard

- Contratti **agnostici** e versionabili per servizio + index/registry.
- Standard comuni “HTTP-ish”:
  - JSON `snake_case`
  - error format unico + error codes stabili/documentati (catalogo globale)
  - convenzioni tecniche per paginazione/sorting/filtering/envelope

### 2.6 Boundaries dati (cosa sta dove)

#### Core DB

- Identity globale: Org, Person, Geo, Venue.
- Presence identity↔vertical.
- Registry dei vertical + governance inbox.

#### Vertical DB

- Competizioni/tornei, roster/tesseramenti, match, stats, season/edition.
- Team è entità nel DB vertical ma deve sempre puntare a Org core (no orfani).

> NB: Org “che ha senso solo nello sport” (es. lega/federazione solo volley): vive nel DB dello sport (non nel core).

### 2.7 Inbox identity: workflow e atomicità end-to-end

- Inbox identity nel core; UI inbox nel platform web; stati request unificati.
- Approve = commit **atomico end-to-end**; se fallisce l’ultimo step → **rollback totale**.
- Idempotenza obbligatoria sui retry per la stessa request.
- Duplicate request ammesse + clustering assistito.
- Esiti request: `create | link | merge | reject`.
- Ownership review: nessuna assegnazione personale; chiunque con permessi adeguati può decidere.

### 2.8 ID, merge e assenza di redirect mapping

- ID strategy: **ULID** o **UUID**.
- Merge può cambiare ID nel core => propagazione lockstep immediata (maintenance totale dei vertical coinvolti).
- **Nessun mapping** `old_id` -> `new_id`: o si aggiorna tutto nella stessa transazione end-to-end o rollback per tutti.

### 2.9 Registry vertical: Git bootstrap + runtime + heartbeat (bootstrap “C”)

- Bootstrap in Git: solo info **stabili/pubbliche** (catalogo whitelisted + display + URL pubblici).
- Runtime/infra: endpoint interni, porte, service discovery, stato UP/DOWN, build version.
- Heartbeat dai vertical verso platform.

### 2.10 Read-model locale (target)

- Vertical mantengono una **snapshot/read-model locale** dei campi minimi necessari per la consultazione pubblica.
- Live-fetch dal core solo dove serve (admin/flow protetti).

### 2.11 Osservabilità

- Correlazione cross-servizi: `request_id` + header W3C `traceparent` propagati e loggati.

## 3. Stack tecnologico (scelto)

### Backend (Platform + Vertical API)

- **Django + Django Ninja** (API tipate, OpenAPI, ergonomia stile FastAPI ma con ORM/migrations Django).
- Postgres per DB (un DB “platform” + uno per vertical).
- Migrazioni: Django migrations.
- Logging strutturato + request correlation (`request_id`, `traceparent`).

### Frontend

- React + TypeScript.
- Next.js come base per i web modules (hub/platform web + vertical web), con riuso di un `web-core` condiviso.

### Infra dev

- Docker Compose per sviluppo locale.
- Reverse proxy per host/subdomain routing (Traefik o Caddy; in dev Traefik è comodissimo per multi-host).

## 4. Docker in sviluppo

### Setup consigliato (MVP: Platform + 1 vertical “volley”)

**Minimo realistico (4–5 container):**

1. `reverse-proxy` (Traefik/Caddy) — routing per host/subdomain
2. `postgres` (una sola istanza) — contiene **più database**: `platform_db`, `[vertical]_db` (e futuri)
3. `platform-api` (Django + Ninja)
4. `[vertical]-api` (Django + Ninja)
5. (opzionale) `pgadmin` o `adminer` per debug DB

**Con web in container (aggiungi 2):** 6) `platform-web` (Next dev) 7) `[vertical]-web` (Next dev)

> Nota pratica: in dev, spesso conviene far girare Next sul host (pnpm dev) e dockerizzare solo backend+db+proxy
> Ma containerizzare anche il web è ok se vuoi replicabilità massima.

### Container futuri (quando serviranno davvero)

- `redis` + `worker` (Celery/RQ) per ingestion/scraping/ETL e job asincroni.
- `minio` per storage oggetti (media, asset).
- stack osservabilità (otel collector + grafana/tempo) se vuoi tracing end-to-end “vero”.

## 5. Struttura repo aggiornata

```text
repo/
  infra/
    docker-compose.dev.yml
    verticals_bootstrap.yaml
    reverse-proxy/
      traefik.yml
    db/
      Dockerfile
      00_roles.sql
      01_bootstrap.sql
      10_platform.sql
      verticals/
        _index_.sql
        volley.sql
        football.sql
        ...

  server/
    platform/                   # Django project + apps core (registry, identity, inbox, auth)
      Dockerfile.dev
      manage.py
      platform_api/
        admin/
        management/
        migrations/
        models/
        routers/
        tests/
      platform_service/
    shared/                     # solo tecnico: contracts, errors, observability, utils
      pyproject.toml
      api_contract/
        codes.py
        errors.py
        factory.py
        ninja.py
        request_id.py
        routing.py
        testing.py
      utils/
        admin.py
        models.py
    scripts/
      bin/
        create-vertical         # usato per creare vertical from scratch
      create_vertical/
      lib/
    verticals/
      volley/                   # Django project/app per [vertical] -> stesso filesystem di "platform"
      football/
      ...

  ui/                           # NB: non ancora creata!
    packages/
      web-core/                 # componenti neutrali + infra FE (query, auth wrapper, ui primitives)
    apps/
      platform-web/             # hub + inbox UI + admin
      volley-web/
      football-web/
      ...

  docs/
    architecture.md
```

## 6. Routing API condiviso

Per evitare URL hardcoded nei router e nei test, il progetto usa helper condivisi in `server/shared/api_contract/routing.py`.

Pattern attuale:

- `BaseRoute` + `TableUrlConfig` per mappare `model -> router prefix + table endpoint + pk`
- `PlatformRoute(Model)` per i path del platform

Questa è la convenzione preferita del progetto per costruire e riusare gli URL API.

## 7. Roadmap operativa

### 7.0 — Bootstrap repo e dev environment

- [x] Monorepo skeleton (backend/ui/infra/docs).
- [x] Docker Compose dev:
  - [x] reverse-proxy + postgres + platform-api + volley-api (+ opz web).
- [x] Convenzioni base:
  - [x] error format + error codes catalog
  - [x] request_id + traceparent propagation

Deliverable:

- [x] `GET /health` ovunque
- [x] DB up
- [ ] logging coerente

### 7.1 — Platform DB (Core Identity + Presence + Inbox)

**Obiettivo:** creare il _Platform DB_ Postgres con le entità **cross-sport** (country/sport/geo/venue/org/person),
le tabelle di **presence** (mapping platform ↔ vertical DB), e il workflow di **Inbox** per richieste `create/update/merge`.

#### 1.1 Bootstrap DB

- [x] Sistemare DB bootstrap files
- [x] Abilitare estensioni DB (`pgcrypto`, `citext`)

#### 1.2 Core Identity (cross-sport)

- campi comuni:
  - `ts_creation`, `ts_last_update`
- [x] `country`
  - PK: `iso2`
  - vincoli unique: `iso3`, `numeric_code`
- [x] `sport`
  - PK: `key` (slug immutabile)
  - `name_en`: display label
- [x] `geo_place`
  - FK: `country_id`
  - self-FK: `parent_id`
  - coordinate coerenti (lat/lon entrambi null o entrambi valorizzati)
- [x] `venue`
  - FK: `country_id`
  - FK opzionale: `geo_place_id`
  - coordinate coerenti (lat/lon entrambi null o entrambi valorizzati)
- [x] `org`
  - `type` con mapping (MVP): `1=nation`, `2=club`
  - FK: `country_id`
  - FK opzionale: `home_geo_place_id`
- [x] `person`
  - `sex`: `1=female`, `2=male`, `3=other`
  - FK: `primary_nationality_id` (NOT NULL)
  - FK opzionale: `sporting_nationality_id`
  - check: `death_date >= birth_date` se entrambe presenti

Deliverable: CRUD/admin minimo per tutte le entità core, con vincoli e indici applicati.

#### 1.3 Presence (platform ↔ vertical DB mapping)

> One-to-many ammesso: una `person`/`org` nel core può mapparsi a più record nel vertical.

- [x] `org_presence`
  - FK: `org_id` (cascade)
  - FK: `sport_key -> sport(key)`
  - campo verso i db vertical: `vertical_entity_id uuid`
  - unique: `(org_id, sport_key, vertical_entity_id)`
- [x] `person_presence`
  - FK: `person_id` (cascade)
  - FK: `sport_key -> sport(key)`
  - campo verso i db vertical: `vertical_entity_id uuid`
  - unique: `(person_id, sport_key, vertical_entity_id)`

Deliverable: inserimenti di presence + verifica vincoli unique + query semplici per sport.

#### 1.4 Inbox (governance MVP nel core)

- [x] `inbox_request`
  - `entity_type`: `{org, person, venue, geo_place}`
  - `action`: `{create, update, merge}`
  - `status`: `{pending, approved, rejected, duplicate, applied}` (default pending)
  - context: `sport_key`, `vertical_id`
  - target (opzionale: nullable per CREATE): `target_entity_id`
  - `payload jsonb NOT NULL`
  - audit fields (users, timestamps, notes)
- [x] `inbox_request_event`
  - event log: `{created, approved, rejected, applied, reviewed, comment}`
  - FK: `request_id` (cascade)
  - `actor` (user che commette l'evento)

Deliverable:

- endpoint _minimi_ (anche temporanei) o comandi admin per:
  - creare request
  - append eventi
  - listare per `status` e `entity_type`

#### 1.5 Timestamp policy

- [x] Tutte le tabelle: `ts_creation`, `ts_last_update` default `now()`
- [x] logic per aggiornare `ts_last_update` su UPDATE

#### **Obiettivi finali**

- [x] Migrations applicate su Postgres senza errori
- [x] Testing models
- [x] Presence funzionante (vincoli + query)
- [x] Inbox funzionante (request + events + listing)

### 7.2 — Core Identity “consumabile” (API read-only + search + alias + hard-refs)

**Obiettivo:** rendere le entità core (Org/Person/Geo/Venue) interrogabili e riusabili: endpoint pubblici read-only, ricerca base, alias, e un primo strato di regole “hard refs” per evitare riferimenti orfani/inconsistenti dai vertical.

#### 7.2.0 - Prerequisiti e definizioni

- [x] Definire standard paginazione (`limit` + `offset`) e applicarlo agli endpoint read-only iniziali
- [x] Definire standard sorting (`?sort=field`, `?sort=-field`) e applicarlo agli endpoint read-only iniziali
- [x] Definire schema errori API (404/400/422) e messaggi coerenti
- [x] Definire naming stabile per endpoint tramite helper condivisi in `shared.api_contract.routing`

#### 7.2.1 - API pubbliche read-only baseline

**Scope iniziale:** `country`, `sport`

- [x] `GET /api/core/countries` (list, paginated)
- [x] `GET /api/core/countries/{iso2}` (detail, 404 se missing)
- [x] `GET /api/core/sports` (list, paginated)
- [x] `GET /api/core/sports/{key}` (detail, 404 se missing)

Deliverable: pattern API read-only stabile e riusabile per entità core semplici.

#### 7.2.2 - Geo API read-only

**Scope iniziale:** `geo_place`

- [x] `GET /api/geo/locations` (list, paginated)
- [x] `GET /api/geo/locations/{id}` (detail, 404 se missing)
- [x] Filtro minimo: `?country_id=...`
- [x] Sorting minimo
- [x] Test list/detail/filter

Deliverable: GeoPlace interrogabile pubblicamente con contratto coerente a countries/sports.

#### 7.2.3 - Core entities read-only successive

**Scope:** `venue`, `org`, `person`

- [x] `GET /api/core/venues` + detail
- [x] `GET /api/core/orgs` + detail
- [x] `GET /api/core/persons` + detail
- [x] Filtri minimi per `venue`
- [x] Filtri minimi per `org`
- [x] Filtri minimi per `person`

Deliverable: Core Identity consultabile pubblicamente in modo uniforme.

#### 7.2.4 - Search MVP

- [x] `GET /api/core/search/orgs?q=...`
- [x] `GET /api/core/search/persons?q=...`
- [x] Ranking semplice e deterministico (`exact > startswith > contains`)

#### 7.2.5 - Presence tables read-only

- [ ] `GET /api/core/orgs/{id}/presences`
- [ ] `GET /api/core/persons/{id}/presences`
- [ ] listing filtrabili per `sport_key`

#### 7.2.6 - Hard-refs per vertical

- [ ] Documentare il contratto minimo platform ↔ vertical
- [ ] Definire cosa è hard-ref vs soft-ref
- [ ] Eventuali endpoint minimi di validate

#### 7.2.7 - Optional: search alias per core entities

- [ ] `OrgAlias`
- [ ] `PersonAlias`
- [ ] eventuale `VenueAlias`
- [ ] Search che include alias

Deliverable: il vertical può referenziare identity core in modo sicuro e il pubblico può consultare i dati base in read-only.

### 7.3 — Inbox identity (governance) + UI piattaforma

- Modello InboxRequest + stati unificati.
- Workflow: create/link/merge/reject.
- Clustering assistito (minimo: chiavi morbide + suggerimenti).
- Atomicità end-to-end: “approve” come transazione coordinata.
- UI inbox (platform-web) per review.

Deliverable: pipeline completa di proposta→review→promozione identity.

### 7.4 — Vertical 1: Volley (dominio minimo + read-only pubblico)

- DB volley con entità minime per consultazione:
  - team (ref Org core), competition, season, match (anche stub)
- Read-model locale per pubblico (snapshot campi minimi identity).
- Vertical heartbeat verso platform registry.
- Pagine web vertical (volley-web) + API pubbliche.

Deliverable: volley consultabile e “sopravvive” in read-only quando platform down (target).

### 7.5 — Scalare a Sport 2 (Football) con processo replicabile

- Template “new vertical”:
  - cartelle backend/frontend
  - DB + migration bootstrap
  - entry in bootstrap.yaml
  - compose snippet
- Verifica che l’aggiunta sport richieda pochi passaggi ripetibili.

Deliverable: “aggiungere sport” diventa una checklist.

### 7.6 — Event vertical (multi-sport) (opzionale dopo 2 sport)

- Event = vertical con DB proprio.
- Link debole event↔sport (discipline mapping).
- Partecipanti evento sempre Org core.

Deliverable: struttura pronta per olimpico/universiade.

### 7.7 — Ingestion/ETL (quando i dati manuali non bastano)

- Worker + queue.
- Pipeline: fetch → normalize → propose to inbox → approve → persist.
- Rate limiting, retry, idempotenza ingestion.

Deliverable: ingest semi-automatizzato con governance.

### 7.8 — Osservabilità “seria”

- OpenTelemetry (strumentazione Django) + backend traces.
- Dashboard base (error rate, latency, heartbeat freshness).

Deliverable: debug cross-servizi “da adulti”.

## 8. Dev Links (local)

### Traefik

- Dashboard: `http://platform.${DEV_DOMAIN}:8080/dashboard/`
  - Nota: `http://platform.${DEV_DOMAIN}:8080` → redirect a `/dashboard/`

### Platform API (via Traefik)

> Nel setup attuale **le porte interne (8000) non sono esposte**: si passa da Traefik (porta 80) usando l’host.

- Swagger / Docs:
  - `GET http://platform.${DEV_DOMAIN}/api/docs`
- OpenAPI JSON:
  - `GET http://platform.${DEV_DOMAIN}/api/openapi.json`

```bash
curl -i -H "Host: platform.${DEV_DOMAIN}" http://localhost/api/openapi.json
curl -i -H "Host: platform.${DEV_DOMAIN}" http://localhost/api/docs
curl -i -H "Host: platform.${DEV_DOMAIN}" http://localhost/api/core/countries
curl -i -H "Host: platform.${DEV_DOMAIN}" http://localhost/api/core/sports
```
