# Approach C — Launcher + stack ("mobile is its own product surface")

> Status: proposed · Part of the **Mobile Refactor** board (design decision pending).
> Owner of the design: Mockups / Designer · Reviewer: board owner.
> Fixes the *model*: phones get a navigation architecture of their own, not a squeezed desktop.

---

## 1. Idea

Approach A wraps the current screens; approach B makes one screen adapt. Approach C accepts
that **a workspace of 35 apps cannot be a phone menu** and gives the phone its own surface:

- a **Launcher** as the landing screen (the modules that make sense on a phone, big targets,
  recents at the top);
- a **per-module stack**: entering a module pushes a stack, "back" pops it, and the bottom
  bar is always reachable (it never changes meaning);
- a small, explicit **mobile registry**: for each `appKey`, an icon, a title, a "fits on a
  phone?" flag, and optionally a dedicated mobile component — so the 12 apps that do *not*
  fit on a phone are not silently cramped, they are routed to a "open on desktop" screen or
  to a list-shaped alternative.

Desktop is untouched. The route tree stays the same (deep links work), but the *phone*
resolves the same URL into a stack-aware surface.

```
LAUNCHER                     STACK (within a module)          BOTTOM BAR (constant)
┌───────────────────┐        ┌───────────────────┐            ┌───────────────────┐
│ codx-junior    ⌄  │        │ ‹  Task Manager ⋯ │            │  ⌂      ✓      💬 │
│ ┌───┐ ┌───┐ ┌───┐ │  tap   ├───────────────────┤   always   │ Home  Tasks  Chat │
│ │ ✓ │ │ 💬│ │ 📁│ │ ─────► │ Backlog   (3)     │   visible  ├───────────────────┤
│ └───┘ └───┘ └───┘ │        │  · task card      │            │   📁      ⊞       │
│ ┌───┐ ┌───┐ ┌───┐ │        │  · task card      │            │ Files   More      │
│ │ 👥│ │ ⚙ │ │ ⋯ │ │        ├───────────────────┤            └───────────────────┘
│ └───┘ └───┘ └───┘ │        │ [ + New task    ] │
│ Recents           │        └───────────────────┘
└───────────────────┘
```

## 2. Navigation model

**Three levels, never more**

| Level | Surface | Example |
|---|---|---|
| L0 | Launcher (`/:project/home` on phone) | module grid + recents + project switcher |
| L1 | Module root | Task Manager boards list, Files roots, Chat list |
| L2 | Detail | a task, a file, a conversation |

The bottom bar is a **sibling of the stack**, not part of it: tapping a bar item *resets* to
that module's L1 (second tap on the active item pops to L1, third does nothing).

**Back rules (explicit, not browser history)**

| Situation | Back does |
|---|---|
| L2 in a module | pop to that module's L1 |
| L1 | pop to the Launcher |
| Launcher | nothing (no dead history exit) |
| Deep link into L2 | synthesize the stack: L1 + L2, so back lands on a real screen |

**"More" sheet** holds the full registry (same sections as the desktop sidebar:
Apps / Workspaces / Account), with a `phone-friendly` badge per app and an
"open on desktop" action for the ones that are not.

## 3. The mobile registry (the core of this approach)

```js
// src/config/mobileApps.js  — the ONLY place that decides "can a phone do this?"
export const MOBILE_APPS = {
  tasks:   { order: 10, primary: true,  title: 'Tasks',  icon: 'fa-list-check',
             entry: 'kanban', fits: 'list',  mobileComponent: null },
  chat:    { order: 20, primary: true,  title: 'Chat',   icon: 'fa-comments',
             entry: 'chats', fits: 'full',   mobileComponent: null },
  files:   { order: 30, primary: true,  title: 'Files',  icon: 'fa-folder-open',
             entry: 'file-explorer', fits: 'drill', mobileComponent: 'MobileFileList' },
  knowledge:{order: 40, title: 'Knowledge', icon: 'fa-magnifying-glass', fits: 'full' },
  'vibe-coding': { order: 90, title: 'Vibe Coding', icon: 'fa-wand-magic-sparkles',
             fits: 'desktop-only', mobileComponent: 'OpenOnDesktopNotice' }
  // …35 entries, one per APPS key
}
```

Every `APPS` key must have a `MOBILE_APPS` entry (asserted by a test): no app can be
"forgotten" on mobile again — which is exactly the failure mode today.

## 4. What changes

| Area | Change |
|---|---|
| `src/config/mobileApps.js` | **new** — the registry above |
| `src/composables/useMobileStack.js` | **new** — stack push/pop, resets per bar item, deep-link synthesis |
| `src/components/mobile/MobileLauncher.vue` | **new** — L0 grid + recents |
| `src/components/mobile/MobileBar.vue` | extends `MobileBottomBar.vue`; items come from the registry, not hardcoded |
| `src/components/mobile/MoreSheet.vue` | **new** — full registry + badges + "open on desktop" |
| `src/components/mobile/StackHeader.vue` | **new** — ‹ + title + ⋯ built from the stack, not from `meta` |
| `src/components/mobile/mobileViews/MobileKanban.vue`, `MobileFileList.vue`, `OpenOnDesktopNotice.vue` | **new** — the 3–4 screens that genuinely need a phone layout |
| `src/router/index.ts` | `/:project/home` resolves to `MobileLauncher` **only** on phone (single resolution point, not `meta.app`) |
| `src/router/navigate.js` | `openApp` chooses the surface: desktop panel / stack push / `desktop-only` notice |
| `src/App.vue`, `src/store/ui.js`, `src/components/layout/DesktopSidebar.vue` | shell + `useViewport` + delete the mobile drawer branch (same as A) |
| `src/components/ChatEntryMobile.vue` | **create** (D6 blocker) — or delete the fork as in B |

## 5. Defects this closes

| D | Closed? | How |
|---|---|---|
| D1 | ✅ | `useViewport` |
| D2 | ✅ | bar + launcher, both always visible |
| D3 | ✅ | `StackHeader` owns the chrome |
| D4 | ✅ | device decides the surface; `.../desktop` on a phone → launcher |
| D6 | ✅ | created/deleted before the first demo |
| D7 | ✅ | drawer mobile branch + `MenuBar` + `SplitView`/`Splitter` |
| D8 | ✅ | `openApp` is the only opener and it now also decides the surface |
| D9 | ✅ | shell + bar + header + sheet |
| D10 | ✅ | `MOBILE_APPS` keyed by `APPS` key, asserted by test |
| D5 | ⚠️ partial | the L2 stack needs identity in the URL anyway → effectively closed for the modules on the bar; the rest keeps `PENDING` until migrated |
| §7 duplication | ⚠️ partial | chat/files get one mobile component; global settings stays duplicated until migrated |

## 6. Effort, risk, rollout

| | |
|---|---|
| Effort | 3–4 sprints; 1 registry + 5 new components + 3–4 mobile-specific screens |
| Risk | **high** — it changes how the phone resolves routes, which is the highest-blast-radius change in the list |
| Rollout | `feature flag: ui.mobileLauncher` + `MOBILE_APPS.fits` can be rolled out per app (an app marked `desktop-only` simply shows the notice) |
| Reversibility | medium — the registry is additive, the launcher landing is a single route resolution |
| Design cost | highest — every bar item, the launcher grid, the sheet and the stack header need mockups |

## 7. Acceptance criteria

1. From the Launcher, any phone-friendly app is reachable in ≤ 2 taps; any desktop-only app is
   *labelled* as such instead of rendering a broken layout.
2. Back never exits the app: L2 → L1 → Launcher → (no-op).
3. Opening a deep link `/:project/kanban/:board` on a phone synthesizes L1 + L2 and back lands
   on the boards list.
4. Every key of `APPS` has exactly one `MOBILE_APPS` entry (automated test).
5. After 5 minutes of use the bar has not changed meaning (same 4 destinations, same order).
6. Desktop: byte-identical dockview behaviour, saved layouts unaffected.

## 8. Why this might be the right answer

It is the only approach that answers the two questions the other two dodge: *"35 apps do not
fit in 5 slots"* and *"some screens cannot be squeezed"*. It gives each screen an explicit,
reviewable mobile status (`fits`) instead of an implicit one (nobody ever tried). It is also
the most expensive and the only one that changes the mental model of the product, so it needs
product sign-off, not only engineering sign-off.

## 9. Why it might be too much

If the mobile audience is "check my tasks and answer a chat while away", then a launcher grid
plus a stack is more architecture than the usage justifies — approach A gets 80 % of the
value in 20 % of the time. The decision hinges on whether mobile is a **support surface** or a
**first-class surface**.
