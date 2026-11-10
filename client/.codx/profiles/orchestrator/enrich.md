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
