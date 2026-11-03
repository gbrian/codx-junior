## Profiles API & knowledge UI conventions

## REST conventions for profiles endpoints

- Identity lives in the URL: `/profiles/knowledge/{profile_name}` + `project_id` as a **query** param on every endpoint. Never put `project_id`/`profile_name` in a request body.
- Bodies only describe the resource (`file_name`, `content`, `title`, `overwrite`).
- `PUT` = upsert (create or replace); `DELETE` takes the resource name as a query param (no DELETE body).
- FastAPI dependencies: one `Depends` chain validates project + profile (404) and permissions (403); FastAPI caches them per request. Do not re-resolve settings inside each handler.
- Request models: `ConfigDict(str_strip_whitespace=True)` + explicit `min_length`/`max_length` matching the tool limits (file name 500, content 200000, rule 4000 = `MAX_RULE_CHARS`).
- Storage `ValueError` → HTTP 400 with the message verbatim; do not string-sniff to build other codes.

## Profile knowledge UI

- `ProfileKnowledgePanel.vue` (rules/files tabs, budget bar, confirm modal) is mounted in `ProfileViewer.vue`; it reads `can_write` from the server and renders read-only with a lock hint otherwise.
- Rules are composed into `profile.content`, so any rule change must trigger a profile reload (panel emits `changed` → viewer emits `refresh`).

## WhatsApp / Channels board convention

All WhatsApp / external-channel work is tracked on board **Channels**, column **WhatsApp** (see `channels/whatsapp-bridge-architecture.md`).

Decisions already made (do not re-open):
- Official **WhatsApp Cloud API**, full duplex. The **Groups API is out of scope**: groups are created by the user in WhatsApp and codx-junior only stores group id/name + syncs messages.
- **Secrets live in global settings → `integrations[]`** (generic list, will also host Slack). Not env-var references, not in `.codx` project JSON, not in git.
- Identity: `CodxUser` carries a phone number (`wa_id`) and an `enabled` WhatsApp flag; a chat-level config lists which participants are synced.
- One group `Chat` ↔ one WhatsApp group/DM; mirrored messages tagged in `Message.meta_data["channel"]`.

## Kanban boards / sprints / task destinations

Kanban catalogue = `.codx/tasks/kanban.json` (`{version, boards: {name: {id,title,description,type,parent_id,columns[],active,last_update}}, tags}`) and is read/written through `ChatManager.load_kanban` / `save_kanban`.

- A board name IS the storage folder (`.codx/tasks/<board>/<column>/`) and is also stored in `Chat.board`; renaming must move the folder AND rewrite every task, deleting must not orphan tasks.
- A **sprint is a board with `type="sprint"`**; membership lives on the task (`Chat.sprints` holds sprint names). Deleting a sprint must clean `Chat.sprints` on tasks of other boards.
- Canonical task states come from `codx/junior/planning_manager.py` `STATUS_ORDER` — never hardcode a second list.
- Board/sprint/column CRUD lives in `codx.junior.tools.project_manager_tools` (`create_board`, `create_sprint`, `update_board`, `delete_board`, `create_column`, `delete_column`) and destination validation is shared via the public `validate_task_destination(chat_manager, board, column, sprints, status)`, used by `create_task` too. Tasks are always created through `TaskManager.create_task`.

## Identity: ids are canonical, names are labels

Every persisted element has an immutable `id` (UUID) and names/titles are only LABELS.

- Board/sprint: `board["id"]` in `.codx/tasks/kanban.json` (a sprint is a board with `type="sprint"`).
- Column: `column["id"]` inside its board entry.
- Chat/task: `Chat.id` (also the file name suffix).
- Message: `Message.id`, mirrored with the legacy `doc_id` (`id` is canonical).
- References on a chat: `Chat.kanban_id` (board id), `Chat.column_id`, `Chat.sprint_ids`
  (source of truth for sprint membership; `Chat.sprints` keeps display names).
- Storage folder is NOT the name: each board/column carries an immutable `folder`
  (`Chat.board_folder` / `Chat.column_folder` cache it). Renaming must only change the
  title — never `shutil.move` a folder nor rewrite every task.
- Identity primitives live in `codx/junior/identity.py`; catalogue lookups/renames in
  `codx/junior/kanban/catalogue.py`; data migration in `codx/junior/migrations/`.
- Never use short ids as keys (`chat_id in path` substring matching is ambiguous).
