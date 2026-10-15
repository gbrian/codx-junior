// ─────────────────────────────────────────────────────────────────────────────
// Wall — event kinds, filter chips and primary navigation.
// Single source of truth for the project activity feed (src/components/wall/*).
//
// The wall is codx-junior's own activity stream. It uses the project branding
// (the codx-junior logo) and daisyUI theme tokens only — no third-party brand
// names, logos or copy are referenced anywhere.
// ─────────────────────────────────────────────────────────────────────────────

export const WALL_KINDS = {
  chat:   { label: 'Chat',         icon: 'fa-solid fa-comment',           color: 'text-info' },
  code:   { label: 'Changes',      icon: 'fa-solid fa-code',              color: 'text-success' },
  kanban: { label: 'Task',         icon: 'fa-brands fa-trello',           color: 'text-codx-primary' },
  commit: { label: 'Commit',       icon: 'fa-solid fa-code-commit',       color: 'text-success' },
  pr:     { label: 'Pull request', icon: 'fa-solid fa-code-pull-request', color: 'text-secondary' },
  meet:   { label: 'Meet',         icon: 'fa-solid fa-video',             color: 'text-error' },
  index:  { label: 'Knowledge',    icon: 'fa-solid fa-database',          color: 'text-warning' },
  wiki:   { label: 'Wiki',         icon: 'fa-solid fa-graduation-cap',    color: 'text-success' },
  system: { label: 'System',       icon: 'fa-solid fa-circle-info',       color: 'text-base-content/60' },
  user:   { label: 'Joined',       icon: 'fa-solid fa-user-plus',         color: 'text-info' }
}

// Kind filter chips, in display order ('all' first)
export const WALL_FILTERS = [
  { key: 'all', label: 'All' },
  { key: 'chat', label: 'Chats' },
  { key: 'code', label: 'Changes' },
  { key: 'kanban', label: 'Tasks' },
  { key: 'pr', label: 'Pull requests' },
  { key: 'meet', label: 'Meets' },
  { key: 'index', label: 'Knowledge' },
  { key: 'wiki', label: 'Wiki' },
  { key: 'system', label: 'System' }
]

// Primary navigation (desktop rail + mobile menu)
export const WALL_NAV = [
  { key: 'home', label: 'Home', icon: 'fa-solid fa-house' },
  { key: 'explore', label: 'Explore', icon: 'fa-solid fa-magnifying-glass' },
  { key: 'notifications', label: 'Notifications', icon: 'fa-solid fa-bell' },
  { key: 'messages', label: 'Messages', icon: 'fa-solid fa-envelope' },
  { key: 'bookmarks', label: 'Bookmarks', icon: 'fa-solid fa-bookmark' },
  { key: 'profile', label: 'Profile', icon: 'fa-solid fa-user' }
]

export function kindConfig(kind) {
  return WALL_KINDS[kind] || WALL_KINDS.system
}
