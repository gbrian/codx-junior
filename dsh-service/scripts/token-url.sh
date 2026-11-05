#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

logs="$(docker compose logs --no-color --no-log-prefix --tail 1000 dsh 2>/dev/null || true)"
url="$(printf '%s\n' "$logs" \
  | grep -oE 'https?://[^[:space:]]*[?&]token=[A-Za-z0-9_-]+' \
  | tail -n 1 || true)"

if [[ -z "$url" ]]; then
  cat >&2 <<'EOF'
No tokenized URL found in the dsh container logs.

The URL is printed once per process, after DSH is ready. Try:
  docker compose logs dsh
  docker compose ps
EOF
  exit 1
fi

printf '%s\n' "$url"
