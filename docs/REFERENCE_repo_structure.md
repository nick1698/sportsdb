# Riferimento progetto: Architettura monorepo (Platform + Sport Apps, DB separati)

Questo documento descrive **la struttura finale** del repository e le **regole di progettazione**.
Scopo: essere un riferimento stabile per le prossime chat e decisioni architetturali.

---

## Obiettivo del prodotto

- Stesso **dominio** con più piattaforme, una per sport (UI/skin e roadmap indipendenti).
- A lungo termine: routing **subdomain-based** (es. `football.example.com`, `volleyball.example.com`).
- **Account unico**: l’utente si registra sulla piattaforma generale (Platform) e poi accede agli sport che gli interessano.
- **Dati sportivi isolati**: ogni sport ha il proprio DB; nessun mix e nessuna query cross-sport.
- **Cross-linking società**: un registry globale (nel platform_db) consente di collegare manualmente la stessa società tra sport diversi.

---

## Concetti chiave (da ricordare sempre)

### 1) DB separati per sport

- `platform_db`: utenti/auth, preferenze utente, registry globale società e mapping sport.
- `volleyball_db`, `football_db`, ...: dati completi dello sport (persone, club, squadre, competizioni, match, stats…).

### 2) “Persona” non è cross-sport

- Se un’atleta passa a un altro sport, viene **duplicata** nel DB dell’altro sport.
- All’interno dello stesso sport, la persona resta la stessa se cambia ruolo (atleta → staff → dirigente).

### 3) Cross-linking società (manuale)

- In `platform_db` esistono:
  - `org_registry` (società globale)
  - `org_sport_presence` (presenza su sport X + riferimento nello sport DB)
- Nel DB sportivo, ogni `club` può avere:
  - `registry_org_id UUID NULL` (link al registry globale)
- Matching **manuale** (nessun automatismo).

### 4) Autenticazione centralizzata

- Registrazione/login solo su Platform.
- Le sport apps **verificano** token emessi da Platform (idealmente JWT verify locale).

---

## Struttura repository (dettagliata, commentata)

```text
sports-platform/                             # Monorepo: platform + N sport, stessa ossatura
  README.md                                  # Overview + avvio dev + principi
  docker-compose.yml                         # Dev stack: platform + sport apps + DB separati + proxy
  .env.example                               # Env template (DB URLs, JWT keys, domains)

  docs/                                      # Documentazione decisionale
    architecture.md                          # Vision: confini platform/sport, subdomain
    conventions.md                           # Naming, versioning, migrazioni, code style
    runbooks.md                              # Operazioni: backup/restore/migrazioni

  infra/                                     # Reverse proxy, script, helper
    nginx/
      nginx.conf                              # Routing subdomain-based (dev/prod)
      snippets/
        common_headers.conf
    scripts/
      dev-bootstrap.sh
      db-reset.sh

  ops/                                       # Packaging/deploy (dockerfiles; poi k8s/terraform se serve)
    docker/
      server.platform.Dockerfile
      server.volleyball.Dockerfile
      server.football.Dockerfile
      client.platform.Dockerfile
      client.volleyball.Dockerfile
      client.football.Dockerfile

  # =========================
  # BACKEND (FastAPI / Python)
  # =========================
  server/
    pyproject.toml                            # Workspace backend
    ruff.toml
    pytest.ini

    packages/
      core/                                   # Libreria condivisa: NO sport knowledge
        src/core/
          settings/                            # pydantic settings base
          logging/                             # logging su file + rotazione
          errors/                              # error mapping coerente
          db/                                  # engine/session factory + healthcheck
          storage/                             # Storage interface + Local FS
          security/                            # hashing/token verify utilities
          utils/
        tests/

      platform_app/                            # Platform API + platform_db
        src/platform_app/
          main.py                              # FastAPI app platform
          deps.py
          settings.py                          # PLATFORM_DATABASE_URL, JWT keys, ecc.
          api/                                 # /api/platform/*
            auth.py                            # register/login/refresh
            users.py
            preferences.py                     # sport seguiti
            org_registry.py                    # registry società + presence mapping (admin)
          domain/
            services/
              org_registry_service.py
              auth_service.py
              preferences_service.py
          db/
            models/                            # SOLO platform_db
              user.py
              user_sport_preference.py
              org_registry.py                  # società globale
              org_sport_presence.py            # mapping società ↔ sport
              media.py                         # (opzionale) media globale
            repositories/
            migrations/                        # Alembic SOLO platform_db
              alembic.ini
              env.py
              versions/
        tests/

      sports/                                  # Una cartella per sport (app + db separati)
        volleyball/
          api_app/
            src/volleyball_app/
              main.py                          # FastAPI app volley
              deps.py
              settings.py                      # VOLLEYBALL_DATABASE_URL + platform token verify config
              api/                             # /api/volleyball/*
                people.py
                clubs.py                       # club.registry_org_id per cross-link
                competitions.py
                seasons.py
                engagements.py
                matches.py                     # volley-specific (quando serve)
                stats.py
              domain/
                services/
              db/
                models/                        # SOLO volleyball_db
                  person.py
                  club.py                      # include registry_org_id UUID NULL
                  team.py
                  competition.py
                  season.py
                  engagement.py
                  # + volley-specific tables quando servono
                repositories/
                migrations/                    # Alembic SOLO volleyball_db
                  alembic.ini
                  env.py
                  versions/
            tests/

        football/                               # (futuro) stessa ossatura di volleyball
          api_app/
            src/football_app/
              main.py
              deps.py
              settings.py                      # FOOTBALL_DATABASE_URL ...
              api/                             # /api/football/*
              domain/
              db/
                models/                        # SOLO football_db
                repositories/
                migrations/
                  versions/
            tests/

  # ==========================
  # FRONTEND (React / TypeScript)
  # ==========================
  client/
    package.json                               # Workspace FE (consiglio pnpm)
    tsconfig.base.json
    eslint.config.js
    prettier.config.cjs

    packages/
      ui/                                      # UI kit neutro (componenti riusabili)
      api-client/                              # HTTP client + auth + tanstack helpers
      config/                                  # eslint/ts config condivise (opzionale)

    apps/
      platform/                                # platform.<domain>: login/account/preferenze sport
        src/
          routes/
          theme/                               # skin platform
      volleyball/                              # volleyball.<domain>: skin volley + feature volley
        src/
          features/
          theme/                               # skin volley
      football/                                # football.<domain>: skin football + feature football
        src/
          features/
          theme/
```

---

## Routing (target subdomain-based)

- Web:
  - `platform.<domain>` → `client/apps/platform`
  - `volleyball.<domain>` → `client/apps/volleyball`
  - `football.<domain>` → `client/apps/football`

- API:
  - `api.platform.<domain>` → `platform_app`
  - `api.volleyball.<domain>` → `volleyball_app`
  - `api.football.<domain>` → `football_app`

---

## Regole di dipendenza (per evitare caos)

- `platform_app` è **centrale** e deve restare piccolo/stabile.
- Le sport apps:
  - dipendono dal `core` (logging/settings/db/storage utilities),
  - **verificano token** del platform,
  - possono fare **read-only** sul registry del platform per mostrare cross-link.
- Mai introdurre join o sync cross-sport nei DB sportivi.
