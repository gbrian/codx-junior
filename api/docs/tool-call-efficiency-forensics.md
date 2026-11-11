# Forensic review: 57 tool calls that fixed nothing

> **Trace under review.** A user reported *"Computer session is not
> opening/working. Nothings is shown"*. The assistant spent **57 tool calls**
> (37 reads, 14 searches, 4 folder/tree calls, 1 repository overview, 1 file
> history) and stopped without a change, a test or a conclusion.
>
> This document reconstructs what happened, maps each failure to the tool
> design that produced it, records the fixes applied in this change, and lists
> the remaining work.

---

## 1. What the trace actually did

| Phase | Calls | Files / queries | Outcome |
| --- | ---: | --- | --- |
| Locate the app registry | 1–6 | `apps.js`, `appComponentsMap.js`, `BrowsersSessionManager.vue`, 2 searches | Found the component name; no route yet |
| Route → store → API | 7–18 | `router/index.ts` (2 chunks), `store/browsers.js`, `api/modules/browsers.js`, `api/api.js`, `navigate.js`, 5 searches | Assembled the chain by reading, not by navigating |
| Render path | 19–33 | `BrowserSessionList.vue`, `BrowserSessionPanel.vue` (4 chunks / 1100 lines), `store/ui.js` (4 chunks / 831 lines), `AppRouteView.vue`, `DesktopSidebar.vue`, `repository_overview` | Read two entire large files; still no hypothesis |
| Desktop / views | 34–41 | `components/desktop/`, `Desktop.vue`, `store/views.js` (2 chunks), `store/index.js`, `AppsSection.vue` history, `NavItem.vue` | More context; no test |
| Mobile / API tail | 42–48 | `computers.js` (2 chunks), `BrowserViewer.vue` (2 chunks), `mobile.js`, `MobileShell.vue`, `DesktopViewer.vue` | Still discovering |
| Last-ditch search | 49–57 | 3 searches, `read_folder src`, `main.js`, `main.ts`, `BrowserViewer.vue` 120–330 | Tool budget ended |

**Call budget**

- 37 `project_read_file` calls; at least 10 were re-reads of paths already read
  in an earlier call (the first call's path is not visible in the trace).
- `router/index.ts`, `computers.js` and `BrowserViewer.vue` were covered end to
  end; `ui.js`, `BrowserSessionPanel.vue` and `views.js` were each read in 2–4
  chunks and **still had gaps** (e.g. `ui.js` lines 61–119 were never read).
- 14 `project_search` calls, each taking **1.4 s – 9.8 s**: ~52 s of tool wall
  time, roughly 87 % of the total. Reads took ~100–200 ms each.
- **0** `project_grep`, **0** `project_glob`, **0** `project_changes`,
  **0** writes, **0** tests, **0** runtime probes (screenshot, browser console,
  network, container/app logs). `project_grep` and `project_glob` were not even
  enabled for that run (see §2.8).
- 5 searches passed a `validation=` argument that the tool silently ignored
  (see §2.3).

The trace is a pure read loop: each phase ended with another read instead of a
hypothesis, a probe, or a change.

---

## 2. Why it needed so many calls

### 2.1 The symptom was never observed

A blank screen is a **runtime** symptom. The assistant never looked at the
running app, the failing request, the browser console or the server log. It
tried to infer the failure from source code, which cannot distinguish "route
missing" from "API 404" from "VNC socket closed" from "component rendered
empty".

The system prompt's rules covered file-change formatting and "do not repeat
tools", but contained **no investigation protocol** and no instruction to gather
evidence before reading code. The repository has browser/computer/log tools;
none were used.

### 2.2 Semantic search was used for exact symbols

Queries such as `setActiveTab`, `activeTab`, `component: 'browser-sessions'`,
`path: 'browsers'` are exact-text/path questions. `project_search` does
knowledge-base retrieval plus **path** matching
(`api/codx/junior/tools/project_tools.py`, `project_search`); it does not return
symbol definitions.

Worse, this project's knowledge config ignores the code being debugged:

```json
"knowledge_file_ignore": "api/,client/,.codx,assets,/.gitignore,xdg,browser"
```

(`.codx/project.json`). The semantic half had no `client/` code to retrieve, so
the searches only matched file **names** and missed the definitions. That is
why the same concept was searched again and again with different wording.

`project_grep` (exact text/regex) and `project_glob` (paths) exist in the
registry and are one call each, but the model could not call them: they were
**not in the active profile's tool allowlist** (see §2.8). `project_search` was
the only discovery tool it had, and its description claimed it "also finds
project files". The tool descriptions competed instead of complementing.

### 2.3 The `validation` argument was a lie

`project_search` still exposed `validation` as *"text used to validate and
filter search results"*, while the implementation ignores it (filtering was
removed to make search fast). The trace passed it 5 times expecting narrower
results. A schema that promises filtering and silently does nothing buys extra
searches.

### 2.4 `project_read_file` actively encouraged paging

After any requested range, the tool appended:

> `N more line(s) are available. Call project_read_file with start_line=... to continue.`

It had no in-file search and no outline, so the only affordance for "find
`setActiveTab` in an 831-line store" was to request the next chunk. The trace
obeyed: 4 calls for `ui.js`, 4 for `BrowserSessionPanel.vue`, 2 for
`router/index.ts`, 2 for `BrowserViewer.vue`.

The model did not need the whole file. It needed one symbol and the lines
around it.

### 2.5 No navigation or aggregation tools

To answer "why is this screen empty", a developer follows
**route → component → store → API → runtime state**. The assistant rebuilt that
chain by hand across ~20 files. There is no tool for "where is this symbol
defined and used" or "what does this route render", and `project_structure` /
`read_folder` are tree dumps, not navigation. `get_file_last_version` was used
once as a substitute for "what changed recently?", which is a different tool.

### 2.6 The tool budget was halved by a counting bug

`LoopGuard.check()` increments `rounds` (`api/codx/junior/ai/smol/loop_guard.py`),
and the agent loop incremented `rounds` **again** after every round
(`api/codx/junior/ai/smol/smol_agent.py`). A configured `max_iterations` of N
therefore behaved like N/2: the run stopped earlier than configured and logged a
wrong `iterations_left`. A long investigation hit the wall before it could
conclude.

### 2.7 Context survived, but the fallback did not carry evidence

Tool events are attached to the response message and persisted on every event
(`ChatEventBridge`), and the next turn rebuilds a `<session_memory>` block from
them (`chat_tool_memory.py`). That part works. But when the loop limit is hit,
the continuation summary is a separate AI request
(`_summarize_tool_usage`); if that request fails, the fallback only listed tool
names and arguments — **not what the tools returned**. The exact evidence the
next iteration needed was the part dropped.

### 2.8 The profile allowlist hid the right tools

The trace's tool list is not the registry: it is the union of the active
profiles' allowlists. `software_developer` enabled exactly:

```
project_search, project_read_file, project_structure,
generate_tasks_tool, create_task, get_file_last_version
```

No `project_grep`, no `project_glob`, no `project_changes`; the other profiles
active in that turn contributed `read_folder`/`repository_overview` but still
no exact search. The model used the only discovery tool it had and read files to
compensate. A registry tool the profile does not enable is invisible to the
model, and the system prompt cannot compensate for an allowlist omission.

The profiles used for code/task work now include the exact tools they need:

| Profile | Added |
| --- | --- |
| `software_developer` | `project_grep`, `project_glob`, `project_changes`, `search_codx` |
| `orchestrator` (project + built-in) | `project_grep`, `project_glob`, `search_codx` |
| `analyst` | `project_grep`, `project_glob`, `search_codx` |
| `TaskManager`, `repository`, `devops`, `web_master`, `workspace` | `project_grep`, `project_glob`, `search_codx` |
| `ProjectManager`, `browser` | `search_codx` |

Profiles should be checked whenever a new search/control-plane tool is added:
the tool list is the real product surface, not the registry.

---

## 3. What a developer would do (the 8-call version)

| # | Call | Why |
| ---: | --- | --- |
| 1 | `project_grep("browser-sessions|/computers|setActiveTab")` | Find the route/registry/symbol definitions in one exact search |
| 2 | `project_read_file("src/store/ui.js", pattern="setActiveTab")` | Definition + context, no paging |
| 3 | `project_read_file("src/components/browsers/BrowserSessionPanel.vue", outline=True)` | Map the 1100-line component, then one targeted range |
| 4 | `docker_logs` / browser screenshot + console + network for the failing page | Actual error instead of inferred error |
| 5 | `project_read_file(<the one suspect>, pattern=<the failing call>)` | Confirm the hypothesis |
| 6 | `project_changes` / `get_file_last_version` on the suspect | Regression check |
| 7 | `apply_file_changes` | The fix |
| 8 | `project_changes` + screenshot / API probe | Verification |

That is ~8 calls, and it ends with a change and evidence — the "find a few
things, do some work, then find more info" loop.

---

## 4. Fixes applied in this change

### 4.1 In-file search and outline (`project_read_file`)

New arguments:

- `pattern="setActiveTab"` — returns only matching lines (plus
  `context_lines`, default 2), with line numbers and a match count. Invalid
  regex falls back to a literal search and says so. No match is a useful
  one-call "it is not here".
- `outline=true` — prepends a heuristic map of declarations (Python/JS/TS/Vue,
  Markdown headings) with line numbers.
- Large files (≥ 400 lines) read **whole** get a compact automatic outline, so
  the first read doubles as a map.

The continuation hint no longer pushes "read the next chunk" when the caller
asked for a specific range; it points to `pattern` / the outline instead.

### 4.2 `project_search` stops pretending to filter

- `validation` removed from the tool schema (the Python argument stays for
  backward compatibility).
- Description now says **concepts**, and routes identifiers to `project_grep`
  and paths to `project_glob`.
- A no-result response explicitly suggests `project_grep` / `project_glob`, so
  a miss does not become another identical search.

### 4.3 Investigation protocol in the system prompt

Added to `HARDCODED_SYSTEM_RULES`:

- runtime evidence first for "not working / blank / nothing shows";
- exact symbol → `project_grep`, paths → `project_glob`, concepts →
  `project_search`;
- large file → `pattern`/outline, not page-by-page;
- at most 3–5 discovery calls before a hypothesis and a probe/change;
- before the budget runs out, write down confirmed / ruled out / next step.

### 4.4 Loop budget counted once

`LoopGuard.complete_round(checked=...)` now counts an all-cached round (which
skips `check()`) and is a no-op for checked rounds. `max_iterations` is no
longer halved, and the `iterations_left` logs are accurate.

### 4.5 Continuation fallback carries evidence

When the analysis model is unavailable at the loop limit, the deterministic
fallback now collapses identical calls and includes a bounded head+tail excerpt
of each result, so the next iteration can continue from the evidence instead of
re-running the reads.

### 4.6 The profile allowlists now expose the tools

`software_developer` (the active profile in the trace) now enables
`project_grep`, `project_glob`, `project_changes` and `search_codx`; the
orchestrator/analyst/task/repository/devops/web/workspace profiles were updated
with the tools their work needs (see §2.8).

As a safety net, `ChatEngine._ensure_investigation_tools` completes the
allowlist of any profile that can read project files with the read-only
`project_grep`, `project_glob`, `project_changes` and `search_codx`. A saved
profile can no longer hide the tools required to investigate the files it is
already allowed to read.

### 4.7 Tests

- `api/tests/test_project_tools.py`: pattern search, context, scope, no-match,
  invalid-regex fallback, outline, automatic outline, no paging nudge, search
  no-result routing.
- `api/tests/test_codx_tools.py`: `.codx` exclusion from `project_*`,
  `read_folder` redirect, `search_codx` inventory/modules/aliases/JSON fields,
  logs opt-in, database/sensitive-file rejection, regex handling.
- `api/tests/ai/smol/test_loop_guard_rounds.py`: one count per checked round,
  depth limit, all-cached rounds.

Combined affected suite: **88 passed**.

---

## 5. What is still missing (priority order)

1. **A runtime-evidence tool for UI bugs.** One call that captures: app/container
   logs, the failing API request, browser console/network and a screenshot.
   Without it, "blank screen" investigations will keep defaulting to code
   reading.
2. **A symbol navigation tool.** `project_find_symbol` / `project_references`
   returning definition + usages + call sites. This replaces both the 14
   searches and half of the 37 reads.
3. **Automatic continuation.** On a loop limit, persist the findings as a
   proper assistant message and offer/trigger a continuation with "do not
   repeat tools" context. The existing `tool-summary` and
   `smolagent-tools-break` backlog cards cover this; the deterministic ledger
   above is the safety net.
4. **Full tool-result store.** Keep complete results in a sidecar keyed by
   tool+args and let `<session_memory>` reference them by id instead of
   truncating every result to ~700 chars (the `tool-summary` backlog card).
5. **Efficiency telemetry.** Per run, log calls by tool, repeated file reads,
   search latency and the read/write ratio. A run with 20+ calls and 0
   mutations should be flagged in the chat as "investigation did not converge".
6. **Knowledge coverage.** `api/` and `client/` are excluded from the index.
   Either index them for development projects or make `project_search` say
   "this folder is not in the knowledge index" and fall back to grep.
7. **Revisit the budget.** The default is 10 rounds × 5 calls (50 calls) with a
   300 s per-tool timeout. That is a lot of reading and very little acting;
   consider a smaller default plus an explicit "deep investigation" budget the
   model must opt into.

---

## 6. Postscript: the defect the trace missed

While this review was being written, the working tree received an uncommitted
fix (not authored by this change) in:

- `client/src/store/browsers.js`
- `client/src/components/browsers/BrowserSessionList.vue`

It confirms the failure mode:

- `/api/computers` can answer a bare array (or `{ computers: [...] }`), while
  `loadSessions` only read `response?.sessions || []` — so a valid response
  became an **empty list** and the screen showed "no sessions" (or nothing).
- When the request failed, the error was stored in `state.error`, but the list
  never rendered it, so the failure looked like an empty screen.

The trace had **already read both files** (calls #11 and #20). It did not find
the defect because it never observed the response shape or the failed request.
Two of the 57 reads were the right files; the missing call was the runtime
probe.

The 4-call version of this investigation was:

1. screenshot / network / console of the page → "empty list, request shape
   mismatch or failed request";
2. `project_grep("loadSessions")` → the store action;
3. `project_read_file("client/src/store/browsers.js", pattern="loadSessions")`;
4. fix the normalisation and render the error state, then verify.

---

## 7. Reproducing the analysis

The trace is the 57-call transcript pasted by the user; the tool timings and
argument previews are the only metadata available (the model's internal
reasoning is not in it). File-level claims above were checked against the
current tree:

- `api/codx/junior/tools/project_tools.py` — read/search/grep/glob/outline.
- `api/codx/junior/tools/__init__.py` — tool schemas and descriptions.
- `api/codx/junior/ai/smol/smol_agent.py` — system rules, loop accounting,
  limit summary/fallback.
- `api/codx/junior/ai/smol/loop_guard.py` — round/depth accounting.
- `api/codx/junior/chat/chat_event_bridge.py` — per-event tool persistence.
- `api/codx/junior/chat/chat_tool_memory.py` — next-turn `<session_memory>`.
- `.codx/project.json` — `knowledge_file_ignore` (`api/`, `client/`, …).


---

## 8. Follow-up: codebase vs `.codx`

A second review found another routing defect: `.codx` (267 MB, 1,787 task files
in this repository) was still included in `project_structure` because the tree
only applied `.gitignore`, and there was no dedicated way to search the control
plane. Mixed into a code investigation, that data is pure noise — the model can
spend a turn reading task histories instead of the source.

The namespaces are now separate and documented:

- every `project_*` tool excludes `.codx` (component-based, so
  `docs/about.codx.md` is not excluded);
- `read_folder(".codx")` returns a pointer to the control-plane search instead
  of a tree;
- `search_codx(modules=[], query="")` inventories tasks, profiles, browser
  sessions, boards, views, teams, workspaces, chat turns, orchestration,
  project metadata and logs; `search_codx(query=..., modules=[...])` searches
  only the selected module, parses JSON fields and never touches databases,
  downloads or secrets.

See [codebase-and-codx.md](codebase-and-codx.md) for the routing table, module
map, limits and examples.
