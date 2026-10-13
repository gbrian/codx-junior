// ─────────────────────────────────────────────────────────────────────────────
// Single source of truth for "how to open an app".
//
// Each entry describes an app that can be opened either:
//   • as a desktop dockview PANEL  (expert view mode / desktop screens), or
//   • as a mobile ROUTE            (mobile screens / router mode).
//
// `openApp(appKey, payload)` (see router/navigate.js) reads this registry and
// picks the right strategy, so the rest of the app never needs to branch on
// isMobile / isDesktopMode again.
// ─────────────────────────────────────────────────────────────────────────────

// Transient payload hand-off for mobile routes. Some apps need rich objects
// (a chat, a team member, a workspace…) that can't be encoded in the URL.
// `openApp` stashes them here and <AppRouteView> reads them back per app.
const PENDING = {}

export function setPendingParams(appId, params) {
  PENDING[appId] = params
}

export function getPendingParams(appId) {
  return PENDING[appId] || null
}

export function clearPendingParams(appId) {
  delete PENDING[appId]
}

// ─────────────────────────────────────────────────────────────────────────────
// MULTI-INSTANCE APPS
//
// By default an app is SINGLE-INSTANCE: opening it again focuses the panel that
// is already open (the UI store de-duplicates by the app's `key`).
//
// Apps that may legitimately live in more than one panel at a time opt in with:
//
//     multiInstance: true
//
// Their per-instance identity is described with the same helpers used by every
// other app — `desktopKey` / `desktopTabId` / `desktopParams`. For example a
// Task Manager instance is a single BOARD, so several boards can be open side by
// side while re-opening the same board just focuses its existing panel.
// ─────────────────────────────────────────────────────────────────────────────

export const APPS = {
  // ── Primary apps ──────────────────────────────────────────────────────────
  home: {
    id: 'home', title: 'Home', component: 'home', icon: 'fa-solid fa-home',
    route: () => ({ name: 'home' })
  },

  tasks: {
    id: 'tasks', title: 'Task Manager', component: 'tasks', icon: 'fa-brands fa-trello',
    // Several Task Managers can be open at once — one per board. The board is
    // what identifies each instance, so different boards become independent
    // panels while re-opening the same board (or opening with no board at all)
    // just focuses the panel that is already showing it.
    multiInstance: true,
    desktopKey: p => (p.board ? `tasks-${p.board}` : 'tasks'),
    desktopTabId: p => (p.board ? `tasks-${p.board}` : undefined),
    desktopParams: p => ({ board: p.board }),
    route: () => ({ name: 'kanban' })
  },

  planning: {
    id: 'planning', title: 'Planning', component: 'tasks', icon: 'fa-solid fa-diagram-project',
    desktopParams: () => ({ view: 'planning' }),
    route: () => ({ name: 'kanban', query: { view: 'planning' } })
  },

  chat: {
    id: 'chat', title: 'Chat', component: 'chat', icon: 'fa-regular fa-comments',
    desktopKey: p => (p.chat?.id ? `chat-${p.chat.id}` : undefined),
    desktopTabId: p => p.chat?.id,
    desktopParams: p => ({ chat: p.chat, ...(p.workspace ? { workspace: p.workspace } : {}) }),
    route: p => p.workspace
      ? { name: 'chat-workspace', params: { chatId: p.chat?.id, chatName: p.chat?.name, workspaceId: p.workspace.id, workspaceName: p.workspace.name } }
      : { name: 'chat', params: { chatId: p.chat?.id, chatName: p.chat?.name || `chat-${p.chat?.id}` } }
  },

  messenger: {
    id: 'messenger', title: 'Messenger', component: 'messenger', icon: 'fa-regular fa-comments',
    route: () => ({ name: 'messenger' })
  },

  meet: {
    id: 'meet', title: 'Meet', component: 'meet', icon: 'fa-solid fa-video',
    desktopParams: p => ({ meetId: p.meetId }),
    route: p => p.meetId
      ? { name: 'meet-session', params: { meetId: p.meetId } }
      : { name: 'meet' }
  },

  team: {
    id: 'team', title: 'Team', component: 'team', icon: 'fa-solid fa-people-group',
    route: () => ({ name: 'team' })
  },

  // ── Workspaces & browsers ─────────────────────────────────────────────────
  workspaces: {
    id: 'workspaces', title: 'Workspaces', component: 'workspaces', icon: 'fa-solid fa-server',
    route: () => ({ name: 'workspaces' })
  },

  workspace: {
    id: 'workspace', title: 'Workspace', component: 'workspace', icon: 'fa-regular fa-window-maximize',
    desktopKey: p => `workspace-${p.workspace?.key}`,
    desktopTabId: p => `workspace-${p.workspace?.key}`,
    // Expose the workspace under the semantic `workspace` key (same convention
    // as `chat`) so name / path reach the Tab and AppWindow readers, which look
    // up `params.params.workspace` directly.
    desktopParams: p => ({ workspace: p.workspace }),
    route: p => ({ name: 'workspace', params: { workspaceId: p.workspace?.key, workspaceName: p.workspace?.name } })
  },

  'browser-sessions': {
    id: 'browser-sessions', title: 'Browser Sessions', component: 'browser-sessions', icon: 'fa-regular fa-compass',
    route: () => ({ name: 'browsers' })
  },

  // ── Files ─────────────────────────────────────────────────────────────────
  'file-explorer': {
    id: 'file-explorer', title: 'File Explorer', component: 'file-explorer', icon: 'fa-solid fa-folder-open',
    route: () => ({ name: 'file-explorer' })
  },

  'file-viewer': {
    id: 'file-viewer', title: 'File', component: 'file-viewer', icon: 'fa-regular fa-file',
    desktopKey: p => (p.filePath ? `file-viewer-${p.filePath}` : undefined),
    desktopTabId: p => (p.filePath ? `file-viewer-${p.filePath}` : undefined),
    desktopParams: p => ({ filePath: p.filePath }),
    route: p => ({ name: 'file-viewer', params: { filePath: p.filePath } })
  },

  // ── Git ───────────────────────────────────────────────────────────────────
  'git-view': {
    id: 'git-view', title: 'Git', component: 'git-view', icon: 'fa-solid fa-code-branch',
    route: () => ({ name: 'git-view' })
  },

  // ── Knowledge / docs ──────────────────────────────────────────────────────
  wiki: {
    id: 'wiki', title: 'Wiki', component: 'wiki', icon: 'fa-solid fa-graduation-cap',
    route: () => ({ name: 'wiki' })
  },

  docs: {
    id: 'docs', title: 'Docs', component: 'docs', icon: 'fa-solid fa-book',
    route: () => ({ name: 'docs' })
  },

  knowledge: {
    id: 'knowledge', title: 'Knowledge', component: 'knowledge', icon: 'fa-solid fa-magnifying-glass',
    desktopParams: p => ({ ...(p.params || {}) }),
    route: () => ({ name: 'knowledge' })
  },

  knowledge_settings: {
    id: 'knowledge_settings', title: 'Knowledge Settings', component: 'knowledge_settings', icon: 'fa-solid fa-sliders',
    route: () => ({ name: 'knowledge-settings' })
  },

  // ── Project & user ────────────────────────────────────────────────────────
  profiles: {
    id: 'profiles', title: 'Profiles', component: 'profiles', icon: 'fa-solid fa-id-badge',
    route: () => ({ name: 'profiles' })
  },

  projects: {
    id: 'projects', title: 'Projects', component: 'projects', icon: 'fa-solid fa-cubes',
    route: () => ({ name: 'projects' })
  },

  activity: {
    id: 'activity', title: 'Activity', component: 'activity', icon: 'fa-solid fa-clock-rotate-left',
    desktopParams: p => ({ project: p.project, board: p.board }),
    route: () => ({ name: 'activity' })
  },

  settings: {
    id: 'settings', title: 'Project Settings', component: 'settings', icon: 'fa-solid fa-gear',
    route: () => ({ name: 'settings' })
  },

  'global-settings': {
    id: 'global-settings', title: 'Global Settings', component: 'global-settings', icon: 'fa-solid fa-gear',
    route: () => ({ name: 'global-settings' })
  },

  account: {
    id: 'account', title: 'Account', component: 'account', icon: 'fa-solid fa-user',
    route: () => ({ name: 'account' })
  },

  // ── Logs & analytics ──────────────────────────────────────────────────────
  'log-viewer': {
    id: 'log-viewer', title: 'Logs', component: 'log-viewer', icon: 'fa-solid fa-file-lines',
    route: () => ({ name: 'log-viewer' })
  },

  'chat-logs': {
    id: 'chat-logs', title: 'Chat logs', component: 'chat-logs', icon: 'fa-solid fa-magnifying-glass-chart',
    route: () => ({ name: 'chat-logs' })
  },

  metrics: {
    id: 'metrics', title: 'Metrics', component: 'metrics', icon: 'fa-solid fa-chart-area',
    route: () => ({ name: 'metrics' })
  },

  analytics: {
    id: 'analytics', title: 'Analytics', component: 'analytics', icon: 'fa-solid fa-chart-area',
    route: () => ({ name: 'analytics' })
  },

  // ── Team ──────────────────────────────────────────────────────────────────
  'team-channel': {
    id: 'team-channel', title: 'Channel', component: 'team-channel', icon: 'fa-solid fa-hashtag',
    desktopKey: p => `team-channel-${p.channel?.id}`,
    desktopTabId: p => `team-channel-${p.channel?.id}`,
    desktopParams: p => ({ team: p.team, channel: p.channel }),
    route: p => ({ name: 'team-channel', params: { channelId: p.channel?.id } })
  },

  'team-dm': {
    id: 'team-dm', title: 'Direct message', component: 'team-dm', icon: 'fa-solid fa-user',
    desktopKey: p => `team-dm-${p.team?.id}-${p.member?.id}`,
    desktopTabId: p => `team-dm-${p.team?.id}-${p.member?.id}`,
    desktopParams: p => ({ team: p.team, member: p.member, chatId: p.chatId }),
    route: p => ({ name: 'team-dm', params: { dmId: `${p.team?.id}-${p.member?.id}` } })
  },

  'team-media-library': {
    id: 'team-media-library', title: 'Media Library', component: 'team-media-library', icon: 'fa-solid fa-image',
    desktopKey: p => `team-media-${p.team?.id}`,
    desktopTabId: p => `team-media-${p.team?.id}`,
    desktopParams: p => ({ team: p.team }),
    route: p => ({ name: 'team-media-library', params: { teamId: p.team?.id } })
  },

  // ── Vibe ──────────────────────────────────────────────────────────────────
  'vibe-coding': {
    id: 'vibe-coding', title: 'Vibe Coding', component: 'vibe-coding', icon: 'fa-solid fa-wand-magic-sparkles',
    route: () => ({ name: 'vibe-coding' })
  }
}

export function isKnownApp(appKey) {
  return !!APPS[appKey]
}

// Whether an app may be open in more than one place at a time (several panels /
// instances). Apps opt in with `multiInstance: true` (see the note above) and
// derive each instance's identity from `desktopKey`/`desktopTabId`/`desktopParams`
// — e.g. one Task Manager per board. Accepts an app key, a registry id or a full
// app object, and matches per-instance keys such as "tasks-My board" through
// their component.
export function isMultiInstance(appOrKey) {
  if (!appOrKey) return false
  const def = typeof appOrKey === 'string'
    ? (APPS[appOrKey] || Object.values(APPS).find(app => app.component === appOrKey))
    : (APPS[appOrKey.id] || Object.values(APPS).find(app => app.component === appOrKey.component))
  return !!def?.multiInstance
}

export default APPS