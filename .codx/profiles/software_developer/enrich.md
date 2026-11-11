## Local dev stack: API does not hot-reload Python

The local codx-junior stack runs the API **without** `--reload` (`scripts/run_api.sh`: DEBUG=1 only raises logging; `CODX_JUNIOR_API_RELOAD=1` is needed for reload). The client container (`codx-junior-client`, vite dev) **does** hot-reload, so UI changes appear immediately while backend changes stay inactive until the API is restarted.

- Backend edits need: `docker restart codx-junior-api codx-junior-api-background`.
- The agent runs **inside** `codx-junior-api`, so never restart it during a turn; ask the user or note it.
- Verify a new query param is loaded without auth: call it with an invalid bool, e.g. `/api/git/repo/validate/context?staged=notabool`. `422` = param exists in the loaded route, `400` ("CODXJuniorSession not found") = param unknown → stale code.
- The client container mounts `/home/codx-junior/codx-junior`; it serves the same tree as the project (`/home/codx-junior-projects/codx-junior`), so a running client does not prove the API has the change.
