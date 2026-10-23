#!/usr/bin/env bash
# =============================================================================
# run-test.sh
#
# One-shot container task: start `magnitude serve` in the background, run the
# model smoke test against it, then stop the server.
#
# Used by:  docker compose run --rm magnitude-test
# =============================================================================
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
source "${HERE}/lib.sh"

MAG="$(resolve_magnitude)" || {
  echo "ERROR: the 'magnitude' CLI was not found in this image." >&2
  exit 1
}

echo "Starting '${MAG} serve' in the background ..."
"${MAG}" serve &
SERVE_PID=$!

cleanup() {
  echo "Stopping Magnitude server (pid ${SERVE_PID}) ..."
  kill "${SERVE_PID}" 2>/dev/null || true
  wait "${SERVE_PID}" 2>/dev/null || true
}
trap cleanup EXIT

# test-model.sh waits for /health itself; this is just a head start.
sleep 2

bash "${HERE}/test-model.sh"
rc=$?

exit "${rc}"
