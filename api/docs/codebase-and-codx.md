# Codebase search vs `.codx` search

The project tree has **two namespaces** and they must never be mixed:

| Namespace | What it is | Size (this repo) |
| --- | --- | --- |
| **Codebase** | the source tree (`api/`, `client/`, `docs/`, scripts, config) | the code you edit |
| **Control plane** | `.codx/` — tasks, boards, profiles, browser/desktop sessions, views, teams, workspaces, chat turns, orchestration state, project metadata, logs | **~267 MB**, 1,787 task files |

A source-code question that searches `.codx` is slow and wrong: the model
walks task histories and chat turns instead of the files it needs. A
control-plane question that searches the codebase is equally wrong: it finds
mentions in source code, not the task/profile/session that owns the data.

---

## 1. Start with a map, not a broad search

For a new question, first choose the namespace and get its map:

- **Codebase:** `project_structure(max_depth=2)` (compact tree) or
  `project_glob("src/**/*.vue")` when the path pattern is known. Then
  `project_grep` for the exact symbol and `project_read_file(pattern=...)` for
  the relevant lines.
- **Control plane:** `search_codx(query="")` lists the modules, their file
  counts/sizes and examples. Then `search_codx(query="...", modules=[...])`.

Do not start with a broad `project_search` (semantic search is slow and does not
return symbol definitions) and never start with `.codx`: it is 267 MB of task
history, not source code.

---

## 2. The two tool families

| Question | Namespace | Tool |
| --- | --- | --- |
| Where is `loadSessions` defined/used? | Codebase | `project_grep`, `project_read_file(pattern=...)` |
| What files make up this feature? | Codebase | `project_structure`, `project_glob` |
| What is the route/component for this page? | Codebase | `project_grep` / `project_read_file` |
| What changed in the working tree? | Codebase | `project_changes` |
| Which tasks mention the wallet? | `.codx` | `search_codx(modules=["tasks"])` |
| Which profile reviews pull requests? | `.codx` | `search_codx(modules=["profiles"])` |
| Which browser/desktop session is this? | `.codx` | `search_codx(modules=["browser_sessions"])` |
| What is on the board / in this column? | `.codx` | `search_codx(modules=["boards","tasks"])` |
| Which chat turn is stuck processing? | `.codx` | `search_codx(modules=["chat_turns"])` |
| Was this task started by an orchestration run? | `.codx` | `search_codx(modules=["orchestration","tasks"])` |
| What are the project settings? | `.codx` | `search_codx(modules=["project"])` |
| What is in the application log? | `.codx` | `search_codx(modules=["logs"])` (opt-in) |

**Never** use `project_search`, `project_grep`, `project_glob`,
`project_structure` or `read_folder` to find control-plane data, and **never**
use `search_codx` to find source code.

---

## 3. Codebase tools exclude `.codx` (mechanically)

The exclusion is not a convention the model must remember; it is enforced in
the tools:

- `list_project_files()` filters any path under the project's `.codx` folder
  (`is_codx_path`, path-component based — `docs/about.codx.md` is **not**
  filtered).
- `project_glob`, `project_grep` and `project_search` all build on
  `list_project_files()`, so `.codx` never appears in their results.
- `project_structure` / `read_folder` use the same listing; a tree read never
  shows `.codx`.
- `read_folder(path=".codx")` (or any `.codx` subpath) does **not** dump a
  tree. It returns a pointer:
  > `.codx/` is the control plane ... Use `search_codx(query="")` to list its
  > modules ... For source code use `project_structure`, `project_glob`,
  > `project_grep` or `project_search`.
- `settings.get_ignore_patterns()` always includes `.codx`, so the knowledge
  index never indexes it either.
- `project_read_file` can still read an exact `.codx` file **if** the model
  already has the path (typically from `search_codx`); it is a targeted read,
  not a search.

The codebase tool descriptions and the global system prompt state this
explicitly, so the model sees the rule at the point of decision:

```text
### CODEBASE vs .codx (control plane)
 * The codebase is the project source tree. Use project_structure, project_glob,
   project_grep, project_search and project_read_file for it. `.codx/` is
   EXCLUDED from all of those tools.
 * `.codx/` is the control plane: task cards and boards, AI profiles, browser/
   desktop sessions, views, teams, workspaces, chat turns, orchestration state,
   project metadata and logs.
 * Use search_codx(modules=[...], query="...") for `.codx` questions. Call
   search_codx(query="") first to see the modules and sizes.
```

---

## 4. `search_codx`

One tool covers the whole control plane, scoped by module:

```python
search_codx(query="", modules=None, mode="text", max_results=30, context_lines=1)
```

### 4.1 Inventory first

`search_codx(query="")` returns the modules with file counts, sizes, newest
file dates and examples:

```text
# .codx control plane (NOT the codebase)
root: `/project/.codx`

- **profiles** — 68 file(s), 524.0 KB, newest 2026-11-10; AI profiles ...
  e.g. `.codx/profiles/py_senior.profile`, ...
- **tasks** — 1787 file(s), 249.7 MB, newest 2026-11-10; Task cards ...
  e.g. `.codx/tasks/...json`, ...
- **browser_sessions** — 12 file(s), 64.0 KB, newest 2026-11-10; ...
...
> Use search_codx(query="...", modules=[...]) to search.
> `logs` is excluded by default; pass modules=["logs"].
> `db`, `computer_library`, `computer_downloads`, `browser_downloads` are never
> text-searched.
```

This is the cheapest way for the model to understand the control plane before
searching it, and it avoids guessing folder names.

### 4.2 Module scoping

`modules` accepts a list (or a comma/space-separated string) and aliases:

| Module | Aliases | Contents |
| --- | --- | --- |
| `profiles` | `profile`, `agent`, `agents` | AI profiles (name, description, content, tools, tags) |
| `tasks` | `task`, `kanban` | task cards, boards, columns, messages, history |
| `browser_sessions` | `browser`, `browsers`, `sessions`, `computers` | browser/desktop session metadata and activity |
| `views` | `view`, `layout` | desktop/board layouts |
| `teams` | `team` | human + AI team rosters |
| `workspaces` | `workspace`, `infra` | dev-container / workspace definitions |
| `chat_turns` | `chat`, `chats` | durable chat-turn records |
| `boards` | `board`, `board_manager` | board-manager state and the task index |
| `orchestration` | `run`, `runs`, `worker` | durable orchestration state |
| `project` | `settings`, `meta` | `project.json`, wiki settings, dependency map |
| `logs` | `log` | application/agent logs (**opt-in**) |

`all` / `*` expands to the safe default modules (logs excluded). Unknown
modules produce a warning; `db` and the download folders are rejected with an
explanation instead of being scanned.

Examples:

```python
search_codx("wallet", modules=["tasks"])
search_codx("browser session", modules=["browser_sessions"])
search_codx("reviewer", modules=["profiles"])
search_codx("stuck", modules=["chat_turns", "orchestration"])
search_codx("timeout", modules=["logs"])
```

### 4.3 Structured JSON hits

Task cards, profiles, sessions, views and workspaces are JSON. The tool parses
them instead of grepping escaped lines, so a hit reports the JSON field:

```text
## tasks (1 match(es))
- `.codx/tasks/maintenance/To Do/wallet.task.json` — description
  Fix the wallet needle
- `.codx/tasks/maintenance/To Do/wallet.task.json` — messages[0].content
  the wallet needle is broken
```

Text files (`.md`, `.py`, `.jsonl`, logs) report line numbers:

```text
- `.codx/logs/app.log` — line 42
  ... the timeout was ...
```

Hits are ranked so `name`/`title` beat `description`, which beats message
bodies. Each module gets up to three hits before the remaining slots are filled
globally, so a task-heavy project does not hide the matching profile/session.

### 4.4 Safety and limits

| Guard | Value |
| --- | --- |
| Max file size | 8 MB (larger files are reported as skipped) |
| Max files scanned | 3,000 |
| Max bytes scanned | 300 MB |
| Max collected matches | 240 (then reported as truncated) |
| Max results returned | 100 (default 30) |
| Never searched | `db`, `computer_library`, `computer_downloads`, `browser_downloads` |
| Never searched | binaries, locks, `.env*`, keys, credentials, hidden files |
| Never searched via keys | `user`, `token`, `api_key`, `api_settings`, `password`, `secret`, `env`, headers, cookies |

The call is read-only and bounded; a huge `.codx` cannot block a turn.

---

## 5. Why this matters for the model

Before this split, `project_structure` included `.codx` (only `.gitignore` was
applied, and most of `.codx` is tracked). A structure call could therefore show
hundreds of task/profile/session files, and the model had no documented way to
tell which namespace a question belonged to. The trace that motivated this
change spent 57 calls reading source files and never inspected the task/session
data that described the failing screen.

The rule is now visible in three places:

1. the tool schemas (`CODEBASE ONLY ... use search_codx`),
2. the global system prompt (the `### CODEBASE vs .codx` section),
3. this document.

A profile's `tools` list is the real tool surface. When a profile can read
project files, `ChatEngine._ensure_investigation_tools` adds the read-only
`project_grep`, `project_glob`, `project_changes` and `search_codx` if they are
missing, so an old saved profile cannot force the model back into the
57-call read loop.

---

## 6. Tests

`api/tests/test_codx_tools.py` covers:

- component-based `.codx` detection (`docs/about.codx.md` is not `.codx`),
- `project_structure` / `read_folder` exclusion and redirect,
- `project_glob` / `project_grep` never returning `.codx`,
- inventory, module scoping, aliases, JSON field hits, line hits,
- logs opt-in, database rejection, regex/invalid-regex handling,
- sensitive `.env` and database files never appearing,
- the explicit "no match" message pointing back to `project_grep`.

`api/tests/test_project_tools.py` covers the codebase read/search tools.

Made with ❤️ by codx-junior
