#!/usr/bin/env bash
# =============================================================================
# lib.sh - shared helpers for the Magnitude docker test harness.
# Sourced by entrypoint.sh, run-test.sh and test-model.sh.
# =============================================================================

# Locate the `magnitude` CLI.  The .deb normally puts it on PATH; we also probe
# a few common locations so the container keeps working across package layouts.
resolve_magnitude() {
  if command -v magnitude >/dev/null 2>&1; then
    command -v magnitude
    return 0
  fi

  local candidate
  for candidate in \
      "${MAGNITUDE_HOME:-$HOME}/.local/bin/magnitude" \
      /usr/bin/magnitude \
      /usr/local/bin/magnitude \
      /opt/magnitude/magnitude \
      /opt/Magnitude/magnitude \
      /opt/magnitude-desktop/magnitude; do
    if [[ -x "${candidate}" ]]; then
      printf '%s\n' "${candidate}"
      return 0
    fi
  done

  return 1
}

# wait_for_health <base-url>
# Polls <base-url>/health until it answers or the retry budget is exhausted.
wait_for_health() {
  local base="${1}"
  local retries="${MAGNITUDE_HEALTH_RETRIES:-60}"
  local i

  for i in $(seq 1 "${retries}"); do
    if curl -fsS "${base}/health" >/dev/null 2>&1; then
      return 0
    fi
    sleep 2
  done

  echo "ERROR: ${base}/health did not become ready after $((retries * 2))s" >&2
  return 1
}
