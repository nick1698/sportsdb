#!/usr/bin/env bash

info() {
  echo "[INFO] $*"
}

warn() {
  echo "[WARN] $*" >&2
}

error() {
  echo "[ERROR] $*" >&2
  exit 1
}

confirm_or_exit() {
  local prompt="${1:-Proceed? [y/N]: }"
  local reply
  read -r -p "$prompt" reply
  [[ "${reply:-}" =~ ^[Yy]$ ]] || error "Aborted."
}

pause() {
  read -r -p "${1:-Press Enter to continue...} "
}