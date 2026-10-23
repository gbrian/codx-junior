#!/bin/bash
###############################################################################
# codx-junior-dind : optional Coolify installer
#
# Sourced by entrypoint-wrapper.sh from /custom-cont-init.d/ AFTER dockerd is up.
# Installs Coolify *inside* the DIND so admins can deploy extra services via a UI.
#
# Design decisions:
#   - Opt-in: no-op unless COOLIFY_ENABLED=true.
#   - Coolify ports are NOT published. The dashboard is exposed through the
#     codx-junior Traefik instance (same docker daemon) using router labels.
#   - The official Coolify installer is used unchanged; we only provide an
#     override file (/data/coolify/source/docker-compose.custom.yml) which is the
#     documented hook reused by Coolify's own upgrade.sh, so upgrades are safe.
#
# Environment variables:
#   COOLIFY_ENABLED             "true" to install/start Coolify (default: false)
#   COOLIFY_APP_URL             Public URL stored as Coolify APP_URL (optional)
#   COOLIFY_PATH_PREFIX         Traefik PathPrefix for the dashboard (default: /coolify)
#   COOLIFY_TRAEFIK_NETWORK     codx-junior Traefik network (auto-detected if unset)
#   COOLIFY_TRAEFIK_ENTRYPOINT  Traefik entrypoint (default: web)
#   COOLIFY_TRAEFIK_MIDDLEWARE  Auth middleware name (default: codx-junior-auth)
#   ROOT_USERNAME / ROOT_USER_EMAIL / ROOT_USER_PASSWORD  Pre-created admin
###############################################################################

# Sourced by entrypoint-wrapper.sh, which runs with `set -e`.
if [ "${COOLIFY_ENABLED:-false}" != "true" ]; then
  echo "[coolify] disabled (set COOLIFY_ENABLED=true to enable), skipping."
  return 0
fi

# Everything below runs in a subshell: lets us disable `set -e` locally without
# leaking shell options into the wrapper, and use `exit` instead of `return`.
(
  set +e

  COOLIFY_SOURCE_DIR="/data/coolify/source"
  COOLIFY_ENV_FILE="${COOLIFY_SOURCE_DIR}/.env"
  COOLIFY_COMPOSE_OVERRIDE="${COOLIFY_SOURCE_DIR}/docker-compose.custom.yml"
  COOLIFY_INSTALL_URL="https://cdn.coollabs.io/coolify/install.sh"

  COOLIFY_APP_URL="${COOLIFY_APP_URL:-}"
  COOLIFY_PATH_PREFIX="${COOLIFY_PATH_PREFIX:-/coolify}"
  COOLIFY_TRAEFIK_NETWORK="${COOLIFY_TRAEFIK_NETWORK:-}"
  COOLIFY_TRAEFIK_ENTRYPOINT="${COOLIFY_TRAEFIK_ENTRYPOINT:-web}"
  COOLIFY_TRAEFIK_MIDDLEWARE="${COOLIFY_TRAEFIK_MIDDLEWARE:-codx-junior-auth}"

  # ---------------------------------------------------------------------------
  # SSH server (Coolify manages its "localhost" server over SSH)
  # ---------------------------------------------------------------------------
  _start_sshd() {
    ssh-keygen -A >/dev/null 2>&1
    if ! grep -qE '^[[:space:]]*PermitRootLogin' /etc/ssh/sshd_config 2>/dev/null; then
      echo 'PermitRootLogin prohibit-password' >> /etc/ssh/sshd_config
    fi
    if pgrep -x sshd >/dev/null 2>&1; then
      echo "[coolify] sshd already running."
      return 0
    fi
    if command -v rc-service >/dev/null 2>&1; then
      rc-service sshd start >/dev/null 2>&1
    elif command -v service >/dev/null 2>&1; then
      service sshd start >/dev/null 2>&1
    fi
    pgrep -x sshd >/dev/null 2>&1 || /usr/sbin/sshd >/dev/null 2>&1
    if pgrep -x sshd >/dev/null 2>&1; then
      echo "[coolify] sshd is running (Coolify can manage the localhost server)."
    else
      echo "[coolify] WARNING: could not start sshd; Coolify may not manage the localhost server."
    fi
  }

  # ---------------------------------------------------------------------------
  # Prevent the installer from restarting docker (the DIND owns dockerd)
  # ---------------------------------------------------------------------------
  _seed_daemon_json() {
    # The installer (re)writes /etc/docker/daemon.json and then restarts the
    # docker service, which is impossible inside the DIND (dockerd is started by
    # entrypoint-wrapper.sh; there is no service manager). Seeding the file with
    # the exact default pool makes the installer treat it as unchanged and skip
    # the restart entirely.
    if [ -f /etc/docker/daemon.json ]; then
      echo "[coolify] /etc/docker/daemon.json exists, leaving it untouched."
      return 0
    fi
    mkdir -p /etc/docker
    cat > /etc/docker/daemon.json <<'JSON'
{
  "default-address-pools": [
    { "base": "10.0.0.0/8", "size": 24 }
  ]
}
JSON
    echo "[coolify] seeded /etc/docker/daemon.json with default address pools."
  }

  # ---------------------------------------------------------------------------
  # Detect the network the codx-junior Traefik container is attached to
  # ---------------------------------------------------------------------------
  _detect_traefik_network() {
    local cid nets net
    cid="$(docker ps --format '{{.ID}} {{.Names}}' 2>/dev/null | grep -i traefik | head -n1 | awk '{print $1}')"
    [ -z "${cid}" ] && return 0
    nets="$(docker inspect -f '{{range $k,$v := .NetworkSettings.Networks}}{{$k}} {{end}}' "${cid}" 2>/dev/null)"
    net="$(echo "${nets}" | tr ' ' '\n' | grep -Ei 'codx|junior|traefik|proxy' | head -n1)"
    [ -z "${net}" ] && net="$(echo "${nets}" | awk '{print $1}')"
    echo "${net}"
  }

  # ---------------------------------------------------------------------------
  # Compose override: no published ports + Traefik routing labels
  # ---------------------------------------------------------------------------
  _write_compose_override() {
    {
      printf '%s\n' \
        '# Managed by codx-junior (coolify-install.sh). Regenerated on every boot.' \
        '# Purpose: do NOT publish Coolify ports; route the dashboard through the' \
        '# codx-junior Traefik instance (same docker daemon) via router labels.' \
        'services:' \
        '  coolify:' \
        '    ports: !reset []' \
        '    labels:' \
        '      - "traefik.enable=true"' \
        "      - \"traefik.http.routers.coolify.rule=PathPrefix(\`${COOLIFY_PATH_PREFIX}\`)\"" \
        "      - \"traefik.http.routers.coolify.entrypoints=${COOLIFY_TRAEFIK_ENTRYPOINT}\"" \
        '      - "traefik.http.routers.coolify.service=coolify"' \
        '      - "traefik.http.services.coolify.loadbalancer.server.port=8080"' \
        "      - \"traefik.http.middlewares.coolify-strip.replacepathregex.regex=^${COOLIFY_PATH_PREFIX}/(.*)\"" \
        '      - "traefik.http.middlewares.coolify-strip.replacepathregex.replacement=/$$1"' \
        "      - \"traefik.http.routers.coolify.middlewares=coolify-strip,${COOLIFY_TRAEFIK_MIDDLEWARE}\""
      if [ -n "${COOLIFY_TRAEFIK_NETWORK}" ]; then
        printf '%s\n' \
          "      - \"traefik.docker.network=${COOLIFY_TRAEFIK_NETWORK}\"" \
          '    networks:' \
          '      coolify: {}' \
          "      ${COOLIFY_TRAEFIK_NETWORK}:" \
          '        aliases:' \
          '          - coolify' \
          '          - coolify-realtime' \
          'networks:' \
          "  ${COOLIFY_TRAEFIK_NETWORK}:" \
          '    external: true'
      fi
    } > "${COOLIFY_COMPOSE_OVERRIDE}"
    echo "[coolify] wrote compose override ${COOLIFY_COMPOSE_OVERRIDE}"
  }

  # ---------------------------------------------------------------------------
  # Install Coolify (official installer)
  # ---------------------------------------------------------------------------
  _run_installer() {
    mkdir -p "${COOLIFY_SOURCE_DIR}"

    # Pre-set APP_URL so path-prefix routing works during onboarding.
    # (install.sh merges only the first occurrence of each key, so ours wins.)
    if [ -n "${COOLIFY_APP_URL}" ]; then
      touch "${COOLIFY_ENV_FILE}"
      if grep -q '^APP_URL=' "${COOLIFY_ENV_FILE}"; then
        sed -i "s|^APP_URL=.*|APP_URL=${COOLIFY_APP_URL}|" "${COOLIFY_ENV_FILE}"
      else
        printf 'APP_URL=%s\n' "${COOLIFY_APP_URL}" >> "${COOLIFY_ENV_FILE}"
      fi
    fi

    local tmp_install
    tmp_install="$(mktemp)"
    if ! curl -fsSL "${COOLIFY_INSTALL_URL}" -o "${tmp_install}"; then
      echo "[coolify] could not download the installer, aborting."
      rm -f "${tmp_install}"
      return 1
    fi

    echo "[coolify] running the official installer..."
    ROOT_USERNAME="${ROOT_USERNAME:-}" \
    ROOT_USER_EMAIL="${ROOT_USER_EMAIL:-}" \
    ROOT_USER_PASSWORD="${ROOT_USER_PASSWORD:-}" \
      bash "${tmp_install}"
    local rc=$?
    rm -f "${tmp_install}"
    return ${rc}
  }

  # ---------------------------------------------------------------------------
  # Ensure the Coolify stack is running
  # ---------------------------------------------------------------------------
  _ensure_stack() {
    if docker ps --format '{{.Names}}' 2>/dev/null | grep -qx 'coolify'; then
      echo "[coolify] stack already running."
      return 0
    fi
    local compose_files
    compose_files="-f ${COOLIFY_SOURCE_DIR}/docker-compose.yml -f ${COOLIFY_SOURCE_DIR}/docker-compose.prod.yml"
    [ -f "${COOLIFY_COMPOSE_OVERRIDE}" ] && compose_files="${compose_files} -f ${COOLIFY_COMPOSE_OVERRIDE}"
    echo "[coolify] starting the Coolify stack..."
    # shellcheck disable=SC2086
    docker compose --env-file "${COOLIFY_ENV_FILE}" ${compose_files} up -d --remove-orphans
  }

  # ---------------------------------------------------------------------------
  # Main
  # ---------------------------------------------------------------------------
  if docker ps --format '{{.Names}}' 2>/dev/null | grep -qx 'coolify'; then
    echo "[coolify] already installed and running, skipping installation."
    _start_sshd
    exit 0
  fi

  # Reuse the codx-junior Traefik network when not explicitly provided.
  if [ -z "${COOLIFY_TRAEFIK_NETWORK}" ]; then
    COOLIFY_TRAEFIK_NETWORK="$(_detect_traefik_network)"
  fi
  if [ -n "${COOLIFY_TRAEFIK_NETWORK}" ]; then
    echo "[coolify] routing through Traefik network '${COOLIFY_TRAEFIK_NETWORK}' at prefix '${COOLIFY_PATH_PREFIX}'."
  else
    echo "[coolify] WARNING: no Traefik network detected; the dashboard will not be reachable until COOLIFY_TRAEFIK_NETWORK is set."
  fi

  _start_sshd
  _seed_daemon_json
  _write_compose_override

  if _run_installer; then
    echo "[coolify] installer finished successfully."
  else
    echo "[coolify] installer failed; attempting to start the stack directly..."
  fi

  _ensure_stack
  echo "[coolify] dashboard exposed through codx-junior Traefik at ${COOLIFY_PATH_PREFIX}"

  exit 0
)

return 0