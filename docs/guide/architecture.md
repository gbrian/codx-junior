# Architecture

codx-junior is a set of Docker services behind a Traefik reverse proxy. Everything is reachable from a single domain, so users only need a browser.

```
browser ──► Traefik (80/443) ──┬──► codx-junior-client   Vue 3 + Vite          :19981
                               ├──► codx-junior-api      FastAPI + Socket.IO   :19980  (/api)
                               ├──► workspaces           Docker Compose dev containers
                               ├──► LocalAI / LiteLLM    model serving (optional)
                               └──► Traefik dashboard    (/traefik, admins only)

codx-junior-api ──► codx-junior-api-background   watchers, indexing, long running jobs
                ──► Milvus                       vector store for knowledge
                ──► Docker socket                workspaces and docker tools
```

## Services

| Service | Role |
| --- | --- |
| `codx-junior-client` | The web application (`client/`). Vue 3, Vite, Tailwind and daisyUI. |
| `codx-junior-api` | The backend (`api/codx/junior`). REST API under `/api`, real-time events over Socket.IO at `/api/socket.io`, OpenAPI docs at `/api/docs`. It also exposes `/api/forward-auth`, used by Traefik to protect every routed app. |
| `codx-junior-api-background` | Same image as the API, started with `CODX_JUNIOR_API_BACKGROUND=1`. Runs file watchers, knowledge indexing, `@codx` mentions and other background work. |
| `milvus` | Vector database used by the knowledge engine. |
| `localai` | Optional local model server for chat and embeddings. |
| `traefik` | Reverse proxy, TLS (Let's Encrypt) and dynamic routes for workspaces, read from `/api/traefik/config`. |

## Backend modules

The API code lives in `api/codx/junior`:

| Module | What it does |
| --- | --- |
| `chat/`, `chat_manager.py` | Chat engine, chat storage, chat modes and the bridge to Socket.IO events. |
| `ai/` | Provider clients (OpenAI-compatible, Ollama, vLLM), the tool-calling agent loop (`ai/smol`), cancellation, raw AI logs and wallet checks. |
| `tools/` | Tools agents can call: project search, read/write files, apply patches, web fetch and DuckDuckGo search, images, Docker and Docker Compose, Git, tasks, tutorials and recipes. |
| `agents/` | Specialised agents such as the GitHub issues agent. |
| `knowledge/`, `engine/knowledge_engine.py` | Code splitting, embeddings, Milvus storage, AI search and knowledge graph. |
| `profiles/` | Profile manager and the built-in profiles. |
| `mentions/` | `@codx` mention detection and processing in project files. |
| `engine/git_engine.py`, `api/git.py` | Branches, commits, diffs and pull-request views. |
| `wiki/` | AI-maintained project wiki. |
| `workspaces/` | Workspace templates, Docker Compose generation and lifecycle. |
| `analytics/` | Token and cxjcoin accounting, usage queries and dashboards. |
| `security/` | Users, roles, permissions, API keys and GitHub OAuth. |
| `plugins/` | Plugin loading and execution. |

## Frontend

The client (`client/src`) is organised by feature under `components/`: `chat`, `kanban`, `vibe`, `workspaces`, `teams`, `messenger`, `knowledge`, `repo`, `wiki`, `analytics`, `security`, `ai_settings`, `global_settings` and more. State lives in Vuex stores (`store/`), and the main routes are:

| Route | View |
| --- | --- |
| `/` and `/chats/...` | Quick chat: the launcher home with recent chats and workspace apps |
| `/kanban` | Kanban boards |
| `/workspaces/...` | Workspaces |
| `/messenger` | Teams and messenger |
| `/desktop/...` | Desktop with windows and tabs |
| `/analytics` | Usage and cost dashboard |
