## Long running tasks (LRT) contract

Long-running tasks (LRT) contract — design in `docs/long-running-tasks.md`.

- A **run is a main task** (`Chat`): objective in `description`, budget in `estimation_cost`, managing profile in `profiles`, switch in `run_status`/`run_state`/`run`.
- Every sub-task is a chat whose `Chat.root_id` is the main task id (`codx/junior/identity.py`); a task on the run board with a foreign root is never processed.
- Cost is monotonic on `Chat.cost` and rolls up to the root chat, so the main task budget covers the whole tree.
- The **worker loop runs only in the background process** (`CODX_JUNIOR_API_BACKGROUND`) via `codx/junior/long_running/runner.py`; the API process only writes intent/reads state (30s request timeout).
- Single worker per run enforced by `.codx/tasks/long_running/<main_task_id>.lock`.
- Kanban catalogue is v2 (`tasks/index.json` + `tasks/boards/<id>/board.json`); board/column `id` and `folder` are immutable, titles are labels.
- Statuses come from `planning_manager.STATUS_ORDER` — never hardcode a second list.
- Milestones: LRT-0 prep (done), LRT-1 run skeleton, LRT-2 autonomy, LRT-3 visibility.
