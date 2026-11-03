# Mobile status — verification delta (v2)

> Supersedes specific claims of `docs/mobile/mobile-current-status.md` (v1).
> Where this file and v1 disagree, **this file wins**.
> Method: direct re-read of the files on disk (v1 was partly written from a stale
> search index, which still returns an old `App.vue` that imports `HomeMobile.vue`).
> Nothing here was verified on a device — items marked 🟨 still need a device check.

---

## 1. Why a delta

The v1 audit concluded "there is no mobile navigation at all, and no state to build on".
Re-reading the files shows the picture is **less bad on state and worse on wiring**:

- the single source of truth for the sidebar (`sidebarCollapsed`) **already exists** and is persisted;
- a **bottom navigation bar already exists** (`components/layout/MobileBottomBar.vue`) but **nobody mounts it**;
- the shell renders the sidebar **twice** for the mobile case, with two stacked backdrops;
- the chat mobile component (`ChatEntryMobile.vue`) referenced by `ChatEntry.vue` **really is missing** (D6 confirmed).

## 2. Corrections to v1

| # | v1 claim | Verified state | Evidence | Impact on the plan |
|---|---|---|---|---|
| 1 | Sidebar lives in `src/components/desktop/DesktopSidebar.vue` | It lives in **`src/components/layout/DesktopSidebar.vue`** and imports `./AppsSection.vue`, `./WorkspacesSection.vue`, `../Notifications.vue`, `../main-menu/WindowsMenu.vue` | `src/App.vue` import; `read_folder src/components/layout` | All refactor paths start from `layout/`, not `desktop/` |
| 2 | "The sidebar open state does not exist / is local" (basis of D2) | **Partly false.** `store/ui.js` has `sidebarCollapsed`, getter `isSidebarExpanded`, mutations `setSidebarCollapsed` / `expandSidebar` / `collapseSidebar` / `toggleSidebar`, persisted in the `uiState` localStorage snapshot | `src/store/ui.js` | What is missing is a **visible trigger**, not the state model. D2 becomes "no trigger mounted" |
| 3 | "No bottom navigation exists anywhere" | **False.** `src/components/layout/MobileBottomBar.vue` exists: `fixed bottom-0 z-50`, 4 items (Menu → `expandSidebar()`, New → `apps.openHome()`, Task Manager → `apps.openKanban()`, Files → `apps.openFileExplorer()`), emits `show-menu` | the file itself | The 3 approaches reuse/extend it instead of inventing it |
| 3b | — | The bar is **not imported by any mounted component** (`App.vue` renders only `DesktopSidebar` + `<RouterView>`): dead primitive | `src/App.vue` template | Cheap first win (M1) |
| 3c | — | Its "New" item opens **Home**, not a new chat — mislabelled/miswired | `handleNavigateToNewChat() → apps.openHome()` | Fix while wiring |
| 3d | — | It uses the class `safe-area-bottom`; **no `safe-area` CSS exists in the project** | search for `safe-area` returns only this file (+ `index.html` viewport meta) | Bar sits under the iOS home indicator until the utility is defined |
| 4 | `src/views/HomeMobile.vue` exists and is referenced by `App.vue` | It **does not exist** in `src/views/` and nothing references it | `read_folder src/views` | D7 partially closed already |
| 5 | `components/mobile/MenuBar.vue` is orphaned | **Confirmed orphaned**: renders `<ProjectSelector>`, `<Notifications>`, `<UserMenu>` without importing them | the file | Safe to delete once the shell lands |
| 6 | Mobile drawer has one backdrop | **Two backdrops**: `DesktopSidebar` renders its own (`fixed inset-0 z-40`) **and** `App.vue` renders another (`fixed inset-0 z-100`), both closing the same store flag | `App.vue` template; `layout/DesktopSidebar.vue` `v-if="isMobile"` branch | Every approach must delete one; otherwise double blur + double click handling |
| 7 | D6: `ChatEntryMobile.vue` missing | **Confirmed missing.** `ChatEntry.vue` does `import ChatEntryMobile from './ChatEntryMobile.vue'` and renders it under `v-else-if="$ui.isMobile"` | `src/components/ChatEntry.vue`; no such file under `src/components/` | Blocker: chat messages have **no** mobile rendering path, and since `$ui.isMobile` is `width <= 1024` this also hits laptops/tablets |
| 8 | D8/D10: `browsers.open()` bypasses the registry | **Confirmed.** It still calls `$storex.ui.showApp({ component: 'browser-viewer' })` when `!$ui.isMobile`; `browser-viewer` exists in neither `config/apps.js` nor `config/appComponentsMap.js` | `src/router/navigate.js` → `browsers.open()` | Dead panel on desktop; route/panel divergence in the browsers module |
| 9 | D8: `openMediaLibrary` has field typos | **Confirmed**: `{ tgabId: 'media-library', compotabIdnent: 'media-library' }` | `src/store/ui.js` | Cannot work on any device |
| 10 | Three breakpoints | **Still three**: `< 768` in `App.vue` (`isMobile`), `<= 1024` in `store/ui.js` (`handleResize` → `$ui.isMobile`), `< 1024` in the chat drawer (🟨 not re-read) | both files | Unchanged: single `useViewport()` required |
| 11 | Mobile drawer collapses on every route change | **Confirmed**: collapsed in `created()` **and** in `watch: { '$route' }` | `src/App.vue` | A drawer-as-navigation model needs `collapsed` decoupled from routing (or a bottom bar) |

Still valid from v1 (not re-verified here, keep as-is): the module/route inventory (§2),
the registry↔router divergences (§2.1), the `PENDING` payload hand-off (D5), the
dockview/`localStorage` constraints (C1–C3), the missing test suite (C5), the `eruda`
CDN load (C6).

## 3. Router / shell facts the three approaches are built on

```
src/App.vue
  ├── isMobile = innerWidth < 768                 (local, own resize listener)
  ├── desktop rail   : isDesktopLandscape && !isFullScreenRoute → layout/DesktopSidebar
  ├── mobile backdrop: isMobile && $ui.isSidebarExpanded         (z-100)
  ├── mobile panel   : isMobile && !isFullScreenRoute            → layout/DesktopSidebar :is-mobile="true"
  └── <RouterView/>                              ← no title, no back, no bottom bar
```

- `isFullScreenRoute` still covers only `route.name === 'solopreneur'`.
- Mode is still derived from the **URL**: `navigate.js → isDesktopMode()` =
  `currentRoute.name === 'codx-junior-split'`; `store/ui.js` repeats the same check in a getter.
- `openApp(appKey, payload)` is the only unified opener; single mode pushes a route,
  desktop mode creates a dockview panel. Every legacy `$ui.showApp({component})`
  call site (browsers, media library, vibe coding in `QuickBar`) bypasses it.
- `AppRouteView` resolves `meta.app → APPS → APP_COMPONENTS_MAP`; params come from
  `getPendingParams(...)` first, then `route.params + route.query`.

## 4. Net effect on the refactor

| D-ref | Still a blocker? | Note |
|---|---|---|
| D1 three breakpoints | yes | unchanged |
| D2 no navigation on phone | **partially** | state exists, bottom bar exists → it is a **wiring** job |
| D3 no page chrome | yes | unchanged: no app bar / title / back anywhere |
| D4 URL decides mode | yes | unchanged |
| D5 in-memory payload | yes | unchanged |
| D6 missing `ChatEntryMobile.vue` | **yes, build-level** | must be fixed before any mobile demo |
| D7 orphan mobile code | **partially closed** | `HomeMobile.vue` is already gone; `MenuBar.vue` remains |
| D8 registry bypass | yes | `openMediaLibrary`, `browsers.open`, `QuickBar.openVibeCoding` |
| D9 no mobile primitives | yes | but the bottom bar + `NavItem.vue` give a starting point |
| D10 registry/router divergence | yes | unchanged |

## 5. Still to verify on a device (🟨)

1. Does `src/App.vue`'s local `isMobile` ever disagree with `$ui.isMobile` in practice
   (768–1024 px: desktop rail **and** all `$ui.isMobile` branches active)?
2. Is the double backdrop visible on a real phone (two blurs, two click targets)?
3. Does opening `.../desktop` on a phone actually mount dockview, and how badly does it fail?
4. Real keyboard behaviour: is the chat composer covered by the virtual keyboard?
5. Touch targets in `layout/AppsSection.vue` / `NavItem.vue` (measured sizes, not guessed).
