# SportsDB / Multi-Vertical Platform — Checkpoint architettura (2026-02-25)

Questo documento riassume **tutte le decisioni architetturali** prese nella chat corrente (domande **23 → 90**), più alcune note di contesto e i punti ancora aperti.  
Obiettivo: usarlo come “bootstrap” per ripartire in una prossima chat senza perdere continuità.

---

## 0) Visione (in una frase)
Piattaforma multi-vertical (sport + eventi multi-sport) con **core centrale** come registry/identity + auth, e **verticali deployabili separatamente** (API+Web+DB) che gestiscono il dominio specifico e restano **consultabili read-only** anche se il platform è down.

---

## 1) Macro-architettura (top-level)

### 1.1 Verticali
- Un “vertical” è un **dominio deployabile** con:
  - `vertical-api`
  - `vertical-web`
  - `vertical-db`
- Tipi di vertical:
  - `sport` (es. volley, football, …)
  - `event` multi-sport (es. olympics, universiade, …) **con DB proprio** (non “appendici” nei DB sport).
- I vertical **non dipendono tra loro** a runtime (solo link *deboli* via core).

### 1.2 Core / Platform
- `platform` è il **control plane**:
  - Identity globale: Person, Org, Geo, Venue, ecc.
  - AuthN/AuthZ (autenticazione/autorizzazione centralizzata)
  - Registry/config (bootstrap Git + override runtime + heartbeat)
  - Workflow di governance (inbox identity, matching, merge)
  - Admin console e area personale utente

### 1.3 Ingress / Routing
- Un **unico ingress “stupido”** (reverse proxy) gestisce TLS e routing per subdomain/host verso i vari web/api.
- L’ingress NON fa autorizzazione né logica “smart”.

---

## 2) Disponibilità e degrado (platform down)

### MVP (stato iniziale)
- Se `platform/core_db` è down → tutto può andare in maintenance (scelta iniziale “A” per MVP).

### Lungo termine (target)
- Se `platform` è down:
  - i vertical sono **consultabili read-only** (pubblico)
  - tutte le funzioni “utente” (protette) sono **disabilitate**

Scelte correlate:
- Enforcement auth nei vertical (non nell’ingress)
- Fail-closed puro: se platform non risponde → rotte protette 503
- Nessun grace period di autorizzazione

---

## 3) Frontend: riuso + deploy indipendenti

### Strategia scelta
- Modello **C**:
  - `web-core` con infrastruttura e componenti funzionali “neutri” (headless-ish)
  - moduli web per sport/event separati: **build/deploy indipendenti** e UI anche molto diversa

### Versioning del web-core
- Modello **C “a strati”**:
  - infra molto stabile
  - componenti UI condivisi più evolutivi

---

## 4) Config/Registry: bootstrap + runtime

Scelta complessiva: **C**
- Bootstrap in **Git**: lista vertical “whitelisted” + config base (slug/domains/base urls).
- Platform: override runtime (feature flags, visibilità, ecc.)
- Vertical: heartbeat/self-report (stato runtime + versione)

---

## 5) Contratti API, naming, error handling

### Contratti
- Contratti **agnostici** (schema neutro, es. OpenAPI/JSON Schema) — scelta (A).
- Contratti per servizio + registry/index dei contratti — scelta (C).

### Standard comuni (shared/contracts)
- Standard “HTTP-ish” (B):
  - error format standard
  - paginazione/sorting/filtering/envelope (convenzioni tecniche)
- Possibile evoluzione verso “vocabolario core” (C) in futuro, ma non ora.

### Naming JSON
- **snake_case** nei payload.

### Error format e codici
- Formato errore **unico platform-wide** e informativo.
- **Error codes stabili e documentati** (catalogo globale), con possibile namespace futuro.
- Quando platform è down e endpoint protetto: **503** (non 401/403).

---

## 6) Repo e dipendenze

### Repo
- Monorepo con unità deployabili indipendenti (C).
- Git submodules: **sconsigliati** per questo scenario (più attrito che beneficio).

### Regole di dipendenza (piramide rigida)
- `shared/*` non dipende da niente
- `platform/*` dipende solo da `shared/*`
- `vertical/*` dipendono solo da `shared/*` (mai da altri vertical)

### shared
- shared “di piattaforma” (B): utilities + contracts tecnici; **no business logic**.
- contracts dentro `shared/contracts/*` (A).

---

## 7) AuthN/AuthZ e surface pubblica

### Autorizzazione
- Dipende dal platform (introspection centrale).
- Enforcement reale nei **vertical** (app-layer), non in ingress, non nel frontend.
- Fail-closed puro: se platform giù → endpoint protetti 503.

### Surface pubblica
- Default: GET pubbliche, write protette.
- Eccezioni: alcune GET user-specific protette.
- Regola di design: **router separati** `public` vs `protected`.

---

## 8) Landing e discoverability

- Landing **statica** indipendente dal platform (C): elenca vertical e linka anche al platform per login.
- Landing mostra lo stato dei vertical (B): “online/offline/maintenance”.
- Fonte stato: healthcheck **diretto** ai vertical (A).

---

## 9) Core data boundaries + Presence

### Identity nel core
- Org/Person come entità globali (identity registry).
- Geo + Venue nel core (A).

### Presence nel core
- Presence nel core: link identity ↔ contesto.
- Con l’introduzione di `Vertical`:
  - `Vertical` nel core con `type = sport | event` (B)
  - Presence generalizzata (A): Person/Org ↔ Vertical con `status` proprio (pending/active/…)

### Competizioni
- Competizioni/tornei sono **solo nei DB vertical** (sport/event), non nel core.
- Eventi multi-sport sono vertical separati (DB proprio).

### Team
- Nei DB sport (e event): `Team` deve sempre puntare a una `Org` core (no orfani).
- Team è entità vera nello sport DB (id proprio) che punta a Org (non derivata).

### Season/Edition
- Season/Edition vive **per-vertical** (nei DB vertical), non nel core.

### Link tra eventi e sport
- Link **debole**: un event può referenziare un `vertical_id` di tipo sport per mappare le discipline, ma i dati dell’evento restano autonomi.

---

## 10) Ingestion/Governance: inbox, matching, merge

### Regola forte: hard refs
- Nei DB vertical, entità “vere” (athlete/team/match/…) esistono solo se hanno ref core valida.
- Niente “soft ref” nelle tabelle principali: coerenza massima.

### Staging/boundary
- Le proposte entrano in una **inbox/boundary** finché non approvate.
- Inbox (per identity) vive nel **core** (B), non nei vertical.

### Creazione/approvazione identity
- Da subito: modello **55 = C**:
  - i vertical possono proporre
  - platform approva/promuove/merge
- Matching dedup: **assistito** (56 = B), con chiavi “morbide” (60 = B).
- Normalizzazione: as-is + alias; per Person: given_name + family_name + nickname + aliases (61 = A).

### Merge e ID
- In caso di merge, scelta: **ID nel core possono cambiare** (57 = B).
- Propagazione merge: **lockstep immediato** (58 = A) con maintenance totale per gli sport coinvolti (59 = A).
- Merge rari e “cerimoniali” (impostazione deliberata).

### Inbox retention
- Richieste con esito definitivo (not null) cancellate completamente dopo X giorni.
- Pending non risolte: restano a tempo indeterminato o cancellate manualmente.

### Commit end-to-end
- Approvazione = commit **atomico end-to-end** (80 = A).
- Se l’ultimo step fallisce: **rollback totale** (81 = A).
- Retry: idempotenza obbligatoria per la stessa request (82 = A).

### Duplicati in inbox
- Possibili richieste duplicate (83 = A: request_id generato dal platform).
- Gestione duplicati: clustering assistito (84 = B).
- Dopo approvazione di una request in cluster: le altre diventano “needs_review” (85 = C).
- Esiti request: create/link/merge/reject (86 = A).

### Future: inbox sport-specific
- MVP: inbox core solo identity.
- Futuro: ogni vertical può avere una inbox sport-specific per richieste di dominio, **separata**, collegabile alla core inbox (89 = A).

### Stati request
- Set di stati unico platform-wide per tutte le inbox (90 = A).

---

## 11) Decision log (Domande 23 → 90)

> Nota: alcune domande sono state riformulate lungo la chat; qui sono riportate in modo compatto.

### Resilienza / Core down
- **Q23**: core down → MVP A, lungo termine B.
- **Q24**: ID strategy → Opzione 3 (ULID preferito).
- **Q25**: deploy backend → **B** (servizi separati per sport).
- **Q26**: auth dipende dal platform; sport read-only se platform down.
- **Q27**: frontend → **C** (core riusabile + moduli separati).
- **Q28**: condivisione FE → **B** (infra + componenti funzionali neutri).
- **Q29**: versioning web-core → **C** (a strati).
- **Q30**: config “SSOT” → **C** (Git bootstrap + platform override).
- **Q31**: registrazione servizi → **C** (whitelist + heartbeat).
- **Q32**: gestione evoluzione API per sport → **A** (web+api insieme).
- **Q33**: repo → **C** (monorepo, deploy indipendente).
- **Q34**: regole dipendenze → **A** (piramide rigida).
- **Q35**: contenuto shared → **B** (tecnico, no dominio).
- **Q36**: dove i contratti → **A** (in shared/contracts).
- **Q37**: contratti agnostici → **A**.
- **Q38**: contratti per servizio + index → **C**.
- **Q39**: common standard → **B** (HTTP-ish).
- **Q40**: naming JSON → **A** (snake_case).
- **Q41**: error format unico → **A** (informativo).
- **Q42**: error codes → **A** (stabili).
- **Q43**: catalogo error codes globale → **A** (namespace forse in futuro).

### Permessi / Edge / Public surface
- **Q44**: ruoli → **A** (globali).
- **Q45**: edge routing → **A** (ingress unico stupido).
- **Q46**: enforcement auth → **A** (nei vertical).
- **Q47**: platform down su rotte protette → **A** (503).
- **Q48**: grace period auth → **A** (fail-closed).
- **Q49**: home/discoverability → **C** (landing statica).
- **Q50**: sport offline UX → **B** (stato visibile).
- **Q51**: fonte stato landing → **A** (healthcheck diretto).
- **Q52**: pubblico vs protetto → **C** (default GET public + eccezioni).
- **Q53**: dichiarare eccezioni → **C** (router public/protected).

### Core vs Sport, Presence, Vertical
- **Q54**: presence Org/Person in sport → **B** (nel core).
- **Q55**: chi crea presence → **C da subito** (proposte sport, approvazione platform).
- **Q56**: dedup → **B** (assistito).
- **Q57**: merge ID → **B** (ID possono cambiare).
- **Q58**: propagazione merge → **A** (immediata lockstep).
- **Q59**: merge downtime → **A** (maintenance totale sport coinvolti).
- **Q60**: matching keys → **B** (morbide).
- **Q61**: normalizzazione nomi → **A** (as-is + alias; person: given/family/nickname).
- **Q62**: provenienza dati → **B MVP**, target **C**.
- **Q63**: confidence → **B** (per entità).
- **Q64**: status su presence → **B**.
- **Q65**: multiple identità nello stesso sport → **A MVP**, target **B**.
- **Q66**: Team può esistere senza Org → **A** (deve sempre puntare a Org core).
- **Q67**: federazioni/nazionali ecc. come Org type → (inizialmente A; poi chiarimento: entità sport-scoped possono comunque essere gestite come identity se desiderato; decisione operativa rimane da rifinire in seguito).
- **Q68**: competizioni nel core? → **A** (solo nei DB sport).
- **Q69**: Geo+Venue nel core → **A**.
- **Q70**: concetto Vertical nel core → **B** (sport|event).
- **Q71**: presence generalizzata per vertical → **A**.
- **Q72**: link evento↔sport → **B** (link debole).
- **Q73**: partecipanti evento multi-sport → **A** (sempre Org core).
- **Q74**: roster/tesseramenti → **A** (entità sport DB).
- **Q75**: team model → **A** (entità team nello sport DB).
- **Q76**: seasons → **A** (per-vertical).

### Hard refs, inbox, atomicity
- **Q77**: hard refs vs soft refs → **A** (hard; staging prima).
- **Q78**: dove vive staging/inbox → **B** (core).
- **Q79**: retention → deciso: chiuse cancellate; pending indefinite/manual.
- **Q80**: approvazione end-to-end → **A**.
- **Q81**: failure end-to-end → **A** (rollback totale).
- **Q82**: idempotenza → **A**.
- **Q83**: chi genera request_id → **A** (platform); duplicate request ammesse.
- **Q84**: duplicati inbox → **B** (cluster assistito).
- **Q85**: dopo approve in cluster → **C** (needs_review per le altre).
- **Q86**: esiti request → **A** (create/link/merge/reject).
- **Q87**: tipi request inbox core → **A MVP**; futuro: inbox sport-specific per vertical.
- **Q88**: UI gestione inbox → **A** (platform web).
- **Q89**: link sport-inbox ↔ core-inbox → **A**.
- **Q90**: set stati request unico → **A**.

---

## 12) Punti aperti / prossime domande (non risolte qui)
- **Q91 (non risposto)**: ownership richieste — user-owned vs group-owned (collaborazione).
- Dettaglio su **Org sport-scoped** (federazioni/leghe): scelta finale su “Org core sempre” vs “in sport DB”. (È emersa una distinzione concettuale importante: identità reale vs semantica sport-scoped).
- Definizione esplicita di:
  - campi minimi per Geo/Venue nel core (solo concettuale)
  - schema “Vertical registry” nel bootstrap Git (concettuale)
  - policy di merge/rename ID (dato che scelto ID-change lockstep)
- Politiche osservabilità (trace_id, log correlation) — solo a livello concettuale.

---

## 13) TL;DR (se devi ricordare una cosa sola)
**Core = identity + auth + governance**.  
**Vertical = dominio specifico** (sport o evento multi-sport) con DB proprio, consultabile read-only se platform down.  
**Hard refs**: niente entità vertical senza identity core.  
**Inbox core**: staging identity + approvazione atomica end-to-end con rollback totale.

