---
title: codx-junior
description: The hybrid AI + human workspace for building, running and documenting software projects.
tags: [overview, install, getting-started]
---

# codx-junior

> **TL;DR** — codx-junior is the open-source workspace where AI agents and
> experienced developers build software together: chats, Kanban, dev
> containers, knowledge, docs and harness integrations in one place.

![Figure 1: codx-junior desktop workspace with a project, chat and Kanban board](/wiki/images/figure-01-codx-junior-desktop.png)

*Figure 1 — The desktop workspace. Replace this placeholder with a full-width
screenshot showing the project switcher, a chat and the Kanban board on one
screen.*

## What is codx-junior?

codx-junior combines the speed of AI automation with the judgement of human
engineers. It gives a single developer the leverage of a small team:

- **Project-aware chats and agents** that read the codebase, use tools, apply
  patches, browse the web and work with containers.
- **Kanban, sprints and tasks** where every card is a real conversation.
- **Workspaces and dev containers** with live previews, routed through Traefik.
- **Knowledge and a living wiki** generated from the project and kept fresh.
- **Teams, messenger and company** views so humans and AI share one workspace.
- **DSH harness integration** for headless DeepSeek Harness sessions.

## Quick start

1. Install the platform with the Docker or local setup guide.
2. Open the dashboard and create or select a project.
3. Open a chat, describe what you want and let the agent inspect the project.
4. Use Kanban to turn the work into visible tasks.
5. Open the wiki for a guided tour of the app and the project internals.

## Tour of the app

### Chat and agents

![Figure 2: Chat panel with an agent using tools on a project](/wiki/images/figure-02-chat.png)

*Figure 2 — A project chat. The screenshot should show the conversation, tool
activity and the generated code/file changes.*

### Kanban and planning

![Figure 3: Kanban board with sprints and task cards](/wiki/images/figure-03-kanban.png)

*Figure 3 — The Kanban board, including columns, a task card and its linked
chat.*

### Workspaces and previews

![Figure 4: Dev workspace with a live preview](/wiki/images/figure-04-workspace.png)

*Figure 4 — A dev container workspace with the file tree, terminal and live
preview side by side.*

### Knowledge and wiki

![Figure 5: Wiki documentation site and assistant](/wiki/images/figure-05-wiki.png)

*Figure 5 — The project wiki with its navigation, search, diagrams and the
documentation assistant.*

## DSH harness integration

codx-junior can mirror DeepSeek Harness sessions as normal tasks. The DSH Host
plugin connects outbound, registers an instance and opens, prompts, renames or
cancels sessions through the agent channel.

- [DSH harness integration](wiki:integrations/dsh-harness)
- `docs/features/dsh-sync.md` — task sync behavior
- `HARNESS_INTEGRATION.md` — full harness specification

## Install and configure

The setup guide covers Docker, local development, environment variables,
Traefik, Milvus and the first login. Start with the project overview and the
setup page, then follow the "choose your path" links:

- **I want to use codx-junior** → Quick start and the app tour.
- **I want to operate it** → Deployment and operations.
- **I want to contribute** → `codx-junior-api` and `codx-junior-ui` wikis.

## Documentation map

- [Project overview](wiki:project-overview/readme-md)
- [Setup and installation](wiki:setup-and-installation)
- [DSH harness integration](wiki:integrations/dsh-harness)
- [Features](wiki:codx-junior.features)
- `codx-junior-ui` — screens, sections and user workflows.
- `codx-junior-api` — backend architecture, setup and operations.

> [!TIP]
> Use the sidebar project tree to jump between the product wiki, the UI wiki
> and the API wiki. Use the assistant when you want an answer with citations
> instead of a page.
