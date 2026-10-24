---
title: codx-junior features
description: Complete reference of every feature and functionality of the codx-junior platform.
---

# codx-junior — Complete feature reference

> **● SYSTEM STATUS: ACTIVE BETA // OPEN SOURCE** — Licensed under **AGPL-3.0**.

**codx-junior is the open-source workspace transforming how software projects are built.**
It pairs cutting-edge AI models with veteran human developers so that every change is
reviewed and steered. A single developer can lead and ship complex IT projects **4x faster**,
working entirely from a browser: Kanban, dev containers, agents and team chat in one tab.

This page is the single, complete catalogue of **all features and functionalities** of the
platform. It is written for final users (developers, tech leads, admins) and covers the
product features, the platform and infrastructure, and the development tooling.

---

## Contents

1. [Overview](#_1-overview)
2. [Chats and agents](#_2-chats-and-agents)
3. [Kanban and tasks](#_3-kanban-and-tasks)
4. [Vibe coding](#_4-vibe-coding)
5. [Workspaces (dev containers)](#_5-workspaces-dev-containers)
6. [Teams and messenger](#_6-teams-and-messenger)
7. [Knowledge (RAG)](#_7-knowledge-rag)
8. [Profiles](#_8-profiles)
9. [@codx mentions](#_9-codx-mentions)
10. [Wiki](#_10-wiki)
11. [Git and code review](#_11-git-and-code-review)
12. [AI providers and models](#_12-ai-providers-and-models)
13. [Budget, wallets and analytics](#_13-budget-wallets-and-analytics)
14. [Users, roles and security](#_14-users-roles-and-security)
15. [Development tools](#_15-development-tools)
16. [Plugins](#_16-plugins)
17. [API](#_17-api)
18. [Platform, installer and scripts](#_18-platform-installer-and-scripts)
19. [Architecture](#_19-architecture)
20. [Feature matrix](#_20-feature-matrix)

---

## 1. Overview

codx-junior is a set of Docker services behind a **Traefik** reverse proxy. Everything is
reachable from a single domain, so users only need a browser to work.

| Pillar | What it gives you |
| --- | --- |
| **Plan** | Kanban boards where every card is a chat with sub-tasks, checklists and assignees. |
| **Build with AI** | Project-aware chats and tool-using agents, plus vibe coding with live diffs and preview. |
| **Run** | Docker Compose dev containers (workspaces) with VS Code, a virtual desktop and your own apps. |
| **Collaborate** | Teams, categories, channels and direct messages shared by humans and agents. |
| **Keep context** | Knowledge (RAG) index, reusable profiles and an AI-maintained wiki. |
| **Ship** | Git branches, diffs, pull-request views and GitHub issues. |
| **Control** | cxjcoins, per-user wallets, spending limits and usage analytics. |
| **Extend** | Python plugins and an OpenAI-compatible API for the profiles. |

### The hybrid model

* **AI agents** search the codebase, write and patch files, run containers, generate images
  and documentation, and review changes.
* **Humans** define the work on the Kanban board, pick the profiles and models the agents
  use, review every diff and pull request, and talk to each other and to the agents.
* **Budget** is visible at all times: AI usage is metered in tokens and **cxjcoins** per user
  and model, next to the human hours you plan.

---

## 2. Chats and agents

Everything in codx-junior is a chat: a quick question, a Kanban task, a team channel or a
pull-request review. Chats belong to a project, so the AI always works with that project's
files, knowledge and settings.

### Starting a chat

From the home screen (quick chat) type a message, or create a chat from a Kanban column.
For each chat you can choose:

* the **mode** (see [Chat modes](#chat-modes)),
* one or more **profiles** that shape the AI's behaviour,
* the **LLM model** to use,
* the **users** involved,
* **files** and **attachments** (images, documents, other chats) to add to the context.

Chats can be **nested**: a chat can have sub-chats (sub-tasks), threads on a message, and
links to other chats. A sub-chat can inherit its parent's messages, files and knowledge, or
ignore them.

### Chat modes

| Mode | Use it to |
| --- | --- |
| `chat` | Have a normal conversation with the AI about the project. |
| `task` | Refine a single document, such as a specification or a plan, message after message. |
| `agent` | Let the AI use tools in a loop to complete the work. |
| `vibe` | Code with the AI while watching the file changes and the app preview. |
| `topic` | Run a team channel where people and AI post messages. |
| `prview` | Review a pull request or a branch comparison. |
| `browser` | Work with a web page inside the chat. |
| `slides` | Produce a presentation. |
| `tutorial` | Write a tutorial organised in chapters. |

### Agent tools

When tools are enabled, agents can call:

| Group | Tools |
| --- | --- |
| Project | `project_search`, `project_read_file`, `project_write_file`, `apply_file_changes`, `project_structure`, `read_folder`, `code_writer`, `get_file_last_version` |
| Web | `fetch_webpage`, `duckduckgo_search` |
| Images | `explain_image`, `generate_image` |
| Tasks | `create_task`, `process_task` |
| Docker | `docker_ps`, `docker_logs`, `docker_stats`, `docker_inspect`, `docker_images`, `docker_run`, `docker_start`, `docker_stop`, `docker_restart` and the Docker Compose equivalents |
| Tutorials and recipes | create, modify and delete chapters; list, start and complete recipe steps |

Projects can also register **MCP servers** in their settings.

::: tip Agent guardrails
The agent loop protects itself against runaway behaviour with a maximum number of iterations
(**Global settings → Agents**), a maximum number of tool calls per provider, loop detection
and a **cancel** button that stops the request at once. Every call is checked against the
user's budget before it is sent.
:::

### Working with messages

* Edit, delete, hide or pin messages, and mark them as read.
* Search inside a chat and across chats.
* Use the mini map and the chat navigator to move around long conversations and sub-chats.
* Upload images and documents, record voice messages, and export a chat.
* Add checklists and tags, and change the chat status.
* Create a chat from a URL, such as a GitHub issue.

---

## 3. Kanban and tasks

The Kanban board is where humans plan the work and hand it to the AI.

### Boards

Each project can have several boards. A board has a name, a description, an optional remote
URL and its **columns** (for example *Backlog*, *To Do*, *In Progress*, *Done*). Boards can be
bookmarked and switched from the sidebar.

### Tasks are chats

Every card on a board is a **chat**. Opening a card opens the conversation, so a task can be
discussed with the team, refined into a specification and executed by an agent, all in one
place.

A task can have:

* a status, tags and assigned users,
* profiles and a model,
* linked files and attachments,
* checklists,
* **sub-tasks**, created by hand or generated by the AI from the parent task.

### Views

Switch between the **board** view (columns and cards), a **grid** view with filters, and a
**tree** view of tasks and sub-tasks. The Kanban panel is also available next to the
conversation in [vibe coding](#4-vibe-coding).

### Templates

Mark a chat as a **template** to reuse it when creating new tasks.

---

## 4. Vibe coding

Vibe coding puts the conversation, the code and the running app side by side so you can build
fast while seeing every change.

### Layout

* **Chat panel**: the conversation with the AI, in `vibe` mode.
* **Changes panel**: the files the AI changed, with diffs you can review.
* **Preview panel**: your app running in a workspace.
* **Kanban panel** (optional): pick another task without leaving the view.

Each panel can be shown or hidden, and the layout is resizable.

### Workflow

1. Open a task and switch it to vibe coding.
2. Describe what you want. The AI edits the files of the project.
3. Review the diff in the changes panel and check the result in the preview.
4. Split the work into sub-tasks, add tags, or jump to the parent task from the header.
5. Select a branch and review the branch's changes or search pull requests from the same view.

---

## 5. Workspaces (dev containers)

Workspaces are dev containers managed by codx-junior. They run your projects with Docker
Compose and publish their apps through Traefik, so the whole team works from the browser.

### Templates

| Template | What it creates |
| --- | --- |
| `dev-stack` | A `devbox` container running with Sysbox: systemd and its own Docker daemon, without `--privileged` or the host Docker socket. Good for full stack development. |
| `static-site` | An `app` container (default image `node:22-slim`) that runs `npm install && npm run dev`. The image and command can be changed with the `IMAGE` and `COMMAND` variables. |
| `custom` | Your own `docker-compose.yaml`. codx-junior can generate the files with AI from a description. |

### Settings

* **Projects** mounted into the workspace.
* **Users** allowed to use it (empty means everyone).
* **Apps**: name, icon, path, port and scheme. Each app is published under a path on your
  domain and protected by codx-junior's login.
* **Environment variables** and **resources** (CPUs, memory, shared memory).
* **Sysbox** on or off.

The workspace files (compose file, Dockerfile, env) can be edited from the UI. You can start,
stop and restart workspaces, follow their status (`stopped`, `starting`, `running`, `error`)
and read their logs.

### Default apps

The default workspace includes:

* **Coder**: VS Code in the browser, with extensions and Docker support.
* **Desktop**: a virtual desktop (noVNC or Kasm VNC) to test your app like a user.
* **LiteLLM**: the model manager UI.
* **Traefik**: the proxy dashboard.

Apps from all your workspaces appear in the home screen and in the workspaces menu, and open
in tabs or windows on the desktop.

---

## 6. Teams and messenger

The messenger brings people and AI agents into the same conversations.

* A **team** has a name, icon, colour and members.
* Channels are grouped in **categories**.
* Each **channel** is backed by a chat in `topic` mode, so agents can read it, answer, and use
  the project's knowledge.
* **Direct messages** between members.
* A **media library** collects the files and images shared in the team.

### Working together

* Mention users and profiles in any chat to bring them in.
* Assign users to Kanban tasks.
* Share a chat or a view with a link.
* Receive notifications for new messages and finished AI work.

---

## 7. Knowledge (RAG)

codx-junior indexes each project so the AI can find the right code and documents before it
answers or acts.

### How it works

1. Project files are split into chunks with a code-aware splitter.
2. Chunks are embedded with the project's **embeddings model** and stored in **Milvus**.
3. When a chat or an agent needs context, codx-junior searches the index, filters the results
   by relevance and passes them to the model.
4. The background worker re-indexes files as they change when **watching** is on.

### Search

* **Similarity search** with a configurable number of documents and relevance cutoffs.
* **AI search**: the model rewrites the query, searches with several terms and validates the
  results.
* **Keywords** and a **knowledge graph** help connect related files.
* Agents use the `project_search` tool with one or many queries at once.

### Knowledge settings

Open **Settings → Knowledge settings** to:

* see index statistics and the list of indexed files,
* reload a single path or the whole project,
* delete sources from the index,
* edit **ignore patterns**,
* add **external folders** and include **sub-projects**,
* tune the search type, document count, relevance cutoff and RAG distance,
* enable tag extraction and document enrichment.

::: tip Chats as knowledge
Chats can also be indexed: give a chat **knowledge topics** and its content becomes searchable
knowledge for the project.
:::

---

## 8. Profiles

Profiles are reusable instructions that tell the AI how to behave. They encode your coding
standards, your architecture and your preferences.

### What a profile contains

| Field | Description |
| --- | --- |
| Name, avatar, description | How the profile appears in chats and mentions. |
| Category | `global`, `file`, `coding` and others. |
| File match | A pattern; the profile is applied automatically to matching files. |
| Content | The instructions, in Markdown. |
| Linked profiles | Other profiles to include. |
| Model | The LLM the profile uses. |
| Tools | The agent tools it may call. |
| Use knowledge | Whether the profile searches the project's knowledge. |
| Chat mode | Changes how the conversation works, for example writing a document instead of chatting. |
| API settings | Expose the profile as a model through the OpenAI-compatible API. |

### Built-in profiles

codx-junior ships with profiles such as **analyst**, **software developer**, **teacher**,
**browser**, **project** and **wiki**. Use them as they are or as a starting point.

### Using profiles

* Pick profiles for a chat or a Kanban task.
* Mention a profile in a message to bring it into the conversation.
* Let file-matching profiles apply automatically when the AI edits matching files.
* Edit profiles from the profile view, or ask the AI to improve a profile from a chat.

---

## 9. @codx mentions

Talk to codx-junior from inside your files. Write a comment that starts with `@codx` in any
project file and save it; the background worker picks it up when the project is being watched.

```js
// @codx: add input validation and return a 400 error when the email is missing
function createUser(req, res) {
  ...
}
```

codx-junior can:

* change the file as requested,
* explain a piece of code,
* suggest improvements.

While it works, the mention is marked with `codx-ok, please-wait...`. If something goes wrong
it is marked with `codx-error`.

### Formats

| Format | Example |
| --- | --- |
| Single line | `@codx: refactor this function --knowledge` |
| Multi-line block | `<codx> ...instructions on several lines... </codx>` |
| Block with attributes | `<codx model="my-model"> ... </codx>` |

Flags are written as `--flag` or `--option=value`:

| Flag | Effect |
| --- | --- |
| `--knowledge` | Search the project's knowledge before changing the file. |
| `--model=<name>` | Use a specific model. |
| `--chat-id=<id>` | Continue an existing chat. |
| `--code` | Treat the request as a code change. |
| `--image` | Work with images. |
| `--vibe` | Use vibe coding mode. |

::: tip
Turn on **Watching** in the project settings so mentions are processed automatically. Turn on
**Save mentions** to keep a chat for each mention.
:::

---

## 10. Wiki

The wiki is the project's documentation, written and maintained by the AI.

### Structure

The wiki goes from a bird's-eye view down to the details:

* **The project**: overview, objectives, the problems it solves and a flowchart.
* **Project modules**: each module's responsibility, with class diagrams.
* **Visual documentation**: flowcharts, class and sequence diagrams (Mermaid).
* **Testing requirements**: functional, integration, unit and acceptance tests.

### Keeping it fresh

When the project is watched, file changes are processed by the wiki engine, which updates the
affected pages with the **wiki model**. You can also build or rebuild the wiki on demand.

### Enabling the wiki

Turn the wiki on in **Project settings** and choose its folder. Then open it from the wiki view,
with its section tree and settings.

---

## 11. Git and code review

codx-junior keeps humans in charge of what gets merged. Every change made by an agent is
visible, explained and reviewable.

### Changes

* See committed and uncommitted changes of the project, with diffs.
* Ask codx-junior to explain a change or to suggest improvements.
* Add comments on a diff and let the AI answer them.
* Restore a file to its last committed version.

### Branches and pull requests

* Browse branches and their commits in a commit tree.
* Compare two branches or pick commits to build a **PR view**.
* Review the PR file by file, in different view modes, with an AI-generated report.
* Open a PR review as a chat in `prview` mode to discuss it with the team and the AI.

### GitHub issues

Paste the URL of a GitHub issue to read it inside codx-junior. The GitHub issues agent
summarises the discussion, finds the related code, reasons about the problem and proposes
sub-tasks to solve it.

### Plugins

Code review can be extended with plugins, for example the Azure DevOps pull requests plugin.

---

## 12. AI providers and models

codx-junior works with any **OpenAI-compatible** provider: OpenAI, Ollama, LocalAI, LiteLLM,
vLLM and others. Mix cloud and local models as you like.

### Providers

A provider has a name, an API URL, an API key and optionally an admin URL and a pricing URL.
You can set its cost in cxjcoins per 1K tokens and limits on tool calls and tool loops per
request.

### Models

Add the models you want from each provider. A model can override the provider's price and
limits. Reload the model list at any time from the provider.

### Models by purpose

Choose a default model for each purpose in **Global settings**, and override it per project:

| Purpose | Used for |
| --- | --- |
| LLM | Chats, tasks and agents |
| RAG | Knowledge search |
| Embeddings | Indexing files |
| Wiki | Wiki pages |
| Vision | Reading images and screenshots |
| Image | Generating images |

Each chat, profile or `@codx` mention can also pick its own model.

### Local models

The installer includes **LocalAI** for running models on your own hardware, reachable at
`/codx-localai/app` and protected by codx-junior's login. The API image also supports **vLLM**
on CPU and **sentence-transformers** for local embeddings.

### MCP servers

Projects can register **MCP servers** (name, URL, API key and an active flag) in their settings.

---

## 13. Budget, wallets and analytics

codx-junior makes AI cost visible and controllable, so you can plan a project with transparent
human hours on one side and scalable AI tokens on the other.

### cxjcoins

Every AI call records its input and output tokens and converts them into **cxjcoins**,
codx-junior's internal unit of cost. Prices are set per 1K tokens at provider level and can be
overridden per model. Providers can link to their pricing page so prices are easy to keep up to
date.

### Wallets

Each user has a wallet with:

* a **balance** in cxjcoins,
* a list of **transactions** (credits and AI charges with their token usage),
* **spending limits** per day, week or month.

Before a request is sent, codx-junior checks the user's balance and limits and blocks the call
if it would go over.

### Token limit rules

Admins can add daily token limits per user, globally, per provider or per model. When a user
hits a limit they can **request an extension** with a reason; an admin approves it (with extra
tokens or an extra percentage for that day) or rejects it.

### Analytics dashboard

The **Analytics** view shows:

* total tokens and cxjcoins for a period,
* a **daily** chart,
* usage **by model**, by user and by project,
* a **price editor** for models.

Users see their own usage; admins see everyone's. Admins can also open the raw AI logs and the
chat logs from **Settings → Miscellaneous**.

---

## 14. Users, roles and security

### Users and roles

Admins manage users in **Global settings → Users**. Each user has:

* a username, email, avatar and theme,
* a **role**: `admin` or `user`,
* **project permissions**, optionally inherited by sub-projects,
* access to specific **workspace apps**,
* personal **environment variables**,
* a wallet and token limits.

Users can be disabled without being deleted.

### Signing in

* **Username and password.** The `admin` user sets its password on the first login.
* **GitHub OAuth.** Configure an OAuth provider in **Global settings → OAuth**. GitHub accounts
  listed as admins get the admin role. A user can be restricted to GitHub-only login.

### Protecting apps

Every app routed by Traefik (workspace apps, LocalAI, the Traefik dashboard) goes through
codx-junior's **forward-auth** endpoint (`/api/forward-auth`). Only signed-in users with access
to that app can open it.

### Settings history

Global settings are versioned by section. Admins can review previous versions and roll back a
change.

---

## 15. Development tools

### Desktop

The desktop is a window manager inside the browser. Open chats, workspace apps, the Kanban board
and settings as tabs or windows, group them, and save the layout as a **view** you can reopen or
share.

### Coder

**Coder** is VS Code in the browser, running in a workspace. It supports VS Code extensions and,
when Docker is available, containers.

### Virtual desktop and preview

A virtual desktop (noVNC or Kasm VNC) lets you test your app like a user would, with a real
browser. The **preview** panel shows the project's preview URL next to the conversation.

### File browser

Browse, search, preview, upload, download, create, rename, move, copy, archive and delete project
files from the UI, and add them to a chat.

### Project scripts

Define named bash scripts per project (build, test, run). Scripts can run in the background,
restart automatically when they stop, and be launched from the UI.

### Logs

Admins can follow the API and system logs, the AI raw logs and the chat logs from
**Settings → Miscellaneous**.

---

## 16. Plugins

Plugins extend codx-junior with your own Python code.

### Managing plugins

Admins manage plugins in **Global settings → Plugins**: load a plugin from a file, edit its
definition, run it, or remove it.

A plugin definition includes:

| Field | Description |
| --- | --- |
| `name`, `description`, `image` | How the plugin appears in the UI. |
| `module_path`, `plugin_path`, `method` | The Python entry point to run. |
| `arguments` | Named arguments with descriptions and default values. |
| `roles` | Who can run it. |
| `extends` | The parts of the UI it extends. |
| `async` | Whether it runs asynchronously. |

### Included examples

The `plugins/` folder of the repository contains:

* **azuredevops**: list and review Azure DevOps pull requests.
* **image_editor**: an image editing service.
* **guide-model**: a lightweight service that answers questions about a project from a guide
  document using small models.
* **claude**: a Docker setup to run an external coding agent container next to codx-junior.

---

## 17. API

### REST API

The backend is a FastAPI application served under `/api`. Interactive documentation is available
on your instance at:

* `/api/docs` (Swagger UI)
* `/api/redoc`
* `/api/openapi.json`

Real-time events (chat streaming, notifications, progress) use **Socket.IO** at
`/api/socket.io`.

Requests are authenticated with the user token returned by `POST /api/users/login`.

### OpenAI-compatible endpoint

Any profile can be exposed as a model. Turn on **API settings → active** in the profile and
optionally give it a model name and description. Then use it from any OpenAI-compatible client:

| Endpoint | Description |
| --- | --- |
| `GET /api/v1/models` | Lists the profiles exposed as models, named `<project>/<profile>` unless a model name is set. |
| `POST /api/v1/completions` | Sends chat `messages` to a `<project>/<profile>` model and returns a chat completion. |

This lets you plug codx-junior's project-aware assistants into other tools, such as IDE
extensions.

---

## 18. Platform, installer and scripts

### Docker Compose stack

The self-hosted stack is defined in `codx-junior-installer/codx-junior/docker-compose.yaml` and
starts the following services:

| Service | Purpose |
| --- | --- |
| `traefik` | Reverse proxy on ports 80 and 443, TLS (Let's Encrypt) and dynamic routes. |
| `codx-junior-client` | The web application (port 19981). |
| `codx-junior-api` | The API (port 19980, served under `/api`). |
| `codx-junior-api-background` | Background jobs: watchers, indexing, `@codx` mentions. |
| `milvus` | Vector store for knowledge. |
| `localai` | Optional local model server. |
| `codx-junior-init` | One-shot initial setup container. |

Projects are stored on the host under `/home/codx-junior-projects`, and global settings are kept
in the `codx-junior` Docker volume.

### Environment variables

Configured in `.env` (installer) and read by the API through `set_env.sh`:

| Variable | Description | Default |
| --- | --- | --- |
| `CODX_JUNIOR_DOMAIN` | Host name Traefik routes on. | `localhost` |
| `ACME_EMAIL` | Email for Let's Encrypt certificates. | `mail@mail.com` |
| `USER_ID`, `GROUP_ID` | Host user and group ids used for file permissions. | `911` |
| `LITELLM_MASTER_KEY`, `LITELLM_SALT_KEY` | Keys for the optional LiteLLM model manager. | — |
| `CODX_JUNIOR_PROJECTS_PATH` | Root folder for cloned projects. | `/home/codx-junior-projects` |
| `CODX_JUNIOR_API_VENV` | Python virtual environment used by the API. | `/tmp/.venv_codx_junior_api` |
| `CODX_JUNIOR_API_LOGS` | Folder for API logs. | `/tmp/codx-junior-logs` |
| `CODX_JUNIOR_API_PORT` | Primary API port. | `19980` |
| `CODX_JUNIOR_WEB_PORT` | Web (client) port. | `19981` |
| `CODX_JUNIOR_API_PORT_BACKGROUND` | Background worker port. | `19984` |
| `CODX_JUNIOR_CONFIG_FOLDER` | Folder where global settings, users and chats are stored. | `/home/codx-junior/codx-junior-global-settings.json` |
| `CODX_JUNIOR_WORKSPACES_FOLDER` | Root folder for workspace files. | `${CODX_JUNIOR_CONFIG_FOLDER}/workspaces` |
| `CODX_JUNIOR_DEFAULT_WORKSPACE_PATH` | Workspace templates folder. | `…/workspace-templates` |
| `CODX_JUNIOR_MILVUS_URL` | Milvus endpoint. | `http://milvus-codx-junior:19530` |
| `CODX_JUNIOR_MILVUS_UI_URL` | Milvus health and UI endpoint. | `http://milvus-codx-junior:9091` |
| `CODX_JUNIOR_LLMFACTORY_URL` | LiteLLM gateway URL. | `http://litellm-codx-junior:4000/v1` |
| `CODX_JUNIOR_API_ANALYTICS_DATA_PATH` | Folder for usage analytics data. | `/home/codx-junior/analytics` |
| `CODX_JUNIOR_AI_RAW_LOG_PATH` | Folder for raw AI request and response logs. | `/home/codx-junior/analytics/chats` |
| `USER_PORT_RANGE_START` / `USER_PORT_RANGE_END` | Reserved app port range. | `99000` / `99050` |
| `CODX_JUNIOR_APPS` | Applications to install. | `client api` |
| `CODX_JUNIOR_HIDDEN` | Hides codx-junior's own project from the projects list. | `0` |

### CLI (`codx-junior`)

The root `codx-junior` script is the control CLI:

```bash
bash codx-junior install     # run the installers (client + api)
bash codx-junior start       # stop, then start api + client
bash codx-junior stop        # stop supervisor, api and client
bash codx-junior status      # check the pid files
bash codx-junior logs <app>  # tail logs (api | client | supervisor)
bash codx-junior supervisor  # run supervisord
```

### Scripts (`scripts/`)

| Script | Purpose |
| --- | --- |
| `install.sh` | Fixes the user id/group, then runs the per-app installers. |
| `install_api.sh` | Creates the Python venv with `uv` (Python 3.11) and installs the API package. |
| `install_client.sh` | Installs node (v24) and builds the Vue client. |
| `run_api.sh` | Runs `uvicorn codx.junior.main:app` (production or debug). |
| `run_client.sh` | Serves the built client. |
| `run_docker.sh` | Starts the Docker daemon helper for the container. |
| `run_llmFactory.sh` | Runs the LiteLLM model manager. |
| `run_browser*.sh` | Runs the browser automation service. |
| `entrypoint.sh` | Container entrypoint: install on first run, then supervisor. |

### Installer folder (`codx-junior-installer/`)

* `codx-junior/`: the compose stack, `Dockerfile`, `build.sh`, `push-images.sh`,
  `initial-setup.sh`, Traefik and Milvus config, and the workspace templates.
* `codx-junior-dind/`: a Docker-in-Docker base image for isolated instances (plus a Coolify
  install helper).
* `vllm/`: helper to run a vLLM model locally.

### Build

```bash
# Build the Docker images used by the stack
bash build-docker.sh
```

---

## 19. Architecture

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

### Backend modules (`api/codx/junior`)

| Module | What it does |
| --- | --- |
| `chat/`, `chat_manager.py` | Chat engine, chat storage, chat modes and the bridge to Socket.IO events. |
| `ai/` | Provider clients (OpenAI-compatible, Ollama, vLLM), the tool-calling agent loop, cancellation, raw AI logs and wallet checks. |
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

### Frontend (`client/src`)

The client is a Vue 3 SPA organised by feature under `components/`: `chat`, `kanban`, `vibe`,
`workspaces`, `teams`, `messenger`, `knowledge`, `repo`, `wiki`, `analytics`, `security`,
`ai_settings`, `global_settings` and more. State lives in Vuex stores (`store/`), and the main
routes are:

| Route | View |
| --- | --- |
| `/` and `/chats/...` | Quick chat: the launcher home with recent chats and workspace apps |
| `/kanban` | Kanban boards |
| `/workspaces/...` | Workspaces |
| `/messenger` | Teams and messenger |
| `/desktop/...` | Desktop with windows and tabs |
| `/analytics` | Usage and cost dashboard |

---

## 20. Feature matrix

| # | Feature | Live in a chat? | Needs workspace? | Admin only |
| --- | --- | :---: | :---: | :---: |
| 1 | Chats and modes | ✅ | — | — |
| 2 | Agents and tools | ✅ | optional | — |
| 3 | Kanban and tasks | ✅ | — | — |
| 4 | Vibe coding | ✅ | optional | — |
| 5 | Workspaces (dev containers) | — | ✅ | — |
| 6 | Teams and messenger | ✅ | — | — |
| 7 | Knowledge (RAG) | ✅ | — | — |
| 8 | Profiles | ✅ | — | — |
| 9 | @codx mentions | — | — | — |
| 10 | Wiki | ✅ | — | — |
| 11 | Git and code review | ✅ | — | — |
| 12 | AI providers and models | ✅ | — | ✅ |
| 13 | Budget and analytics | ✅ | — | partial |
| 14 | Users and security | — | — | ✅ |
| 15 | Development tools | ✅ | optional | partial |
| 16 | Plugins | ✅ | — | ✅ |
| 17 | REST + OpenAI-compatible API | ✅ | — | — |
| 18 | Installer, CLI and scripts | — | — | ✅ |

---

## Where to go next

* **Self-host it**: [Getting started](/getting-started) and [Initial setup](/initial-setup).
* **Understand the design**: [Architecture](/guide/architecture).
* **Feature deep dives**: the [features](/features/) documentation section.
* **Configuration**: [Configuration](/configuration).
* **Managed team**: [Self-hosted or managed](/managed).

> You will never code alone! ❤️

---

*Source: `docs/features/*`, `README.md`, `api/`, `client/`, `scripts/` and
`codx-junior-installer/`.*
