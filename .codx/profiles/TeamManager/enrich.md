## Profile content: no hardcoded tool names

## Never hardcode tool names in profile content (.md)

Tool names can change (rare) and their full names + signatures are already injected in the LLM message at runtime. Repeating them in the profile content is redundant and drifts.

- Describe the **capability/concept** ("the browser script library lets you list, read, save and delete reusable scripts"), never the exact tool names or JSON parameter schemas.
- Do not paste tool parameter examples (e.g. `save_browser_script(name=..., site=..., script=...)`).
- Do NOT say "the tools are listed at runtime" either — that is meta-instruction noise; the model already sees the tool definitions.
- Phrase guidance as intent + recommendation ("reuse an existing script for the site when there is one; save a step that worked"), so the model maps it to whatever tool signature exists.
- `tools` in the `.profile` JSON must still reference real registry names (validated on save) — the rule only concerns the Markdown content.
