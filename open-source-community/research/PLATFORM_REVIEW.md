# Platform review — what codx-junior actually is today

**Audited:** 2026-11-09 · branch `v1.3-demo-site` · commit `34a4da11`
**Method:** read the docs, the compose stack, the API routers, the client API modules,
built the docs site, and pulled the published images' metadata. No runtime install was
performed in this audit; anything runtime-dependent is marked **needs QA**.

This is the internal truth document. Launch copy is derived from it — not from the README.

---

## 1. What the product is

A self-hosted, AI-native software delivery workspace. One browser tab contains:

* **Kanban** boards where every card *is* a chat (sub-tasks, checklists, assignees).
* **Chats and agents** with project tools: file read/write, patches, search, shell, Docker,
  web browsing, image generation — driven by reusable **profiles** (model + tools + standards).
* **Knowledge (RAG)** over the repo in Milvus, plus an AI-maintained **wiki**.
* **Vibe coding**: chat + live diff + running app side by side.
* **Workspaces**: Docker Compose dev containers (VS Code/Coder, virtual desktop, your apps)
  routed through Traefik.
* **Computer sessions**: Linux desktops, Windows/macOS VMs and remote VNC/SSH machines
  shared live between the human and the AI (OCR-driven clicking/typing).
* **Browser sessions**: a shared Chromium page with CDP tools and co-browsing.
* **Teams/messenger**: channels and DMs where humans and agents are the same kind of member.
* **Company mode**: an org chart of departments/teams above projects, missions dispatched to
  a durable orchestration runtime, and a guard-railed autopilot.
* **Governance**: users/roles/permissions, per-user wallets, cxjcoins metering, spending
  limits, analytics, forward-auth for proxied apps.
* **Extensibility**: Python plugins, REST API, Socket.IO, OpenAI-compatible `/api/v1/models`
  and `/completions`.

Technically: Python 3.11 / FastAPI (`api/`, ~97k LOC / 235 files), Vue 3 + Vite SPA
(`client/`, ~147k LOC / 490 `.vue` files), Docker Compose stack with Traefik, Milvus,
optional LocalAI/LiteLLM, and a VitePress docs site (`docs/`).

## 2. Maturity map

Status legend: **Ship** = demoable and safe to advertise · **Beta** = works, label it beta ·
**Internal** = not for public consumption · **Broken** = do not show until fixed ·
**Unknown** = existence confirmed in code, runtime not verified.

| Capability | Evidence | Status | Launch treatment |
| --- | --- | --- | --- |
| Chats, profiles, modes, tool loop | `api/codx/junior/api/chat.py`, `features/chats-and-agents.md` | Ship (needs QA) | Lead demo |
| Kanban where cards are chats | `management_manager.py`, `features/kanban.md` | Ship (needs QA) | Lead demo |
| RAG / knowledge / wiki | `knowledge.py`, `wiki.py`, Milvus in compose | Beta | Demo with a seeded repo |
| Budget, wallets, cxjcoins, analytics | `analytics.py`, `budget-and-analytics.md` | Beta | Differentiator slide |
| Users/roles/GitHub OAuth/forward-auth | `users.py`, `features/users-and-security.md` | Beta | Mention, don't demo |
| AI providers (OpenAI-compatible, Ollama, LocalAI, LiteLLM) | `global_settings.py`, `.env.example` | Ship | Lead demo |
| Git/PR review, GitHub issues | `git.py`, `features/code-review.md` | Beta | Demo |
| @codx mentions | `features/mentions.md`, watcher | Beta | Blog post, not demo |
| DSH task sync | `dsh.py` (9 routes verified) + `dsh-codx-junior/` bundle | Beta | Niche, post-launch |
| Browser sessions / co-browsing | `browser.py`, `browser-use.md` | Beta | Wow moment in video |
| Computer sessions (VNC/OCR) | `computer.py`, `computer-use.md` | Beta | Wow moment in video |
| Company mode / org chart / missions | `company.py`, `COMPANY.md` | Beta | Story, not demo |
| Plugins | `plugins/`, `features/plugins.md` | Beta | Mention |
| OpenAI-compatible API | `chatGPTLikeApi.py`, `features/api.md` | Ship | Developer angle |
| **Workspaces (create/start/stop/logs)** | see §3 | **Broken** | **Do not advertise until fixed** |

## 3. The workspace blocker (verified)

The client and the server disagree, and one server path calls a method that does not exist.

| # | Finding | Evidence |
| --- | --- | --- |
| 1 | `POST /api/workspaces` calls `WorkspaceManager.create_workspace_files(...)`; no such method is defined anywhere in `api/` | `api/codx/junior/api/workspaces.py:232`; only definition site is that call |
| 2 | Client calls `/api/workspaces/templates`, `/{id}/start`, `/{id}/stop`, `/{id}/status`, `/{id}/logs`, `/{id}/generate-files` — none exist in the router (router has CRUD + files only) | `client/src/api/modules/workspaces.js:110-159` vs `api/codx/junior/api/workspaces.py` (`GET /accessible`, `GET /`, `POST /`, `PUT /{id}`, `DELETE /{id}`, files CRUD) |
| 3 | Client `PUT /api/workspaces` (no id) vs server `PUT /api/workspaces/{workspace_id}` | `workspaces.js:70` vs `workspaces.py:253` |
| 4 | Lifecycle methods exist in the manager but are never exposed: `start_workspace`, `stop_workspace`, `workspace_status` | `api/codx/junior/workspaces/manager.py:164,192,210` |
| 5 | The shipped installer mounts workspaces under the global volume, so `build:` contexts and bind mounts may not resolve on the host — **needs QA** | `codx-junior-installer/codx-junior/docker-compose.yaml` workspace volume |

**Consequence:** a user who installs and clicks *Workspaces* gets a 500 and a UI wired to
404s. Two of the README's headline rows ("Workspaces (dev containers)", "Everything in one
tab: Kanban, dev containers, agents and chat") depend on this feature.

**Options**

| Option | Work | Launch impact | Recommendation |
| --- | --- | --- | --- |
| A. Fix lifecycle API + creation + UI contract | ~5–8 dev-days | Keeps the full story | **Preferred if launch ≥ 3 weeks out** |
| B. Hide workspaces in the UI behind a feature flag, remove from launch copy | ~1 dev-day + docs edits | Loses one pillar, keeps credibility | Fallback |
| C. Ship as "experimental" with a UI banner and a docs warning | ~0.5 day | Honest but weakens the "one tab" claim | Last resort |

## 4. What is genuinely differentiated

1. **The unit of work is a chat inside a board**, not an issue beside a chat. A task, its
   sub-tasks, its agent conversation, its diffs and its review are one object. Competitors
   split this across Jira + IDE + PR review.
2. **Humans and AI are peers in the org**: same channels, same board, same budget system,
   same permissions model. "Company mode" makes the AI a member of the org chart, not a tool.
3. **Cost governance is native**: per-user wallets, cxjcoins, token rules, extension
   requests, per-model analytics. Most AI coding tools bill seats and hide usage.
4. **Self-hosted and provider-agnostic**: your repos, your Docker, your models (Ollama,
   vLLM, LiteLLM, any OpenAI-compatible endpoint). The whole stack is AGPL-3.0.
5. **The AI can use a whole machine**: a shared desktop/browser where the human watches the
   agent click, not just a terminal. This is the most *demoable* differentiator in 60 seconds.
6. **The managed-team wedge**: the same product is the delivery vehicle for a human services
   business — a rare, honest path from OSS to revenue.

## 5. What is weak or unproven

| Weakness | Why it matters | Mitigation |
| --- | --- | --- |
| Install friction: clone + build 3 images | Kills launch conversion | Publish versioned images + one-command install |
| No public demo instance | Product Hunt traffic needs instant gratification | Hosted read-only demo with a seeded repo (see PUBLISH_PLAN D4) |
| Beta quality across modules | Early users will hit bugs | "Active beta" label, public roadmap, fast response SLA |
| Workspaces broken (above) | Contradicts marketing | Fix or hide |
| Claims without evidence ("4x faster") | Erodes trust with HN/YC | Replace with measurable claims (time-to-first-diff, cost per task) |
| Single maintainer | Risk for contributors and investors | Publish contribution guide + good-first-issues + response times |
| AGPL-3.0 | Enterprises with anti-AGPL policies | Publish a plain-language AGPL FAQ + commercial licensing contact |
| No telemetry | Can't prove adoption | Optional privacy-first ping + install survey |
| Huge SPA + 14 MB of docs images | Mobile bounce | Image optimization, code splitting (client), CDN |
| iOS/mobile experience unknown | Claim says "only needs a browser" | **Needs QA** before that line ships |

## 6. Positioning implications

* **Promote:** the single-tab workspace, hybrid humans+AI, budget control, self-hosting,
  computer/browser use, company mode as the vision, OpenAI-compatible API as the developer hook.
* **Label beta:** wiki, mentions, plugins, DSH sync, company mode.
* **Do not promote until fixed:** workspaces, and any "deploy to cloud" claim without a
  verified path.
* **Replace unverifiable claims** ("4x faster", "elite human expertise") with:
  * "Every task, agent run, diff and dollar in one tab."
  * "Self-host in 10 minutes, or let our team run it with you."
  * "Your models, your repos, your budget."

## 7. What an honest 90-second demo looks like

1. Open a seeded repo project with knowledge already indexed. *(5 s)*
2. Drag a card from Backlog to In Progress — it opens as a chat with a developer profile. *(10 s)*
3. The agent searches the repo, proposes a patch, runs the tests, opens the diff. *(25 s)*
4. Show the same change in **vibe coding**: diff + live preview. *(15 s)*
5. Show the **analytics** dashboard: this task cost N cxjcoins, and the user's wallet. *(10 s)*
6. Cut to **computer session**: the agent opens the app in a desktop, clicks, and fixes a
   visual bug while the human watches. *(20 s)*
7. End card: "Self-host it. Or hire the team that runs it." *(5 s)*

Everything in that script is demonable today except step 1's workspace-free path — no
workspaces required, which is why option B in §3 is a viable fallback.

## 8. Open questions to close before launch

- [ ] Does `docker compose up -d` on a clean host work with the **published** images (Feb 2026)?
- [ ] Time-to-first-install on a 16 GB / 4 vCPU Ubuntu 24.04 box?
- [ ] Does the client build and serve correctly behind Traefik on `localhost` (no TLS)?
- [ ] Is the mobile layout usable enough to support "only needs a browser"?
- [ ] Which models are actually required for a first successful chat (LLM + embeddings)?
- [ ] Does computer use work without a KVM/host GPU on a plain Docker host?
- [ ] What is the minimum RAM/VRAM for LocalAI defaults?
