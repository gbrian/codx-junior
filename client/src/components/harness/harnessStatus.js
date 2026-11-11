/**
 * Status vocabulary of the codx-junior harness, shared by the diagnostic view.
 *
 * Mirrors `api/codx/junior/orchestration/constants.py` so the UI labels a run,
 * its steps and the board phase exactly like the runtime that produced them.
 * Keep the two in sync when a status is added.
 */

/** Run (harness task) statuses. */
export const RUN_STATUS = {
  queued: { label: 'Queued', badge: 'badge-info', icon: 'fa-regular fa-clock', color: 'text-info' },
  running: { label: 'Running', badge: 'badge-primary', icon: 'fa-solid fa-arrows-spin fa-spin', color: 'text-primary' },
  paused: { label: 'Paused', badge: 'badge-warning', icon: 'fa-solid fa-pause', color: 'text-warning' },
  stalled: { label: 'Stalled', badge: 'badge-warning', icon: 'fa-solid fa-triangle-exclamation', color: 'text-warning' },
  completed: { label: 'Completed', badge: 'badge-success', icon: 'fa-solid fa-circle-check', color: 'text-success' },
  stopped: { label: 'Stopped', badge: 'badge-error', icon: 'fa-solid fa-circle-stop', color: 'text-error' },
  failed: { label: 'Failed', badge: 'badge-error', icon: 'fa-solid fa-circle-xmark', color: 'text-error' },
  budget_exhausted: { label: 'Budget exhausted', badge: 'badge-error', icon: 'fa-solid fa-coins', color: 'text-error' }
}

/** Plan step statuses. */
export const STEP_STATUS = {
  pending: { label: 'Pending', badge: 'badge-ghost', icon: 'fa-regular fa-circle', color: 'text-base-content/40' },
  running: { label: 'Running', badge: 'badge-primary', icon: 'fa-solid fa-arrows-spin fa-spin', color: 'text-primary' },
  done: { label: 'Done', badge: 'badge-success', icon: 'fa-solid fa-circle-check', color: 'text-success' },
  failed: { label: 'Failed', badge: 'badge-error', icon: 'fa-solid fa-circle-xmark', color: 'text-error' },
  blocked: { label: 'Blocked', badge: 'badge-warning', icon: 'fa-solid fa-hand', color: 'text-warning' },
  skipped: { label: 'Skipped', badge: 'badge-ghost', icon: 'fa-solid fa-forward', color: 'text-base-content/40' }
}

const UNKNOWN = { label: 'unknown', badge: 'badge-ghost', icon: 'fa-regular fa-circle-question', color: 'text-base-content/50' }

/** Board column phase of a step (keys of `run.config.columns`). */
export const STEP_BOARD_PHASE = {
  pending: 'backlog',
  running: 'running',
  done: 'done',
  failed: 'blocked',
  blocked: 'blocked',
  skipped: 'done'
}

export const SUCCESSFUL_STEP_STATUSES = ['done', 'skipped']
export const TERMINAL_STEP_STATUSES = ['done', 'failed', 'blocked', 'skipped']

/** Human label of the workflow status mirrored on a plan step card. */
export const STEP_CHAT_STATUS_LABEL = {
  todo: 'todo',
  doing: 'doing',
  onhold: 'on hold',
  done: 'done',
  rejected: 'rejected'
}

export const TERMINAL_RUN_STATUSES = ['completed', 'stopped', 'failed', 'budget_exhausted', 'stalled']

/** Metadata of the worker's next action (`run.next_action`). */
export const NEXT_ACTIONS = {
  dispatch: { label: 'Dispatch', icon: 'fa-solid fa-play' },
  wait: { label: 'Wait', icon: 'fa-solid fa-hourglass-half' },
  supervisor: { label: 'Supervisor round', icon: 'fa-solid fa-user-astronaut' }
}

/** Human explanation of `run.next_action.reason`. */
export const NEXT_REASONS = {
  ready_steps: 'ready steps can be dispatched',
  steps_running: 'waiting for the steps that are running',
  no_plan: 'no plan yet — the supervisor must plan',
  blocked_steps: 'pending steps depend on a blocked step',
  failed_steps: 'failed steps need a decision',
  verify: 'every step finished — verify and report',
  no_progress: 'no progress without a supervisor round'
}

/** Return the display metadata of a run status. */
export function runMeta(status) {
  return RUN_STATUS[status] || { ...UNKNOWN, label: status || 'unknown' }
}

/** Return the display metadata of a step status. */
export function stepMeta(status) {
  return STEP_STATUS[status] || { ...UNKNOWN, label: status || 'unknown' }
}

/** Return the next-action metadata of a run. */
export function nextActionMeta(action) {
  return NEXT_ACTIONS[action] || { label: action || 'idle', icon: 'fa-solid fa-circle-info' }
}

/** Return the human explanation of a next-action reason. */
export function nextReasonLabel(reason) {
  return NEXT_REASONS[reason] || reason || ''
}

/** Format an ISO timestamp for the UI (never throws). */
export function formatTime(value) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return String(value)
  return date.toLocaleString()
}

/** Shorten an id/hash for display. */
export function shortId(value, size = 8) {
  const text = String(value || '')
  if (!text) return '—'
  return text.length > size + 2 ? `${text.slice(0, size)}…` : text
}

/** Format cxjcoins (2 decimals, no trailing noise). */
export function formatCost(value) {
  const amount = Number(value || 0)
  return amount ? amount.toFixed(2) : '—'
}

/** Format a duration in seconds as a compact human string. */
export function formatDuration(seconds) {
  const total = Math.max(0, Math.round(Number(seconds) || 0))
  if (!total) return '—'
  if (total < 60) return `${total}s`
  const minutes = Math.floor(total / 60)
  const rest = total % 60
  if (minutes < 60) return rest ? `${minutes}m ${rest}s` : `${minutes}m`
  const hours = Math.floor(minutes / 60)
  return `${hours}h ${minutes % 60}m`
}

/**
 * Duration of one plan step: the reported worker duration when available,
 * otherwise the wall clock between `started_at` and `finished_at`.
 */
export function stepDuration(step) {
  if (!step) return '—'
  const reported = Number(step.result?.duration_seconds || 0)
  if (reported > 0) return formatDuration(reported)
  const start = Date.parse(step.started_at || '')
  const end = Date.parse(step.finished_at || '')
  if (Number.isFinite(start) && Number.isFinite(end) && end > start) {
    return formatDuration((end - start) / 1000)
  }
  return '—'
}
