# SportsDB / Multi‑Vertical Platform — Decisioni architetturali (Checkpoint v3, 2026‑02‑25)

Questo documento **consolida**:
- le decisioni architetturali già raccolte nel checkpoint precedente (**Q23 → Q90**)
- le decisioni aggiuntive di questa ripartenza (**Q91 → Q96**) e le correzioni/raffinamenti emersi (es. Org sport‑scoped).

> Obiettivo: avere un *single reference* da tenere nel repo (docs/) e usare come base per iniziare l’implementazione.

---

## 0) Visione (in una frase)
Piattaforma multi‑vertical (sport + eventi multi‑sport) con **core centrale** come registry/identity + auth + governance, e **verticali deployabili separatamente** (API+Web+DB) che gestiscono il dominio specifico e restano **consultabili read‑only** anche se il core/platform è down.

---

## 1) Terminologia (minima)
- **Core / Platform**: control plane (identity globale, auth, registry, governance).
- **Vertical**: dominio deployabile con `api + web + db`. Tipi:
  - `sport` (es. volley, football)
  - `event` multi‑sport (es. olympics) con **DB proprio**.
- **Presence**: relazione identity↔vertical (es. Org/Person presente nel vertical con uno status).
- **Inbox**: staging/governance per proposte di identity (create/link/merge/reject), con workflow di review.

---

## 2) Macro‑architettura (top‑level)

### 2.1 Verticali
- Ogni vertical è un pacchetto deployabile: `vertical-api`, `vertical-web`, `vertical-db`.
- I vertical **non dipendono tra loro** a runtime (solo link deboli via core).

### 2.2 Core / Platform
Il core gestisce:
- Identity globale (Org, Person, Geo, Venue…)
- AuthN/AuthZ centralizzata (introspection)
- Registry/config dei vertical (bootstrap + runtime + heartbeat)
- Governance: inbox, matching, merge
- Admin console + area utente

### 2.3 Ingress / routing
- Un unico ingress “stupido” (reverse proxy) per TLS e routing host/subdomain → web/api.
- L’ingress **non** fa autorizzazione.

---

## 3) Disponibilità e degrado (core down)

### MVP (inizio)
- Se `platform/core_db` è down: si accetta anche che tutto vada in maintenance (scelta iniziale “A”).

### Target (lungo termine)
- Se `platform` è down:
  - vertical **consultabili read‑only** per il pubblico
  - funzioni utente (protette) **disabilitate** (fail‑closed)

Scelte correlate:
- enforcement auth nei vertical (app layer), non nell’ingress
- fail‑closed: se platform non risponde → endpoint protetti **503**
- nessun grace period auth

---

## 4) Repo, dipendenze, shared

### Repo
- **Monorepo** con unità deployabili indipendenti.

### Regole di dipendenza (piramide rigida)
- `shared/*` non dipende da niente
- `platform/*` dipende solo da `shared/*`
- `vertical/*` dipendono solo da `shared/*` (mai da altri vertical)

### shared
- shared “tecnico” (utilities + contracts), **no business logic**.

---

## 5) Contratti API e standard

### Contratti
- Contratti **agnostici** (schema neutro).
- Contratti **per servizio** + **index/registry** dei contratti.

### Standard comuni
- Standard “HTTP‑ish”:
  - error format standard
  - convenzioni tecniche per paginazione/sorting/filtering/envelope
- JSON payload: **snake_case**
- Error codes: **stabili e documentati** (catalogo globale; namespace forse in futuro)

---

## 6) Frontend: riuso + deploy indipendenti
- Strategia: `web-core` con infrastruttura e componenti neutri + moduli sport/event separati (build/deploy indipendenti).
- Versioning web-core: “a strati” (infra più stabile, UI shared più evolutiva).

---

## 7) AuthN/AuthZ e surface pubblica
- Auth dipende dal platform (introspection centrale).
- Enforcement nei vertical (app layer).
- Default: **GET pubbliche**, write protette; eccezioni: GET user‑specific protette.
- Router separati: `public` vs `protected`.

---

## 8) Landing e discoverability
- Landing **statica** indipendente dal platform (elenca vertical + link login).
- Mostra stato vertical (online/offline/maintenance).
- Fonte stato: healthcheck diretto ai vertical.

---

## 9) Core data boundaries (cosa sta dove)

### Nel core (identity)
- **Org/Person** come identità globali.
- **Geo + Venue** nel core.
- Presence nel core: link identity↔vertical con status.

### Nei DB vertical (dominio sport/event)
- Competizioni/tornei: **solo** nei DB vertical (sport/event), non nel core.
- Team: entità nel DB sport/event con **hard ref** a Org core (no orfani).
- Roster/tesseramenti: nel DB sport/event.
- Season/Edition: per‑vertical (nel DB vertical).

### Org sport‑scoped
- Org che hanno senso **solo** in uno sport (es. lega/federazione “solo volley”) vivono **nel DB dello sport** (non nel core).

### Link event↔sport
- Link debole: un event può referenziare `vertical_id` sport per mappare discipline, ma i dati evento restano autonomi.

---

## 10) Hard refs, inbox, governance, atomicità

### Hard refs + staging
- Nel dominio vertical, entità “vere” esistono solo se la ref core è valida.
- Niente soft ref nelle tabelle principali: staging/inbox prima.

### Inbox identity
- Inbox (identity) nel **core**.
- UI inbox nel platform web.
- Stati request: set unico platform‑wide.

### Workflow (end‑to‑end)
- Approve = commit **atomico end‑to‑end**.
- Se uno step finale fallisce → **rollback totale**.
- Retry: idempotenza obbligatoria per la stessa request.

### Dedup e merge
- Dedup matching: **assistito** con chiavi “morbide”.
- Merge può cambiare ID nel core.
- Propagazione merge: lockstep immediato; maintenance totale per gli sport coinvolti (merge rari e “cerimoniali”).

### Duplicati inbox
- Duplicate request ammesse.
- Clustering assistito.
- Dopo approvazione in cluster: le altre vanno in `needs_review`.
- Esiti request: create/link/merge/reject.

### Inbox sport‑specific (futuro)
- MVP: inbox core solo identity.
- Futuro: vertical può avere inbox di dominio separata, collegabile alla core inbox.

### Ownership review inbox (Q91)
- La request **non viene assegnata a una persona**: chiunque con permessi adeguati può fare review/decisione.
- Concorrenza gestita a livello implementativo (es. optimistic locking) — dettagli rimandati.

---

## 11) Registry/config dei vertical (bootstrap + runtime)

Scelta complessiva: **Git bootstrap + runtime override + heartbeat**.

### Contenuto bootstrap Git (Q93 = C)
- In Git: **solo info stabili/pubbliche** (catalogo vertical whitelisted + display + URL pubblici o domini).
- Fuori da Git (runtime/infra/registry DB): endpoint interni, porte, service discovery, stato UP/DOWN, versioni deployate.

---

## 12) Read model locale (Q94 = C)
- Per garantire consultazione pubblica anche se core down:
  - i vertical mantengono una **snapshot/read‑model locale** dei campi minimi necessari per il pubblico
  - live‑fetch dal core solo dove serve (admin/strumenti interni/flow protetti)

---

## 13) Redirect old_id → new_id (Q95 = C)
- **Nessun mapping** old_id → new_id.
- Merge/ID‑change è valido solo se tutte le dipendenze vengono aggiornate **nella stessa transazione end‑to‑end**; altrimenti rollback.

---

## 14) Osservabilità / correlazione log (Q96)
- Standard minimo cross‑servizi:
  - `request_id` + header W3C `traceparent` (propagati e loggati)
- Nota: non implica “installare subito” tracing backend; prepara però la strada (OpenTelemetry/Tempo/Jaeger) senza refactor.

---

## 15) Decision log (Q23 → Q96)

> Nota: molte domande sono state raggruppate/ri‑parafrasate in chat; qui il log è in forma compatta ma tracciabile.

### Resilienza / core down
- Q23: MVP A, target B (vertical read‑only pubblico).
- Q24: ID strategy: **ULID**.
- Q26, Q46–Q48: auth dipende dal platform; enforcement nei vertical; fail‑closed; endpoint protetti 503.

### Vertical, routing, repo
- Q25: servizi separati per sport.
- Q45: ingress unico stupido.
- Q33: monorepo deploy indipendente.
- Q34: piramide dipendenze.
- Q35–Q36: shared tecnico; contracts in `shared/contracts`.

### Contratti, naming, errors
- Q37: contratti agnostici.
- Q38: contratti per servizio + index.
- Q39: standard HTTP‑ish.
- Q40: snake_case.
- Q41: error format unico.
- Q42–Q43: error codes stabili + catalogo globale.

### Frontend
- Q27–Q29: web‑core riusabile + moduli separati; versioning a strati.

### Discoverability
- Q49: landing statica.
- Q50: stato visibile.
- Q51: healthcheck diretto.

### Core boundaries / presence
- Q54: presence nel core.
- Q55: vertical propone; platform approva.
- Q68: competizioni solo nei vertical DB.
- Q69: geo/venue nel core.
- Q70–Q72: vertical type sport|event + presence generalizzata + link debole event↔sport.
- Q66, Q75: team sport DB con ref a Org core (no orfani).
- Q74, Q76: roster/season per vertical.

### Governance / inbox / atomicità
- Q77: hard refs con staging.
- Q78: inbox identity nel core.
- Q80–Q82: approve atomico end‑to‑end; rollback totale; idempotenza.
- Q83–Q86: request_id dal platform; duplicati ammessi; clustering assistito; esiti create/link/merge/reject.
- Q87–Q90: MVP solo identity; futuro inbox sport‑specific; UI nel platform web; stati unificati.

### Decisioni aggiuntive (ripartenza)
- Q91: request non assegnate; review by permission.
- Q92: Org sport‑scoped nel DB sport.
- Q93: bootstrap Git “C” (catalogo pubblico stabile; dettagli interni a runtime).
- Q94: read‑model locale per pubblico.
- Q95: no redirect mapping old→new; lockstep o rollback.
- Q96: request_id + traceparent.

---

## 16) TL;DR
**Core = identity + auth + governance.**  
**Vertical = dominio specifico** (sport o event) con DB proprio, consultabile read‑only se platform down.  
**Hard refs** + **inbox core** per identity: approvazione atomica end‑to‑end con rollback totale.  
Registry: catalogo verticale in Git (pubblico/stabile) + runtime per stato/endpoint interni.
