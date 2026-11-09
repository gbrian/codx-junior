# Positioning

Derived from [`PLATFORM_REVIEW.md`](PLATFORM_REVIEW.md). If a line here is not supported by
that document, it does not ship.

---

## 1. Category

We are not an IDE plugin and not an autonomous agent. The closest honest category is:

> **The open-source workspace for hybrid AI + human software teams** —
> sometimes called an *AI-native software delivery workspace* or a *virtual software company*.

**Category sentence for the docs, README and Product Hunt:**

> codx-junior is the open-source workspace where a whole software project — Kanban, AI agents,
> dev containers, team chat, code review and AI budget — lives in one browser tab.

Why this framing wins:

* "AI coding tool" puts us in a 300-product knife fight against Cursor and Copilot.
* "Workspace / delivery platform" competes with Jira + GitHub + Cursor *combined*, which is
  the actual pain: context and control spread across five tools.
* "Open source + self-hosted" is a distribution strategy, not a feature: it earns HN, the
  self-hosted crowd, and privacy-sensitive teams.

## 2. One-liner ladder

| Length | Copy | Use |
| --- | --- | --- |
| 6 words | Run your whole project in one tab. | Logo lockup |
| 12 words | The open-source workspace for teams of humans and AI agents. | Hero, GitHub description |
| 25 words | Plan on a Kanban board where every card is an AI chat, run it in Docker, review every diff and every dollar — self-hosted or with our managed team. | Docs intro, PH description |
| 60 words | codx-junior puts the whole software project in one tab: Kanban, AI agents with project tools, dev containers, team chat, code review and per-user AI budgets. Self-host the open-source engine, or hire the team that runs it with you. | Boilerplate, press, YC |

## 3. Who it is for (ranked for launch)

| # | Segment | Trigger | What they want | Where they hang out |
| --- | --- | --- | --- | --- |
| 1 | **Solo devs / indie hackers running many projects** | "I have five ideas and one brain" | Velocity without losing the thread; predictable AI cost | X, Indie Hackers, r/SideProject, Product Hunt |
| 2 | **Small dev shops / agencies (2–15 people)** | "Every client project has its own mess" | Per-client isolation, visible budget, junior+AI leverage | LinkedIn, local dev communities, Clutch |
| 3 | **Tech leads at SMBs** | "AI is in the 30% of the team's day we can't audit" | Review gates, permissions, cost caps | HN, r/devops, LinkedIn |
| 4 | **Self-hosters and privacy-first engineers** | "No SaaS, no data leaving my box" | Docker Compose, own models, AGPL | r/selfhosted, r/LocalLLaMA, awesome-selfhosted |
| 5 | **AI-tooling tinkerers** | "I want MCP + local models + agents I can wire" | OpenAI-compatible endpoints, plugins, API | r/LocalLLaMA, r/LangChain, Discord |
| 6 | **Non-technical founders who need an IT team** | "I need a developer" | Company mode + managed team | LinkedIn, accelerators, YC-adjacent |

Segments 1–4 are the launch audience. Segment 6 is the revenue story (managed team), not the
Product Hunt audience — do not lead with it.

## 4. Jobs to be done

1. *When I start a project, I want planning, code, running containers and review in one place,
   so I stop losing context switching between Jira, GitHub, the IDE and Docker.*
2. *When I delegate to an AI, I want to see what it did and approve it, so I stay accountable
   for the code that ships.*
3. *When AI usage grows, I want per-user budgets and cost visibility, so the bill never surprises me.*
4. *When my data cannot leave my infrastructure, I want to self-host the whole stack with my own models.*
5. *When my team grows, I want AI agents to be first-class members with roles, channels and limits.*

## 5. Messaging pillars (with proof)

| Pillar | Claim | Proof to show | Proof to fix first |
| --- | --- | --- | --- |
| **One tab** | Plan, build, run, review and talk without leaving the browser | 3 screenshots: board → chat → diff → analytics | Workspaces broken; mobile unverified |
| **Humans in the loop** | AI does the volume, you keep direction and approve every change | profile + review gate + diff view | None |
| **Budget you can see** | Every call metered in cxjcoins, per user, with wallets and limits | analytics screenshot | Needs a clean demo dataset |
| **Self-hosted, provider-agnostic** | Your repos, your Docker, your models (Ollama, vLLM, LiteLLM, any OpenAI-compatible) | compose stack + local model screenshot | Stale images; install friction |
| **Agents with a whole machine** | The AI clicks, types and reads the screen while you watch | 15 s computer-session clip | Needs QA on plain Docker hosts |
| **Open source, AGPL-3.0** | Audit it, fork it, run it forever | repo + license | No AGPL FAQ yet |

## 6. Claims discipline

| Do not say | Why | Say instead |
| --- | --- | --- |
| "4x faster" | No measurement behind it | "One developer can run a project with a team of agents" — or publish a real measured case study |
| "elite human developers" | Unverifiable for a reader | "The managed team works inside the same workspace you do" |
| "enterprise-grade security" | Beta, single maintainer | "Roles, permissions, forward-auth and per-user budgets — auditable in the open" |
| "replaces Jira / Cursor" | Trivially falsifiable | "Replaces the hand-offs between them" |
| "fully autonomous" | Contradicts the thesis | "Supervised autonomy" |
| "production ready" | Beta | "Active beta, used daily by its own team" |

## 7. Objections and answers

| Objection | Answer (short) |
| --- | --- |
| "Another AI coding tool?" | "It's the workspace around the tools: the board, the containers, the budget and the review — in one tab." |
| "Why not Cursor + Linear + GitHub?" | "You can keep Cursor. codx-junior is where the work is planned, run, reviewed and paid for; the editor is one of its windows." |
| "Is it usable yet?" | "Active beta. Core loop — board, agents, diffs, budgets — is used daily. Workspaces are behind a flag while we finish the runtime." *(after the fix: "ship in v1.3")* |
| "Self-hosting is a pain." | "`v1.3.0` images + one compose file, no build step. 10-minute quickstart, verified on Ubuntu and macOS." |
| "AGPL means I can't use it at work." | "AGPL only triggers if you offer a modified version as a network service. Internal use is fine. Commercial licensing available." |
| "Where does my code go?" | "Nowhere you don't send it: your Git, your Docker, your model provider. Local models supported." |
| "How is this funded?" | "Open-source core + a managed team. We're raising a seed round and onboarding early partners." |

## 8. Voice and tone

* **Engineer-to-engineer.** Short sentences, concrete nouns, no superhero adjectives.
* **Show the seam.** Naming what is beta buys more credibility than polish.
* **Dry humour, sparingly.** "You will never code alone" is the one romantic line we allow.
* **Never imply the AI replaces the developer.** It replaces the hand-offs.

## 9. Naming and boilerplate

* Always lowercase, hyphenated: **codx-junior** (never CodX Junior, CodxJunior, CODEX).
* Tagline: *You will never code alone.*
* Domain: to be decided (see `website/PUBLISH_PLAN.md`, D1). Email: `join@codx-junior.ai`.
* Boilerplate (50 words):

> codx-junior is an open-source workspace for hybrid AI + human software teams. Kanban boards,
> AI agents with project tools, dev containers, team chat, code review and per-user AI budgets
> live in one browser tab. Self-host the engine under AGPL-3.0, or hire the managed team to
> execute your roadmap.

## 10. Metrics the story needs (and does not have yet)

| Metric | Why it matters | How to get it |
| --- | --- | --- |
| Time to first successful chat | The only install metric that matters | Stopwatch on 3 clean hosts |
| Stars → installs conversion | Proves the funnel | Install survey + optional ping |
| Tasks completed per week per project | Proves usage depth | Local analytics they can share |
| AI cost per task | Proves the budget story | cxjcoins export from a real project |
| Human hours saved (self-reported) | The commercial claim | 10 design-partner interviews |
| Paying managed clients | The YC story | 3 signed pilots |
