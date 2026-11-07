## Admin-only chat dump (postmortem export)

Chat dump is an **admin-only** postmortem export of a whole chat as JSON.

- Permission is resolved in `ChatView.vue` (`isAdminUser`, read defensively from `$storex.user`, **fails closed**). Hosts may override with the `dumpEnabled` prop.
- Child components never decide permissions: `ChatViewHeader` receives `canDump` and emits `show-dump`; `ChatSidebar` receives `canDump` and emits `action: { type: 'dump' }`.
- `ChatView.handleSidebarAction` already maps `'dump'` → `showDumpChat = true`.
- The dialog is `src/components/chat/ChatDumpDialog.vue` (payload: `dump_version`, `exporter`, `summary`, full `chat` incl. hidden messages, `children`, `environment`, `diagnostics`). Export surface = download `.json` + copy to clipboard.
- Never dumb down the payload: postmortems need hidden/system messages, so `includeHidden` defaults to `true`.
