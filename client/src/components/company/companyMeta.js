// ─────────────────────────────────────────────────────────────────────────────
// Company View — shared presentation metadata
//
// Keeps labels/tones/icons and small formatting helpers out of the components,
// so a status or a badge looks the same in every panel (overview, board, list).
// ─────────────────────────────────────────────────────────────────────────────

export const MISSION_STATUS_META = {
  draft: { label: 'Draft', badge: 'badge-ghost', icon: 'fa-regular fa-file-lines', tone: 'text-base-content/60' },
  ready: { label: 'Ready', badge: 'badge-info', icon: 'fa-solid fa-circle-play', tone: 'text-info' },
  running: { label: 'Running', badge: 'badge-primary', icon: 'fa-solid fa-person-running', tone: 'text-primary' },
  paused: { label: 'Paused', badge: 'badge-warning', icon: 'fa-solid fa-pause', tone: 'text-warning' },
  blocked: { label: 'Blocked', badge: 'badge-error', icon: 'fa-solid fa-circle-exclamation', tone: 'text-error' },
  review: { label: 'In review', badge: 'badge-accent', icon: 'fa-solid fa-magnifying-glass', tone: 'text-accent' },
  done: { label: 'Done', badge: 'badge-success', icon: 'fa-solid fa-circle-check', tone: 'text-success' },
  cancelled: { label: 'Cancelled', badge: 'badge-ghost', icon: 'fa-solid fa-ban', tone: 'text-base-content/40' }
}

export function statusMeta(status) {
  return MISSION_STATUS_META[status] || MISSION_STATUS_META.draft
}

/** Missions board columns, in execution order. */
export const MISSION_COLUMNS = [
  { id: 'draft', label: 'Draft', hint: 'Being shaped' },
  { id: 'ready', label: 'Ready', hint: 'Can be dispatched' },
  { id: 'running', label: 'Running', hint: 'AI team is working' },
  { id: 'review', label: 'Review', hint: 'Waiting for a human' },
  { id: 'done', label: 'Done', hint: 'Accepted' }
]

/** Statuses shown outside the main columns (rendered as a separate row). */
export const MISSION_OTHER_STATUSES = ['paused', 'blocked', 'cancelled']

export const PRIORITY_META = {
  low: { label: 'Low', badge: 'badge-ghost', icon: 'fa-solid fa-arrow-down' },
  medium: { label: 'Medium', badge: 'badge-info', icon: 'fa-solid fa-minus' },
  high: { label: 'High', badge: 'badge-warning', icon: 'fa-solid fa-arrow-up' },
  critical: { label: 'Critical', badge: 'badge-error', icon: 'fa-solid fa-fire' }
}

export function priorityMeta(priority) {
  return PRIORITY_META[priority] || PRIORITY_META.medium
}

export const ORG_KIND_META = {
  department: { label: 'Department', icon: 'fa-solid fa-building', badge: 'badge-primary' },
  function: { label: 'Function', icon: 'fa-solid fa-diagram-project', badge: 'badge-secondary' },
  division: { label: 'Division', icon: 'fa-solid fa-layer-group', badge: 'badge-accent' }
}

export function orgKindMeta(kind) {
  return ORG_KIND_META[kind] || ORG_KIND_META.department
}

export const AUTONOMY_LEVELS = [
  { id: 'off', label: 'Off', hint: 'Nothing runs automatically' },
  { id: 'supervised', label: 'Supervised', hint: 'Dispatch auto missions; humans accept the outcome' },
  { id: 'autonomous', label: 'Autonomous', hint: 'Dispatch and close auto missions without a human' }
]

export const TEAM_AUTONOMY_LEVELS = [
  { id: 'manual', label: 'Manual', hint: 'Only humans dispatch this team’s missions' },
  { id: 'supervised', label: 'Supervised', hint: 'Autopilot dispatches; humans review' },
  { id: 'autonomous', label: 'Autonomous', hint: 'Autopilot dispatches and closes' }
]

export const COMPANY_STATUS_META = {
  active: { label: 'Active', badge: 'badge-success' },
  paused: { label: 'Paused', badge: 'badge-warning' },
  archived: { label: 'Archived', badge: 'badge-ghost' }
}

export const COMPANY_TEMPLATES = [
  { id: 'blank', label: 'Blank company', hint: 'Start with only the company shell' },
  {
    id: 'saas',
    label: 'SaaS — codx-junior cloud',
    hint: 'Leadership, Product, Engineering, Growth, Customer Success + 4 draft missions'
  }
]

// ── Members ─────────────────────────────────────────────────────────────────

export function memberKey(member) {
  if (!member) return ''
  return `${member.kind || 'profile'}:${member.name || ''}`
}

export function memberLabel(member) {
  if (!member) return 'Unknown'
  return member.name || member.username || 'Unknown'
}

export function memberIsAI(member) {
  return (member?.kind || 'profile') === 'profile'
}

/** Same robohash fallback used by the profile cards. */
export function memberAvatar(member) {
  if (member?.avatar) return member.avatar
  const seed = encodeURIComponent(member?.name || 'member')
  return `https://gravatar.com/avatar/baa8db8ab2afb7ababc235269e762662?s=200&d=robohash&r=${seed}`
}

export function memberRef(kind, name) {
  return `${kind || 'profile'}:${name || ''}`
}

// ── Dates / numbers ─────────────────────────────────────────────────────────

export function formatDate(value) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return String(value)
  return date.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  })
}

export function formatDateTime(value) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return String(value)
  return date.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

export function relativeTime(value) {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  const seconds = Math.round((Date.now() - date.getTime()) / 1000)
  if (seconds < 60) return 'just now'
  const minutes = Math.round(seconds / 60)
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.round(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.round(hours / 24)
  if (days < 30) return `${days}d ago`
  return formatDate(value)
}

export function money(value) {
  const number = Number(value || 0)
  if (!number) return '0'
  return number.toLocaleString(undefined, { maximumFractionDigits: 0 })
}

// ── Event labels ────────────────────────────────────────────────────────────

export const EVENT_META = {
  'company.created': { icon: 'fa-solid fa-building', tone: 'text-primary' },
  'company.updated': { icon: 'fa-solid fa-pen', tone: 'text-info' },
  'org_unit.created': { icon: 'fa-solid fa-sitemap', tone: 'text-primary' },
  'org_unit.updated': { icon: 'fa-solid fa-pen', tone: 'text-info' },
  'org_unit.deleted': { icon: 'fa-solid fa-trash', tone: 'text-error' },
  'team.created': { icon: 'fa-solid fa-people-group', tone: 'text-primary' },
  'team.updated': { icon: 'fa-solid fa-pen', tone: 'text-info' },
  'team.deleted': { icon: 'fa-solid fa-trash', tone: 'text-error' },
  'team.members.added': { icon: 'fa-solid fa-user-plus', tone: 'text-success' },
  'team.members.removed': { icon: 'fa-solid fa-user-minus', tone: 'text-warning' },
  'team.lead.changed': { icon: 'fa-solid fa-crown', tone: 'text-warning' },
  'project.linked': { icon: 'fa-solid fa-link', tone: 'text-primary' },
  'project.updated': { icon: 'fa-solid fa-pen', tone: 'text-info' },
  'project.unlinked': { icon: 'fa-solid fa-link-slash', tone: 'text-warning' },
  'mission.created': { icon: 'fa-solid fa-flag', tone: 'text-primary' },
  'mission.updated': { icon: 'fa-solid fa-pen', tone: 'text-info' },
  'mission.deleted': { icon: 'fa-solid fa-trash', tone: 'text-error' },
  'mission.dispatched': { icon: 'fa-solid fa-rocket', tone: 'text-primary' },
  'mission.dispatch_failed': { icon: 'fa-solid fa-triangle-exclamation', tone: 'text-error' },
  'mission.run_synced': { icon: 'fa-solid fa-rotate', tone: 'text-info' },
  'mission.transitioned': { icon: 'fa-solid fa-arrow-right-arrow-left', tone: 'text-info' },
  'mission.accepted': { icon: 'fa-solid fa-circle-check', tone: 'text-success' },
  'mission.rejected': { icon: 'fa-solid fa-rotate-left', tone: 'text-warning' },
  'autopilot.cycle': { icon: 'fa-solid fa-robot', tone: 'text-primary' },
  'autonomy.updated': { icon: 'fa-solid fa-sliders', tone: 'text-info' }
}

export function eventMeta(type) {
  return EVENT_META[type] || { icon: 'fa-solid fa-circle', tone: 'text-base-content/50' }
}

// Made with ❤️ by codx-junior
