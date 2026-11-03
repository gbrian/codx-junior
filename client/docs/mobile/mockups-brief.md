# Mockups brief — mobile strategy, 3 approaches

> Audience: **Mockups / Designer** profile (owner of this brief), reviewed by the
> **Mobile Refactor** board owner.
> Input documents: `docs/mobile/mobile-current-status.md` (v1 audit) and
> `docs/mobile/status-verification-delta.md` (v2 corrections — **read this first**).
> Deliverable of this brief: three *different* mobile strategies, mocked at the same
> fidelity so they can be compared and one can be chosen.

---

## 1. What must be designed

The product is a project-scoped workspace with **35 registered apps**
(`src/config/apps.js`) rendered either as dockview panels (desktop) or as one route at a
time (`AppRouteView`). On a phone today there is **no chrome at all**: `<RouterView/>`
fills the screen, the navigation drawer exists but has **no visible trigger**, and each
screen invents its own header, sidebar and scroll container.

The brief is **not** "make these screens responsive one by one". It is:

> Give the product **one** mobile navigation model, **one** page shell and **one**
> decision about who owns navigation (the shell) versus content (the screen) — then show
> three *structurally different* ways to get there.

## 2. Hard constraints (apply to all three approaches)

| # | Constraint |
|---|---|
| C1 | Phones must **never** mount the dockview workspace (`.../desktop`), even if the URL says so |
| C2 | Deep links keep working: every route is `/:projectName/...`; identity (chat id, board, file path) must be recoverable from the URL |
| C3 | Touch targets ≥ 44×44 px; no hover-only affordance; nothing important in the top-right corner |
| C4 | Safe areas: `env(safe-area-inset-top)` under the status bar, `env(safe-area-inset-bottom)` under the home indicator |
| C5 | Sticky app bar ≈ 56 px, bottom navigation ≤ 5 destinations (last may be "More") |
| C6 | The virtual keyboard must not cover the chat composer or a form's primary action |
| C7 | Long content is horizontally scrollable (code blocks, tables, kanban columns) — never clipped |
| C8 | Dark theme tokens only (daisyUI `base-*` / `primary` / `secondary`), icons = Font Awesome as used today |
| C9 | Every destination reachable from the bottom bar/More in **≤ 2 taps** from anywhere |
| C10 | The desktop experience must not regress: approaches must be shippable behind a flag |

## 3. Frames required for EACH approach

Primary canvas: **390 × 844** (iPhone 14 class). One tablet variant per approach: **768 × 1024**.

| # | Frame | What it must answer |
|---|---|---|
| F1 | Landing / Home | Which screen does a phone land on, and what is the first navigation affordance? |
| F2 | Navigation surface | Bottom bar, drawer, launcher grid, or hybrid — open **and** closed states |
| F3 | A module with a list | Task Manager board (or planning list) — how does a dense board survive 390 px? |
| F4 | Chat | Conversation + composer + the moment the keyboard is open |
| F5 | A nested screen | File explorer / file viewer — journey *list → detail → back* |
| F6 | Settings | A screen that today ships **two** duplicated markup branches (`GlobalSettings.vue`) |
| F7 | State matrix | Loading, empty, error, offline for F3 and F4 as small tiles |
| F8 | Navigation diagram | The navigation graph + back-stack rules (what "back" means) |

Every frame must be annotated with: **where the back action lives**, **what `$ui.isMobile`
branch was deleted**, and **the route(s) it maps to**.

## 4. Comparison criteria (fill in for each approach)

| Criterion | Weight | How to judge |
|---|---|---|
| Learnability (find anything in ≤ 2 taps) | high | F9 walkthrough: open chat from Home, open a board, come back |
| Consistency across the 35 apps | high | does every screen get the same header/back/scroll, without per-screen work? |
| One-hand reachability | medium | primary actions inside the bottom 40% of the screen |
| Screens that cannot adapt (kanban, file explorer, vibe coding, infra tables) | high | does the approach have an answer other than "horizontal scroll"? |
| Implementation cost / risk | high | files touched, screens rewritten, desktop risk |
| Reversibility | medium | flag-gated? deletable? |
| Residual duplication removed | medium | §7 duplication map in the v1 audit |

## 5. Deliverables

1. `docs/mobile/approaches/01-*.md`, `02-*.md`, `03-*.md` — one document per approach,
   same structure: idea, navigation model, page shell, what changes (files), D-refs fixed,
   D-refs left, effort/risk, rollout flag, acceptance criteria, wireframes.
2. The frames above, exported as PNG/SVG in `docs/mobile/approaches/assets/<n>/`
   (or as inline HTML/SVG inside the approach document if binary export is not available).
3. A one-page comparison table appended to `docs/mobile/README.md` with a recommendation.

## 6. Non-goals

- No visual redesign of the desktop workspace (dockview, panels, splitters).
- No new product features, no new endpoints.
- No pixel-perfect brand work: this is a **navigation and shell** decision.

## 7. Open questions the mockups must resolve (not dodge)

1. **Bottom bar or drawer, or both?** A drawer-only model failed in production because the
   trigger is invisible; a bottom bar has only 5 slots for 35 apps.
2. **What does "back" mean** when screens are routes: browser history, an app-defined
   parent (`meta.parent`), or a per-module stack?
3. **Where does the project switcher live** on a phone (today it only exists inside the
   off-canvas drawer and inside `AppsSection`)?
4. **Do chat / workspaces / browsers keep two components** (desktop ↔ mobile) or become one
   adaptive component? This is the single biggest cost driver.
