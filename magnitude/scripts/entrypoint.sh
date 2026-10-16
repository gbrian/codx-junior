#!/usr/bin/env bash
# =============================================================================
# entrypoint.sh
#
# Container entrypoint used by the `magnitude` and `magnitude-test` services.
#
#   1. makes sure ~/.magnitude/config.json exists and enables network access
#      (needed so the server listens on all interfaces / other containers),
#   2. dispatches on the first argument:
#        serve  -> run the Magnitude server in the foreground (default)
#        test   -> run the built-in smoke test (scripts/run-test.sh)
#        <cmd>  -> execute <cmd> (e.g. `bash` for an interactive shell)
# =============================================================================
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
source "${HERE}/lib.sh"

MAGNITUDE_HOME="${MAGNITUDE_HOME:-$HOME}"
CONFIG_DIR="${MAGNITUDE_HOME}/.magnitude"
CONFIG_FILE="${CONFIG_DIR}/config.json"

mkdir -p "${CONFIG_DIR}"

# --- config.json --------------------------------------------------------------
# Created only on first start so that anything you change later is preserved.
# `allowedHosts` lets other containers reach the API by its compose service name.
if [[ ! -f "${CONFIG_FILE}" ]]; then
  cat > "${CONFIG_FILE}" <<JSON
{
  "network": {
    "enabled": ${MAGNITUDE_NETWORK_ENABLED:-true},
    "apiKey": "${MAGNITUDE_API_KEY:-mag_local_dev_key}",
    "allowedHosts": ["magnitude", "magnitude.local", "host.docker.internal"]
  }
}
JSON
  echo "Wrote ${CONFIG_FILE} (network access enabled, port ${MAGNITUDE_PORT:-10100})"
fi

MAG="$(resolve_magnitude)" || {
  echo "ERROR: the 'magnitude' CLI was not found in this image." >&2
  exit 1
}

case "${1:-serve}" in
  serve)
    shift || true
    # shellcheck disable=SC2086
    exec "${MAG}" serve ${MAGNITUDE_SERVE_ARGS:-} "$@"
    ;;
  test)
    exec bash "${HERE}/run-test.sh"
    ;;
  *)
    exec "$@"
    ;;
esac
