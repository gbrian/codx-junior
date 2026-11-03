# Approach B — Adaptive page contract ("one component, two densities")

> Status: proposed · Part of the **Mobile Refactor** board (design decision pending).
> Owner of the design: Mockups / Designer · Reviewer: board owner.
> Fixes the *inconsistency*: one screen definition, rendered at two densities.

---

## 1. Idea

Instead of wrapping the current screens, **change what a screen is**. Every screen declares
its own chrome through a single contract — title, back, actions, scroll behaviour — and the
contract is rendered by the mode, not by the screen. Screens stop building headers, drawers
and scroll containers; the duplicate desktop/mobile component pairs are collapsed into one
adaptive component each.

The user-visible result: the same product at 390 px and at 1600 px, with the *same* features,
laid out differently — not two products that happen to share a colour scheme.

```
PHONE (390)                    TABLET (768)                DESKTOP (unchanged)
┌───────────────┐              ┌───────────────────────┐    ┌────┬──────────────────────┐
│ ‹  Chat    ⋯  │              │ ‹  Chat           ⋯   │    │rail│  dockview panels     │
├───────────────┤              ├──────────┬────────────┤    │    │  (ChatView, Kanban…) │
│ messages      │              │ list     │ messages   │    │    │                      │
│               │  ← same      │ (rail)   │            │    │    │                      │
├───────────────┤    component │          │            │    │    │                      │
│ [ composer ]  │              ├──────────┴────────────┤    │    │                      │
└───────────────┘              │ [ composer ]          │    │    │                      │
                               └───────────────────────┘    └────┴──────────────────────┘
```

## 2. The contract

```vue
<!-- src/components/mobile/MobilePage.vue  (rendered by the shell in mobile mode) -->
<MobilePage :title="title" :back="back" :actions="actions" :pad="false">
  <ChatConversation />          <!-- the screen's real content, nothing else -->
</MobilePage>
```

Rules:

1. A screen **never** renders a top bar, a drawer, or a full-height scroll container.
2. A screen **never** reads `window.innerWidth`; it reads `useViewport()` only to choose a
   *density*, not to fork into another component.
3. A screen declares `meta.title` / `meta.parent` / `meta.actions` in the router, so the shell
   can render chrome before the screen chunk even loads (skeleton ≠ blank).
4. Identity comes from the URL; the screen fetches its object on mount (kills the `PENDING`
   map, D5).
5. Layout differences are expressed with **container queries** on the page root
   (`@container`), not with `v-if` on a global flag — a dockview panel at 500 px wide behaves
   like a phone even on a desktop.

## 3. What changes

**New primitives**

| File | Purpose |
|---|---|
| `src/components/mobile/MobilePage.vue` | app bar + content slot + scroll owner + safe areas |
| `src/components/mobile/MobileList.vue` / `MobileListItem.vue` | list → detail pattern used by kanban, files, teams, knowledge |
| `src/components/mobile/MoreSheet.vue` | registry grouped in the desktop sidebar's sections |
| `src/composables/useViewport.js` | `phone` / `tablet` / `desktop`, single breakpoint table |

**Screens consolidated (duplicate removed)**

| Kept | Deleted | Note |
|---|---|---|
| `views/ChatView.vue` (adaptive) | `views/QuickChatView.vue`, `components/ChatEntryMobile.vue` | chat becomes **one** component; `ChatEntry` loses the `$ui.isMobile` fork |
| `components/workspaces/WorkspacesManager.vue` (adaptive) | `views/WorkspaceView.vue` | |
| `components/browsers/BrowserSessionList.vue` (adaptive) | `components/browsers/BrowsersSessionManager.vue` | also fixes `browser-viewer` (D8) |
| `views/ManagementDashboardView.vue` | `views/CodxWelcomeView.vue` | one Home |
| `views/GlobalSettings.vue` | the second (mobile) markup branch *inside the same file* | 10 duplicated blocks → 1 |

**Screens that must be re-laid out (not just re-wrapped)**

`KanbanBoardView.vue` (columns → vertically paged columns), `FileExplorerPanel.vue`
(tree → drill-down list), `VibeCodingView.vue` (splitter → tabs), `InfraView.vue`
(tables → cards), `views/TeamView.vue` (`TeamBar` → sheet).

**Shell / plumbing**

`src/App.vue` (shell only), `src/store/ui.js` (drop `isMobile`, keep `viewport`),
`src/router/index.ts` (`meta` on every route + `/desktop` device guard),
`src/config/apps.js` + `src/config/appComponentsMap.js` (one table, asserted equal by a test),
`src/router/navigate.js` (`openApp` is the only opener; delete the `browsers.open` bypass).

## 4. Defects this closes

| D | Closed? | How |
|---|---|---|
| D1 three breakpoints | ✅ | `useViewport` + container queries |
| D2 no navigation | ✅ | shell (bottom bar + More sheet) |
| D3 no page chrome | ✅ | `MobilePage` contract |
| D4 URL decides mode | ✅ | device guard + container queries make width, not URL, the driver |
| D5 in-memory payload | ✅ | identity in the URL, object fetched on mount |
| D6 missing chat component | ✅ | the fork is deleted, not implemented |
| D7 orphan mobile code | ✅ | `MenuBar`, sidebar mobile branch, `SplitView`/`Splitter` |
| D8 registry bypass | ✅ | all openers funnel through `openApp` |
| D9 no primitives | ✅ | `MobilePage` / `MobileList` / `MoreSheet` |
| D10 registry/router divergence | ✅ | single table + test |
| §7 duplication | ✅ | 6 duplicate pairs collapsed |

## 5. Effort, risk, rollout

| | |
|---|---|
| Effort | 2–3 sprints, ~15 screens touched, 4 screens re-laid out |
| Risk | **medium-high** — touches the screens people use daily; needs the D6/D5 decisions taken first |
| Rollout | per-screen increment: each migration is one PR, behind `ui.mobilePages`, merged screen by screen |
| Reversibility | medium — deleting the duplicate component is irreversible per screen, hence the flag |
| Biggest trap | `useViewport` *and* container queries both exist; a screen that uses the global flag will look right in the browser test and wrong inside a narrow dockview panel |

## 6. Sequencing (if chosen)

1. Primitives + shell (same code as approach A §4 — the two approaches share M1).
2. Fix D6 properly (delete `ChatEntryMobile`, make `ChatEntry` adaptive).
3. Migrate Chat (proves list→detail + composer + keyboard).
4. Migrate Tasks (proves the dense board).
5. Migrate the four "cannot adapt" screens.
6. Sweep the remaining `@/views/*` screens to the contract; delete duplicates at the end of each PR.
7. Add the registry/router equality test (C5: the project has almost no tests).

## 7. Acceptance criteria

1. For chat, workspaces, browsers and home there is **exactly one** component; a repo search
   for `QuickChatView`, `WorkspaceView`, `BrowsersSessionManager`, `CodxWelcomeView`,
   `ChatEntryMobile` returns zero hits.
2. No screen contains a top bar, a `drawer`, or `window.innerWidth` (grep == 0 outside `useViewport`).
3. Every screen renders correctly inside a 500 px wide dockview panel on desktop (container
   query proof) **and** at 390 px on a phone.
4. Refresh on a deep link (`/:project/chat/:id/:name`, `/:project/kanban/:board`) renders the
   object from the URL with the `PENDING` map removed.
5. `appKey → route → component` is asserted by an automated test.

## 8. Why this might be the right answer

It is the only approach that removes the *reason* the pages are inconsistent: two UI stacks.
The cost is honest: it is the approach with the most screen churn, the most mockups needed
(two densities per screen), and the one that most needs the test suite the project does not
have yet.
