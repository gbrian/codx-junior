# codx-junior harness — the @codx-junior profile

> **Status:** implemented · **Profile:** `codx-junior` (built-in) ·
> **Code:** `api/codx/junior/harness/`, `api/codx/junior/orchestration/` ·
> **API:** `/api/harness/*`, `/api/orchestration` ·
> **UI:** Harness app (sidebar → *Harness*)

The **codx-junior harness** is the native, self-contained way to hand a whole
task to the platform and get notified when it is done. It is modeled on how a
modern AI harness works (durable runs, background workers, notifications,
audit trail) but it is built entirely inside codx-junior: no external harness,
no bridge, nothing to install.

## The @codx-junior profile

`codx-junior` is a **built-in profile** — the main contact between the user and
every other profile and capability of the platform. It is granted **all tools**
(the profile allowlist contains the `*` marker, expanded to the whole tool
registry at request time) and its `team` lists the profiles it can put to work:
`software_developer`, `analyst`, `reviewer`, `TaskManager`, `ProjectManager`,
`devops`, `repository`, `web_master`, `workspace`, `browser`, `wiki`,
`teacher` and `support`.

### Give it a task

1. Open any chat and write `@codx-junior <your task>`.
2. The harness profile registers the request (audited as `task_requested`) and
   decides how to run it:
   - quick, independent questions are answered directly or through a `delegate`
     card,
   - everything non-trivial becomes a **run** via
     `orchestrator(action="start")` with `profiles=["codx-junior"]`, so the
     harness profile itself supervises the work.
3. The background worker plans the steps and executes them **in parallel,
   isolated task cards**, each with the best profile for the job.
4. The user can watch every card live on the board and in the run sprint.
5. When the run finishes (or fails/stops/burns its budget), codx-junior
   publishes the **delivery report on the task** and sends the user a
   **notification**: *"Run X finished (completed). The delivery report is on
   the task."* The notification is sent exactly once per terminal status, even
   across worker restarts.

## Observability: navigate and review everything

- **Every step is a task card.** Open a card to read the worker conversation,
  move it, retry it or take over manually.
- **The run sprint** groups all the cards of a run by status.
- **The Harness app** (sidebar → *Harness*) shows, per project:
  - the worker heartbeat and watchdog state (restarts, incidents),
  - every run with status, progress, board/sprint, budget and a one-click
    *Open task* link to the run dashboard,
  - the full **audit journal** (see below), filterable by event type.

## Audit: all work is registered

Everything the harness does is appended to an immutable journal at
`<project>/.codx/harness/audit.jsonl` (one JSON object per line, atomic
appends):

| Event | Meaning |
| --- | --- |
| `task_requested` | the user gave `@codx-junior` a task (chat, user, request text) |
| `run_event` | every run transition: `run_created`, `run_started`, `step_started`, `step_finished`, `step_retried`, `run_completed`, `run_failed`, `run_stopped`, `run_budget_exhausted`, `run_stalled`, `report`, … with run id, status and message |
| `notification_sent` | the user was notified of a terminal status |
| `turn_resumed` / `turn_recovered` | an interrupted chat turn was resumed by the recovery worker (attempt n/m) and completed |
| `turn_failed` / `turn_cancelled` | an interrupted turn was given up after the retry bound (the user is notified), or stopped by the user |
| `worker_recovered` | the background worker (re)started and took over a project |
| `worker_stalled` | the watchdog detected a dead/wedged worker with active runs |
| `worker_restarted` / `worker_restart_failed` | supervision actions and their outcome |

The journal is read-only through the API (`GET /api/harness/audit`); writing
never raises, so auditing can never break the work it records.

## Restart: processes survive errors and interruptions

Three layers guarantee the harness comes back on its own:

1. **Durable state.** Runs, steps, budgets and reports are persisted on disk
   with atomic writes; run locks are OS `flock`s released on process death; the
   worker tick recovers steps whose owner died. A restart resumes in-flight
   work instead of losing it.
2. **Process supervision.** `supervisor.conf` (monolithic deployment) runs
   `codx-junior-api`, `codx-junior-api-background` and `codx-junior-client`
   with `autorestart=true` and bounded retries. The Docker Compose deployment
   runs the same three services with `restart: unless-stopped`.
3. **Harness watchdog.** Runs inside the API process and monitors the durable
   worker heartbeat: when a project has **active runs but no live worker**, it
   registers a `worker_stalled` audit entry, notifies connected users and
   restarts `codx-junior-api-background` (`supervisorctl` in the monolith,
   `docker restart` in Compose), with a per-project cooldown so a storm of
   restarts is impossible.

Environment switches: `CODX_JUNIOR_HARNESS_WATCHDOG` (on by default),
`CODX_JUNIOR_HARNESS_WATCHDOG_SECONDS`, `CODX_JUNIOR_HARNESS_WATCHDOG_STALE_SECONDS`,
`CODX_JUNIOR_HARNESS_WATCHDOG_RESTART`.

### Never let the API restart itself while it works

The API must not run with source reload on a server where the AI agents edit
the project: `uvicorn --reload` restarts the process on every file the agent
writes, which interrupts the in-flight turn it is itself executing (and the
recovery worker then has to retry it). Reload is therefore **opt-in**:
`CODX_JUNIOR_API_RELOAD=1` (development machines only). `DEBUG=1` only raises
verbosity. Restarts are owned by `supervisor.conf` / Docker `restart:
unless-stopped`, and interrupted turns are resumed by the recovery worker
(3 attempts, audited and notified).

## API

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/harness/audit?limit&offset&event` | read the audit journal (newest first) |
| `GET` | `/api/harness/status` | worker presence, active runs, watchdog state |
| `GET` | `/api/orchestration` | list runs (the Harness UI table) |
| `POST` | `/api/orchestration/{run_id}/tick` | wake the worker (admin) |

## Related docs

- [`orchestration.md`](../../api/docs/orchestration.md) — the board-native run
  runtime underneath the harness.
- [`profiles.md`](profiles.md) — how profiles and tool allowlists work.
