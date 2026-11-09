# open-source-community — go-to-market workspace

Working folder for promoting **codx-junior**: publishing the documentation website,
launching on Product Hunt, applying to Y Combinator, and running the ongoing
open-source community motion.

> **Snapshot:** audited `2026-11-09` on branch `v1.3-demo-site` (commit `34a4da11`).
> Re-run the checks in [`website/AUDIT.md`](website/AUDIT.md) before trusting any
> status below.

---

## Current status at a glance

| Area | State | Blocking launch? |
| --- | --- | --- |
| Public website | **Does not exist.** No DNS for `codx-junior.ai` / `.com`, no GitHub Pages, no deploy workflow | **Yes** |
| Docs build | Builds clean in ~8 s, 32 pages, 0 broken internal links | No |
| Docs content | Good feature coverage; missing install/troubleshooting/FAQ/legal/contributing | Partly |
| Published images | Docker Hub tags last pushed **2026-02-16**, ~9 months older than the docs | **Yes** |
| Install path | `git clone` + `build.sh` (heavy) or stale `docker compose pull` | **Yes** |
| Headline feature health | Workspaces API is broken in this tree (500 on create, missing lifecycle routes) | **Yes** for the claim, not for the whole product |
| Internal notes exposure | Two engineering review docs are built into the public site | **Yes** |
| Demo | `demo.md` renders an unregistered `<RegisterForm />`; no demo instance | **Yes** for the hero CTA |
| SEO / sharing | No sitemap, robots.txt, canonical, OG/Twitter tags, 1200×630 image | High |
| CI/CD | No docs CI, no image publishing workflow (only a disabled `.wip` file) | High |
| Community files | No CONTRIBUTING, SECURITY, CODE_OF_CONDUCT, issue/PR templates, CHANGELOG | High |
| Launch plan | This folder | — |

**Only 5 GitHub stars and 2 watchers today** (`api.github.com/repos/gbrian/codx-junior`).
Every launch plan here assumes a cold start, not an audience amplifier.

---

## How to use this folder

1. Read [`website/PUBLISH_PLAN.md`](website/PUBLISH_PLAN.md) — the master plan and timeline.
2. Fix the P0 items in [`website/AUDIT.md`](website/AUDIT.md) before anything else.
3. Prepare the story with [`research/POSITIONING.md`](research/POSITIONING.md) and
   [`research/COMPETITORS.md`](research/COMPETITORS.md).
4. Build launch assets from [`assets/ASSET_CHECKLIST.md`](assets/ASSET_CHECKLIST.md).
5. Execute Product Hunt from [`launch/PRODUCT_HUNT_PLAN.md`](launch/PRODUCT_HUNT_PLAN.md)
   and [`launch/LAUNCH_DAY_RUNBOOK.md`](launch/LAUNCH_DAY_RUNBOOK.md).
6. Submit to YC with [`yc/YC_STRATEGY.md`](yc/YC_STRATEGY.md) and
   [`yc/YC_APPLICATION_DRAFT.md`](yc/YC_APPLICATION_DRAFT.md).
7. Run the weekly rhythm from [`content/CALENDAR.md`](content/CALENDAR.md) and
   measure it with [`measurement/ANALYTICS.md`](measurement/ANALYTICS.md).

## Map

```
open-source-community/
├── README.md                      ← you are here
├── research/
│   ├── PLATFORM_REVIEW.md         full-platform review: what ships, what doesn't
│   ├── POSITIONING.md             category, ICP, messaging pillars, objections
│   └── COMPETITORS.md             honest comparison set and where we win/lose
├── website/
│   ├── AUDIT.md                   evidence-based readiness audit (P0/P1/P2)
│   ├── PUBLISH_PLAN.md            phases, tasks, owners, dates, acceptance criteria
│   ├── GO_LIVE_CHECKLIST.md       pre-flight, deploy, verification, rollback
│   └── QUICKSTART_DRAFT.md        rewritten install page (≤ 15 min, with troubleshooting)
├── launch/
│   ├── PRODUCT_HUNT_PLAN.md       4-week pre-launch, launch day, post-launch
│   ├── PRODUCT_HUNT_COPY.md       every string Product Hunt asks for
│   └── LAUNCH_DAY_RUNBOOK.md      hour-by-hour, roles, incidents, templates
├── yc/
│   ├── YC_STRATEGY.md             batch calendar, narrative, metrics, interview prep
│   └── YC_APPLICATION_DRAFT.md    draft answers with metric placeholders
├── channels/
│   └── PLAYBOOKS.md               HN, Reddit, X, LinkedIn, dev.to, directories, podcasts
├── content/
│   ├── CALENDAR.md                12-week editorial + launch calendar
│   ├── COPY_BANK.md               reusable one-liners, bios, boilerplate
│   └── drafts/
│       └── why-hybrid-ai-teams.md flagship blog post draft
├── measurement/
│   └── ANALYTICS.md               events, UTM schema, KPI tree, weekly review
└── assets/
    └── ASSET_CHECKLIST.md         screenshots, video, OG cards, PH gallery
```

## The one-paragraph story we are selling

codx-junior is an open-source workspace where a software project lives in one tab:
the Kanban board, the AI agents doing the work, the dev containers running the code,
the team chat, the code review and the AI budget. It is built on the observation that
unattended AI agents drift and purely manual teams are slow — so it keeps humans in
the loop, meters every AI call per user, and lets you self-host the whole thing or
hire a managed team to run it with you.

## Rules of this folder

* **No claim ships without evidence.** If a feature is not demoable on a fresh install,
  it does not go in the launch copy. See the status column in `research/PLATFORM_REVIEW.md`.
* **Dates are real dates.** Anything not confirmed by the counterparty (YC, Product Hunt)
  is marked *expected* and re-checked the week before.
* **One source of truth per string.** Copy lives in `launch/PRODUCT_HUNT_COPY.md` and
  `content/COPY_BANK.md`; the website and the launch posts import from those.
* **Measure or don't claim.** Every channel gets UTM parameters from `measurement/ANALYTICS.md`.

## Next 5 actions (week of 2026-11-09)

1. Decide the canonical domain and register it (see PUBLISH_PLAN.md, decision D1).
2. Merge `v1.3-demo-site` → `main` so the published site describes the product that exists.
3. Remove the two internal workspace review docs from `docs/features/` and rebuild.
4. Publish versioned Docker images (`v1.3.0`) so `docker compose up -d` installs the documented product.
5. Replace the broken `<RegisterForm />` demo CTA with a working request-demo flow.
