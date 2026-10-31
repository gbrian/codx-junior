/**
 * ============================================================================
 * codx-junior — Console API module
 * File: src/api/modules/console.js
 * ----------------------------------------------------------------------------
 * BACKEND CONTRACT
 * ----------------
 * Thin HTTP client for the console REST API implemented by
 * `api/codx/junior/api/console.py`, the routing layer over
 * `codx.junior.console_manager.ConsoleManager`.
 *
 *   GET  /api/console/info     -> ConsoleInfo
 *   POST /api/console/execute  -> ConsoleResult     body: ConsoleCommand
 *
 * SCOPE OF EXECUTION
 * ------------------
 * Commands run on the codx-junior host, in the project working directory, with
 * the permissions of the API process:
 *   - `admin` users are unrestricted (any command, any `cwd`).
 *   - Any other user is confined to the projects they can access: a `cwd`
 *     outside of them is rejected with `403`.
 *
 * A FAILING COMMAND IS NOT AN HTTP ERROR
 * --------------------------------------
 * `stdout`, `stderr`, `exit_code` and `timed_out` are always present in the
 * response, so the UI must never assume success from a `200` alone — it has to
 * check `exit_code === 0` and `timed_out === false`.
 *
 * ERROR STATUSES TO HANDLE IN THE UI
 * ----------------------------------
 *   - `400` empty command / unknown working directory / no project context.
 *   - `401` not authenticated.
 *   - `403` target directory outside the caller's projects.
 *   - `500` the process could not be started.
 *
 * The machine-readable contract is exported as `CONSOLE_ENDPOINTS` and mirrored
 * by the JSDoc typedefs below.
 * ============================================================================
 */

/* ──────────────────────────────────────────────────────────────────────────
 * 1. CONTRACT
 * ────────────────────────────────────────────────────────────────────────── */

/**
 * @typedef {Object} ConsoleInfo
 * Caller context, used to know whether the console is unrestricted.
 *
 * @property {string}    username         Caller username.
 * @property {string}    role             Caller role ("admin" or a user role).
 * @property {boolean}   unrestricted     True when the caller may run anything anywhere.
 * @property {?string}   project_path     Working directory of the active project.
 * @property {?string[]} allowed_roots    Real project paths the caller may use
 *                                        (null when the caller is unrestricted).
 * @property {number}    default_timeout  Timeout applied when none is sent (seconds).
 * @property {number}    max_timeout      Maximum accepted timeout (seconds).
 */

/**
 * @typedef {Object} ConsoleCommand
 * Body of `POST /api/console/execute`.
 *
 * @property {string}  command           Shell command line to execute.
 * @property {?string} [cwd]             Working directory (defaults to the project path).
 * @property {?Object.<string,string>} [env]  Extra environment variables.
 * @property {?number} [timeout]         Timeout in seconds (clamped server-side).
 */

/**
 * @typedef {Object} ConsoleResult
 *
 * @property {string}  command       Command that was executed.
 * @property {string}  cwd           Working directory actually used.
 * @property {string}  user          Caller username.
 * @property {boolean} unrestricted  Whether the run was unrestricted.
 * @property {number}  timeout       Timeout applied (seconds).
 * @property {string}  stdout        Captured standard output.
 * @property {string}  stderr        Captured standard error.
 * @property {?number} exit_code     Process exit code (null on timeout).
 * @property {boolean} timed_out     True when the timeout was hit.
 */

/**
 * @typedef {Object} ConsoleScript
 * A script defined in the project settings (`project_scripts`). Only `script`
 * is needed to run it; the other fields are UI metadata.
 *
 * @property {string}  name
 * @property {string}  description
 * @property {string}  script        The shell command line.
 * @property {boolean} background
 * @property {boolean} restart
 */

/**
 * Machine-readable endpoint contract.
 * @type {{method:string, path:string, desc:string, body?:string, response:string}[]}
 */
export const CONSOLE_ENDPOINTS = [
  { method: 'GET',  path: '/api/console/info',    desc: 'Console context of the caller (role, project, allowed roots, timeouts).', response: 'ConsoleInfo' },
  { method: 'POST', path: '/api/console/execute', desc: 'Run a shell command and return its output.', body: 'ConsoleCommand', response: 'ConsoleResult' }
]

/* ──────────────────────────────────────────────────────────────────────────
 * 2. HELPERS
 * ────────────────────────────────────────────────────────────────────────── */

/**
 * Resolve the command line of a console script.
 *
 * Accepts a script object (`{ script }`) or a raw command string, so the UI can
 * call it on anything it holds in `project_scripts` without normalizing first.
 *
 * @param {ConsoleScript|string} script
 * @returns {string} Command line (empty when the script has none).
 *
 * @example
 * consoleScriptCommand({ name: 'Dev', script: 'npm run dev' }) // "npm run dev"
 * consoleScriptCommand('  ls -la  ')                           // "ls -la"
 */
export function consoleScriptCommand(script) {
  if (!script) return ''
  if (typeof script === 'string') return script.trim()
  return String(script.script || script.command || '').trim()
}

/* ──────────────────────────────────────────────────────────────────────────
 * 3. MODULE — the public API surface used by the UI
 * ────────────────────────────────────────────────────────────────────────── */

/**
 * Console module factory.
 * @param {object} API  The codx-junior API instance (see src/api/api.js).
 */
export function consoleModule(API) {
  /**
   * Single exit point: every execution goes through `POST /console/execute`.
   * @param {ConsoleCommand} payload
   * @returns {Promise<ConsoleResult>}
   */
  const execute = (payload) => API.post('/api/console/execute', payload)

  return {
    /** @type {typeof CONSOLE_ENDPOINTS} machine-readable backend contract. */
    endpoints: CONSOLE_ENDPOINTS,

    /**
     * Console context of the caller.
     * @returns {Promise<ConsoleInfo>}
     */
    info: () => API.get('/api/console/info'),

    /**
     * Run a shell command.
     *
     * No confirmation is done here: this is the execution primitive used by
     * callers that already asked the user.
     *
     * @param {ConsoleCommand} payload
     * @returns {Promise<ConsoleResult>}
     *
     * @example
     * const result = await API.console.execute({ command: 'git status' })
     */
    execute,

    /**
     * Shorthand for `execute({ command, ...options })`.
     * @param {string} command
     * @param {{cwd?:string, env?:Object, timeout?:number}} [options]
     * @returns {Promise<ConsoleResult>}
     */
    run(command, options = {}) {
      return execute({ command, ...options })
    },

    /**
     * Run a console script (`project_scripts` entry or a raw command).
     *
     * The confirmation step belongs to the UI: this method executes
     * immediately, so callers must ask the user first (see
     * `components/console/ConsoleScriptConfirm.vue`).
     *
     * `background` / `restart` are project-script flags this endpoint does not
     * interpret: the request waits for the command to finish (or for the
     * timeout to be reached), it does not detach a background process.
     *
     * @param {ConsoleScript|string} script
     * @param {{cwd?:string, env?:Object, timeout?:number}} [options]
     * @returns {Promise<ConsoleResult>}
     * @throws {Error} When the script has no command to run.
     *
     * @example
     * await API.console.runScript({ name: 'Dev', script: 'npm run dev' }, { timeout: 120 })
     */
    runScript(script, options = {}) {
      const command = consoleScriptCommand(script)
      if (!command) {
        const name = typeof script === 'string' ? script : script?.name
        return Promise.reject(new Error(`Script "${name || 'unnamed'}" has no command`))
      }
      return execute({ command, ...options })
    }
  }
}