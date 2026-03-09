# SPDB — Setup del repo su una nuova macchina

Questa guida riassume i passaggi necessari per configurare il repo SPDB su una nuova macchina, in modo il più possibile indipendente dal sistema operativo.

## Principio generale

Il repo funziona bene quando gira in un ambiente **Linux-like**.

- Su **Linux**: va bene nativamente.
- Su **macOS**: in genere va bene senza particolari problemi.
- Su **Windows**: la strada consigliata è **WSL2 + Docker Desktop**, lavorando dentro il filesystem Linux di WSL.

Importante avere:

- shell Unix-like
- Docker funzionante
- Python gestito in modo coerente
- filesystem adatto allo sviluppo

## 1. Prerequisiti

Servono questi strumenti:

- **Git**
- **Docker** + **Docker Compose**
- **shell Unix-like**
- **pyenv**
- **pyenv-virtualenv**
- **Python 3.12.12**
- un editor che lavori bene col filesystem del progetto

### Nota per Windows

Su Windows è fortemente consigliato:

- usare **WSL2**
- installare **pyenv dentro WSL**
- clonare il repo **dentro WSL**
- lanciare i comandi **da shell WSL**

## 2. Clonare il repo

Clonare il repository in una cartella di lavoro locale.  
Esempio:

```bash
git clone git@github.com:nick1698/sportsdb.git ~/dev/sportsdb
```

## 3. Installare Python con `pyenv` dentro la directory `server`

La shell deve caricare correttamente il setup di `pyenv`.

Se si usa **bash**, nel file `~/.bashrc` deve esserci una sezione come questa:

```bash
export PYENV_ROOT="$HOME/.pyenv"
[[ -d "$PYENV_ROOT/bin" ]] && export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init - bash)"
eval "$(pyenv virtualenv-init - bash)"
```

Il progetto utilizza **Python 3.12.12**

```bash
cd sportsdb/server

# installare python 3.12.12 con pyenv
pyenv install 3.12.12
# creare un virtualenv dedicato al progetto
pyenv virtualenv 3.12.12 sportsdb-3.12.12
# associare la cartella "server" del repo al virtualenv
pyenv local sportsdb-3.12.12
# aggiornare pip e installare le dipendenze richieste
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

## 4. Configurare le env vars

Nella root del repo serve un file `.env` usato da Docker Compose e dal Makefile.  

```bash
cp .env.example .env
```

Le variabili minime da controllare sono:

```env
POSTGRES_USER
POSTGRES_PASSWORD
PLATFORM_DB
DJANGO_SECRET_KEY
DEV_DOMAIN
```

I valori precisi possono essere adattati, ma il file deve esistere ed essere coerente.

> Per `DEV_DOMAIN`, `localtest.me` è comodo in locale perché risolve verso `127.0.0.1`.

## 5. Avviare lo stack Docker

> Da qualunque punto del filesystem del repo

```bash
mk up
# oppure in Windows
./mk up
# che corrisponde a
docker compose --env-file .env infra/docker-compose.dev.yml up -d --build
```

Lo stack deve includere almeno:

- reverse proxy
- database Postgres
- API platform

Più:

- [API vertical già installati]

Verificare:

- stato dei container
- log dei servizi
- salute del database

> Non basta che i container siano “up”: vanno controllati anche i log

## 6. Applicare le migrazioni Django

Su una macchina nuova bisogna eseguire le migrazioni dei servizi applicativi.

```bash
# default: SVC=platform
mk migrate
# oppure in Windows
./mk migrate
# altrimenti, per ogni [vertical]
mk migrate SVC=[vertical_slug]
```

## 7. Verificare gli endpoint locali

Controllare almeno questi endpoint:

- dashboard Traefik su `localhost:8080`
- host applicativo platform: `platform.<DEV_DOMAIN>`
- host applicativo per singolo vertical: `[vertical].<DEV_DOMAIN>`

Per singola app:

- admin: `[app].<DEV_DOMAIN>/admin`
- api docs: `[app].<DEV_DOMAIN>/api/docs`

Test base:

```bash
# default: EP=health
mk test-ep
# oppure in Windows
./mk test-ep
# altrimenti, per ogni [endpoint] disponibile
mk test-ep EP=[endpoint]
```

## 8. Testare l'ambiente per sviluppo locale

Per sviluppo locale, il codice modificato sul filesystem deve essere visibile correttamente nei container.  
Test minimo:

1. modificare un file del codice
2. controllare che il container veda la modifica
3. osservare i log o il comportamento dell’app

Se questo non funziona, l’ambiente non è adatto allo sviluppo iterativo.

### Test reale di sviluppo

Verifiche necessarie:

- test applicativi minimi `mk test-code`
- comando `mk manage ARGS=check` per ogni app
- controllo log
- piccola modifica di codice
- verifica del ciclo di sviluppo

## Conclusione

Per installare correttamente SPDB su una nuova macchina serve soprattutto coerenza dell’ambiente:

- filesystem giusto
- shell giusta
- Python giusto
- Docker giusto
- configurazione locale minima (`.env`, pyenv, migrazioni)
