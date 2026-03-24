#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"

# Carica le variabili dal file .env (se esiste)
ENV_FILE="$ROOT/.env"
if [ -f "$ENV_FILE" ]; then
    set -a
    # shellcheck disable=SC1091
    source "$ENV_FILE"
    set +a
fi

make -s -C "$ROOT" "$@"
