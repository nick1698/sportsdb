#!/usr/bin/env bash

validate_vertical_key() {
  local key="$1"

  [[ -n "$key" ]] || error "Empty vertical key."
  [[ "$key" =~ ^[a-z0-9_]+$ ]] || error "Invalid key. Use only lowercase letters, numbers, underscore."
}