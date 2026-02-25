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

## 5. Struttura repo (proposta)

```text
repo/
  infra/
    compose/
      docker-compose.dev.yml
    reverse-proxy/
      traefik/...
    verticals/
      bootstrap.yaml

  backend/
    shared/                     # solo tecnico: contracts, errors, observability, utils
    platform/                   # Django project + apps core (registry, identity, inbox, auth)
    verticals/
      volley/                   # Django project/app per [vertical] (API + read-model)
      football/
      ...

  ui/
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

## 6. Roadmap estesa (operativa)

### Phase 0 — Bootstrap repo e dev environment

- Monorepo skeleton (backend/ui/infra/docs).
- Docker Compose dev:
  - reverse-proxy + postgres + platform-api + volley-api (+ opz web).
- Convenzioni base:
  - snake_case JSON
  - error format + error codes catalog
  - request_id + traceparent propagation

Deliverable: `GET /health` ovunque + logging coerente + DB up.

### Phase 1 — Platform Registry (bootstrap Git “C” + runtime + heartbeat)

- Definire `infra/verticals/bootstrap.yaml` (whitelist).
- Tabelle/Models registry nel DB platform:
  - `Vertical` (stabile/pubblico)
  - `VerticalRuntime` (dinamico: heartbeat, status, build_version, internal urls)
- Endpoint:
  - `GET /public/registry/verticals`
  - `POST /internal/registry/heartbeat` (protetto con internal token)

Deliverable: landing/UI può mostrare elenco vertical + stato.

### Phase 2 — Fondamenta Identity nel core (senza inbox ancora completa)

- Modelli base: Org, Person, Geo, Venue (+ alias).
- Presence: Org↔Vertical, Person↔Vertical con status.
- Endpoint pubblici read-only (listing/search semplice).
- Prime regole “hard refs” (validation layer) per i vertical.

Deliverable: il vertical può referenziare identity core in modo sicuro.

### Phase 3 — Inbox identity (governance) + UI piattaforma

- Modello InboxRequest + stati unificati.
- Workflow: create/link/merge/reject.
- Clustering assistito (minimo: chiavi morbide + suggerimenti).
- Atomicità end-to-end: “approve” come transazione coordinata.
- UI inbox (platform-web) per review.

Deliverable: pipeline completa di proposta→review→promozione identity.

### Phase 4 — Vertical 1: Volley (dominio minimo + read-only pubblico)

- DB volley con entità minime per consultazione:
  - team (ref Org core), competition, season, match (anche stub)
- Read-model locale per pubblico (snapshot campi minimi identity).
- Vertical heartbeat verso platform registry.
- Pagine web vertical (volley-web) + API pubbliche.

Deliverable: volley consultabile e “sopravvive” in read-only quando platform down (target).

### Phase 5 — Scalare a Sport 2 (Football) con processo replicabile

- Template “new vertical”:
  - cartelle backend/frontend
  - DB + migration bootstrap
  - entry in bootstrap.yaml
  - compose snippet
- Verifica che l’aggiunta sport richieda pochi passaggi ripetibili.

Deliverable: “aggiungere sport” diventa una checklist.

### Phase 6 — Event vertical (multi-sport) (opzionale dopo 2 sport)

- Event = vertical con DB proprio.
- Link debole event↔sport (discipline mapping).
- Partecipanti evento sempre Org core.

Deliverable: struttura pronta per olimpico/universiade.

### Phase 7 — Ingestion/ETL (quando i dati manuali non bastano)

- Worker + queue.
- Pipeline: fetch → normalize → propose to inbox → approve → persist.
- Rate limiting, retry, idempotenza ingestion.

Deliverable: ingest semi-automatizzato con governance.

### Phase 8 — Osservabilità “seria”

- OpenTelemetry (strumentazione Django) + backend traces.
- Dashboard base (error rate, latency, heartbeat freshness).

Deliverable: debug cross-servizi “da adulti”.
