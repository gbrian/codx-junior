# Board-native orchestration — handoff summary

> **Purpose.** Self-contained summary of the objective, the work completed and
> the continuation points, so the task can resume in another workspace without
> this conversation.
>
> **Status:** merged into `v1.3-demo-site` · **Feature commit:** `54d98c7d`
> **Merge commit:** `c1aaca49` · **Tests:** 29 offline orchestration tests pass
> **Detailed design:** [`docs/orchestration.md`](orchestration.md)

---

## 1. Objective

Make **codx-junior** handle complex, multi-step tasks at the execution level of
DSH — plan, delegate to isolated agents, run independent work in parallel,
verify, continue across restarts — **without losing the existing visibility in
boards and sprints**.

The guiding constraint was that the work model must not be replaced:

* a chat is already a task, a conversation and a budget;
* boards group tasks by column;
* sprints group the same tasks by status;
* `root_id` anchors ancestry and cost rolls up to the root.

The implementation therefore adds an **orchestration runtime** on top of those
primitives. The run is anchored on a normal main task, every plan step is a
normal child task card, and the run is also a sprint.

---

## 2. Starting analysis

The relevant parts of the existing architecture were:

* **`SmolAgent`** (`api/codx/junior/ai/smol/smol_agent.py`) — iterative
  streaming tool loop with tool cache, loop guard, cancellation, dual-response
  tools and a hard per-chat budget. It runs in **one context** and executes tools
  sequentially.
* **`ChatEngine`** (`api/codx/junior/chat/chat_engine.py`) — one AI request per
  turn. Resolves mentions, files, profiles, model and tools; composes the prompt;
  handles RAG/vision/guardrails; persists tool/lifecycle events crash-safely.
* **Profiles and tools** — tools come from active profiles; two internal request
  headers (`profiles`, now also `orchestration`) are consumed by `SmolAgent` and
  stripped before the provider. Profile `team` only listed names in the prompt;
  the model could not actually execute them.
* **Work model** — `Chat` is the task; boards use `board`/`column`; sprint
  membership uses `sprints` and groups by `status`; `TaskManager` is the
  canonical task factory; kanban storage v2 is atomic and lock-protected.
* **Background process** — already exists for project watching; long work must
  run there, not in the API request path.

Gaps for complex work:

* one shared context for all tools;
* no persisted plan/dependency graph;
* no isolated subagents or parallel fan-out;
* no durable continuation or verification loop;
* no run-level budget split/reserve;
* `process_task(wait=True)` returned before the task turn completed;
* parallel cost roll-up had a lost-update race;
* auxiliary summary requests could receive tools/internal headers.

---

## 3. What was built

### 3.1 Execution model

```
Run = main task (dashboard) + persisted plan + step cards + run sprint
```

* **Main task** — objective, budget (`Chat.estimation_cost`), supervisor
  profile, `run_id`/`run_status`, delivery report. Must be a **root task**.
* **Plan** — `RunState.steps[]` with `objective`, `acceptance`, `profile`,
  `depends_on`, `files`, `context`, `priority`, status, attempts and structured
  result.
* **Step card** — a normal child `Chat` with `run_id`/`run_step_id`, its own
  conversation/context, `ignore_parent_knowledge=True` and
  `ignore_parent_files=True`. It is a real board card.
* **Run board** — default `Orchestration`, columns
  `Backlog` / `In progress` / `Done` / `Blocked`.
* **Run sprint** — default `Run: <name>`, columns `To do` / `Doing` /
  `On hold` / `Done`; it is the same cards grouped by `Chat.status`.
* **Run document** — `.codx/orchestration/runs/<run_id>.json`, the source of
  truth for plan/results/rounds/events. Written atomically; `flock` gives
  single-flight per run.
* **Worker heartbeat** — `.codx/orchestration/worker.json`; the API reports
  `worker.present`.

### 3.2 Runtime components

| File | Responsibility |
|---|---|
| `orchestration/models.py` | `RunState`, `RunConfig`, `PlanStep`, `StepResult`; plan validation, dependency graph, ready/blocked steps, result-contract parser, status mapping |
| `orchestration/store.py` | Atomic run JSON store, per-run `RunLock` (`flock`), list/load, worker heartbeat |
| `orchestration/board.py` | Ensures run board/sprint/columns; creates/updates step cards and main card via `TaskManager`/`ChatManager` |
| `orchestration/executor.py` | Runs one isolated `ChatEngine` turn, propagates cancellation, enforces timeout, parses the structured result, downgrades budget-stopped workers to `blocked` |
| `orchestration/service.py` | Create/attach/start/pause/resume/stop runs; plan upsert; retry/remove/archive steps; budget admission; tick/advance; supervisor rounds; finalization; delegation |
| `orchestration/worker.py` | Background loop, thread pool, per-project heartbeat, single-flight run lock |
| `orchestration/prompts.py` | Supervisor/worker prompts, bounded run-state rendering, delivery/budget/stall/stop/failure reports |
| `orchestration/constants.py` | Dependency-free shared constants (roles, statuses, columns, worker tools, env names) |
| `tools/orchestration_tools.py` | `orchestrator` and `delegate` tools |
| `api/orchestration.py` | REST surface |
| `utils/file_lock.py` | Cross-process lock helper used by the run store and cost roll-up |
| `profiles/orchestrator.profile` | Built-in supervisor role, team table and planning rules |

### 3.3 Tick / state machine

A tick:

1. returns if terminal/paused;
2. reloads the main task and refreshes `spent` from the root cost;
3. skips if the main task or a step card has a live manual turn;
4. enforces `remaining > supervisor_reserve` (otherwise `budget_exhausted`
   with a template report, no AI call);
5. recovers steps marked `running` whose worker disappeared (no live
   cancellation token);
6. dispatches ready steps in parallel (`max_parallel`) or runs a supervisor
   round (`plan`, `verify`, `replan`);
7. applies structured results, updates cards, refreshes cost;
8. verifies/replans or finishes.

Run states: `queued`, `running`, `paused`, `completed`, `stopped`, `failed`,
`budget_exhausted`, `stalled`.

`start` semantics (UI/API single action):

* active/queued → unchanged;
* paused/queued/stalled → resume;
* stopped/failed → reopen from the persisted plan (new `report_generation`);
* completed → refused;
* budget-exhausted → refused until `Chat.estimation_cost` is raised.

`stop` cancels the registered tokens; `pause` lets the in-flight turn finish;
`resume` continues paused/queued/stalled runs.

### 3.4 Parallelism and budget

* `max_parallel` default 2, max 4.
* Batch budget = `remaining − reserve`; per-step cap =
  `min(per_step_budget, batch_budget / batch_size)`.
* The main task's `estimation_cost` is the run budget, so the supervisor turn is
  also capped by `SmolAgent`.
* `supervisor_reserve` defaults to 10% of the budget.
* Cost is recomputed from `Chat.cost` each tick; `RunState.spent_cxjcoins` is a
  monotonic mirror.
* Cost roll-up read-modify-write is serialized with
  `.codx/.cost-rollup.lock`.

### 3.5 Tools

**`orchestrator`** (stateful, cache-disabled, supervisor-only by injection):

`start`, `plan`, `add_step`, `status`, `finish`, `pause`, `resume`, `stop`,
`retry_step`, `remove_step`.

**`delegate`** (stateful, cache-disabled, available to the `orchestrator`
profile for normal chats):

* `task` or `tasks` (max 8), `profile`, `files`, `context`, `concurrency` (1-4),
  `wait`, `timeout_seconds`;
* `wait=true` → cards next to the parent, concurrent isolated turns, structured
  results returned in the turn;
* `wait=false` → creates a durable run with one step per task;
* a run worker cannot delegate, and a delegated subagent cannot delegate again.

### 3.6 Agent / chat integration

* `ChatEngine` declares the internal `orchestration` header:
  * main run task → `supervisor`;
  * step card or `mode="delegate"` → `worker`.
* `SmolAgent` parses the header, injects `orchestrator` for supervisors, a
  worker baseline for workers, strips the header before the provider, and never
  lets a profile smuggle a control tool into the wrong role.
* Stateful tools opt out of the tool cache via `ToolSettings.cache=False`
  (or raw `"cache": False`).
* Auxiliary summary/description requests receive no tools and no internal
  headers.
* Orchestration chats skip summary/auto-init AI calls to save cost and latency.
* `SmolAgent` exposes the active cancellation token to tools so `delegate` can
  cancel its subagents when the parent is cancelled.
* `Chat` gained `run_id`, `run_status`, `run_step_id`.
* `TaskManager.create_task` gained `estimation_cost`, run ids and
  `ignore_parent_*`; it resolves a parent by id so root/cost ancestry is
  correct.
* `process_task(wait=True)` now awaits; `wait=False` uses a dedicated thread
  with its own loop.

### 3.7 API

Prefix `/api` (router auto-discovered):

| Method | Path |
|---|---|
| `GET` | `/api/orchestration` |
| `POST` | `/api/orchestration` |
| `GET` | `/api/orchestration/{run_id}` |
| `POST` | `/api/orchestration/{run_id}/steps` |
| `POST` | `/api/orchestration/{run_id}/finish` |
| `POST` | `/api/orchestration/{run_id}/start` |
| `POST` | `/api/orchestration/{run_id}/pause` |
| `POST` | `/api/orchestration/{run_id}/resume` |
| `POST` | `/api/orchestration/{run_id}/stop` |
| `POST` | `/api/orchestration/{run_id}/tick` |

Socket event: `codx-junior-orchestration` with `run_id`, `status`, `progress`,
`main_chat_id`, event payload. REST remains authoritative.

### 3.8 Client UI

The merged client includes a chat-level run bar:

* `client/src/store/orchestration.js` — run cache, socket patching, debounced
  detail refresh, start/pause/stop actions;
* `client/src/api/modules/orchestration.js` — API module;
* `client/src/components/chat/ChatRunBar.vue` — status, budget, step counts and
  controls;
* `client/src/views/ChatView.vue` — renders the bar when `chat.run_id` is set
  and drives “Agent mode” → create run;
* `client/src/api/api.js`, `client/src/store/index.js`,
  `client/src/store/session.js` — module registration and socket forwarding.

The UI starts a run with `POST /api/orchestration` (`main_chat_id`, objective,
budget) and uses `/start`, `/pause`, `/stop` afterwards.

---

## 4. Key invariants and decisions

1. **The run main task is a budget root.** A task with `parent_id` cannot be a
   run main task (cost would roll to an ancestor and desynchronize the budget).
2. **Every plan step is a card.** No invisible queue.
3. **Workers are isolated.** The contract is the only input; the structured
   result is the only output the supervisor sees.
4. **The supervisor plans/verifies/finishes; workers do.**
5. **No AI call for budget/stall/stop bookkeeping.**
6. **The run store, not the chat file, is the source of truth** for plan and
   results; chat fields are board-facing mirrors.
7. **Single-flight per run** via `flock`; a dead process releases the lock.
8. **Completed runs are immutable**; stopped/failed runs can be reopened
   explicitly with `start`.
9. **`report_generation`** distinguishes reports from different reopen attempts
   so an old report cannot suppress a new delivery report.
10. **Delegation is one level** — finite tree, bounded budget.

---

## 5. Files changed / added

### New

```
api/codx/junior/api/orchestration.py
api/codx/junior/orchestration/{__init__,constants,models,store,board,executor,prompts,service,worker}.py
api/codx/junior/profiles/orchestrator.profile
api/codx/junior/tools/orchestration_tools.py
api/codx/junior/utils/file_lock.py
api/docs/orchestration.md
api/tests/test_orchestration.py
client/src/api/modules/orchestration.js
client/src/components/chat/ChatRunBar.vue
client/src/store/orchestration.js
```

### Modified

```
api/codx/junior/ai/smol/smol_agent.py
api/codx/junior/background.py
api/codx/junior/chat/chat_engine.py
api/codx/junior/chat_manager.py
api/codx/junior/db.py
api/codx/junior/events/event_manager.py
api/codx/junior/task_manager.py
api/codx/junior/tools/__init__.py
api/codx/junior/tools/model.py
api/codx/junior/tools/process_task_tool.py
api/docs/long-running-tasks-plan.md
api/docs/long-running-tasks.md
client/src/api/api.js
client/src/store/index.js
client/src/store/session.js
client/src/views/ChatView.vue
```

---

## 6. Git state

```text
Branch:          v1.3-demo-site
Merge commit:    c1aaca49  Merge branch 'feat/board-native-orchestration' into v1.3-demo-site
Feature commit:  54d98c7d  Add board-native orchestration runtime
Feature worktree: /home/codx-junior/codx-junior/.worktrees/board-native-orchestration
```

Note: the main branch had already advanced and contained the same feature
content in `85af6626` (“Checkpoint”). The merge is therefore a clean ancestry
merge with no tree changes relative to its first parent; `54d98c7d` is now in
the main history.

The only untracked items in the main checkout are unrelated and were not
touched:

```
.codx/tasks/codx-junior maintenance/Backlog/workspace-models-module.<id>.json
plugins/simpleopd.ai/
```

---

## 7. Verification

Passing in the current environment:

* Python `py_compile` on all new/changed orchestration and integration files.
* **29/29** offline orchestration tests:
  * result contract parsing and fallbacks;
  * plan validation, id reuse, title dependencies, cycle rejection;
  * ready/blocked steps and next-action diagnosis;
  * atomic store round-trip, exclusive lock, worker heartbeat;
  * run creation/plan persistence;
  * sequential dependency dispatch and parallel independent dispatch;
  * budget exhaustion without an executor call;
  * stagnation stop;
  * completion + recovery report;
  * pause/resume/stop/start/reopen and report generation;
  * retry reset;
  * board/sprint creation and card linking to the run/main task;
  * delegation wait/reject recursive delegation;
  * `orchestrator`/`delegate` schemas.

Because this container lacks the project’s full dependency set and `pytest`,
the suite was executed with a minimal pytest shim. In the normal API
environment run:

```bash
cd api
pytest tests/test_orchestration.py -q
```

**Not yet run:** a provider-backed end-to-end run and the client build
(`npm run build`); this environment has no model credentials and no
`node_modules`.

---

## 8. Continuation points / next steps

Priority order:

1. **Provider-backed end-to-end test**
   * enable a project + model;
   * start a run from ChatView and from `POST /api/orchestration`;
   * confirm the supervisor plans, cards appear on the board/sprint, workers
     execute, results feed the next round, delivery report is published;
   * verify cost push-down/reserve and cancel/pause/stop under a real model.

2. **Run the full test suite and client build**
   * `pytest tests -q` in the normal environment;
   * `npm run build` / `npm run type-check` in `client/`;
   * fix any integration/type errors.

3. **Supervisor context compaction**
   * long runs append one prompt per round; `max_rounds` bounds it, but add
     compaction of older rounds into a bounded run summary while keeping the
     full timeline in the run store.

4. **Run UI surface**
   * currently the ChatView bar is the main UI;
   * add a run header on the board/main task and a runs list/dashboard backed by
     `GET /api/orchestration` and the socket event.

5. **API authorization**
   * mutating endpoints currently use the authenticated-user dependency but do
     not enforce a specific role/project membership; review before exposing
     runs to untrusted users.

6. **Operational cleanup**
   * run document retention/archival;
   * handling corrupt run documents (currently skipped/logged by the worker);
   * expose worker lag/heartbeat in the API summary.

7. **Possible next features**
   * nested delegation with a depth cap;
   * per-step verification cards (`verification="step"`);
   * parallel runs across projects with a global concurrency cap;
   * retry/backoff policy distinct from the supervisor’s replan decision.

---

## 9. Handoff checklist

```bash
# main branch already merged
cd /home/codx-junior/codx-junior
git log --oneline -3

# optional feature worktree (kept intact)
cd .worktrees/board-native-orchestration

# API tests
cd api && pytest tests/test_orchestration.py -q

# start the product with the worker enabled
CODX_JUNIOR_API_BACKGROUND=1 <normal start command>

# create a run
curl -X POST 'http://localhost:3080/api/orchestration?codx_path=/path/to/project' \
  -H 'Content-Type: application/json' \
  -d '{"name":"Auth refactor","objective":"...","budget_cxjcoins":25,"max_parallel":2}'

# inspect it
curl 'http://localhost:3080/api/orchestration/<run_id>?codx_path=/path/to/project'
```

Environment switches:

| Variable | Default | Meaning |
|---|---|---|
| `CODX_JUNIOR_ORCHESTRATION` | `1` | background worker feature switch |
| `CODX_JUNIOR_ORCHESTRATION_WORKER` | `1` | worker switch |
| `CODX_JUNIOR_ORCHESTRATION_TICK_SECONDS` | `5` | worker cycle |
| `CODX_JUNIOR_ORCHESTRATION_MAX_RUNS` | `2` | runs advanced concurrently |
| `CODX_JUNIOR_ORCHESTRATION_WORKER_TTL` | `45` | heartbeat staleness (s) |

If the worker is off, a run stays `running`; the API detail reports
`worker.present: false`.

---

## 10. Quick “where do I look?” map

| Question | File |
|---|---|
| Full design and DSH comparison | `api/docs/orchestration.md` |
| Run state machine / tick / budget | `api/codx/junior/orchestration/service.py` |
| Plan graph and result contract | `api/codx/junior/orchestration/models.py` |
| Atomic state and locks | `api/codx/junior/orchestration/store.py` |
| Board/sprint/card mapping | `api/codx/junior/orchestration/board.py` |
| Worker turn + isolation | `api/codx/junior/orchestration/executor.py` |
| Supervisor/worker prompts, reports | `api/codx/junior/orchestration/prompts.py` |
| Background worker | `api/codx/junior/orchestration/worker.py` |
| LLM tools | `api/codx/junior/tools/orchestration_tools.py` |
| REST API | `api/codx/junior/api/orchestration.py` |
| Agent tool injection | `api/codx/junior/ai/smol/smol_agent.py` |
| Chat/run headers and auxiliary cleanup | `api/codx/junior/chat/chat_engine.py` |
| Run fields on tasks | `api/codx/junior/db.py` |
| Task creation with run metadata | `api/codx/junior/task_manager.py` |
| Cost roll-up lock | `api/codx/junior/chat_manager.py` |
| Tests | `api/tests/test_orchestration.py` |
| Client run bar/store | `client/src/components/chat/ChatRunBar.vue`, `client/src/store/orchestration.js` |

---

## 11. Follow-up fixes (this ticket)

The feature was reviewed end to end. The following defects were found and
fixed:

1. **`orchestrator(action="add_step")` raised `UnboundLocalError`** — the branch
   used an undefined local `run`. It now returns the updated plan table and next
   action (`tools/orchestration_tools.py`).
2. **A resumed stalled run could never publish its final report** — the stall
   report set `report_written=True` and `resume()` did not bump
   `report_generation`, so `finish`/budget reports were suppressed by the
   idempotency marker. `resume()` now starts a new report generation
   (`service.py`).
3. **Reports are durable in the run document** — `RunState.last_report` keeps the
   last report even when the main task is missing/moved; the old code logged
   "report kept in the run store" but did not store it (`models.py`,
   `service.py`).
4. **The worker card mirror was overwritten on start** — the executor ran the
   pre-update card object, so its end-of-turn save could reset the card from
   `doing`/`In progress` to `todo`/`Backlog`. The card returned by
   `update_step_card` is now the one executed (`service.py`).
5. **The run detail payload missed fields the ChatRunBar renders** —
   `budget_cxjcoins`, `spent_cxjcoins` and `counts.total` are now present in
   `GET /api/orchestration/{run_id}` and in the list payload (`service.py`).
6. **Cancellation tokens were registered under `None`** — `Chat.doc_id` is a
   legacy field that is normally empty, so every chat shared one registry entry
   and the orchestration guards (`stop`, "is this card processing?") could never
   find the in-flight token. The engine now registers by `chat.doc_id or chat.id`
   (`chat_engine.py`).
7. **`ProfileManager.read_profile` did not resolve built-in profiles** (the
   built-in `orchestrator.profile` was listed but unreadable by
   `GET /api/profiles/orchestrator`), and it matched the profile name against
   the whole path. It now performs an exact lookup and falls back to the base
   profile (`profile_manager.py`).
8. **`RunStore.lock_path` replaced every `.json` occurrence** — a run id
   containing `.json` produced a different lock stem. It now uses the path stem
   (`store.py`).
9. **Project profile created** — `codx-junior/.codx/profiles/orchestrator/`
   (`orchestrator.profile` + `orchestrator.md`) overrides the built-in profile in
   this project and is editable from the UI. The built-in team list also uses
   the real profile name `ProjectManager`.

Regression tests were added for the new behaviour; the offline suite is now
**33/33 passing**:

```bash
cd api
pytest tests/test_orchestration.py -q
```

---

*Generated for continuation in a fresh workspace. The authoritative technical
detail is [`docs/orchestration.md`](orchestration.md); this file summarizes the
objective, the delivered changes, the current repository state and the open
work.*
