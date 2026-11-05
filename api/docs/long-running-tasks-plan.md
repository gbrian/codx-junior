# Long running tasks — execution plan (LRT‑1)

> Owner: ProjectManager · Implementation: `software_developer` / `py_senior` / `py_test`
> Design contract: [`docs/long-running-tasks.md`](long-running-tasks.md) — this file only says **who does what, in which order, and how we call it done**.

#TL; DR;

LRT‑0 (preparation) is **mostly** in the repository, but three items are still open (see §1). The work for milestone **LRT‑1 (run skeleton)** is sliced into five work packages, each with one owner and a verifiable acceptance list. They are sequential: **WP1 → WP2 → WP3 → WP5**, with WP0 (cleanup) first because the runner depends on the agent loop being gone.

---

## 1. State of LRT‑0 (verified on disk)

| # | Item | State | Evidence |
|---|---|---|---|
| 0.1 | `codx/junior/kanban` importable | **done** | `__init__.py` resolves names lazily, no `board_status_review` |
| 0.2 | Kanban storage v2 + migration + lock | **done** | `codx/junior/kanban/{model,store}.py`, `codx/junior/migrations/kanban_v1_to_v2.py` |
| 0.3 | `Chat.root_id` + `identity` | **done** | `db.Chat.root_id`, `codx/junior/identity.py`, `TaskManager.create_task` stamps it |
| 0.4 | Cost roll‑up to the root chat | **done** | `ChatManager._accumulate_message_cost` → `_roll_up_cost_to_root` |
| 0.8 | `find_by_id` exact match | **done** | matches `.<chat_id>.json` suffix |
| 0.5 | Remove `AGENT_DONE_WORD` + agent loop | **OPEN** | still defined in `globals.py`, still used in `chat/chat_engine.py` |
| 0.6 | Remove dead `generate_tasks` | **OPEN** | `engine/chat_engine_actions.py`, sio `codx-junior-subtasks`, `app.py` route |
| 0.9 | De‑duplicate startup hook and routes | **OPEN** | two `on_event("startup")`, legacy duplicated `/api/chats` + `/api/kanban`, mark‑seen twice |

Everything else in LRT‑0 can be considered closed.

---

## 2. Work packages

| WP | Deliverable | Owner (profile) | Depends on | Deployable | Demoable |
|---|---|---|---|---|---|
| **WP0** | Agent loop + dead sub‑task generation removed, routes de‑duplicated | software_developer | — | yes | yes (chat works, `grep` evidence) |
| **WP1** | `Chat.run` / `run_status` / `run_state` + `long_running/{models,store,service}.py` | software_developer + model | WP0 | yes (inert) | via API of WP3 |
| **WP2** | `long_running/runner.py` tick + worker in `background.py` | software_developer + py_senior | WP1 | yes | yes (kill/restart resumes) |
| **WP3** | `api/long_running.py`, `tools/long_running_tools.py`, `profiles/long_running.profile` | software_developer | WP1, WP2 | yes | yes (start a run from the API) |
| **WP4** | Tests (offline) + 5‑minute demo script | py_test + software_developer | WP1–WP3 | yes | yes |

### WP0 — cleanup (blocking)
Remove `AGENT_DONE_WORD`, the `is_agent` recursion/headers/refine prompt, `append_agent_message`, `CHAT_MODE_AGENT`, `get_agent_max_iterations`; remove `ChatEngineActions.generate_tasks`, `CODXJuniorSession.generate_tasks`, the `codx-junior-subtasks` sio handler and every `/api/chats/sub-tasks` call site; one `on_event("startup")`, one mark‑seen route.
**Done when:** `grep -rn AGENT_DONE_WORD codx/` empty, `grep -rn generate_tasks codx/` only docstrings, imports of the engine modules succeed, `mode="agent"` answers once.

### WP1 — run model, store and service
`Chat.run` (config), `Chat.run_status`, `Chat.run_state` (attempts, current task, ticks, stagnation, stop reason, finished); `LongRunStatus` + progress models; `RunLock` (`.codx/tasks/long_running/<main_task_id>.lock`, `O_CREAT|O_EXCL`, heartbeat, stale takeover); `LongRunningService.start/pause/resume/stop/status/list`, budget aggregated from `Chat.cost` of every chat whose `root_id` is the main task, task counts from `planning_manager` constants only.
**Done when:** imports clean, lock is exclusive and takeable after a stale heartbeat, `start` creates board + main task with `estimation_cost == budget`, `status.spent` equals the sum of chat costs.

### WP2 — runner + worker
One tick: lock → reload main task from disk → `run_status == running` → budget admission (`remaining <= supervisor_reserve` → `budget_exhausted` + template report) → pick one actionable task (`root_id` match, attempts < 3) → `estimation_cost = min(per_task_budget, remaining - reserve)` → `chat_with_project` → persist state/heartbeat; supervisor turn on the main task when there is nothing actionable; stagnation at 3 no‑progress turns → `stalled`. Worker: `check_long_running_runs()` in `background.py`, background process only, 5s interval.
**Done when:** two workers never double‑process, a restart resumes without a click, pause/stop are honoured before and during a turn, the run never spends above `budget`.

### WP3 — API, tool, prompt
REST router (list / create-or-attach / detail / pause / resume / stop / tick) following the project conventions (`project_id` as query param, bodies resource‑only, nothing long inside the 30s request); `long_running` tool (`start`, `status`, `finish`, `add_task` with `finish` validated server‑side); supervisor profile content.
**Done when:** list/detail answer with the worker off (`worker_present: false`), `finish` from a foreign chat is rejected, the tool is registered in `TOOLS`.

### WP4 — tests + demo
Offline pytest coverage (lock, ancestry, budget admission, service transitions, recovery, stagnation) and a one‑screen `docs/long-running-tasks-demo.md`.
**Done when:** `pytest -k run_` green offline in < 30s and every demo step has a visible expected result.

---

## 3. Critical path

```
WP0 → WP1 → WP2 → WP3 → WP4
```

WP4 can start its lock/ancestry/budget tests as soon as WP1 lands.

## 4. Decisions still open (defaults applied if nobody answers)

1. **Budget unit** — cxjcoins via `estimation_cost` / `cost` (**default**).
2. **Concurrency per run** — one task turn at a time (**default**).
3. **Run state** — on the main task (`run` / `run_status` / `run_state`) + lock file (**default**).
4. **Manual turns on a paused descendant** — allowed and budgeted (**default**).

## 5. Board location note

The cards for WP0–WP4 were created from a chat whose owning project is the **root `codx-junior` project**, so they were persisted in that project's `.codx/tasks/Engine/To Do` and are **not visible from the `codx-api` project board**. Drive them from the root project, or re‑create them as described in the chat report.

## 6. Next checkpoint

**Demo after LRT‑1** (to be run once WP1–WP3 are deployed):

1. `POST /api/long-running` with a tiny objective → board + main task appear.
2. The worker splits 2–3 tasks; the first completes.
3. Kill the background process mid‑run, restart → the run continues alone.
4. `pause` → nothing moves; `resume` → it moves; `stop` → the in‑flight turn is cancelled.
5. Force `budget_exhausted` → the delivery report is written without an extra paid turn.
