#!/bin/bash
###############################################################################
# codx-junior-dind : optional Coolify installer
#
# This file is *sourced* by entrypoint-wrapper.sh from /custom-cont-init.d/
# AFTER the Docker daemon is up. It installs Coolify inside the DIND container
# so admins can deploy additional services through a UI instead of writing
# compose files by hand.
#
# Opt-in: it does nothing unless COOLIFY_ENABLED=true is set on the container.
#
# Environment variables:
#   COOLIFY_ENABLED           "true" to install/start Coolify (default: false)
#   COOLIFY_PROXY_HTTP_PORT   port for the Coolify proxy HTTP  (default: 8080)
#   COOLIFY_PROXY_HTTPS_PORT  port for the Coolify proxy HTTPS (default: 8443)
#   ROOT_USERNAME             optional pre-created admin username
#   ROOT_USER_EMAIL           optional pre-created admin email
#   ROOT_USER_PASSWORD        optional pre-created admin password
###############################################################################

# NOTE: this script is sourced (see entrypoint-wrapper.sh) and the wrapper runs
# with `set -e`. We therefore use `return` (never `exit`) and `set +e` so a
# Coolify failure can never tear down the container entrypoint.

if [ "${COOLIFY_ENABLED:-false}" != "true" ]; then
  echo "[coolify] disabled (set COOLIFY_ENABLED=true to install), skipping."
  return 0
fi

COOLIFY_PROXY_HTTP_PORT="${COOLIFY_PROXY_HTTP_PORT:-8080}"
COOLIFY_PROXY_HTTPS_PORT="${COOLIFY_PROXY_HTTPS_PORT:-8443}"
COOLIFY_SOURCE_DIR="/data/coolify/source"
COOLIFY_INSTALL_URL="https://cdn.coollabs.io/coolify/install.sh"

_install_coolify() {
  set +e

  echo "[coolify] installing prerequisites..."
  apk add --no-cache curl wget git jq openssl >/dev/null 2>&1 || true

  if docker ps --format '{{.Names}}' 2>/dev/null | grep -qx 'coolify'; then
    echo "[coolify] already running, skipping installation."
    return 0
  fi

  # Coolify deploys its own Traefik proxy bound to 80/443, which collides with
  # the codx-junior Traefik (also on 80/443). Remap Coolify's proxy so both can
  # coexist inside the same DIND daemon. docker-compose.custom.yaml is the
  # documented Coolify override mechanism, merged on install and upgrade.
  # NOTE: `!override` requires Docker Compose v2.24+.
  echo "[coolify] remapping Coolify proxy to ${COOLIFY_PROXY_HTTP_PORT}/${COOLIFY_PROXY_HTTPS_PORT}..."
  mkdir -p "${COOLIFY_SOURCE_DIR}"
  cat > "${COOLIFY_SOURCE_DIR}/docker-compose.custom.yaml" <<EOF
services:
  coolify-proxy:
    ports: !override
      - "${COOLIFY_PROXY_HTTP_PORT}:80"
      - "${COOLIFY_PROXY_HTTPS_PORT}:443"
EOF

  echo "[coolify] running the official installer..."
  local tmp_install
  tmp_install="$(mktemp)"
  if ! curl -fsSL "${COOLIFY_INSTALL_URL}" -o "${tmp_install}"; then
    echo "[coolify] could not download the installer, aborting."
    rm -f "${tmp_install}"
    return 1
  fi

  if [ -n "${ROOT_USERNAME:-}" ] && [ -n "${ROOT_USER_EMAIL:-}" ] && [ -n "${ROOT_USER_PASSWORD:-}" ]; then
    ROOT_USERNAME="${ROOT_USERNAME}" \
    ROOT_USER_EMAIL="${ROOT_USER_EMAIL}" \
    ROOT_USER_PASSWORD="${ROOT_USER_PASSWORD}" \
    bash "${tmp_install}"
  else
    bash "${tmp_install}"
  fi
  local rc=$?
  rm -f "${tmp_install}"

  echo "[coolify] install finished (rc=${rc}). Dashboard: http://<host>:${COOLIFY_PROXY_HTTP_PORT}"
  return ${rc}
}

# Never let a Coolify failure break the container initialization.
_install_coolify || echo "[coolify] installation failed, continuing boot (see output above)."

return 0