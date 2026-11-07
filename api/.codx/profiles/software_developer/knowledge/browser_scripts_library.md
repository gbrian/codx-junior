# Browser script tools — registration

## Files
- `codx/junior/browser/scripts.py` — `BrowserScriptStore`, `BrowserScript`, `coerce_code`, `parse_steps`, `normalize_site`.
- `codx/junior/tools/browser_script_tools.py` — `list_browser_scripts`, `get_browser_script`, `save_browser_script`, `delete_browser_script` + `BROWSER_SCRIPT_TOOLS` / `BROWSER_SCRIPT_TOOL_NAMES` registry entries.
- `codx/junior/tools/browser_script_registration.py` — `register_browser_script_tools(registry)`, `missing_tool_names(registry)`, `ensure_registered()`; accepts a **list** or a **dict** registry and is idempotent.
- `tests/browser/test_browser_scripts.py` — 12 unit tests (store, validation, versioning, soft delete).

## Storage layout (per project)
```
<project>/.codx/browser_scripts/index.json        # catalogue (self-healing, rebuilt from folders)
<project>/.codx/browser_scripts/.trash/           # soft deleted scripts
<project>/.codx/browser_scripts/<id>/script.json  # metadata
<project>/.codx/browser_scripts/<id>/script.<ext> # json | js | py
<project>/.codx/browser_scripts/<id>/versions/v<N>.<ext>
```

## Design decisions
- `id` (uuid) is canonical; `title`/`site` are labels only → renaming never moves a folder.
- `save_script` updates in place when given `script_id` **or** when title+site already exist → archives previous body to `versions/`, bumps `version`, keeps `uses`/`created_at`. Max 10 archived versions.
- `language="steps"` (default) = JSON array of `browse_action` vocabulary steps, replayed by the browser layer.
- **Scripts are data, never code**: no `eval`/`exec` of model-written Python in the API process. `javascript` scripts are meant for in-page evaluation only.
- Deletes are soft (`.trash/`) unless `hard=True`.
- `normalize_site()` maps URL → site key (`https://www.GitHub.com/x` → `github.com`), with parent/subdomain matching.

## Registration
In `codx/junior/tools/__init__.py` (1600+ lines — **read before rewriting**):
```python
from codx.junior.tools.browser_script_registration import register_browser_script_tools
# after the registry object (TOOLS / tools dict) is built:
register_browser_script_tools(TOOLS)
```
In `codx/junior/profiles/browser.profile`, add to `tools:`:
`list_browser_scripts`, `get_browser_script`, `save_browser_script`, `delete_browser_script`.

## Pending
`run_browser_script`: replay `store.get_script(id).steps` through the existing `browse_action` plumbing.