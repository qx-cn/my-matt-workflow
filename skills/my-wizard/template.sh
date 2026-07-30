#!/usr/bin/env bash
set -euo pipefail

TOTAL_STAGES=0
TOTAL_MINUTES=0
STAGE_INDEX=0
ENV_FILE="${ENV_FILE:-.env}"

stage() { STAGE_INDEX=$((STAGE_INDEX + 1)); printf '\n[%s/%s] %s\n' "$STAGE_INDEX" "$TOTAL_STAGES" "$1"; }
say() { printf '  %s\n' "$1"; }
open_url() { printf 'Open in your browser: %s\n' "$1"; }
confirm() { read -r -p "$1 [y/N] " reply; [[ "$reply" =~ ^[Yy]$ ]]; }
ask() { read -r -p "$2 " "$1"; }
ask_secret() { read -r -s -p "$2 " "$1"; printf '\n'; }

write_env() {
  local key="$1" value="$2" temporary
  confirm "Write $key to $ENV_FILE?" || return 0
  temporary=$(mktemp)
  { grep -vE "^${key}=" "$ENV_FILE" 2>/dev/null || true; printf '%s=%s\n' "$key" "$value"; } > "$temporary"
  mv "$temporary" "$ENV_FILE"
}

set_secret() {
  local name="$1" value="$2"
  say "GitHub Secret: $name. Purpose and rollback must be stated in this stage."
  confirm "Write GitHub Secret $name now?" || return 0
  printf '%s' "$value" | gh secret set "$name"
}

set_var() {
  local name="$1" value="$2"
  say "GitHub Variable: $name. Purpose and rollback must be stated in this stage."
  confirm "Write GitHub Variable $name now?" || return 0
  gh variable set "$name" --body "$value"
}

# Define approved stages below this line. Do not print secret values.
