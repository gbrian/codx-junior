# Chat intellisense (`@` mentions) — performance analysis

## Symptom
Typing `@…` in the chat composer takes many seconds (sometimes ~tens of seconds) when the
active project contains several sub-projects.

## Data flow
- `client/src/components/chat/Chat.vue` → `scheduleIntelliSense()` (220 ms debounce) →
  `runIntelliSense()` → `project.$state.searchMentions(...)`.
- `project.$state.searchMentions` is defined in `client/src/store/project.js` (`initProject`).
- `project.js` action `searchMentions` / `reloadMentions` are the public entry points;
  `getRelatedProjects()` = sub-projects whose `abs_project_path` starts with the active
  project path + `project_dependencies`.

## Root causes found
1. **Quadratic HTTP fan-out (client).** `searchMentions` loops over
   `[project, ...getRelatedProjects(project)]` *sequentially*, and for each of them calls
   `searchProjectMentions(proj, …)` → `searchProjectFiles(proj, …)`, which **again** expands
   `getRelatedProjects(proj)` and calls `proj.$api.files.search()` for each. With N
   sub-projects that is O(N²) sequential `GET /api/files/search` round-trips per keystroke.
2. **Redundant work.** The backend `FileEngine.search_files` already resolves paths across
   the current project **and** its child projects (`get_project_roots`), and it walks
   `settings.abs_project_path`, which physically contains the sub-project folders. One call
   on the active project is therefore enough; the client fan-out is pure duplication.
3. **Two full filesystem walks per request (backend).** `FileEngine.search_files` builds a
   `GitIgnoreManager`, whose `_load_all_gitignore_files` does a full `os.walk`, and then
   walks the tree again for the search. On a repo with `.worktrees/` (≈7k files each) a
   single call takes seconds, and it runs `N+1`–`(N+1)²` times per keystroke.
4. **Event loop blocked.** `GET /api/files/search` is an `async def` handler calling the
   synchronous `search_files`; every intellisense request blocks the whole API event loop
   (other requests queue behind it), unlike `api/file_finder.py`, which uses
   `asyncio.to_thread`.
5. **Per-project full file lists.** `ensureFilesLoaded()` fetches `GET /api/knowledge/files`
   (the complete indexed file list) for every related project on the first search and after
   every `reloadMentions()`.

## Fix direction (implemented by the run)
- Backend: cache `GitIgnoreManager` and a path index per project root (short TTL, lock
  protected), filter the index instead of re-walking, and run the search off the event loop
  with `asyncio.to_thread`.
- Client: fan out once (no nested expansion), skip related projects already contained in
  another searched root, bound concurrency, merge + rank once, keep the suggestion shape
  (`name`, `file`, `project`, `searchIndex`, `avatar`, `mention`, `score`).