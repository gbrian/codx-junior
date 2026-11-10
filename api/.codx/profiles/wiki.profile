{
  "name": "wiki",
  "url": "",
  "avatar": "https://avatar.iran.liara.run/public/job/teacher/female",
  "description": "codx-junior-api docs: internal architecture, setup and operations",
  "category": "project",
  "file_match": "",
  "content": "# codx-junior-api — backend documentation profile\n\n## Purpose\nThis project is the **codx-junior backend API**. Its wiki documents how the\nplatform works internally and how to set it up, extend it and operate it.\n\n## What to document\n- FastAPI app initialization, middleware and router discovery.\n- Sessions, settings, project discovery and security.\n- Chat, agents, profiles and model routing.\n- Knowledge ingestion, embeddings, Milvus and search.\n- Change detection, background workers, orchestration and the wiki scheduler.\n- Wiki generation, docs manifest, assistant and search.\n- DSH harness integration: agent channel, registry, commands, events and board\n  mirroring.\n- Workspaces, containers, Traefik and infrastructure.\n- Setup, environment variables, tests and troubleshooting.\n\n## Architecture pages\nUse Mermaid for:\n- request lifecycle and middleware,\n- router/module boundaries,\n- chat and agent execution,\n- knowledge ingestion and retrieval,\n- background workers and the wiki pipeline,\n- DSH register/heartbeat/command/event flow.\n\n## Style\n- Write for backend contributors and operators.\n- Lead with the responsibility of a module, then its API, then internals.\n- Document real endpoints, request/response shapes and failure modes.\n- Use tables for configuration keys and environment variables.\n- Include runnable examples for API calls and tests.\n- Link UI behavior to `codx-junior-ui` instead of duplicating it.\n\n## Images\nUse diagrams and optional screenshots for dashboards or setup screens:\n\n![Figure 3: DSH Harness settings and instance dashboard](/wiki/images/figure-03-dsh-settings.png)\n\n*Figure 3 — Global Settings → DSH Harness, showing a registered instance and\nthe token controls.*\n\nKeep captions immediately below the image and describe the configuration or\nstate shown.\n",
  "path": "/home/codx-junior/codx-junior/api/.codx/profiles/wiki.profile",
  "content_path": "/home/codx-junior/codx-junior/api/.codx/profiles/wiki.profile.md",
  "profiles": [],
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
    "api_key": ""
  },
  "tools": [],
  "tags": [],
  "api_settings": {
    "active": false,
    "model_name": null,
    "description": null
  },
  "chat_mode": null,
  "project_id": null,
  "chat_id": ""
}