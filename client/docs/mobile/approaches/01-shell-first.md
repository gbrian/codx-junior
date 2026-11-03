# Approach A — Shell-first ("wrap and ship")

> Status: proposed · Part of the **Mobile Refactor** board (design decision pending).
> Owner of the design: Mockups / Designer · Reviewer: board owner.
> Fixes the navigation *hole* with the smallest possible surface change.

---

## 1. Idea

Keep every existing screen exactly as it is. Add **one** wrapper between `App.vue` and
`<RouterView/>` that owns all the chrome a phone needs — app bar, back, bottom navigation,
safe areas, scroll container — and let each screen keep its own layout inside it.

The phone stops being "a desktop route rendered alone" and becomes "a desktop screen inside
a mobile shell". No screen is rewritten; the worst screens (kanban, file explorer, vibe
coding, infra) are accepted as degraded for now and addressed in later increments.

```
┌─────────────────────────────┐
│ ☰  Task Manager      ⌄  ⋯   │ ← MobileAppBar (56px, sticky, safe-area-top)
├─────────────────────────────┤
│                             │
│      current <RouterView/>  │ ← unchanged screen
│                             │
├─────────────────────────────┤
│ ⌂     ✓     💬     📁    ⋯  │ ← MobileBottomBar (safe-area-bottom)
│Home  Tasks  Chat  Files More│
└─────────────────────────────┘
```

## 2. Navigation model

- **Bottom bar = the only global navigation.** 5 slots: Home, Tasks, Chat, Files, More.
  "More" opens a full-screen sheet that renders the whole registry (`APPS`) grouped by the
  same sections the desktop sidebar uses (`AppsSection` / `WorkspacesSection`).
- **App bar = context.** Title from `route.meta.title`, back arrow when `route.meta.parent`
  is set, right slot for one screen action.
- **Back** = `router.back()` when there is in-app history, otherwise `router.push(meta.parent)`
  (never leaves the app on a dead history entry).
- **Drawer stays**, but only as the *More* content on tablets (≥ 768 px); on phones the
  drawer is not used at all (it is the thing that failed).
- **Project switcher** moves into the app bar (it is the one global object on every screen).

## 3. Page shell contract

```
MobileShell
  ├── <MobileAppBar :title :back :actions/>
  ├── <main class="flex-1 min-h-0 overflow-y-auto">  ← the ONLY scroll container
  │      <RouterView/>
  └── <MobileBottomBar/>
```

Everything is driven by route meta, so a screen opts in with 3 lines:

```ts
{ path: '/:projectName/kanban/:board?/:boardName?', name: 'kanban',
  meta: { app: 'tasks', title: 'Task Manager', parent: 'home', primary: 'tasks' } }
```

## 4. What changes

| File | Change |
|---|---|
| `src/components/mobile/MobileShell.vue` | **new** — grid layout + safe areas + scroll owner |
| `src/components/mobile/MobileAppBar.vue` | **new** — title / back / action slot |
| `src/components/layout/MobileBottomBar.vue` | **extend** — 5 slots, `primary` from route meta, real "New chat" action, registered `safe-area-bottom` utility |
| `src/composables/useViewport.js` | **new** — `phone` / `tablet` / `desktop` from one breakpoint table |
| `src/App.vue` | render `MobileShell` instead of the raw `<RouterView/>`; delete the local `isMobile`; delete the duplicate backdrop; **keep** `DesktopSidebar` for `desktop` only |
| `src/store/ui.js` | `handleResize` delegates to `useViewport`; expose `viewport` (`phone`/`tablet`/`desktop`) next to the legacy `isMobile` |
| `src/router/index.ts` | add `meta.title` / `meta.parent` / `meta.primary` to every route |
| `src/router/navigate.js` | device guard: on `phone`, `codx-junior-split` redirects to the last non-desktop route (or `home`) |
| `src/components/layout/DesktopSidebar.vue` | delete the whole `v-if="isMobile"` branch (the shell owns the drawer) |
| `src/components/ChatEntryMobile.vue` | **create** — D6 is a hard blocker (see §7) |
| `src/components/mobile/MenuBar.vue` | delete (orphaned, unimported children) |

## 5. Defects this closes

| D | Closed? | How |
|---|---|---|
| D1 three breakpoints | ✅ | `useViewport` is the only reader of `innerWidth` |
| D2 no navigation on phone | ✅ | bottom bar is always rendered, independent of route changes |
| D3 no page chrome | ✅ | app bar + one scroll container |
| D4 URL decides mode | ✅ | guard: a phone never mounts `.../desktop` |
| D6 missing chat mobile component | ✅ | created (or the fork deleted — see §7) |
| D7 orphan mobile code | ✅ | `MenuBar.vue` and the `isMobile` sidebar branch removed |
| D9 no primitives | ✅ | shell ships back/title/safe areas/scroll |
| D5 payload hand-off | ❌ | untouched |
| D8 registry bypass | ❌ | untouched (`openMediaLibrary`, `browsers.open`) |
| D10 registry/router divergence | ❌ | untouched |

§7 duplication map is untouched: chat, workspaces, browsers and home still ship two components.

## 6. Effort, risk, rollout

| | |
|---|---|
| Effort | ~1 sprint (1 dev + design review), no screen rewrites |
| Risk | **low** — additive; the desktop path is untouched and the shell is behind a flag |
| Rollout | `feature flag: ui.mobileShell`, default off, on for the team first |
| Reversibility | high — delete one wrapper and the meta fields |
| Known degradation | kanban board, file explorer (256 px tree), vibe coding splitter, infra tables remain cramped; horizontal scroll only |

## 7. The D6 decision (must be taken inside this increment)

`ChatEntry.vue` imports `./ChatEntryMobile.vue`, which does not exist → no mobile message
rendering at all. Two options:

- **A1 (cheap):** create a thin `ChatEntryMobile.vue` that re-uses the desktop template in a
  single column (markdown + collapsible tool calls, no diff panel).
- **A2 (right):** delete the fork and make `ChatEntry.vue` responsive with container queries.

Approach A can ship with A1; approach B requires A2.

## 8. Acceptance criteria

1. On a 390 × 844 device, from cold start: Home → Tasks → a task → back → Chat → back:
   every step reachable in ≤ 2 taps and no screen without a visible back affordance.
2. Opening `/:project/home` on a phone, then pasting `/:project/desktop`, does **not** mount
   dockview (redirects instead).
3. Nothing sits under the iOS home indicator or the status bar (safe-area check on a notched device).
4. `$ui.isMobile` is no longer read outside `useViewport` (grep == 0 hits).
5. Chat renders messages at 390 px (D6 closed) — no console error, no blank bubbles.
6. Desktop: identical layout, identical saved dockview layouts (`projectLayout_<project>` intact).

## 9. Why this might be the right answer

It converts a *blocked* product (no navigation) into a *usable* one in one sprint, keeps the
desktop unaffected, and produces the shell + primitives (`useViewport`, app bar, bottom bar,
guards) that approaches B and C need anyway. Its weakness is honest: it does not fix the
inconsistency between screens — it only stops the inconsistency from being *fatal*.
