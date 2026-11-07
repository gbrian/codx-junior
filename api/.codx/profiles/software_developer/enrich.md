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

## Project search must degrade, not fail

`/project/search` (codx/junior/api/project_search.py → CODXJuniorSession.project_search) goes through the RAG/embeddings layer.

- Error "sentence-transformers is required for local embeddings" means the local (HuggingFace) embedding provider was selected but the library is not installed in that environment.
- Fixes: install `sentence-transformers`, or configure an embedding model served by the AI provider (Ollama `nomic-embed-text`, OpenAI-compatible `/v1/embeddings`), then re-index knowledge.
- The endpoint must never hard-fail on this: catch the embeddings-unavailable error and fall back to a bounded lexical scan of the project files, returning items with `id`, `name`, `resource_type`.

## Browser scripts library conventions

Reusable per-site browser scripts live in `codx/junior/browser/scripts.py` (`BrowserScriptStore`).

- Storage: `<project>/.codx/browser_scripts/index.json` + `<id>/script.json` + `<id>/script.<ext>` + `<id>/versions/v<N>.<ext>`; deletes are soft (`.trash/`).
- `BrowserScript.id` (uuid) is canonical, `title`/`site` are labels; folder name == id, never renamed.
- Scripts are DATA: `language="steps"` = JSON array of `browse_action` steps replayed by the browser layer. NEVER `eval`/`exec` model-written Python in the API process; `javascript` scripts are evaluated inside the page only.
- Saving with an existing `id`, or the same title+site, updates in place and bumps `version`, archiving the previous code.
- Tools + schemas are exported as `BROWSER_SCRIPT_TOOLS` in `codx/junior/tools/browser_script_tools.py` (entry shape `{tool_json, settings, tags, tool_call}`); they must also be added to `browser.profile` tools.

## Browser script tools registration

Browser script tools live in `codx/junior/tools/browser_script_tools.py` (`BROWSER_SCRIPT_TOOLS`, `BROWSER_SCRIPT_TOOL_NAMES`) and must be merged into the global registry in `codx/junior/tools/__init__.py`, plus listed in `codx/junior/profiles/browser.profile` (`tools:`).

Never rewrite `codx/junior/tools/__init__.py` (1600+ lines) from memory: it must be read before any full-file `file_change`. When read access is unavailable, provide the exact minimal patch instead.

Browser scripts are DATA (JSON `steps` replayed by the browser layer) — never `eval`/`exec` model-written Python in the API process.

## Big files: append-only edits, never invented full content

Never emit a full-file `file_change` for a file you have not read in the current session (notably `codx/junior/tools/__init__.py`, ~1600 lines: a rewrite silently drops tool registrations).

- If asked anyway: say so once, then offer the two safe paths — (a) paste the file so the verbatim version can be returned, (b) an **append-only** block at the end of the file (imports + one call), which needs no knowledge of the body.
- Prefer designs that need no edit to the big file: registration helpers living in their own module (`codx/junior/tools/browser_script_registration.py`), idempotent `ensure_registered()`, tolerant of list-or-dict registries, warning instead of raising when the registry is missing.
- Long term fix (approved direction): a `patch` change type — model returns hunks + file path, UI calls the diff API with full file context, user approves.

## Editing files: anchored hunks, never whole-file rewrites

**File changes must be anchored hunks, not whole-file rewrites.**

- Engine: `codx/junior/file_patch/` (`format.py` = pure parser/matcher, `service.py` = sandbox + read + diff + atomic write + backup).
- Format `find-replace/1`: `<<<<<<< FIND` / `=======` / `>>>>>>> REPLACE`, plus `CREATE` / `DELETE`. FIND must match **exactly once**; `at=<line>` only breaks ties between already-verified occurrences.
- Flow is validate → apply: `validate_patch` returns the real unified diff + `sha256`; `apply_patch` refuses when the sha changed (`stale_file`) and leaves `.codx/patches/<ts>-<name>.bak`.
- Tools: `validate_file_patch` / `apply_file_patch`. REST: `POST /api/file-patch/validate`, `POST /api/file-patch/apply`, `GET /api/file-patch/window`.
- Never emit a full-file `file_change` for a file you have not read in the session; prefer a patch block.

## Registering routers and tools in codx-junior

**New API router:** drop `codx/junior/api/<name>.py` exporting `router = APIRouter()`. `codx.junior.api.discover_routers()` imports every module in that package and includes it with prefix `/api`, so `app.py` must never be edited for a new router.

**New tools:** a module exports `XXX_TOOLS` (entries shaped `{tool_json, settings, tags, tool_call}`) and `XXX_TOOL_NAMES`; `codx/junior/tools/__init__.py` only needs two lines: the import and a `*XXX_TOOLS,` spread at the end of the `TOOLS` list (same as `*BROWSER_SCRIPT_TOOLS`).

Do not add lazy/`ensure_registered()` helpers: explicit import + spread is the convention (no import cycles, greppable). `codx/junior/tools/__init__.py` is 1600+ lines — edit it with hunks, never rewrite it.
