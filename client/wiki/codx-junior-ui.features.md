# codx-junior UI — Features & Functionality Guide

**codx-junior** is an AI-powered development workspace. It brings your projects,
chats with AI assistants, task boards, documentation, knowledge search, code
review, team collaboration and analytics together in a single application.

This guide is written **for end users**. It explains *what you can do* and *why
it matters*, grouped by topic. No technical or installation details are covered
here — only the features you will see and use.

---

## Table of contents

1. [Getting around the app](#getting-around-the-app)
2. [Projects](#projects)
3. [AI Chat & Assistants](#ai-chat--assistants)
4. [Tasks, Boards & Planning](#tasks-boards--planning)
5. [Vibe Coding](#vibe-coding)
6. [Knowledge Base & Search](#knowledge-base--search)
7. [Wiki & Documentation](#wiki--documentation)
8. [Files, Code & Git](#files-code--git)
9. [Teams & Collaboration](#teams--collaboration)
10. [Messenger & Activity Wall](#messenger--activity-wall)
11. [Meet — Video Calls](#meet--video-calls)
12. [Browser Sessions](#browser-sessions)
13. [Workspaces](#workspaces)
14. [Analytics, Metrics & Logs](#analytics-metrics--logs)
15. [AI Settings & Models](#ai-settings--models)
16. [Global & Project Settings](#global--project-settings)
17. [Users, Security & Accounts](#users-security--accounts)
18. [Media Library](#media-library)
19. [Import, Export & Templates](#import-export--templates)
20. [Personalization & Notifications](#personalization--notifications)
21. [Mobile & Desktop Experience](#mobile--desktop-experience)

---

## Getting around the app

codx-junior adapts to the device you are using and gives you two ways to work:

- **Desktop mode** — a flexible workspace where several apps stay open at the
  same time as side-by-side **panels** (like windows).
- **Single mode** — a focused, one-app-at-a-time experience used on smaller
  screens and mobile.

### The sidebar

The left sidebar is your main launcher. It gives quick access to your projects,
recent chats, tasks and the most used apps.

- **Collapse / expand** the sidebar to gain screen space.
- On **mobile** the sidebar slides in as an overlay and closes automatically when
  you navigate away.

### Main menu & command palette

- The **Menu** button opens the full application menu (projects, views,
  workspaces, settings and every app).
- **Top bar search / command palette** (shortcut **⌘K**) lets you jump straight
  to a project, chat or command without hunting through menus.

> **Tip:** In desktop mode you can open the same app several times (for example,
> one Task Manager per board) and arrange them however you like. In single mode,
> opening an app replaces the current one.

---

## Projects

A **project** is the unit everything else revolves around — chats, tasks,
knowledge, wiki and analytics all belong to a project.

### Working with multiple projects

- **Switch projects** at any time from the project selector, sidebar or menu.
- The address bar always reflects which project you are working in, so you can
  bookmark or refresh a page and stay in the same project.
- **Recent projects** are remembered, and you can **pin** your favourite projects
  for one-click switching.

### Project structure

- Projects can be **nested**: a project can have **sub-projects** and a
  **parent project**.
- **Linked / dependency projects** can be associated so the AI can search and
  reference related work across projects.
- The **Project Overview** screen shows your projects as cards with their status
  and metrics.

### Creating projects

- **New Project** — clone from a Git URL or point to a project folder. Pasting a
  GitHub issue URL will resolve to the repository automatically.
- **Delete a project** from the project settings *Danger Zone*.

### Per-project settings

Each project has its own configuration (see
[Global & Project Settings](#global--project-settings)) covering name and icon,
paths, wiki generation, branches, AI models, MCP servers, knowledge options and
more.

---

## AI Chat & Assistants

Chat is the heart of codx-junior. Every conversation is a **chat** that can hold
one or many messages, spawn subtasks and run AI work in the background.

### Chat modes

A chat can run in several **modes**, each tuned for a different kind of work:

| Mode | What it is for |
| --- | --- |
| **Chat** | A normal back-and-forth conversation with the assistant. |
| **Agent** | The assistant autonomously plans and executes steps. |
| **Task** | Work items that produce a result you can review. |
| **Topic** | Discussion threads grouped by subject. |
| **Preview** | Reviewing rendered output. |
| **Browser** | Interacting with web content. |
| **Slides** | Producing presentation-style content. |
| **Tutorial** | Step-by-step guided content. |
| **Channel** | Team/group conversations. |

### Statuses

Chats and tasks can carry a **status**: *To Do*, *Doing*, *On Hold*, *Done*, and
*Rejected*. Statuses are colour-coded so you can read a board at a glance.

### Subtasks, threads & hierarchy

- **Split a chat into subtasks** — the AI can break a larger request into smaller
  tasks automatically, or you can add subtasks manually.
- **Threads** let you reply to a specific message without polluting the main
  conversation.
- A **breadcrumb** at the top shows where you are in a chat hierarchy, and you can
  jump to any parent or sibling chat.
- Subtasks can inherit or ignore their parent's **knowledge** and **files**.

### Rich messaging

- **@mentions** — reference files, AI profiles, teammates and other projects
  directly in a message. A mention bar shows the active mentions.
- **File attachments & images** — drag and drop, paste, or pick files from the
  project. Images get inline previews.
- **Voice input** — dictate messages using speech recognition (multiple
  languages supported).
- **Emoji picker** and **find & replace** while composing.
- Reply to, edit, hide, or delete individual messages.
- Chats can be **pinned**, tagged, and searched.

<details>
<summary><strong>Power features inside a chat</strong></summary>

- **Chat profiles** — attach one or more AI profiles to a chat to shape how the
  assistant behaves.
- **Model selector** — choose the AI model used for the conversation.
- **Export chat** — save a conversation for sharing or archiving; you can also
  export to a notebook format.
- **Chat logs** — see the AI requests and activity generated by a chat.
- **Checklists** — track progress items inside a conversation.
- **Code blocks** — review suggested code, generate code, apply patches, or ask
  the assistant to improve existing code without leaving the chat.
- **Linked chats** — connect related conversations together.
- **Templates** — turn a chat into a reusable template to start future chats
  faster.
- **PR views** — chats can present pull-request style reviews of files and
  changes.

</details>

### The assistant bar

A lightweight **assistant** is always within reach: ask a quick question, pick a
profile, and continue in a full chat when you need more room.

---

## Tasks, Boards & Planning

codx-junior includes a full **Task Manager** where every task is itself a chat —
so a task can be discussed, planned and executed by the AI.

### Boards

- **Kanban boards** organise tasks into **columns** you define (for example
  *To Do*, *In Progress*, *Done*).
- **Sprint boards** group tasks by **status** instead of free columns.
- Boards can be **nested** (parent and child boards) and **bookmarked**.
- Use **board backgrounds** to visually separate your boards.
- Board templates (**Backlog**, **Scrum**) get you started quickly.

### Working with tasks

- **Create tasks** with a name, mode, destination column, assignees, deadline,
  cost estimate, files and an opening message — optionally running immediately.
- **Drag & drop** tasks between columns and reorder tasks and columns.
- Open a task **inline** next to the board, or in its **own window/panel**.
- **Task settings** let you adjust status, priority, tags and more.
- Filter and search tasks by text, column, message content, files and profiles.

### Planning view

The **Planning** view turns your tasks into a management dashboard:

- **Priorities** — High, Medium, Low, each colour-coded.
- **Due dates, progress and assignees** on every task.
- **Metrics** — totals, completed, active, on hold, overdue and due-today counts.
- **Needs attention** — tasks that are overdue, due today, or high priority and
  unassigned.
- **Board progress** — completion percentage per board.
- **Activity feed** — a running log of task updates.

### Follow-up view

The **Follow-up** view helps you keep an eye on what needs action, using the same
task dataset filtered by date range and status.

### Board transfer & the "No board" board

- **Export / import** a board (with all its tasks) as a portable file.
- **Copy or move** a board — including every task — to another project.
- A virtual **"No board"** board collects tasks that are not attached to any
  board, so nothing gets lost.

---

## Vibe Coding

**Vibe Coding** is a focused, side-by-side coding workspace that combines
conversation and code in one screen.

- **Chat panel** — talk to the assistant about the task at hand.
- **Changes panel** — review proposed code changes and diffs.
- **Preview panel** — see the running application.
- Toggle each panel on or off to fit your workflow.
- Work on **subtasks** and navigate between parent and child chats.
- Choose which **project app** to preview, including full-screen preview.
- Jump to the relevant **task board** or **parent task** directly from the header.

---

## Knowledge Base & Search

The knowledge base lets you **ask questions about your code and documents** and
get AI answers grounded in your project's content.

### Knowledge search

- Ask a natural-language question and receive:
  - an **AI answer**,
  - the **supporting documents** used, ranked by relevance, with previews.
- Results show the source file, score, language and document metadata.
- The AI can search across **related projects** (parent, children and linked
  projects), so answers can draw on a wider context.

### Agent Plan

The **Agent Plan** tool turns a request into a structured plan showing:

- Which files to **read**,
- Which files to **modify**, and
- Which files to **create**,

along with the reasoning for each and any supporting documents found.

### Indexing

- Project files are **indexed** so the AI can search them. You can watch indexing
  progress live (stages such as loading, enriching and writing to the database).
- Manage what gets indexed: search settings, file-ignore patterns, external
  folders, document enrichment and more (see Project Settings).
- A **Data** explorer lets you inspect the underlying knowledge data.

---

## Wiki & Documentation

codx-junior can **generate and host a wiki** for your project automatically.

### Browsing the wiki

- The wiki is organised into **domains** and **modules** with a browsable tree.
- **AI wiki search** finds answers and jumps to the relevant domain or module.
- Domain pages describe a slice of your project; module pages describe individual
  files, generated on demand.
- A **Home** page (README) is shown on entry.

### Building & editing

- The wiki is produced by a **pipeline**: build the dependency graph, detect
  domains, then build the index.
- A **Wiki Settings** panel lets you edit the wiki tree (add/rename/delete
  categories and pages), attach files, and rebuild individual pages.
- **Wiki modes** — a default mode and a **MkDocs** mode — control how the wiki is
  presented.
- An **external documentation** view is also available for hosted docs.

---

## Files, Code & Git

### File explorer & viewer

- Browse the project's files with a **file explorer** and open files in a
  **viewer** with tabs, so several files can be open at once.
- **Search by file name** and **search inside file contents** (with case and
  regex options).
- **Create, rename, delete** files and folders.
- **Upload** one or many files; uploads can optionally be processed/indexed.
- **Preview** many file types inline: code, HTML, images, video, PDFs and more.
- Open files in an external **code editor** (code-server) when available.

### Code editing & diffs

- A built-in **Monaco code editor** with syntax highlighting for many languages.
- **Diff viewers** show changes side-by-side, including Git-style diffs.
- **Git Diff Viewer** displays the changes between branches.

### Repository & Git

- **Git view** with **branches**, **commit history** and **changed files**.
- **Branch selector** to switch the branch you are looking at.
- **Pull Request** (PR) tools: PR viewer, PR report, PR file views, commit
  selection, branch selection and code comments.
- Review a task's files and proposed changes directly from a chat.

### GitHub integration

- Browse **help-wanted** issues and read individual issues.
- **Process an issue with AI** to turn it into work.
- A Git-issue **wizard** helps you go from issue to task.

---

## Teams & Collaboration

Teams let people (and AI profiles) collaborate inside a project.

### Teams, channels & DMs

- Create **teams** with a name, icon, colour, description and tags.
- Organise conversations into **categories** and **channels**.
- Hold **direct messages** with individual team members.
- A team sidebar shows channels, members and quick links to recent chats.

### Members & AI profiles

- Add **members** with roles and online status.
- Attach **AI profiles** to a team to bring assistants into the collaboration.
- Manage members, roles and statuses for each team.

### Team media

- Each team has a **media library** for images, video and other files shared by
  the team.

### Team settings

- Dedicated screens for **Team**, **Channel**, **Category** and **Member**
  settings, plus dialogs to **create teams**, **create channels** and **add
  members**.

---

## Messenger & Activity Wall

### Messenger

A dedicated **Messenger** view for conversations, keeping team and direct
messaging in one place.

### Activity Wall

The **Activity Wall** is a social-style feed of everything happening across your
projects.

- See **activity** from chats, tasks and meetings, newest first.
- Browse tabs such as **For you**, **Following**, **Explore**, **Bookmarks**,
  **Notifications**, **Messages** and your **Profile**.
- **Compose a post**, **reply** to events, **like**, **repost**, **bookmark** and
  **share** (copy a link).
- Filter the feed by **kind** (for example, chats, tasks, meets) and show only
  items with **unread replies**.
- A right-hand rail shows **trends**, **suggestions** and who you are
  **following**.

> On mobile, the Activity Wall is the default home screen.

---

## Meet — Video Calls

**Meet** provides built-in **video calls** between users.

- **Start a meeting** and share a **meeting code**, or **join** one by entering a
  code.
- **Discover active meetings** you can join.
- **Camera and microphone controls**, mute, and a **device picker** for choosing
  camera/microphone/speaker.
- **Audio test** to check your speakers before joining.
- **Knock-to-join**: if a meeting already has participants, you request to join
  and a host **admits or declines** you.
- **Invitations** for incoming calls, with accept/reject.
- A **meeting chat** is associated with each call.
- Works with multiple devices per account (for example, a desktop and a phone can
  both join).

---

## Browser Sessions

Manage **browser sessions** from within codx-junior.

- **Create, edit, delete** and **run** browser sessions.
- Sessions open in their own viewer/panel so you can use a browser alongside your
  work.
- A session list and a session panel appear side-by-side on desktop, and as
  switchable screens on mobile.

---

## Workspaces

**Workspaces** are complete development environments that bundle one or more
projects and applications.

- **Create workspaces** from templates, choose which projects they include, and
  add applications to them.
- **Start and stop** workspaces and follow their **status**.
- **Edit, clone and delete** workspaces.
- **Workspace settings** also let you tune Docker-related options globally.
- A **Workspace App Builder** helps assemble the apps a workspace provides.

---

## Analytics, Metrics & Logs

### Analytics dashboard

Understand how AI is being used:

- **Token usage** over time (per minute, hour or day) with charts.
- KPIs such as total tokens, total calls, input vs. output tokens, average
  duration, generation speed and total **cost** (in coins).
- **Usage by model**, with input/output breakdowns and cost.
- **Model performance** table (calls, tokens, average duration, tokens/second,
  cost and a speed indicator).
- **Period breakdown** table with per-period totals.
- **Admin view** (for administrators) adds **usage by user** and **usage by
  project**, plus a **Price Editor** to manage model pricing and recalculate
  historical costs.
- Filter by **date presets**, **date range**, **model**, **user** and **project**;
  supports **auto-refresh**.

### Metrics & logs

- A **Log Viewer** for application logs with log selection, **auto-refresh** and
  filtering.
- An **LLM Requests viewer** to inspect AI request/response logs.
- A **Chat Logs** analyzer dashboard with live metrics and analytics per chat.
- Admin log tools to review, filter and purge logs.

---

## AI Settings & Models

### AI providers & models

- Configure **AI providers** and the **models** they offer.
- A **Model Selector** lets you pick the model used for a given purpose
  (reasoning, embeddings, wiki, knowledge search, image generation, image
  vision, etc.).
- Reload/refresh the available models at any time.

### Agents

- Define and configure **AI agents** that can act on your project.
- **Agent Studio** provides a dedicated environment for building and running
  agents.

### MCP servers

- Configure **Model Context Protocol (MCP) servers** to extend what the AI can
  do, per project or globally.

### Chat prompts & AI profiles

- Set **global chat prompts** that shape all conversations.
- Manage **AI profiles** — named collections of instructions and tools (with
  descriptions and avatars) you can attach to chats and teams.

---

## Global & Project Settings

### Global Settings

Application-wide configuration, organised into clear sections:

- **General** — basic preferences.
- **AI Models** — providers and model configuration.
- **Agents** — agent definitions.
- **Chat Prompts** — global prompt text.
- **Plugins** — install and manage plugins.
- **Workspaces** — global workspace and Docker settings.
- **Users** — user accounts and access.
- **Scripts** — project scripts.
- **OAuth** — configure OAuth login providers.
- **ENV Variables** — manage environment variables.

Each section is accessible from a sidebar (desktop) or a drawer (mobile), with
Reload, Save and Export/Import actions.

### Project Settings

Per-project configuration:

- **General** — project name, icon, path, wiki generation and wiki path,
  dependencies, and project **branches** (parallel copies of a project).
- **AI Models** — choose which models handle wiki, embeddings, knowledge search,
  reasoning, image generation and image vision.
- **MCP Servers** — project-level MCP configuration.
- **Knowledge** — enable/disable knowledge, training datasets, file watching,
  RAG distance, relevance cut-off, document counts, HNSW parameters, sub-project
  querying, document enrichment and tag extraction, external folders, file-ignore
  patterns and search type.
- **Miscellaneous** — options such as saving file mentions as tasks.
- **Danger Zone** — delete the project.

### Project scripts

- Define and run **project scripts** (for example, build or test scripts), see
  their **status** (running, stopped, error) and whether they run in the
  background or restart automatically.

---

## Users, Security & Accounts

- **Login** with a local account or via **OAuth** providers (configured in Global
  Settings).
- **User list** and **online users** so you can see who is around.
- **Account settings** for your own profile.
- **Security / user management** screens for administrators.
- **Token limits**: rules that control how much AI usage a user may consume, plus
  request approval workflows for administrators.
- **Wallet settings** on the user profile for tracking usage/cost.
- **Roles** for access control.

---

## Media Library

A central place to store and reuse media.

- Create **media libraries** for a team, channel, chat or profile.
- **Upload** images, video, audio and documents, with progress feedback.
- **Gallery** and **preview** views, plus a media **manager** to organise items.
- Tag, search, add or remove media from libraries.

---

## Import, Export & Templates

- **Export / import settings** (global and project) to move configuration between
  environments.
- **Export / import boards** (with all tasks), and **copy or move** boards between
  projects.
- **Export chats** and **export to notebook** formats.
- **Board and chat templates** to reuse common structures — including turning any
  chat into a reusable template.
- **Project wizards** and the **Git-issue wizard** guide you through common setup
  tasks.

---

## Personalization & Notifications

- **Theme** selection (light/dark) and **colour swatches** to make the app yours.
- **View mode** — switch between **Vibe** (focus) and **Expert** (full workspace)
  layouts.
- **Collapsible sidebar** and **panel widths** that persist between sessions.
- **Voice language** for dictation.
- **Call device preferences** (default microphone/speaker, auto-mute).
- **Notifications & toasts** for events like indexing progress, errors and
  updates. Notifications are also collected on the Activity Wall.

---

## Mobile & Desktop Experience

- **Responsive design** that adapts to phones, tablets and desktops.
- On **mobile**, the **Activity Wall** is the home screen, the sidebar is a
  slide-in overlay, and apps open one at a time.
- On **desktop**, the **multi-panel workspace** lets you arrange many apps side
  by side, with per-project **layout persistence** — reopen the app and your
  arrangement is right where you left it.
- Panels can be **maximised/fullscreen**, and tabs make it easy to switch between
  open apps.

---

*This document describes the codx-junior user interface at a feature level. Some
capabilities depend on your project's configuration and the AI providers and
plugins enabled for your workspace.*
