# Wiki

The wiki is a **living documentation site** generated from the project and kept
up to date in the background. Open it from the wiki tab to get a modern docs
experience: a grouped sidebar, searchable pages, Mermaid diagrams, copyable
examples, callout hints and a built-in AI assistant.

> [!TIP]
> Start with the landing page. It is generated from the project profile and the
> current section tree, so it doubles as a guided tour for new contributors.

## What the site gives you

| Area | What you get |
| --- | --- |
| **Navigation** | Sections grouped by purpose (Get started, Guides, Architecture, API reference, Operations) with page descriptions, icons and reading time. |
| **Pages** | YAML metadata, a TL;DR, "What you'll learn", Mermaid diagrams, runnable examples and `> [!TIP]` / `> [!WARNING]` hints. |
| **Search** | Local command palette (`⌘K` / `Ctrl+K`) across titles, descriptions, sections and tags. |
| **Assistant** | A per-project chat grounded in the generated wiki, with citations back to the pages it used. |
| **Ecosystem** | A parent project's sidebar lists its child projects and can open their wikis without leaving the docs site. |
| **Freshness** | A debounced background scheduler updates only the pages affected by recent edits. |

## How a page is produced

```mermaid
flowchart TD
    A[Source file changes] --> B[Change manager detects it]
    B --> C[Queue file for the project]
    C --> D{Project quiet?}
    D -- no --> C
    D -- yes --> E[Generate only changed pages]
    E --> F[Normalize frontmatter + headings]
    F --> G[Rebuild docs.json]
    G --> H[Index pages for the assistant]
    H --> I[Refresh parent site manifest]
```

Each page is written as markdown with frontmatter that drives the site:

````markdown
---
title: Authentication
description: How login and signed tokens work
tags: [auth, security]
category: Guides
source: src/auth/service.py
---

# Authentication

> **TL;DR** — the API issues short-lived signed tokens.

## How it works

```mermaid
sequenceDiagram
    Client->>API: POST /login
    API-->>Client: access token
```
````

## Background updates without the refresh churn

Editing a project produces a stream of saves. Regenerating documentation on
every save would keep the wiki busy and consume AI tokens while the developer is
still working. The scheduler instead:

1. collects changed files per project,
2. waits for a **quiet period** (`wiki_update_debounce_seconds`, 60s by default),
3. caps the wait at `wiki_update_max_delay_seconds` (10 min),
4. regenerates **only the changed pages** and rebuilds the docs manifest once.

```mermaid
stateDiagram-v2
    [*] --> Idle
    Idle --> Queued: file change
    Queued --> Queued: another save (reset timer)
    Queued --> Updating: quiet period reached
    Updating --> Idle: pages + manifest written
    Updating --> Queued: new save during update
```

You can turn this off in **Project settings → Generate wiki**, or change the
quiet period and maximum delay there.

## The docs assistant

The assistant answers questions about the current project (and summarizes
related child projects). It retrieves the most relevant wiki pages, optionally
enriches them with knowledge-base snippets, and asks the configured model for an
answer with citations.

* Every answer returns `citations` and `pages_used`, so the UI can show source
  chips and deep-link into the site.
* If the model is unavailable, the assistant degrades to a deterministic
  "closest pages" answer instead of failing.
* Disable it per project with `wiki_assistant_enabled`.

## Child project wikis

A project's wiki is navigable from its parent. The docs manifest includes the
resolved child and dependency projects, so the parent sidebar can open each
child's documentation in place. When a child wiki changes, the scheduler
refreshes the parent manifest so counts, descriptions and links stay accurate.

```mermaid
flowchart LR
    Parent[Parent wiki] --> ChildA[api]
    Parent --> ChildB[client]
    ChildA --> Parent
    ChildB --> Parent
```

## Enabling and rebuilding the wiki

1. Open **Project settings** and enable **Generate wiki**.
2. Open the wiki tab and use **Wiki settings** to build the category tree.
3. Run the **Dependency graph**, **Domains** and **Wiki index** steps to add
   architecture pages and make the content searchable by the assistant.
4. Use **Rebuild** for a full regeneration, or the refresh button in the docs
   site to rebuild the manifest and changed pages.

## Related files

- `api/codx/junior/wiki/wiki_manager.py` — page generation, prompts, batch updates.
- `api/codx/junior/wiki/site.py` — docs manifest, navigation, landing page, child projects.
- `api/codx/junior/wiki/assistant.py` — per-project documentation assistant.
- `api/codx/junior/wiki/scheduler.py` — debounced background updater.
- `client/src/views/WikiView.vue` — docs-site shell and assistant panel.
- `client/src/components/wiki/WikiMarkdown.vue` — callouts, Mermaid and wiki links.
