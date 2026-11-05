#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

user="${1:-admin}"

if [[ ! -f .env ]]; then
  printf '.env not found; copy .env.example to .env first.\n' >&2
  exit 1
fi

if [[ -t 0 ]]; then
  read -r -s -p "Password for ${user}: " password
  printf '\n'
else
  IFS= read -r password || true
fi

if [[ -z "${password:-}" ]]; then
  printf 'Password must not be empty.\n' >&2
  exit 1
fi

# htpasswd -i reads the password from stdin so it never appears in `ps`.
# Traefik accepts the resulting bcrypt hash in a label; no file mount into the
# Traefik container is needed.
entry="$(
  printf '%s\n' "$password" \
    | docker run --rm -i httpd:2.4-alpine htpasswd -inB "$user" \
    | awk 'NF { print; exit }'
)"
if [[ -z "$entry" ]]; then
  printf 'htpasswd did not produce a hash.\n' >&2
  exit 1
fi

# Compose interpolates $ in .env, so double every dollar of the bcrypt hash.
escaped="${entry//\$/\$\$}"
line="DSH_BASIC_AUTH_USERS=${escaped}"

tmp="$(mktemp "${TMPDIR:-/tmp}/dsh-env.XXXXXX")"
trap 'rm -f "$tmp"' EXIT

awk -v line="$line" '
  BEGIN { replaced = 0 }
  /^DSH_BASIC_AUTH_USERS=/ { print line; replaced = 1; next }
  { print }
  END { if (!replaced) print line }
' .env > "$tmp"

chmod 600 "$tmp"
mv "$tmp" .env

printf 'Wrote DSH_BASIC_AUTH_USERS to .env for user %s.\n' "$user"
printf 'Start with: docker compose -f docker-compose.yml -f compose.auth.yml up -d\n'
