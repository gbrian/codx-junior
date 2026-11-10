{
  "name": "wiki",
  "url": "",
  "avatar": "https://api.dicebear.com/10.x/glyphs/svg?seed=wiki",
  "description": "codx-junior public docs: product landing page, install, usage and DSH integration",
  "category": "project",
  "file_match": "",
  "content": "# codx-junior — public documentation profile\n\n## Purpose\nThis wiki is the **main public web page for codx-junior** and the first place a\nvisitor, evaluator, or new user should land. It must explain what codx-junior is,\nwhy it exists, how to install it, and how to use it. It is both the marketing\nfront door and the user guide.\n\n## Audience\n- People evaluating codx-junior for the first time.\n- Developers installing and operating the platform.\n- Users learning the app screen by screen.\n- Teams adopting the DSH harness, workspaces, chats, Kanban, teams and browser\n  sessions.\n\n## Required narrative\n1. **What is codx-junior** — the hybrid AI + human workspace, the problem it\n   solves and who it is for.\n2. **Install and run** — prerequisites, Docker/local installation, configuration,\n   first login and a working \"hello world\" flow.\n3. **Tour of the app** — the main screens and how to move between them.\n4. **Core workflows** — chats and agents, Kanban/sprints, workspaces, teams,\n   knowledge, wiki, browser/computer sessions, Git and code review.\n5. **DSH harness integration** — first-class section with the outbound channel,\n   token setup, board sync, triggering tasks and the headless contract.\n6. **Operations** — deployment, upgrades, security, backups and troubleshooting.\n7. **Reference** — API entry points and configuration keys for advanced users.\n\n## Landing page\nThe home page must work as a modern product landing page:\n- a clear hero (name, one-line pitch, two short paragraphs),\n- primary actions: **Get started**, **Explore the app**, **DSH integration**,\n- feature cards for the main capabilities,\n- a \"quick start in 5 minutes\" block,\n- a \"choose your path\" block (user, operator, contributor),\n- links to the child project wikis (`codx-junior-ui`, `codx-junior-api`),\n- a final call to action.\n\nDo not make the landing page a file index or an API reference.\n\n## Images\nLeave deliberate space for screenshots. When a screen or workflow should have\nan image, add this pattern (the files will be supplied later):\n\n![Figure 1: Desktop workspace with chat and Kanban](/wiki/images/figure-01-desktop-workspace.png)\n\n*Figure 1 — Description of what the screenshot shows and why it matters.*\n\nRules:\n- Use a numbered, descriptive filename under `images/` or `/wiki/images/`.\n- Always include a useful alt text and a caption line immediately below.\n- Describe the screen, the action being shown and the outcome.\n- Leave the image line and caption even when the image file does not exist yet.\n- Prefer one focused screenshot per section over long image galleries.\n\n## Style\n- Write for a smart reader who has never seen codx-junior.\n- Start every page with a TL;DR, then what the reader will learn.\n- Use numbered steps for setup and tasks.\n- Use tables for comparisons and settings.\n- Use Mermaid for architecture and flows, not for marketing decoration.\n- Use callouts for prerequisites, tips and pitfalls.\n- Link to the child project wikis instead of duplicating their internals.\n- Never copy documentation from other products or unrelated AI tools.\n\n## DSH\nThe DSH harness must be easy to find and clearly explained. Explain:\n- the DSH Host plugin and the outbound registration/heartbeat/command channel,\n- how to generate and configure the agent token,\n- the DSH board mirror and live task conversation,\n- how to trigger a task and sync sessions,\n- the security boundary (DSH calls codx-junior, never the reverse).\n",
  "parsed_content": null,
  "path": "/home/codx-junior-projects/codx-junior/.codx/profiles/wiki/wiki.profile",
  "profiles": [
    "biblio",
    "file_editor"
  ],
  "llm_model": "",
  "use_knowledge": true,
  "user": {
    "username": "",
    "email": "",
    "avatar": "",
    "theme": "dim",
    "projects": [],
    "role": "user",
    "token": "",
    "disabled": false,
    "github": "",
    "apps": [],
    "api_key": "",
    "env": {},
    "wallet": {
      "wallet_id": "6458cb27-df8f-401b-a806-340d3d24b757",
      "name": "Default Wallet",
      "balance_cxjcoins": 0.0,
      "spending_limits": [],
      "transactions": [],
      "created_at": "2026-08-14T06:03:50.373847",
      "updated_at": "2026-08-14T06:03:50.373858",
      "enabled": true
    },
    "github_admin": false,
    "github_only": false,
    "token_limit_rules": [],
    "token_limit_requests": []
  },
  "tools": [],
  "tags": [],
  "api_settings": {
    "active": false,
    "model_name": null,
    "description": null
  },
  "guardrails": {
    "enabled": false,
    "scope": null,
    "scope_keywords": [],
    "scope_similarity_threshold": 0.35,
    "allowed_tools": [],
    "refusal_message": "I can only answer questions within my configured scope.",
    "risk_threshold": 10.0,
    "use_llm_classifier": false
  },
  "chat_mode": null,
  "project_id": "d4e4b4a9-2281-4970-bff1-f845b4d98456",
  "chat_id": ""
}