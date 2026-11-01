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
