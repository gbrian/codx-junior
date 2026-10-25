/**
 * Repository (git) API module
 * Handles every git operation used by the Git view: repository info, branches,
 * commits, the commit graph, working tree actions, remote sync, the repository
 * lock, commit message generation and the local PR (branch) lifecycle.
 *
 * Backend routes: `api/codx/junior/api/git.py` (engine:
 * `codx/junior/engine/git_commit_message.py`).
 *
 *   GET    /api/git/repo/info
 *   GET    /api/git/repo/status
 *   GET    /api/git/repo/branches
 *   GET    /api/git/repo/graph
 *   GET    /api/git/repo/remotes
 *   GET    /api/git/repo/worktrees
 *   GET    /api/git/repo/branch/commits
 *   GET    /api/git/repo/changes
 *   GET    /api/git/repo/commit/changes
 *   GET    /api/git/repo/commit/detail
 *   GET    /api/git/repo/file/diff
 *   GET    /api/git/repo/file/history
 *   GET    /api/git/repo/lock
 *   GET    /api/git/repo/staged
 *   GET    /api/git/files/content
 *   POST   /api/git/repo/stage | unstage | discard | commit | commit/message
 *   POST   /api/git/repo/fetch | pull | push
 *   POST   /api/git/repo/lock/release
 *   POST   /api/git/repo/branch | branch/checkout | merge | rebase
 *   DELETE /api/git/repo/branch
 *   POST   /api/git/repo/pr | pr/close | pr/abandon
 */

import { buildGraphLayout, normalizeGraphPayload } from '../models/gitGraph'

const GRAPH_ENDPOINT = '/api/git/repo/graph'
const COMMIT_DETAIL_ENDPOINT = '/api/git/repo/commit/detail'

/** Default number of commits requested when loading the graph. */
const DEFAULT_GRAPH_LIMIT = 150

/**
 * Build a query string, skipping empty values.
 *
 * @param {Object} params - Query parameters.
 * @returns {string} `?a=1&b=2` or an empty string.
 */
const toQuery = (params = {}) => {
  const search = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') return
    search.append(key, String(value))
  })
  const query = search.toString()
  return query ? `?${query}` : ''
}

/**
 * Normalize a path list argument (`"a"` or `["a", "b"]`).
 *
 * @param {string|string[]} paths - Paths to normalize.
 * @returns {string[]} Paths list.
 */
const asList = (paths) => {
  if (!paths) return []
  return Array.isArray(paths) ? paths : [paths]
}

/**
 * Count diff lines matching an addition/deletion prefix (headers excluded).
 *
 * @param {string} diff - Unified diff.
 * @param {string} prefix - `+` or `-`.
 * @returns {number} Line count.
 */
const countDiffLines = (diff = '', prefix = '+') => {
  const header = prefix.repeat(3)
  return String(diff)
    .split('\n')
    .filter((line) => line.startsWith(prefix) && !line.startsWith(header)).length
}

/**
 * Normalize the commit changes payload (`pr_details` or
 * `branch_file_and_commits`) into a flat file list with line counters.
 *
 * @param {Object} payload - Response of `commit/changes`.
 * @returns {Array} `[{ path, status, additions, deletions, diff }]`.
 */
export const normalizeCommitFiles = (payload = {}) => {
  const details = payload?.pr_details || []
  if (details.length) {
    return details
      .map((change) => ({
        path: change.file_name || change.path || '',
        status: change.status || 'modified',
        additions: countDiffLines(change.diff, '+'),
        deletions: countDiffLines(change.diff, '-'),
        diff: change.diff || ''
      }))
      .filter((file) => !!file.path)
  }

  const files = payload?.branch_file_and_commits || {}
  return Object.keys(files).map((path) => ({
    path,
    status: 'modified',
    additions: countDiffLines(files[path]?.diff, '+'),
    deletions: countDiffLines(files[path]?.diff, '-'),
    diff: files[path]?.diff || ''
  }))
}

export const repoModule = (API) => ({
  // ── Repository overview ───────────────────────────────────────────────────

  /** Repository summary: branches, counters, lock state, worktrees, last commit. */
  info() {
    return API.get('/api/git/repo/info')
  },

  /** Working tree status (staged / unstaged lists). */
  status() {
    return API.get('/api/git/repo/status')
  },

  /** Local + remote branches (plus `repo_tree` when provided). */
  branches() {
    return API.get('/api/git/repo/branches')
  },

  /**
   * Configured remotes.
   *
   * @returns {Promise<Array>} `[{ name, url, fetch_url, push_url }]`.
   */
  async remotes() {
    const payload = await API.get('/api/git/repo/remotes')
    return Array.isArray(payload) ? payload : payload?.remotes || []
  },

  /**
   * Registered worktrees.
   *
   * @returns {Promise<Array>} `[{ path, branch }]`.
   */
  async worktrees() {
    const payload = await API.get('/api/git/repo/worktrees')
    return Array.isArray(payload) ? payload : payload?.worktrees || []
  },

  // ── Commits ───────────────────────────────────────────────────────────────

  /**
   * Commits of a branch (or of `HEAD`).
   *
   * Accepts both `commits('main')` and `commits({ branch, limit })`.
   *
   * @param {string|Object} branchOrParams - Branch name or `{ branch, limit }`.
   * @param {number} [limit] - Commit count when a branch name is given.
   * @returns {Promise<Array>} Raw commit list.
   */
  commits(branchOrParams = {}, limit = 50) {
    const params =
      typeof branchOrParams === 'string' || !branchOrParams
        ? { branch: branchOrParams, limit }
        : branchOrParams
    return API.get(
      `/api/git/repo/branch/commits${toQuery({
        branch: params.branch,
        limit: params.limit || limit
      })}`
    )
  },

  /**
   * Changes between two commits (`from_commit` is the newer one).
   *
   * @param {Object} params - `{ from_commit, to_commit }`.
   * @returns {Promise<Object>} Repo changes payload.
   */
  commitChanges({ from_commit, to_commit } = {}) {
    return API.get(`/api/git/repo/commit/changes${toQuery({ from_commit, to_commit })}`)
  },

  /**
   * Commit detail for the commit panel: file list with patches and counters.
   *
   * The backend reads the whole commit with a single `git diff`, so no extra
   * request is needed to render a file diff.
   *
   * @param {Object} params - `{ hash }`.
   * @returns {Promise<Object>} `{ commit, stat, total_additions, total_deletions, files }`.
   *
   * @example
   * const detail = await api.repo.commitDetail({ hash: 'a2d3b55' })
   */
  async commitDetail({ hash } = {}) {
    const payload = await API.get(
      `${COMMIT_DETAIL_ENDPOINT}${toQuery({ commit: hash })}`
    )
    const files = (payload?.files || []).map((file) => ({
      path: file.path,
      status: file.status,
      additions: file.additions || 0,
      deletions: file.deletions || 0,
      diff: file.diff || ''
    }))

    return {
      commit: payload?.commit?.hash || hash || '',
      stat: payload?.stat || '',
      total_additions: payload?.total_additions || files.reduce((total, file) => total + file.additions, 0),
      total_deletions: payload?.total_deletions || files.reduce((total, file) => total + file.deletions, 0),
      files
    }
  },

  /**
   * Diff of one file.
   *
   * @param {Object} params - `{ path, mode, commit }`; mode is
   * `worktree`, `staged` or `commit`.
   * @returns {Promise<Object>} `{ diff, header, additions, deletions }`.
   */
  fileDiff({ path, mode = 'worktree', commit } = {}) {
    return API.get(`/api/git/repo/file/diff${toQuery({ path, mode, commit })}`)
  },

  /**
   * Commit history of a single file.
   *
   * @param {Object} params - `{ path, limit }`.
   * @returns {Promise<Object>} `{ commits: [...] }`.
   */
  fileHistory({ path, limit = 25 } = {}) {
    return API.get(`/api/git/repo/file/history${toQuery({ path, limit })}`)
  },

  /**
   * File content at a given branch.
   *
   * @param {string} path - Repository relative path.
   * @param {string} branch - Branch name (defaults to the current branch).
   * @returns {Promise<string>} File content.
   */
  async readFromBranch(path, branch) {
    const payload = await API.get(`/api/git/files/content${toQuery({ path, branch })}`)
    return typeof payload === 'string' ? payload : payload?.content || ''
  },

  /**
   * File changes and diffs between two branches.
   *
   * @param {Object} params - `{ from_branch, to_branch }`.
   * @returns {Promise<Object>} Repo changes payload.
   */
  changes({ from_branch, to_branch } = {}) {
    return API.get(`/api/git/repo/changes${toQuery({ from_branch, to_branch })}`)
  },

  // ── Commit graph ──────────────────────────────────────────────────────────

  /**
   * Commit graph (VSCode *Git Graph* style) with lane layout.
   *
   * @param {Object} [options] - Options.
   * @param {string} [options.branch] - Restrict to one branch.
   * @param {number} [options.limit] - Maximum commits.
   * @param {boolean} [options.includeRemote] - Include remote branches.
   * @returns {Promise<Object>} `{ rows, laneCount, commits, branches }`.
   *
   * @example
   * const { rows } = await api.repo.graph({ limit: 150 })
   */
  async graph({ branch, limit = DEFAULT_GRAPH_LIMIT, includeRemote = true } = {}) {
    const payload = await API.get(
      `${GRAPH_ENDPOINT}${toQuery({
        branch,
        limit,
        include_remote: includeRemote ? 1 : 0
      })}`
    )
    return normalizeGraphPayload(payload)
  },

  /**
   * Re-lay out a commit list (used when switching the graph branch filter).
   *
   * @param {Object[]} commits - Normalized commits.
   * @returns {Object} `{ rows, laneCount }`.
   */
  layout(commits = []) {
    return buildGraphLayout(commits)
  },

  // ── Working tree ──────────────────────────────────────────────────────────

  /** Stage files (defaults to every change when no path is given). */
  stage(paths) {
    return API.post('/api/git/repo/stage', { paths: asList(paths) })
  },

  /** Remove files from the index. */
  unstage(paths) {
    return API.post('/api/git/repo/unstage', { paths: asList(paths) })
  },

  /** Roll files back to the last commit. */
  discard(paths, includeStaged = true) {
    return API.post('/api/git/repo/discard', {
      paths: asList(paths),
      include_staged: includeStaged
    })
  },

  /**
   * Repository lock state (a stale `.git/index.lock` blocks every write).
   *
   * @returns {Promise<Object>} `{ locked, path, git_dir, repository, age_seconds }`.
   *
   * @example
   * const { locked, path } = await api.repo.lock()
   */
  lock() {
    return API.get('/api/git/repo/lock')
  },

  /**
   * Release the stale `.git/index.lock` file.
   *
   * Only safe when no git process is running: the UI must confirm it first.
   *
   * @returns {Promise<Object>} `{ success, released, path, lock }`.
   */
  releaseLock() {
    return API.post('/api/git/repo/lock/release', {})
  },

  /**
   * Changes summary of the index: exactly what the next commit will contain.
   *
   * The staged files (path + code + status), the diff stat and, unless
   * `include_diff` is false, the staged patch. This is the same payload the
   * commit message generator reads, so the UI and the generated message can
   * never describe different changes.
   *
   * @param {Object} [params] - Options.
   * @param {boolean} [params.include_diff] - Include the staged patch.
   * @param {number} [params.max_diff_chars] - Patch budget (0 = no limit).
   * @returns {Promise<Object>} `{ success, repo_path, files, file_count, stat, diff, diff_truncated, errors }`.
   *
   * @example
   * const { files, stat } = await api.repo.staged({ include_diff: false })
   */
  staged({ include_diff = true, max_diff_chars } = {}) {
    return API.get(
      `/api/git/repo/staged${toQuery({
        include_diff: include_diff ? 1 : 0,
        max_diff_chars
      })}`
    )
  },

  /**
   * Commit the working tree.
   *
   * @param {Object} params - `{ message, stage_all, allow_empty }`.
   * @returns {Promise<Object>} Operation result.
   */
  commit({ message, stage_all = true, allow_empty = false } = {}) {
    return API.post('/api/git/repo/commit', { message, stage_all, allow_empty })
  },

  // ── Commit message ────────────────────────────────────────────────────────

  /**
   * Generate a commit message for the staged changes (50/72 rule).
   *
   * The backend reads the staged patch, asks the project LLM for the message
   * and normalizes the answer: subject of at most 50 characters, body lines of
   * at most 72, separated by one blank line. Nothing is committed: the message
   * is returned so the user can review and edit it first.
   *
   * When the AI is unavailable the answer carries `fallback = true` and a
   * message built from the staged file names, so the commit box is never left
   * empty. Nothing staged answers **400**.
   *
   * @param {Object} [params] - Options.
   * @param {string} [params.hint] - Intent (issue reference, reason for the change).
   * @param {boolean} [params.include_body] - Ask only for the subject when false.
   * @param {number} [params.max_diff_chars] - Prompt budget for the patch.
   * @returns {Promise<Object>} `{ success, title, body, message, fallback, files, file_count, stat, diff_truncated, errors }`.
   *
   * @example
   * const { message, fallback } = await api.repo.commitMessage({ hint: 'fixes #42' })
   */
  commitMessage({ hint, include_body = true, max_diff_chars } = {}) {
    return API.post('/api/git/repo/commit/message', {
      hint: hint || null,
      include_body,
      max_diff_chars
    })
  },

  // ── Remote operations ─────────────────────────────────────────────────────

  fetch() {
    return API.post('/api/git/repo/fetch', {})
  },

  pull() {
    return API.post('/api/git/repo/pull', {})
  },

  push() {
    return API.post('/api/git/repo/push', {})
  },

  // ── Branches ──────────────────────────────────────────────────────────────

  /**
   * Create a branch.
   *
   * @param {Object} params - `{ branch, from_branch, checkout }`.
   * @returns {Promise<Object>} Operation result.
   */
  createBranch({ branch, from_branch, checkout = false } = {}) {
    return API.post('/api/git/repo/branch', {
      branch,
      from_branch: from_branch || undefined,
      checkout
    })
  },

  /** Check out a branch (tracks the remote branch when needed). */
  checkoutBranch(branch) {
    return API.post('/api/git/repo/branch/checkout', { branch })
  },

  /** Delete a local branch (and its worktree when it has one). */
  deleteBranch(branch, { force = true } = {}) {
    return API.delete(
      `/api/git/repo/branch${toQuery({ branch, force: force ? 1 : 0 })}`
    )
  },

  /**
   * Merge a branch into another one.
   *
   * @param {Object} params - `{ from_branch, to_branch, message, delete_branch }`.
   * @returns {Promise<Object>} Operation result.
   */
  merge({ from_branch, to_branch, message, delete_branch = false } = {}) {
    return API.post('/api/git/repo/merge', {
      from_branch,
      to_branch,
      message: message || undefined,
      delete_branch
    })
  },

  /**
   * Rebase a branch onto another one.
   *
   * Rewrites the history of the rebased branch, so the UI must confirm it with
   * the user first.
   *
   * @param {Object} params - `{ onto_branch, branch }`; `branch` defaults to
   * the checked out branch.
   * @returns {Promise<Object>} `{ branch, onto_branch, commit, up_to_date, conflicts }`.
   *
   * @example
   * await api.repo.rebase({ onto_branch: 'main', branch: 'fix-login' })
   */
  rebase({ onto_branch, branch } = {}) {
    return API.post('/api/git/repo/rebase', {
      onto_branch,
      branch: branch || undefined
    })
  },

  // ── Local PR lifecycle ────────────────────────────────────────────────────

  /** Create a local PR branch from the current branch. */
  createPR(payload = {}) {
    return API.post('/api/git/repo/pr', payload)
  },

  /** Close a local PR (merge the branch into its base). */
  closePR(payload = {}) {
    return API.post('/api/git/repo/pr/close', payload)
  },

  /** Abandon a local PR (drop the branch and its commits). */
  abandonPR(payload = {}) {
    return API.post('/api/git/repo/pr/abandon', payload)
  }
})