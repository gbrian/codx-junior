#!/usr/bin/env bash
set -Eeuo pipefail

# Entrypoint for the dsh web service. DSH refuses wildcard bind addresses, so
# the container resolves its own (single) non-loopback address unless the
# operator supplied DSH_HOST. The address is exported for the healthcheck and
# for debugging; the same value must remain stable for the life of the process.
: "${DSH_HOME:=/home/dsh/.dsh}"
: "${DSH_PORT:=3080}"
: "${DSH_HOST:=}"
: "${DSH_PUBLIC_URL:=}"
: "${DSH_TRUSTED_HOSTS:=}"

export DSH_HOME DSH_PORT DSH_HOST

log() {
  printf 'dsh-entrypoint: %s\n' "$*" >&2
}

mkdir -p "$DSH_HOME"
chmod 700 "$DSH_HOME" 2>/dev/null || true

if [[ -z "$DSH_HOST" ]]; then
  if ! DSH_HOST="$(
    node -e '
      const os = require("node:os");
      const addrs = Object.values(os.networkInterfaces()).flat().filter(Boolean);
      const pick =
        addrs.find((a) => !a.internal && a.family === "IPv4") ??
        addrs.find((a) => !a.internal && a.family === "IPv6");
      if (!pick) process.exit(1);
      process.stdout.write(pick.address);
    '
  )"; then
    log "could not determine a non-loopback address; set DSH_HOST to one concrete local IP"
    exit 1
  fi
fi

if [[ -z "$DSH_HOST" ]]; then
  log "DSH_HOST resolved empty; refusing to start"
  exit 1
fi

args=(--profile web --no-open --port "$DSH_PORT" --host "$DSH_HOST")

if [[ -n "$DSH_PUBLIC_URL" ]]; then
  args+=(--public-url "$DSH_PUBLIC_URL")
fi

if [[ -n "$DSH_TRUSTED_HOSTS" ]]; then
  read -r -a trusted_hosts <<< "${DSH_TRUSTED_HOSTS//,/ }"
  for authority in "${trusted_hosts[@]}"; do
    [[ -z "$authority" ]] && continue
    args+=(--trusted-host "$authority")
  done
fi

log "starting dsh ${DSH_VERSION:-} web on ${DSH_HOST}:${DSH_PORT}"
if [[ -n "$DSH_PUBLIC_URL" ]]; then
  log "advertised public URL: ${DSH_PUBLIC_URL}"
fi
if [[ -n "$DSH_TRUSTED_HOSTS" ]]; then
  log "trusted authorities: ${DSH_TRUSTED_HOSTS}"
fi

exec dsh "${args[@]}" "$@"
