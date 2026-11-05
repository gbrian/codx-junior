/**
 * ============================================================================
 * Infrastructure (Docker) — compose STACK commands.
 * ----------------------------------------------------------------------------
 * The Stacks tab needs the same command surface the container rows already
 * have (`up`, `stop`, `restart`, `build`, `pull`, `down`) plus an aggregated
 * log overlay. That is TRANSIENT UI state — which command is in flight, which
 * stack's logs are open — so it lives here instead of in useInfra.js, which
 * keeps holding host data only (the single shared store read by every panel).
 *
 * Nothing here talks HTTP directly: every request goes through `API.infra`
 * (see src/api/modules/infra.js), which is mock-backed until the backend
 * implements /api/infra/stacks/:name/*.
 *
 * `up` vs `start`
 * ---------------
 * A stack that was brought `down` has no containers left, so `start` cannot
 * revive it — only `up` creates them again. The UI therefore labels `up` as
 * "Start" and never sends `start`/`create`.
 * ============================================================================
 */
import { reactive } from 'vue'
import { API } from '../../api/api'
import { state, confirm, pushToast, loadAll } from './useInfra'

/**
 * Compose commands offered by the Stacks tab.
 *
 * `id` is sent verbatim as `{ action }` to
 * `POST /api/infra/stacks/:name/actions`, so it must match `docker compose <id>`.
 *
 * `text` is the sentence shown inside the confirmation dialog. It is EMPTY for
 * the non destructive commands (build, pull): they are idempotent and long
 * running, so an extra click would only slow the operator down — they execute
 * straight away and report through the busy spinner instead.
 */
export const STACK_ACTIONS = [
  { id: 'up', label: 'Start', icon: 'fa-play', danger: false,
    text: 'the stack services will be created and started (docker compose up -d).' },
  { id: 'stop', label: 'Stop', icon: 'fa-stop', danger: true,
    text: 'every service will be stopped. The containers are kept (docker compose stop).' },
  { id: 'restart', label: 'Restart', icon: 'fa-rotate-right', danger: true,
    text: 'every service will be restarted (docker compose restart).' },
  { id: 'build', label: 'Build', icon: 'fa-hammer', danger: false, text: '' },
  { id: 'pull', label: 'Pull', icon: 'fa-download', danger: false, text: '' },
  { id: 'down', label: 'Down', icon: 'fa-power-off', danger: true,
    text: 'the containers and the networks of the stack will be removed. ' +
          'Named volumes are kept (docker compose down).' }
]

const STACK_ACTION_META = STACK_ACTIONS.reduce((acc, action) => {
  acc[action.id] = action
  return acc
}, {})

/** Marker for "no command running". A fresh object each time avoids sharing. */
function idleBusy() {
  return { name: '', action: '' }
}

/**
 * Compose command + log overlay state. Kept as ONE reactive object so the panel
 * and the overlay always agree on what is running.
 *
 *   busy  – { name, action } of the command in flight ('' when idle)
 *   logs  – aggregated log overlay (see StackLogsModal.vue)
 */
export const stackState = reactive({
  busy: idleBusy(),
  logs: {
    open: false,
    name: '',
    path: '',
    tail: 200,
    lines: [],
    loading: false,
    error: null
  }
})

/**
 * True while a compose command is running on `name`.
 * @param {string} name          Compose project name.
 * @param {string|null} action   When given, only true for THAT command (used to
 *                               spin only the button that was pressed).
 */
export function stackActionBusy(name, action = null) {
  const busy = stackState.busy
  if (!name || !busy.name || busy.name !== name) return false
  return action ? busy.action === action : true
}

/**
 * Entry point of every button in the Stacks tab.
 *
 * Destructive commands (`up`, `stop`, `restart`, `down`) go through `confirm()`
 * first, exactly like the container actions do; `build` and `pull` run straight
 * away. Either path ends in `doStackAction()`, which reloads the host snapshot
 * so the card, the tab counter and the KPI strip agree again.
 *
 * @param {object} stack   Stack from `state.stacks` (needs `name`).
 * @param {string} action  Id from STACK_ACTIONS.
 */
export function askStackAction(stack, action) {
  if (!stack?.name) return
  const meta = STACK_ACTION_META[action]
  if (!meta) return

  const name = stack.name
  if (!meta.text) {
    doStackAction(name, action)
    return
  }

  confirm({
    title: `${meta.label} ${name}?`,
    html: `<b>${name}</b> — ${meta.text}`,
    confirmText: meta.label,
    danger: meta.danger,
    onConfirm: () => doStackAction(name, action)
  })
}

/**
 * Runs the compose command and refreshes the snapshot.
 * Never throws: failures are reported with a toast, like `doAction()` does.
 */
export async function doStackAction(name, action) {
  if (!name) return
  const meta = STACK_ACTION_META[action] || { label: action }
  // The confirm dialog stored `onConfirm`; closing it here keeps the flow the
  // same whether the command was confirmed or not.
  state.modal = null
  stackState.busy = { name, action }
  try {
    await API.infra.stackAction(name, action, state.hostId)
    pushToast({ text: `${name}: ${meta.label.toLowerCase()} requested`, kind: 'success' })
    await loadAll({ silent: true })
  } catch (err) {
    pushToast({ text: `${name}: ${err?.message || err}`, kind: 'error' })
  } finally {
    stackState.busy = idleBusy()
  }
}

/* ── Aggregated compose logs (see StackLogsModal.vue) ─────────────────────── */

/**
 * Opens the compose log overlay for `stack`.
 *
 * The container drawer is closed first: both overlays are full-window, so
 * stacking them would put two Escape handlers on top of each other.
 *
 * @param {object} stack   Stack from `state.stacks` (needs `name`).
 * @param {number} [tail]  Initial tail size (defaults to the last choice).
 */
export function openStackLogs(stack, tail = stackState.logs.tail) {
  if (!stack?.name) return null
  // Imported lazily to avoid a module cycle with the drawer state helpers.
  stackState.logs.open = true
  stackState.logs.name = stack.name
  stackState.logs.path = stack.path || ''
  stackState.logs.tail = Number(tail) || 200
  stackState.logs.lines = []
  stackState.logs.error = null
  return loadStackLogs(stackState.logs.tail)
}

/** Closes the overlay and drops the lines (they belong to the closed stack). */
export function closeStackLogs() {
  stackState.logs.open = false
  stackState.logs.name = ''
  stackState.logs.path = ''
  stackState.logs.lines = []
  stackState.logs.loading = false
  stackState.logs.error = null
}

/**
 * Fetches the tail of every service.
 *
 * Responses for a stack that is no longer open are DISCARDED: a slow request
 * must never paint lines of the previous stack into the current overlay.
 *
 * @param {number} [tail]  Lines requested from the daemon.
 */
export async function loadStackLogs(tail = stackState.logs.tail) {
  const name = stackState.logs.name
  if (!name) return
  stackState.logs.tail = Number(tail) || stackState.logs.tail
  stackState.logs.loading = true
  try {
    const res = await API.infra.stackLogs(name, stackState.logs.tail, state.hostId)
    if (stackState.logs.name !== name) return
    stackState.logs.lines = res?.lines || []
    stackState.logs.error = null
  } catch (err) {
    if (stackState.logs.name !== name) return
    stackState.logs.lines = []
    stackState.logs.error = err?.message || String(err)
  } finally {
    if (stackState.logs.name === name) stackState.logs.loading = false
  }
}