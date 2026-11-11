## AI: harness=False for single-shot prompts

- **Single-shot LLM calls must opt out of the agent harness.** `AI(..., harness=False)` (forwarded to `SmolAgent`) skips the agent system prompt and every tool schema. Without it the model believes it is a coding agent, emits a tool call that no loop executes, and the answer reaches the user as raw provider tool-call markup (DeepSeek `<｜｜DSML｜｜invoke …>`).
- **Never render provider-inline tool-call markup.** Use `codx.junior.ai.utils.strip_tool_call_markup(text)` for any assistant text (already applied to the final answer in `SmolAgent._run_chat_loop`).
- **Wiki docs assistant** = `client/src/views/WikiView.vue` → `POST /api/wiki/assistant` → `codx/junior/wiki/assistant.py::WikiAssistant` (pure RAG over the generated wiki, no tools).

## Runtime code drift: verify the loaded code, not the tree

`scripts/run_api.sh` starts uvicorn **without --reload**, so the running API keeps
the code it imported at boot. A source change (even committed) has no effect
until the API is restarted, and the symptom is misleading: orchestration runs stay
"Running" at 0 % while every card creation fails with
`TaskManager.create_task() got an unexpected keyword argument ...`.

Before diagnosing any "harness/run is blocked" symptom, verify the *loaded* code:

1. `docker_container(action="exec", container_name="codx-junior-api",
   command="grep -n <symbol> <path inside the container>")`
2. If the symbol is missing there but present in the checkout, the process is
   stale — restart `codx-junior-api` **and** `codx-junior-api-background`
   (never from the chat that the API is serving: the restart kills the turn).
3. Compose lives in `scripts/docker-compose.yaml`; docker compose tools run from
   the project root, so pass `-f scripts/docker-compose.yaml`.

Orchestration card creation is signature-tolerant since `RunBoard._supported_task_kwargs`
(drops kwargs the loaded `create_task` lacks and logs the stale runtime), so a
future drift degrades instead of deadlocking the run.

## client/src is not indexed by project_grep/project_glob

`client/src` is excluded from `project_grep` / `project_glob` / `project_search` (custom ignore patterns), so searching it there returns "no matches" even for strings that exist.

Workarounds that DO work:
- `project_read_file` with `pattern=` (regex) on a concrete file (or a list of files) — case-sensitive.
- `read_folder` / `project_structure` to discover paths.
- `project_changes` with `paths=["client/src"]` for diffs.

Navigation/IA of the web client lives in `client/src/config/apps.js` (app registry), `client/src/config/mobile.js` (mobile tabs + "More" launcher groups), `client/src/config/appComponentsMap.js` (app → component), `client/src/router/index.ts` (routes + `meta.mobile`) and `client/src/components/mobile|layout|main-menu/*` (nav surfaces). Adding an app to mobile = APPS entry + route + MOBILE_APP_GROUPS tile + MOBILE_ROUTE_TITLES.

## Repo search gotcha: project_grep under-scans

In `/home/codx-junior-projects/codx-junior`, `project_grep` is unreliable: it returns "No matches" even for literal strings that exist (e.g. it does not find `ProjectDetailt` inside `client/src`, and it never scans `api/`). Do not conclude a symbol is absent from grep results.

Reliable discovery:
- `project_glob` with explicit patterns (works).
- `read_folder` to map folders, then `project_read_file` with `pattern=` / `start_line`/`end_line`.
- `project_read_file(pattern=...)` finds symbols inside a file reliably.

Client conventions: `@` alias → `client/src`. `$storex`, `$projects`, `$project`, `$ui` etc. are global computed props from a mixin in `client/src/main.ts`, so any Options-API component can use them. Settings pages are Options API-friendly; `ProjectSettings.vue` is `<script setup>`.
