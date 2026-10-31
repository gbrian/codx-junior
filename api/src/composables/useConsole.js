/**
 * ============================================================================
 * codx-junior — Console composable
 * File: src/composables/useConsole.js
 * ----------------------------------------------------------------------------
 * Reusable "ask → run → report" cycle for shell commands executed through the
 * console API (`src/api/modules/console.js` → `POST /api/console/execute`).
 *
 * WHY A COMPOSABLE
 * ----------------
 * Every place that runs a command (project scripts, the code viewer, a shell
 * code block in a chat) needs the same four things: normalize the command, ask
 * the user, execute, normalize the output. Copying that per component drifts:
 * one forgets the confirmation, another assumes HTTP 200 means success.
 *
 * THE TWO CALL STYLES
 * -------------------
 *   // 1. Interactive: opens a dialog, executes only on confirm
 *   const { scriptToRun, running, requestRun, confirmRun, cancelRun } = useConsole()
 *
 *   <ConsoleScriptConfirm
 *     :show="!!scriptToRun" :script="scriptToRun" :busy="running"
 *     @confirm="confirmRun" @cancel="cancelRun" />
 *
 *   // 2. Direct: the caller already asked the user
 *   const { run } = useConsole()
 *   await run('npm test')
 *
 * WHAT IT OWNS / WHAT IT DOES NOT
 * -------------------------------
 * Owns: the pending script, the busy flag, the normalized last result, the last
 * error message and the notification.
 * Does not own: the dialog markup. Render `ConsoleScriptConfirm.vue` (or any
 * component) bound to the returned refs.
 *
 * A FAILING COMMAND IS NOT AN ERROR
 * ---------------------------------
 * `exit_code !== 0` and `timed_out` arrive inside a successful response. They
 * are exposed through `lastRunFailed` / `lastRunSummary`; only transport and
 * access failures (400 / 401 / 403 / 500) reject and land in `error`.
 *
 * DIAGRAM
 * -------
 * ```mermaid
 * flowchart TD
 *     A[requestRun script] --> B{command?}
 *     B -- no --> C[error: nothing to run]
 *     B -- yes --> D[scriptToRun set → dialog]
 *     D --> E{confirmRun}
 *     E -- cancel --> F[discard]
 *     E -- confirm --> G[console.execute]
 *     G --> H[lastRun: stdout, stderr, exit_code, timed_out]
 *     G -- 400/401/403/500 --> I[error + notification]
 * ```
 * ============================================================================
 */

import { computed, getCurrentInstance, ref } from 'vue'
import { consoleScriptCommand } from '@/api/modules/console'

/* ──────────────────────────────────────────────────────────────────────────
 * 1. PURE HELPERS
 * ────────────────────────────────────────────────────────────────────────── */

/**
 * Languages of the fenced code blocks that can be sent to the console.
 * @type {readonly string[]}
 */
export const SHELL_LANGUAGES = Object.freeze(['bash', 'sh', 'shell', 'zsh', 'console'])

/**
 * Build a display name out of a command line (first line, truncated).
 *
 * @param {string} command - Command line.
 * @param {string} [fallback] - Name used when the command is empty.
 * @returns {string} Short label suitable for a dialog title or a badge.
 *
 * @example
 * commandLabel('npm run dev -- --port 3000') // "npm run dev -- --port 3000"
 */
export function commandLabel(command, fallback = 'Command') {
  const line = String(command || '').split('\n')[0].trim()
  if (!line) return fallback
  return line.length > 48 ? `${line.slice(0, 45)}…` : line
}

/**
 * Tell whether a code block (or a language id) is a shell script that the
 * console can run.
 *
 * Accepts a language string or a code-block object exposing `language` / `lang`.
 *
 * @param {string|{language?:string, lang?:string}} languageOrBlock
 * @returns {boolean}
 *
 * @example
 * isShellBlock('bash')                        // true
 * isShellBlock({ language: 'python' })        // false
 * isShellBlock({ language: 'sh', code: 'ls' })// true
 */
export function isShellBlock(languageOrBlock) {
  const language = typeof languageOrBlock === 'string'
    ? languageOrBlock
    : languageOrBlock?.language || languageOrBlock?.lang || ''
  return SHELL_LANGUAGES.includes(String(language).toLowerCase())
}

/**
 * Normalize anything that may describe a command into the shape the console
 * UI and the API expect: `{ name, description, script, background, restart }`.
 *
 * Accepts a `project_scripts` entry, a code block (`{ language, code }`) or a
 * raw command string. Returns `null` when there is no command to run, so
 * callers can disable their action instead of sending an empty payload.
 *
 * @param {object|string|null} script - Script, code block or command.
 * @param {string} [fallbackName] - Name used when the input carries none.
 * @returns {?{name:string, description:string, script:string, background:boolean, restart:boolean}}
 *
 * @example
 * normalizeConsoleScript({ name: 'Dev', script: 'npm run dev' })
 * normalizeConsoleScript({ language: 'bash', code: 'npm test' }) // name = "npm test"
 * normalizeConsoleScript('   ')                                  // null
 */
export function normalizeConsoleScript(script, fallbackName = 'Command') {
  if (!script) return null

  // A code block: the command is its `code`
  if (typeof script === 'object' && !script.script && !script.command && script.code) {
    const command = String(script.code).trim()
    if (!command) return null
    return {
      name: script.name || commandLabel(command, fallbackName),
      description: script.description || '',
      script: command,
      background: false,
      restart: false
    }
  }

  const command = consoleScriptCommand(script)
  if (!command) return null

  return {
    name: script.name || commandLabel(command, fallbackName),
    description: script.description || '',
    script: command,
    background: !!script.background,
    restart: !!script.restart
  }
}

/**
 * Build a runnable script object out of a raw command line.
 *
 * @param {string} command - Command line.
 * @param {string} [name] - Display name (defaults to the command itself).
 * @returns {?{name:string, description:string, script:string, background:boolean, restart:boolean}}
 *
 * @example
 * scriptFromCommand('npm run lint', 'Lint') // { name: 'Lint', script: 'npm run lint', ... }
 */
export function scriptFromCommand(command, name) {
  const normalized = normalizeConsoleScript(command, name)
  if (!normalized) return null
  return { ...normalized, name: name || normalized.name }
}

/**
 * Read the most useful message out of an API error.
 *
 * The console endpoints answer `{ detail: "..." }` (403 outside the projects,
 * 400 empty command, 401 unauthenticated), so the detail wins over the generic
 * axios message.
 *
 * @param {*} error - Rejection value.
 * @returns {string} Human readable message.
 */
export function consoleErrorMessage(error) {
  return error?.response?.data?.detail || error?.message || String(error || 'Unknown error')
}

/* ──────────────────────────────────────────────────────────────────────────
 * 2. COMPOSABLE
 * ────────────────────────────────────────────────────────────────────────── */

/**
 * Console composable.
 *
 * Call it from `setup()` so the notifications and the API instance can be
 * resolved from the component (`$ui`, `$storex`). From a plain module pass the
 * API instance explicitly.
 *
 * @param {Object} [options] - Options.
 * @param {Object} [options.api] - API instance to use (defaults to `$storex.api`).
 * @param {boolean} [options.notify] - Show a notification after each run (default `true`).
 * @returns {Object} Console state and actions.
 *
 * @example
 * // Options API component
 * export default {
 *   setup() { return useConsole() }
 * }
 *
 * @example
 * // Plain module
 * import { API } from '@/api/api'
 * const { run } = useConsole({ api: API, notify: false })
 * const { stdout, exit_code } = await run('git status')
 */
export function useConsole(options = {}) {
  const { api: injectedApi = null, notify = true } = options

  // `getCurrentInstance` is only available during setup(); calling the
  // composable elsewhere is allowed as long as an api is injected.
  const instance = getCurrentInstance()
  const proxy = instance?.proxy

  // ── State ────────────────────────────────────────────────────────────────

  /** Script waiting for the user confirmation (null when no dialog is open). */
  const scriptToRun = ref(null)
  /** True while a command is on the wire. */
  const running = ref(false)
  /** Normalized result of the last execution (`null` before the first run). */
  const lastRun = ref(null)
  /** Last failure message (`400` / `401` / `403` / `500`). */
  const error = ref(null)

  /**
   * Options applied to the pending execution.
   * Kept outside of `scriptToRun` so the dialog only receives script metadata.
   * @type {{cwd?:string, env?:Object, timeout?:number}}
   */
  let pendingOptions = {}

  // ── API plumbing ─────────────────────────────────────────────────────────

  /**
   * Resolve the API instance: injected first, then the component store.
   *
   * @returns {?Object} API instance.
   */
  function resolveApi() {
    if (injectedApi) return injectedApi
    const store = proxy?.$storex
    return store?.api || store?.projects?.activeProject?.$api || null
  }

  /**
   * Same as `resolveApi` but fails when the console module is missing.
   *
   * @returns {Object} API instance exposing `console`.
   * @throws {Error} When no API / no console module is available.
   */
  function requireConsoleApi() {
    const api = resolveApi()
    if (!api?.console) {
      throw new Error('Console API is not available for the active project')
    }
    return api
  }

  /**
   * Push a notification through the global UI store (best effort).
   *
   * @param {string} text - Message.
   * @param {string} [type] - `info`, `error`, `warning`…
   * @returns {void}
   */
  function notifyUser(text, type = 'info') {
    if (!notify) return
    proxy?.$ui?.addNotification?.({ text, type })
  }

  // ── Payload / result helpers ─────────────────────────────────────────────

  /**
   * Build the `ConsoleCommand` body from a normalized script + run options.
   *
   * @param {object} script - Normalized script.
   * @param {{cwd?:string, env?:Object, timeout?:number}} [runOptions]
   * @returns {{command:string, cwd?:string, env?:Object, timeout?:number}}
   */
  function buildPayload(script, runOptions = {}) {
    const payload = { command: consoleScriptCommand(script) }
    if (runOptions.cwd) payload.cwd = runOptions.cwd
    if (runOptions.env) payload.env = runOptions.env
    if (runOptions.timeout) payload.timeout = runOptions.timeout
    return payload
  }

  /**
   * Normalize a `ConsoleResult` for rendering.
   *
   * `stdout` and `stderr` are merged into `output` (what the output panel
   * prints) but kept separately for callers that need to tell them apart.
   *
   * @param {Object} result - Response of `POST /api/console/execute`.
   * @param {object} script - Script that was executed.
   * @returns {Object} `{ name, command, cwd, exit_code, timed_out, stdout, stderr, output, unrestricted }`
   */
  function formatResult(result, script) {
    const stdout = result?.stdout || ''
    const stderr = result?.stderr || ''
    return {
      name: script?.name || 'Command',
      command: result?.command || consoleScriptCommand(script),
      cwd: result?.cwd || '',
      exit_code: result?.exit_code ?? null,
      timed_out: !!result?.timed_out,
      stdout,
      stderr,
      output: [stdout, stderr].filter(Boolean).join('\n').trim(),
      unrestricted: !!result?.unrestricted
    }
  }

  // ── Computed view state ──────────────────────────────────────────────────

  /** Command line of the pending script (empty when no dialog is open). */
  const pendingCommand = computed(() => consoleScriptCommand(scriptToRun.value))

  /** True when the dialog can submit (there is a command and nothing running). */
  const canConfirm = computed(() => !!pendingCommand.value && !running.value)

  /** True when the last execution failed or timed out. */
  const lastRunFailed = computed(() => {
    const run = lastRun.value
    if (!run) return false
    return !!run.timed_out || (run.exit_code !== 0 && run.exit_code !== null)
  })

  /** Short label of the last execution: `exit 0`, `exit 2`, `timed out`. */
  const lastRunSummary = computed(() => {
    const run = lastRun.value
    if (!run) return ''
    if (run.timed_out) return 'timed out'
    return run.exit_code === null ? 'finished' : `exit ${run.exit_code}`
  })

  // ── Interactive flow ─────────────────────────────────────────────────────

  /**
   * Open the confirmation dialog for a script / command.
   *
   * Nothing is executed here: this is the only safe entry point for a click.
   *
   * @param {object|string} script - `project_scripts` entry, code block or command.
   * @param {{cwd?:string, env?:Object, timeout?:number, name?:string}} [runOptions]
   * @returns {boolean} False when there is nothing to run (dialog stays closed).
   *
   * @example
   * requestRun(script)                                  // project script
   * requestRun({ language: 'bash', code: 'npm test' })   // chat code block
   * requestRun('git status', { cwd: 'api' })
   */
  function requestRun(script, runOptions = {}) {
    const normalized = normalizeConsoleScript(script, runOptions.name)
    if (!normalized) {
      error.value = 'This script has no command to run'
      return false
    }
    if (runOptions.name) normalized.name = runOptions.name

    pendingOptions = { cwd: runOptions.cwd, env: runOptions.env, timeout: runOptions.timeout }
    scriptToRun.value = normalized
    error.value = null
    return true
  }

  /**
   * Close the dialog without executing (ignored while a command runs).
   *
   * @returns {void}
   */
  function cancelRun() {
    if (running.value) return
    scriptToRun.value = null
    pendingOptions = {}
  }

  /**
   * Execute the script waiting for confirmation.
   *
   * The dialog stays open when the request fails so the user can retry or
   * cancel; it closes on success.
   *
   * @returns {Promise<?Object>} Normalized result, or `null` on failure.
   */
  async function confirmRun() {
    const script = scriptToRun.value
    if (!script || running.value) return null

    running.value = true
    error.value = null
    try {
      const result = await requireConsoleApi().console.execute(
        buildPayload(script, pendingOptions)
      )
      lastRun.value = formatResult(result, script)
      notifyUser(
        `${lastRunFailed.value ? '⚠️' : '✅'} ${script.name}: ${lastRunSummary.value}`,
        lastRunFailed.value ? 'error' : 'info'
      )
      scriptToRun.value = null
      pendingOptions = {}
      return lastRun.value
    } catch (ex) {
      error.value = consoleErrorMessage(ex)
      notifyUser(`❌ ${script.name}: ${error.value}`, 'error')
      return null
    } finally {
      running.value = false
    }
  }

  // ── Direct flow ──────────────────────────────────────────────────────────

  /**
   * Execute a script / command immediately, without a dialog.
   *
   * Only use it when the user already confirmed the action (a secondary click
   * on a button they just pressed, a retry…). Rejections carry the backend
   * `detail`, so surface them in the caller.
   *
   * @param {object|string} commandOrScript - Script, code block or command.
   * @param {{cwd?:string, env?:Object, timeout?:number}} [runOptions]
   * @returns {Promise<Object>} Normalized result.
   * @throws {Error} When the command is empty or the request fails.
   *
   * @example
   * const { exit_code, output } = await run('npm run build', { timeout: 120 })
   */
  async function run(commandOrScript, runOptions = {}) {
    const script = normalizeConsoleScript(commandOrScript)
    if (!script) throw new Error('Nothing to run: the command is empty')

    const result = await requireConsoleApi().console.execute(
      buildPayload(script, runOptions)
    )
    lastRun.value = formatResult(result, script)
    return lastRun.value
  }

  /**
   * Raw access to `POST /api/console/execute` (full control, no result cache).
   *
   * @param {{command:string, cwd?:string, env?:Object, timeout?:number}} payload
   * @returns {Promise<Object>} Backend `ConsoleResult`.
   */
  function execute(payload) {
    return requireConsoleApi().console.execute(payload)
  }

  /**
   * Console context of the caller: role, `unrestricted`, project path, allowed
   * roots and timeouts (`GET /api/console/info`).
   *
   * @returns {Promise<Object>} Backend `ConsoleInfo`.
   */
  function info() {
    return requireConsoleApi().console.info()
  }

  /**
   * Drop the last result (dismiss the output panel).
   *
   * @returns {void}
   */
  function dismiss() {
    lastRun.value = null
  }

  return {
    // state
    scriptToRun,
    running,
    lastRun,
    error,

    // computed
    pendingCommand,
    canConfirm,
    lastRunFailed,
    lastRunSummary,

    // interactive flow
    requestRun,
    cancelRun,
    confirmRun,

    // direct flow
    run,
    execute,
    info,

    // helpers
    dismiss,
    commandOf: consoleScriptCommand,
    isShellBlock
  }
}