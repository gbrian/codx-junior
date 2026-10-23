#!/usr/bin/env bash
# =============================================================================
# test-model.sh
#
# Downloads the fastest (i.e. smallest) model Magnitude recommends for this
# machine and runs a single chat completion against the local server.
#
# Steps:
#   1. wait for the service (/health)
#   2. show the detected hardware      (magnitude hardware)
#   3. wait for the catalog assessment (magnitude catalog status)
#   4. list recommendations            (magnitude catalog recommendations)
#   5. download + load the model       (catalog pull / models load)
#   6. run one chat completion         (POST /inference/v1/chat/completions)
#
# Environment (all optional - see .env.example):
#   MAGNITUDE_URL          server base URL        (default http://127.0.0.1:10100)
#   MAGNITUDE_API_KEY      bearer key for the API (default empty -> no header)
#   MAGNITUDE_MODEL / MODEL_ID   explicit catalog model id (skips auto-pick)
#   MAGNITUDE_PREFERENCE   fastest|faster|balanced|smarter|smartest
#   MAGNITUDE_RECO_LIMIT   number of recommendations to show
#   MAGNITUDE_PROMPT       prompt for the completion
#   MAGNITUDE_MAX_TOKENS   max output tokens
# =============================================================================
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
source "${HERE}/lib.sh"

BASE_URL="${MAGNITUDE_URL:-http://127.0.0.1:${MAGNITUDE_PORT:-10100}}"
API_KEY="${MAGNITUDE_API_KEY:-}"
MODEL_ID="${MODEL_ID:-${MAGNITUDE_MODEL:-}}"
PREFERENCE="${MAGNITUDE_PREFERENCE:-fastest}"
LIMIT="${MAGNITUDE_RECO_LIMIT:-5}"
PROMPT="${MAGNITUDE_PROMPT:-In one sentence, what is an inference engine?}"
MAX_TOKENS="${MAGNITUDE_MAX_TOKENS:-128}"

header() { printf '\n\033[1;36m=== %s ===\033[0m\n' "$*"; }
info()   { printf '    %s\n' "$*"; }

curl_json() { # curl_json <path> [extra curl args...]
  local path="${1}"; shift
  local args=(-fsS -H 'Content-Type: application/json')
  [[ -n "${API_KEY}" ]] && args+=(-H "Authorization: Bearer ${API_KEY}")
  curl "${args[@]}" "$@" "${BASE_URL}${path}"
}

MAG="$(resolve_magnitude)" || {
  echo "ERROR: the 'magnitude' CLI was not found in this image." >&2
  exit 1
}

# --- 1/6 health ---------------------------------------------------------------
header "1/6 Service health (${BASE_URL})"
if wait_for_health "${BASE_URL}"; then
  info "service is up"
else
  echo "ERROR: ${BASE_URL}/health never became ready" >&2
  exit 1
fi

# --- 2/6 hardware -------------------------------------------------------------
header "2/6 Hardware detected by Magnitude"
"${MAG}" hardware || info "(magnitude hardware failed - continuing)"

# --- 3/6 catalog --------------------------------------------------------------
header "3/6 Catalog preparation"
for _ in $(seq 1 30); do
  status="$("${MAG}" catalog status 2>&1 || true)"
  info "${status}"
  grep -qiE 'ready|prepared|complete|done' <<<"${status}" && break
  sleep 10
done

# --- 4/6 pick a small model ---------------------------------------------------
header "4/6 Model recommendations (--preference ${PREFERENCE})"
recos="$("${MAG}" catalog recommendations --preference "${PREFERENCE}" --limit "${LIMIT}" 2>&1 || true)"
printf '%s\n' "${recos}"

if [[ -z "${MODEL_ID}" ]]; then
  # catalog ids are usually HuggingFace-style ("owner/name"); take the first one
  MODEL_ID="$(grep -oE '[A-Za-z0-9][A-Za-z0-9._-]*\/[A-Za-z0-9][A-Za-z0-9._-]*' <<<"${recos}" | head -n1 || true)"
fi

if [[ -z "${MODEL_ID}" ]]; then
  cat >&2 <<MSG

ERROR: no model id could be determined automatically.

Pick a small model from the recommendation list printed above and re-run with:

    MODEL_ID="<catalog-model-id>" bash ${BASH_SOURCE[0]}

or set MAGNITUDE_MODEL=<catalog-model-id> in .env and run 'make test' again.
MSG
  exit 2
fi
info "selected model: ${MODEL_ID}"

# --- 5/6 download + load ------------------------------------------------------
header "5/6 Downloading ${MODEL_ID} (this can take a while)"
"${MAG}" catalog pull "${MODEL_ID}" || info "(catalog pull reported an issue - continuing)"

for _ in $(seq 1 180); do
  status="$("${MAG}" models status "${MODEL_ID}" 2>&1 || true)"
  info "${status}"
  grep -qiE 'downloaded|installed|ready|100 ?%' <<<"${status}" && break
  sleep 10
done

info "loading into memory"
"${MAG}" models load "${MODEL_ID}" \
  || info "(models load reported an issue - the first request will load it on demand)"

# --- 6/6 inference ------------------------------------------------------------
header "6/6 Chat completion"
body="$(jq -nc --arg m "${MODEL_ID}" --arg p "${PROMPT}" --argjson mx "${MAX_TOKENS}" \
  '{model:$m, messages:[{role:"user", content:$p}], max_tokens:$mx}')"

start="$(date +%s.%N)"
response="$(curl_json '/inference/v1/chat/completions' -d "${body}" 2>&1)"
curl_rc=$?
end="$(date +%s.%N)"

if [[ ${curl_rc} -ne 0 ]]; then
  echo "ERROR: request to ${BASE_URL}/inference/v1/chat/completions failed:" >&2
  printf '%s\n' "${response}" >&2
  exit 1
fi

printf '\n--- answer ---\n%s\n' "$(jq -r '.choices[0].message.content // "(no content)"' <<<"${response}")"
printf '\n--- usage ---\n%s\n' "$(jq -c '.usage // {}' <<<"${response}")"

completion_tokens="$(jq -r '.usage.completion_tokens // empty' <<<"${response}")"
elapsed="$(awk -v s="${start}" -v e="${end}" 'BEGIN{ printf "%.2f", e - s }')"
printf '\nwall clock: %ss\n' "${elapsed}"
if [[ -n "${completion_tokens}" ]]; then
  awk -v t="${completion_tokens}" -v s="${elapsed}" \
    'BEGIN{ if (s > 0) printf "approx. %.2f output tokens/s\n", t / s }'
fi

header "Done"
info "model '${MODEL_ID}' was downloaded and served successfully."
