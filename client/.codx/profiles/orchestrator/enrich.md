## Admin-only chat dump (postmortem export)

Chat dump is an **admin-only** postmortem export of a whole chat as JSON.

- Permission is resolved in `ChatView.vue` (`isAdminUser`, read defensively from `$storex.user`, **fails closed**). Hosts may override with the `dumpEnabled` prop.
- Child components never decide permissions: `ChatViewHeader` receives `canDump` and emits `show-dump`; `ChatSidebar` receives `canDump` and emits `action: { type: 'dump' }`.
- `ChatView.handleSidebarAction` already maps `'dump'` → `showDumpChat = true`.
- The dialog is `src/components/chat/ChatDumpDialog.vue` (payload: `dump_version`, `exporter`, `summary`, full `chat` incl. hidden messages, `children`, `environment`, `diagnostics`). Export surface = download `.json` + copy to clipboard.
- Never dumb down the payload: postmortems need hidden/system messages, so `includeHidden` defaults to `true`.

## Base code only — never edit worktrees

## Scope rule

All changes must be made in the **base code only** (`/client/src/...`).

- Never read-and-edit files that live inside `.worktrees/**` (e.g. `.worktrees/mobile_redesign/client/src/...`).
- Never propose `<file_change>` blocks for paths starting with `.worktrees/`.
- When a file exists in both the base tree and a worktree, the base tree copy is the source of truth; worktrees are treated as disposable and are synced later by the user.
- If a worktree copy accidentally carries one of our changes, revert it and keep the change only in the base tree.

## Base code only — never .worktrees

Work only with the base code tree rooted at `src/` of `/home/codx-junior-projects/codx-junior/client`.

- Never read, edit, create or revert files under `.worktrees/` (e.g. `.worktrees/mobile_redesign/client/...`).
- All features, fixes and reviews land in the main tree only; worktrees belong to other checkouts and stay untouched.
- If a previous change was made inside a worktree, treat main as the single source of truth and do not mirror code into the worktree.

## UI: reuse Modal.vue / ConfirmDialog.vue — never a native dialog or a local copy

Reuse the existing dialog components; never create a local modal copy.

- `src/components/Modal.vue` is registered globally in `src/main.ts` → usable as `<modal close @close>` in any template. Props: `title`, `fullscreen`, `scope`, `close`. Slots: default (body), `header`, `footer`. It teleports itself to the app root, handles ESC and the backdrop.
- `src/components/ConfirmDialog.vue` is the project-wide confirmation (built on `<modal>`): props `title`, `message`, `details[]`, `hint`, `icon`, `iconClass`, `confirmLabel`, `confirmIcon`, `confirmClass`, `busy`; events `confirm` / `cancel`. Focus starts on Cancel (safe choice).
- Standard usage (see `repo/GitView.vue`, `browsers/BrowserSessionList.vue`, `RepoFileDiff.vue`): keep `confirmRequest: null` in `data`, a `confirmAction(options)` that returns a Promise and stores `{ ...options, resolve }`, `resolveConfirmation(accepted)`, and render `<ConfirmDialog v-if="confirmRequest" v-bind... @confirm="resolveConfirmation(true)" @cancel="resolveConfirmation(false)">`. Call sites: `if (!(await this.confirmAction({...}))) return`.
- Never use native `confirm()`, `alert()` or `prompt()`: they are light-only, block the page, have no focus management and cannot show context (paths, items).
- Destructive actions: `confirmClass: 'btn-error'` + `icon: 'fa-trash'`, `iconClass: 'text-error'`.
- Before writing any dialog, search `src/components/**` for an existing one (`*Modal.vue`, `*Dialog.vue`) — many feature-specific ones already exist.
