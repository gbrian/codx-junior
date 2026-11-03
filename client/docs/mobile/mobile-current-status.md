# Mobile mode — current status audit

> Status document for the **Mobile Refactor** board.
> Scope: the customer-facing web client (`/home/codx-junior-projects/codx-junior/client`).
> Method: static reading of the router, the app registry, the shell and the heaviest screens.
> **No device testing was performed for this version** — every "mobile status" below is inferred from the code
> structure. Items marked 🟥 are confirmed by code; items marked 🟨 need a device check.

---

## 1. Executive summary

On a phone the application **cannot be navigated**. The shell renders only the current screen with no app bar,
no title, no back button and no bottom navigation; the one navigation surface (the sidebar) is an off-canvas
panel that is collapsed on every route change and whose only open controls live *inside* the closed panel.
On top of that the "is this a phone?" question has three different answers in three files, the app decides
"desktop workspace vs single screen" from the **URL** instead of the device, and every screen invents its own
header, sidebar and scroll container — so the same product looks like 40 different products.

**Three root causes**

1. **No mobile shell.** There is no persistent navigation/chrome owned by the application; each screen is
   responsible for its own navigation and most simply have none.
2. **No single source of truth for viewport / mode.** Three breakpoints (`768`, `1024`, and a route name) decide
   what "mobile" means, in three different places.
3. **Two parallel UI stacks.** Desktop renders dockview panels; mobile renders routes through
   `AppRouteView`. Some modules resolve to a *different component* in each path (chat, workspaces, browsers, home),
   which is why behaviour and layout diverge between the modes.

**Business impact:** the product is effectively desktop-only. Phones and small tablets are a first-class
support surface for chat/task triage, and today they cannot even reach the screens.

---

## 2. Module & route inventory

Sources of truth (and they disagree — see §2.1):

- `src/config/apps.js` → `APPS`: the registry that decides *how an app is opened*.
- `src/router/index.ts` → project-scoped routes, all under `/:projectName/...`.
- `src/config/appComponentsMap.js` → `appKey → component` (lazy `defineAsyncComponent`).

| # | appKey | Title | Route (name → path) | Component (route) | Component (panel) | Desktop = panel | New phone route | Mobile status |
|---|---|---|---|---|---|---|---|---|
| 1 | `home` | Home | `home` → `/:projectName` | `AppRouteView` → **management-dashboard** (`meta.app`) | `CodxWelcomeView` | yes | yes | 🟨 diverges (different component per mode) |
| 2 | `solopreneur` | Solopreneur | `solopreneur` → `/solopreneur/:module?` (unscoped) | `SolopreneurView` | `SolopreneurView` | yes | yes | 🟨 full-screen route; sidebar hidden by `isFullScreenRoute` |
| 3 | `tasks` | Task Manager | `kanban` → `/:projectName/kanban/:board?/:boardName?` | `KanbanBoardView` | `KanbanBoardView` | yes (multi-instance) | yes | 🟥 degrades (dense board UI) |
| 4 | `planning` | Planning | `kanban?view=planning` | `KanbanBoardView` | `KanbanBoardView` | yes | yes | 🟥 degrades |
| 5 | `management-dashboard` | Management | `management-dashboard` → `/:projectName/management-dashboard` | `ManagementDashboardView` | `ManagementDashboardView` | yes | yes | 🟨 unknown (also the landing screen) |
| 6 | `chat` | Chat | `chat` → `/:projectName/chats/:chatId/:chatName` (+ `chat-workspace`) | **`QuickChatView`** | **`views/ChatView.vue`** | yes | yes | 🟥 broken (`ChatEntryMobile` missing, §6 D6) |
| 7 | `messenger` | Messenger | `messenger` → `/:projectName/messenger` | `MessengerView` | `MessengerView` | yes | yes | 🟨 unknown |
| 8 | `meet` | Meet | `meet` / `meet-session` | `MeetView` | `MeetView` | yes | yes | 🟨 unknown |
| 9 | `team` | Team | `team` → `/:projectName/team/:teamId?` | `TeamView` | `TeamView` | yes | yes | 🟨 unknown |
| 10 | `workspaces` | Workspaces | `workspaces` → `/:projectName/workspaces` | **`WorkspaceView`** | **`WorkspacesManager`** | yes | yes | 🟥 diverges per mode |
| 11 | `workspace` | Workspace | `workspace` → `/:projectName/workspaces/:workspaceId/:workspaceName` | `AppWindow` | `AppWindow` | yes | yes | 🟨 iframe shell |
| 12 | `browser-sessions` | Browser Sessions | `browsers` → `/:projectName/browsers` | **`BrowsersSessionManager`** | **`BrowserSessionList`** | yes | yes | 🟥 diverges per mode |
| 13 | `infra` | Infrastructure | `infra` → `/:projectName/infra` | `InfraView` | `InfraView` | yes | yes | 🟥 degrades (Docker tables/drawers) |
| 14 | `file-explorer` | File Explorer | `file-explorer` → `/:projectName/file-explorer` | `FileExplorerPanel` | `FileExplorerPanel` | yes | yes | 🟥 broken risk: panel embeds a **second dockview** inside the screen |
| 15 | `file-viewer` | File | `file-viewer` → `/:projectName/file-viewer/:filePath(.*)*` | `FileViewer` | `FileViewer` | yes | yes | 🟨 monaco on touch |
| 16 | `git-view` | Git | `git-view` → `/:projectName/git-view` | `GitView` | `GitView` | yes | yes | 🟨 unknown |
| 17 | `wiki` | Wiki | `wiki` → `/:projectName/wiki` | `WikiView` | `WikiView` | yes | yes | 🟨 unknown |
| 18 | `docs` | Docs | `docs` → `/:projectName/docs` | `DocsView` | `DocsView` | yes | yes | 🟨 unknown |
| 19 | `knowledge` | Knowledge | `knowledge` → `/:projectName/knowledge` | `KnowledgeView` | `KnowledgeView` | yes | yes | 🟨 unknown |
| 20 | `knowledge_settings` | Knowledge Settings | `knowledge-settings` → `/:projectName/knowledge-settings` | `KnowledgeSettings` | `KnowledgeSettings` | yes | yes | 🟨 unknown |
| 21 | `projects` | Projects | `projects` → `/:projectName/projects` | `ProjectOverview` | `ProjectOverview` | yes | yes | 🟨 unknown |
| 22 | `activity` | Activity | `activity` → `/:projectName/activity` | `Wall` | `Wall` | yes | yes | 🟨 unknown (was the old mobile home) |
| 23 | `settings` | Project Settings | `settings` → `/:projectName/settings` | `ProjectSettings` | `ProjectSettings` | yes | yes | 🟨 unknown |
| 24 | `global-settings` | Global Settings | `global-settings` → `/:projectName/global-settings` | `GlobalSettings` | `GlobalSettings` | yes | yes | 🟥 duplicated markup (§7) |
| 25 | `account` | Account | `account` → `/:projectName/account` | `AccountSettings` | `AccountSettings` | yes | yes | 🟨 unknown |
| 26 | `log-viewer` | Logs | `log-viewer` → `/:projectName/logs` | `LogViewer` | `LogViewer` | yes | yes | 🟨 unknown |
| 27 | `chat-logs` | Chat logs | `chat-logs` → `/:projectName/chat-logs` | `LogsAnalyzerDashboard` | `LogsAnalyzerDashboard` | yes | yes | 🟥 degrades |
| 28 | `decision-model-logs` | Decision model logs | `decision-model-logs` → `/:projectName/decision-model-logs` | `DecisionModelLogs` | `DecisionModelLogs` | yes | yes | 🟨 unknown |
| 29 | `metrics` | Metrics | `metrics` → `/:projectName/metrics` | `MetricsViewer` | `MetricsViewer` | yes | yes | 🟨 unknown |
| 30 | `analytics` | Analytics | `analytics` → `/:projectName/analytics` | `MetricsDashboard` | `MetricsDashboard` | yes | yes | 🟨 unknown |
| 31 | `api-monitoring` | API monitoring | `api-monitoring` → `/:projectName/api-monitoring` | `ApiMonitoringView` | `ApiMonitoringView` | yes | yes | 🟨 unknown |
| 32 | `team-channel` | Channel | `team-channel` → `/:projectName/team-channel/:channelId` | `TeamChannel` | `TeamChannel` | yes | yes | 🟨 needs payload (§6 D5) |
| 33 | `team-dm` | Direct message | `team-dm` → `/:projectName/team-dm/:dmId` | `TeamDM` | `TeamDM` | yes | yes | 🟨 needs payload (§6 D5) |
| 34 | `team-media-library` | Media Library | `team-media-library` → `/:projectName/team-media-library/:teamId` | `TeamMediaLibrary` | `TeamMediaLibrary` | yes | yes | 🟨 needs payload (§6 D5) |
| 35 | `vibe-coding` | Vibe Coding | `vibe-coding` → `/:projectName/vibe-coding` | `VibeCodingView` | `VibeCodingView` | yes | yes | 🟥 degrades (multi-panel splitter) |

**Routes with no registry entry:** `root` (bootstrap), `home`, `chats` (chat list, `QuickChatView`),
`browser-session`, `codx-junior-split` (`/:projectName/desktop/*` → `Desktop` = dockview workspace), catch-all redirect.

**Registry/component entries not reachable as a route:** `window`, `app-window` (fallback component), `tabComponent`,
`ViewProperties`, `EmptyStateWelcome`.

### 2.1 Registry vs router divergences (all confirmed by reading both files)

| Divergence | Effect |
|---|---|
| `APPS.home.component = 'home'` (`CodxWelcomeView`) but route `home` sets `meta.app = 'management-dashboard'` | "Home" is a different screen depending on the entry point |
| `APPS.chat.component = 'chat'` (`views/ChatView.vue`) but route `chat` mounts `QuickChatView.vue` | desktop panel and phone screen are **two different chat UIs** |
| `APPS.workspaces.component = 'workspaces'` (`WorkspacesManager`) but route `workspaces` mounts `WorkspaceView` | same |
| `APPS['browser-sessions'].component = 'browser-sessions'` (`BrowserSessionList`) but route `browsers` mounts `BrowsersSessionManager` | same |
| `router/navigate.js → browsers.open()` creates a panel with `component: 'browser-viewer'` | `browser-viewer` exists in neither `APPS` nor `appComponentsMap` → silent dead panel |
| `views/DesktopSidebar.vue` reads `$storex.$router.$navigation.getWorkspaceId()` / `.isDesktopMode` | works only because `router/index.ts` attaches `$navigation`; a second, older navigation object (`router.$navigate`) was removed and any leftover reference is dead code |

---

## 3. Navigation model as it exists today

```
URL  /:projectName/<segment>
        │
        ├── segment === "desktop"  → route name "codx-junior-split" → Desktop.vue → dockview panels
        │                                                            (many apps side by side)
        └── any other segment      → "single mode" → AppRouteView.vue
                                          │  reads route.meta.app
                                          ├── APPS[appKey]            (src/config/apps.js)
                                          ├── APP_COMPONENTS_MAP[...] (lazy component)
                                          └── params: getPendingParams() || route.params + query
```

- **Mode is derived from the route, not from the device** — `isDesktopMode()` in `src/router/navigate.js` is
  literally `$router.currentRoute.value.name === 'codx-junior-split'`.
- **`openApp(appKey, payload)`** is the unified opener: single mode → `router.push(def.route(payload))`;
  desktop mode → `$storex.ui.showApp({...})` which creates a dockview panel.
- **Payload hand-off**: objects that cannot live in a URL (chat, team, channel, member, workspace) are stashed in
  the in-memory map `PENDING` (`setPendingParams`) and read back by `AppRouteView`. There is no persistence.
- **Bootstrap**: `/` → guard redirects to `/:projectName` (`home`), whose `meta.app` is `management-dashboard`.
  So the phone landing screen is the cross-project management dashboard.

Consequences:

- A phone that receives `.../desktop` (bookmark, history, "open in new window") gets the dockview workspace.
- A phone that reloads a screen with a pending payload gets an app with `params = { …route.params }`, i.e. usually
  `undefined` for `chat`/`team`/`channel`.
- Nothing in the URL tells the user where they are: no re-usable title, no back stack semantics.

---

## 4. Shell audit

### `src/App.vue` (the mobile shell that does not exist)

- Root layout: `<Login>` or `<div class="flex">` containing `DesktopSidebar` (desktop rails **and** the mobile
  overlay, both from the same component) + `grow` wrapper + `<RouterView/>` + `<Toast>` + the global "New project"
  modal.
- `isMobile` is computed **locally**: `window.innerWidth < 768`, updated by a `resize` listener.
- On `created()` the mobile sidebar is collapsed, and it is collapsed again on **every** `$route` change.
- There is **no app bar, no title, no back button, no bottom navigation, no safe-area padding**.
- `isFullScreenRoute` only covers `route.name === 'solopreneur'`.

### `src/components/desktop/DesktopSidebar.vue` (~450 lines, two products in one file)

- `v-if="isMobile"` branch: fixed overlay + `aside` with `transform: translateX(-100%)` when
  `$storex.ui.sidebarCollapsed`, plus the overlay backdrop.
- `v-else` branch: the desktop icon-rail / expanded sidebar with width animation, wallet, daily spend, footer menu.
- Both branches duplicate the header, the `AppsSection`/`WorkspacesSection` block and the footer menu.
- Expand controls (`toggleCollapse`, and the collapsed-rail button) exist **only inside the panel**. On mobile the
  panel starts off-screen, so once collapsed there is no visible way to open it (see D2).

### `src/components/desktop/Desktop.vue`

- Hosts `<dockview-vue>` and registers every component from `ALL_COMPONENTS`.
- Syncs panels with `$storex.ui.openApps` (`syncPanelsWithApps`), persists layout to `localStorage`
  (`projectLayout_<project>`), restores it on project change, shows an error toast for failed panels.
- Drag/split/tab UI is designed for pointer + large screens; nothing suppresses it on small viewports.

### `src/main.ts` / `index.html`

- Global mixin injects `$storex`, `$ui`, `$projects`, `$app`, `$project`, `$session`, `$user`, `$users`, `$chats`,
  `$teams`, `$media`, `$globalSettings`, `$service` into **every** component.
- Mobile debugging hook: `eruda` is loaded from a CDN when `navigator.userAgent` matches `Mobi|Android`.
- `index.html` sets `body{ overflow: hidden; height:100% }` and `#app{ height:100% }` — the standard
  `100vh` + virtual-keyboard problem, with no viewport-unit or `visualViewport` handling anywhere.

---

## 5. Per-screen consistency audit

| Screen | Own header? | Own sidebar/drawer? | Own scroll container? | Works at 375 px? | Way back? |
|---|---|---|---|---|---|
| `views/ChatView.vue` (+ `Chat`, `ChatSidebar`, `ChatPanelHeader`) | yes (chat header) | yes (`ChatSidebar`, collapsible "compact") | yes, multiple nested | 🟥 no (fixed sidebars, monaco, 400 px editor heights) | only via the sidebar |
| `components/kanban/board/KanbanBoardView.vue` | yes (board toolbar, filters, view switcher) | no | yes | 🟥 no (columns are side-by-side) | a `fa-circle-arrow-left` that resets the board, not the route |
| `views/GlobalSettings.vue` | yes, **twice** (desktop `<aside>` + mobile drawer) | daisyUI `drawer` hand-rolled | yes, twice | 🟨 partially (10 duplicated `v-if` content blocks) | drawer overlay only |
| `views/ProjectSettings.vue` | own tabs | — | yes | 🟨 | no |
| `views/KnowledgeView.vue` | yes (title + tabs) | no | yes | 🟨 search usable, results dense | no |
| `views/VibeCodingView.vue` (+ `VibeCodingHeader`) | yes (2-row toolbar) | no | yes | 🟥 no (vertical splitter + 3 panels) | no |
| `views/TeamView.vue` (+ `TeamBar`, `TeamQuickBar`) | yes | yes (`TeamBar`, collapsible) | yes | 🟨 | no |
| `views/infra/InfraView.vue` | yes | rail + drawers | yes | 🟨 tables overflow | no |
| `components/filebrowser/FileExplorerPanel.vue` | no | fixed `w-64` tree | yes | 🟥 no (tree takes 256 px of 375) | no |
| `views/ManagementDashboardView.vue` | yes | left rail of sections | yes | 🟨 rail + content compete for width | no (it is the root) |

**Pattern:** every screen answers the same four questions (header, navigation entry, scroll, back) differently,
and six of ten answer "no" to back.

---

## 6. Defect list

| ID | Severity | Defect | Evidence | Fix direction |
|---|---|---|---|---|
| **D1** | high | Three definitions of "mobile": `<= 1024` in the store, `< 768` in the shell, `< 1024` in the chat drawer. Between 768–1024 px the **desktop shell renders while all `$ui.isMobile` branches behave as mobile**. | `src/store/ui.js` (`handleResize`: `const isMobile = width <= 1024`), `src/App.vue` (`isMobile(){ return this.windowWidth < 768 }`), `src/components/chat/ProfileDrawer.vue` (`window.innerWidth < 1024`) | one `useViewport()` / store getter with named breakpoints (phone / tablet / desktop) used everywhere |
| **D2** | **blocker** | No visible global navigation on mobile: the drawer is collapsed on `created()` and on every `$route` change; the only expand controls are inside the off-canvas panel (`translateX(-100%)`). | `src/App.vue` (`created()`, `watch: { '$route' }`), `src/components/desktop/DesktopSidebar.vue` (`toggleCollapse` inside the panel, `transform: isCollapsed ? 'translateX(-100%)'`) | render a persistent trigger in the shell (app bar) or a bottom bar; keep the open state independent of route changes |
| **D3** | **blocker** | No mobile chrome at all: shell = `<RouterView/>` only. No app bar, title, back, bottom nav. Every screen invents its own or has none. | `src/App.vue` template | one `<MobilePage>` shell: app bar (title/back/actions) + page container |
| **D4** | high | Mode comes from the URL, not the device: `.../desktop` on a phone mounts the dockview workspace. | `src/router/navigate.js` (`isDesktopMode()`, `currentRoute.value.name === 'codx-junior-split'`) | resolve `.../desktop` to a single-screen route below the tablet breakpoint |
| **D5** | high | Rich payloads travel in memory (`PENDING`): refresh, back-forward, shared link or new tab lose chat/team/channel/workspace/member; `AppRouteView` silently falls back to `route.params`. | `src/config/apps.js` (`setPendingParams`/`getPendingParams`), `src/views/AppRouteView.vue` (`params()`), consumers: `ChatView`, `TeamChannel`, `TeamDM`, `TeamMediaLibrary`, `WorkspaceView` | put identity in the URL and fetch the object in the screen (`onMounted`) |
| **D6** | **blocker** | `ChatEntry.vue` imports and renders `./ChatEntryMobile.vue`, **which does not exist in the repository**. Mobile message rendering is broken / build-blocking. | `src/components/ChatEntry.vue` (`import ChatEntryMobile from './ChatEntryMobile.vue'`, `<ChatEntryMobile v-else-if="$ui.isMobile" …/>`); repo search finds no such file | create the component or delete the fork and make `ChatEntry` responsive |
| **D7** | medium | Orphan / legacy mobile code: `components/mobile/MenuBar.vue` renders `<ProjectSelector>`, `<Notifications>`, `<UserMenu>` without importing them and is referenced nowhere; `views/HomeMobile.vue` is referenced by an older `App.vue` and no longer exists; `SplitView.vue`/`Splitter.vue` are no longer mounted by the router. | files above | delete after confirming zero references |
| **D8** | high | Registry bypass: legacy `$ui.showApp({ component })` call sites never go through `config/apps.js`, so they cannot work in route (mobile) mode. `openMediaLibrary` also has field typos (`tgabId`, `compotabIdnent`) so it cannot work anywhere. | `src/store/ui.js` (`openMediaLibrary`, `cloneApp`, `openNewWindowAppPanel`) | route every opener through `$storex.ui.openApp(appKey, payload)` |
| **D9** | high | No shared mobile primitives: no page header/back, no bottom nav, no `env(safe-area-inset-*)`, no scroll lock, no `visualViewport` handling, inconsistent touch targets. | project-wide search: no `safe-area` usage; `index.html` (`body{overflow:hidden}`) | ship the primitives with the shell (M1) |
| **D10** | high | Registry/router divergence (§2.1): home, chat, workspaces and browsers resolve to **different components** depending on the entry point; `browser-viewer` is referenced but does not exist. | `src/config/apps.js` vs `src/router/index.ts` vs `src/config/appComponentsMap.js` | one table: appKey → route → component; assert equality in a test |

---

## 7. Duplication map

| Duplicated pair | Where |
|---|---|
| Chat message rendering: desktop vs mobile fork | `components/ChatEntry.vue` ↔ `components/ChatEntryMobile.vue` (missing) |
| Global settings content, twice in one file | `views/GlobalSettings.vue` (desktop `<aside>` block + mobile `drawer` block, each listing the same 10 `<… v-if="activeTab === …">`) |
| Navigation sidebar | `components/desktop/DesktopSidebar.vue` (mobile overlay branch + desktop rail branch: header, apps, workspaces, footer repeated) |
| Chat UIs | `views/ChatView.vue` (panel) ↔ `views/QuickChatView.vue` (route) |
| Workspaces screens | `components/workspaces/WorkspacesManager.vue` (panel) ↔ `views/WorkspaceView.vue` (route) |
| Browser sessions | `components/browsers/BrowserSessionList.vue` (panel) ↔ `components/browsers/BrowsersSessionManager.vue` (route) |
| Home | `views/CodxWelcomeView.vue` (registry) ↔ `views/ManagementDashboardView.vue` (route `meta.app`) |
| Per-screen toolbars | `ChatPanelHeader.vue`, `VibeCodingHeader.vue`, `TeamBar.vue`, kanban toolbar, settings headers — each one bespoke |
| Layout containers | `SplitView.vue`, `Splitter.vue`, `HTMLPreview.vue`, `FileExplorerPanel.vue` (nested dockview), plus `@container` usage only on `DesktopView` |

---

## 8. Constraints & risks for the refactor

| # | Constraint / risk | Why it matters |
|---|---|---|
| C1 | **dockview is the desktop workspace** (`Desktop.vue`, panels, saved layouts in `localStorage` under `projectLayout_<project>`) | the refactor must not disturb desktop layouts; a phone must never mount it |
| C2 | **Deep links must keep working**: every route is project-scoped (`/:projectName/...`) and `router.push/replace` inject the project automatically | changing route shapes breaks bookmarks and the `withProject()` wrapper |
| C3 | **Saved UI state in `localStorage`** (`uiState` snapshot incl. `sidebarCollapsed`, `openApps` reset on save) | mobile navigation state must not be persisted into a state that fights the shell |
| C4 | **Global mixin in `main.ts`** injects ~12 store helpers into every component | a new shell must integrate with it, not duplicate it |
| C5 | **No tests** (only `tests/fileChangeParser.test.mjs`) | regressions in the shell would be discovered only by hand — plan a manual device matrix |
| C6 | **`eruda` is loaded from a CDN on mobile UAs** | keep it for debugging, but it is a startup cost on phones |
| C7 | **Two UIs per module in some cases** (chat, workspaces, browsers) | deciding *which* component survives is a product decision, not only a code change |

---

## 9. Annex — target principles (no code)

1. **One navigation model.** One shell owns: app bar (title, back, actions, project switcher) and one
   persistent navigation surface (drawer or bottom bar). Screens never render their own navigation.
2. **One page component.** Every screen is wrapped by the same container that owns scrolling, padding,
   safe areas and the header slot. Screens that need a toolbar use the slot instead of building a header.
3. **One source of truth for viewport.** Named breakpoints (`phone` / `tablet` / `desktop`) exposed once;
   no `window.innerWidth` comparisons inside components, no `v-if="$ui.isMobile"` forks.
4. **Device decides the mode; the URL only describes the screen.** A phone never mounts the dockview workspace,
   even if the URL says `.../desktop`.
5. **Identity in the URL.** Anything needed to rebuild a screen (chat id, team id, board, file path) goes in the
   route; objects are fetched by the screen. No in-memory payload hand-off.
6. **The registry is the truth.** `appKey → route → component` in one table, checked by a test.
7. **Every increment ships behind a flag and is demoed on a real device**, at 390 px and 768 px, before it is
   called done.
