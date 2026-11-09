# Asset checklist

Everything visual that the site, Product Hunt, HN and YC need — with specs, sources and
naming. All screenshots must come from the **released** build with a seeded demo project.

---

## 1. Screenshot set (the backbone)

**Rules**
- Capture at 2× on a 1600×1000 viewport, dark and light only if the product supports both.
- Seed data: one project with 20–30 tasks, 5 profiles, 3 indexed docs, non-empty analytics.
- Hide real names, emails, tokens, local paths.
- Export WebP (quality 82) + PNG fallback; target < 250 KB per image.
- One idea per screenshot. If it needs a caption to be understood, reshoot.

| # | File | Screen | What must be visible | Used on |
| --- | --- | --- | --- | --- |
| 1 | `hero-kanban.png` | Kanban board + open chat + diff panel | Board, task card, chat, running agent | Home hero, PH #1 |
| 2 | `card-is-chat.png` | Task detail | Chat thread, checklist, sub-tasks, assignee profile | Home, PH #2 |
| 3 | `vibe-coding.png` | Vibe view | Chat, live diff, app preview | Features/vibe, PH #2 alt |
| 4 | `analytics.png` | Analytics | Tokens, cxjcoins, per-user table, day chart | Home, PH #3 |
| 5 | `budget-wallet.png` | User wallet / limits | Wallet balance, limit rule, extension request | Features/budget |
| 6 | `computer-use.png` | Computer session | Desktop with agent cursor, live view badge | PH #4, features/computer-use |
| 7 | `browser-use.png` | Browser session | Shared Chromium, co-browsing indicator | Features/browser-use |
| 8 | `providers.png` | AI models settings | Provider list incl. Ollama/LiteLLM, per-purpose models | PH #5 |
| 9 | `knowledge.png` | Knowledge settings | Indexing status, ignore patterns, search result | Features/knowledge |
| 10 | `review.png` | PR/diff view | Branch, diff, AI comment | Features/code-review |
| 11 | `teams.png` | Messenger | Channel with a human + an agent | Features/teams |
| 12 | `company.png` | Company mode | Org chart, missions, assistant | features/company (if public) |
| 13 | `install.png` | Terminal | `docker compose up -d` finishing + app URL | Getting started, PH #6 |
| 14 | `mobile.png` | Narrow viewport | Whatever is genuinely good on mobile | Only if it is good |

**Do not capture:** workspaces (broken), empty states, error toasts, placeholder lorem ipsum,
the settings pages without data.

## 2. Brand assets

| Asset | Spec | Notes |
| --- | --- | --- |
| Logo mark | SVG + PNG 512 | `docs/public/only_icon.png` is 267×266 — recreate as SVG for crispness |
| Wordmark | SVG | "codx-junior" lowercase |
| Favicon | ICO 32 + PNG 32/180/192/512 | `apple-touch-icon` included |
| OG card (site) | **1200×630** PNG < 300 KB | Logo + headline + "Open source · AGPL-3.0" |
| OG card (features) | 1200×630 | One per top-level section |
| PH thumbnail | **240×240** | Logo on brand gradient, no small text |
| PH gallery | **1270×760** ×6 | See `launch/PRODUCT_HUNT_PLAN.md` §3 |
| GitHub social preview | 1280×640 | Same as OG card, safe-area aware |
| X header | 1500×500 | Optional |

Brand colors from `docs/.vitepress/theme/custom.css`: `#550e57`, `#8f008f`, `#cc0099`.
Type: one sans (Inter/Geist) + monospace for code (JetBrains Mono).

## 3. Demo video — 90 seconds

No music, no intro animation, captions on, 1080p, real product, real cursor.

| Time | Shot | Narration (on-screen caption) |
| --- | --- | --- |
| 0:00–0:06 | Board with a client project | "A whole project. One tab." |
| 0:06–0:14 | Drag a card to In progress | "Moving a task starts an agent." |
| 0:14–0:30 | Agent searches, patches, runs tests | "It works in your repo, with your context." |
| 0:30–0:44 | Diff + review + approve | "You approve every change." |
| 0:44–0:54 | Cost appears in the wallet | "Every call is metered. Per user." |
| 0:54–1:10 | Computer session: agent clicks, fixes a bug | "It can even use a whole machine — while you watch." |
| 1:10–1:20 | Providers screen | "Self-hosted. Your models. Any provider." |
| 1:20–1:30 | End card: logo, `docker compose up`, URL | "Open source. AGPL-3.0. Install in 10 minutes." |

**20-second clip for X/PH thumbnail loop:** 0:06–0:14 + 0:44–0:54, captioned.

**Script discipline:** record 3 takes; keep the fastest; never hide the loading states — the
honesty reads as confidence.

## 4. Diagrams

| Diagram | Format | Used in |
| --- | --- | --- |
| Architecture (browser → Traefik → client/api/workspaces/models; Milvus; background worker) | SVG, light/dark | `guide/architecture`, HN comment |
| Agent loop (task → context → tools → diff → review → cost) | SVG | Blog, PH #2 |
| Data model (project → board → task = chat → messages/tools/cost) | SVG | Blog, HN |
| Deployment (compose services + volumes) | SVG | Getting started |

Make diagrams at 2× and export SVG; keep the source (Figma/Excalidraw) in `assets/source/`.

## 5. Naming and storage

```
open-source-community/assets/
├── source/            # Figma/Excalidraw/PSD (not shipped)
├── brand/             # logo.svg, wordmark.svg, favicon set
├── og/                # 1200x630 cards
├── screenshots/       # raw 2x PNGs, named as §1
├── screenshots/web/   # WebP exports used by docs/public/images
├── video/             # master MP4, captions .vtt, poster .jpg
└── launch/            # PH gallery 1270x760, thumbnail 240x240
```

Naming: `kebab-case`, no dates, no "final", no "v2". One file per concept.

## 6. Accessibility

- [ ] Every image on the site has an `alt` that describes the *information*, not the pixels.
- [ ] No text baked into screenshots without an alt equivalent.
- [ ] Contrast ≥ 4.5:1 for text over the gradient cards.
- [ ] Video has captions and a transcript link.
- [ ] Animations respect `prefers-reduced-motion`.

## 7. Pre-launch asset QA

- [ ] Screenshots show the shipped version (check nav/footer version string).
- [ ] No token, key, email, private repo name or local path visible.
- [ ] OG image renders in LinkedIn/X/Slack/Discord/WhatsApp.
- [ ] PH gallery text readable at 50% zoom on a phone.
- [ ] Video plays muted, captions legible, first frame is not a black screen.
- [ ] Total `docs/public/images` ≤ 3 MB after conversion.
