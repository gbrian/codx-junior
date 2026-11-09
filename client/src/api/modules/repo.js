/**
 * Repository (git) API module
 * Handles every git operation used by the Git view: repository info, branches,
 * commits, the commit graph, working tree actions, remote sync, branch
 * synchronisation, commit message generation and the local PR (branch)
 * lifecycle.
 *
 * Backend routes: `api/codx/junior/api/git.py` (engine:
 * `api/codx/junior/engine/git_graph.py`).
 *
 *   GET    /api/git/repo/info
 *   GET    /api/git/repo/status
 *   GET    /api/git/repo/branches
 *   GET    /api/git/repo/graph
 *   GET    /api/git/repo/remotes
 *   GET    /api/git/repo/worktrees
 *   POST   /api/git/repo/worktree/remove
 *   GET    /api/git/repo/gitignore
 *   POST   /api/git/repo/gitignore
 *   POST   /api/git/repo/gitignore/add
 *   GET    /api/git/repo/branch/commits
 *   GET    /api/git/repo/changes
 *   GET    /api/git/repo/validate/context
 *   GET    /api/git/repo/commit/changes
 *   GET    /api/git/repo/commit/detail
 *   GET    /api/git/repo/file/diff
 *   GET    /api/git/repo/file/history
 *   GET    /api/git/repo/lock
 *   GET    /api/git/repo/staged
 *   GET    /api/git/repo/conflicts
 *   GET    /api/git/files/content
 *   POST   /api/git/repo/validate
 *   POST   /api/git/repo/stage | unstage | discard | commit | commit/message
 *   POST   /api/git/repo/fetch | pull | push
 *   POST   /api/git/repo/lock/release
 *   POST   /api/git/repo/conflicts/resolve | conflicts/ai | conflicts/continue
 *   POST   /api/git/repo/conflicts/abort
 *   POST   /api/git/repo/branch | branch/checkout | merge | rebase
 *   DELETE /api/git/repo/branch
 *   POST   /api/git/repo/pr | pr/close | pr/abandon
 *
 * File diffs and commit details go through the short-term request cache
 * (`api/requestCache.js`): both are expensive and are requested repeatedly by
 * the diff panels while the user clicks through the file list. File diffs also
 * go through the `files:diff` request queue (`api/requestQueue.js`), so they are
 * serialized with the editor diffs instead of being fired in parallel.
 */

import { buildGraphLayout, normalizeGraphPayload } from '../models/gitGraph'
import { CACHE_TTL, normalizePath } from '../requestCache'
import { QUEUE_NAMES } from '../requestQueue'

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
 * Drop the cached file diffs of the current project.
 *
 * Working tree mutations (stage, unstage, discard, commit, checkout) change
 * what those diffs contain, so their cached entries must not survive them.
 *
 * @param {Object} API - API instance.
 */
const invalidateDiffs = (API) => {
  API.invalidateCache(API.cacheKey('repo:fileDiff'))
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

  /** Local + remote branches (plus `active_branch`, `default_branch` and `repo_tree`). */
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
   * Registered worktrees with their file changes.
   *
   * The backend reads `git status` inside every worktree, so each entry carries
   * the staged / unstaged files changed in that checkout.
   *
   * @param {Object} [params] - Options.
   * @param {boolean} [params.includeChanges] - Read each worktree status.
   * @returns {Promise<Array>} `[{ path, branch, changes: { staged, unstaged, file_count } }]`.
   */
  async worktrees({ includeChanges = true } = {}) {
    const payload = await API.get(
      `/api/git/repo/worktrees${toQuery({ include_changes: includeChanges ? 1 : 0 })}`
    )
    return Array.isArray(payload) ? payload : payload?.worktrees || []
  },

  /**
   * Remove a registered worktree, keeping its branch.
   *
   * The backend resolves the target against the registered worktrees, so it
   * cannot delete an arbitrary directory. Pass `path` for a detached worktree.
   *
   * @param {Object} params - `{ branch, path }`.
   * @returns {Promise<Object>} `{ success, branch, path, removed, errors }`.
   */
  removeWorktree({ branch, path } = {}) {
    return API.post('/api/git/repo/worktree/remove', {
      branch: branch || undefined,
      path: path || undefined
    })
  },

  // ── .gitignore editor ─────────────────────────────────────────────────────

  /**
   * Read the checkout's `.gitignore`.
   *
   * @returns {Promise<Object>} `{ success, path, root, exists, content, errors }`.
   */
  gitignore() {
    return API.get('/api/git/repo/gitignore')
  },

  /**
   * Write the checkout's `.gitignore`.
   *
   * @param {string} content - New file content.
   * @returns {Promise<Object>} `{ success, path, root, exists, content, errors }`.
   */
  saveGitignore(content = '') {
    return API.post('/api/git/repo/gitignore', { content })
  },

  /**
   * Append ignore patterns for files/folders.
   *
   * @param {Array<string|Object>} entries - Paths or `{ path, is_dir }` entries.
   * @returns {Promise<Object>} `{ success, path, content, added, skipped, errors }`.
   */
  addToGitignore(entries = []) {
    const payload = (entries || []).map(entry => (
      typeof entry === 'string'
        ? { path: entry, is_dir: false }
        : { path: entry?.path || '', is_dir: !!entry?.is_dir }
    )).filter(entry => entry.path)
    return API.post('/api/git/repo/gitignore/add', { entries: payload })
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
   * Commit detail for the commit panel: the files changed by a commit, each
   * with its patch diffed against the first parent (previous version).
   *
   * The backend reads the whole commit with a single `git diff`, so no extra
   * request is needed to render a file diff. A commit never changes once
   * created, so the payload is cached for longer than a working tree diff.
   *
   * @param {Object} params - `{ hash, force }`.
   * @param {string} params.hash - Commit hash.
   * @param {boolean} [params.force] - Bypass the cache and refresh the entry.
   * @returns {Promise<Object>} `{ commit, stat, total_additions, total_deletions, files }`.
   *
   * @example
   * const detail = await api.repo.commitDetail({ hash: 'a2d3b55' })
   * detail.files[0].diff // patch against the previous version
   */
  async commitDetail({ hash, force = false } = {}) {
    const payload = await API.cached(
      API.cacheKey('repo:commitDetail', hash),
      () => API.get(`${COMMIT_DETAIL_ENDPOINT}${toQuery({ commit: hash })}`),
      { ttl: CACHE_TTL.commitDetail, force }
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
      parents: payload?.commit?.parents || [],
      stat: payload?.stat || '',
      total_additions:
        payload?.total_additions ||
        files.reduce((total, file) => total + file.additions, 0),
      total_deletions:
        payload?.total_deletions ||
        files.reduce((total, file) => total + file.deletions, 0),
      files
    }
  },

  /**
   * Diff of one file.
   *
   * Cached for a few seconds: the diff panels request it again on every
   * selection change and on every re-render. Working tree mutations invalidate
   * the entry, so a stale diff cannot survive a stage / discard / commit.
   *
   * It runs in the `files:diff` queue together with `files.diff`, so only one
   * diff is on the wire at a time whatever panel asked for it.
   *
   * @param {Object} params - `{ path, mode, commit, force }`; mode is
   * `worktree`, `staged` or `commit`.
   * @param {boolean} [params.force] - Bypass the cache and refresh the entry.
   * @returns {Promise<Object>} `{ diff, header, additions, deletions }`.
   *
   * @example
   * const { diff } = await api.repo.fileDiff({ path, mode: 'worktree' })
   */
  fileDiff({ path, mode = 'worktree', commit, force = false } = {}) {
    return API.get(`/api/git/repo/file/diff${toQuery({ path, mode, commit })}`, {
      key: API.cacheKey('repo:fileDiff', normalizePath(path), mode, commit || ''),
      ttl: CACHE_TTL.fileDiff,
      force,
      queue: QUEUE_NAMES.fileDiff
    })
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

  // ── Validator (AI review) ─────────────────────────────────────────────────

  /**
   * Validator context: changed files and the profiles associated with them.
   *
   * The backend matches every changed file against the profile `file_match`
   * rules (`ProfileManager.get_file_profiles_by_file_path`) and returns them as
   * `default_profiles`, so the UI starts with the relevant reviewer profiles.
   * Each file entry carries its own `profiles` list.
   *
   * It also correlates the changed files with the tasks that touched them since
   * the base commit (`tasks`) so the review knows why the files changed, and
   * treats task text as untrusted context to detect prompt injections.
   *
   * @param {Object} [params] - Options.
   * @param {'local'|'branch'} [params.source] - Change source.
   * @param {string} [params.from_branch] - Base (local) or source branch.
   * @param {string} [params.to_branch] - Target branch.
   * @param {string[]} [params.paths] - Local files to restrict the review to.
   * @returns {Promise<Object>} `{ files, profiles, default_profiles, tasks, ... }`.
   *
   * @example
   * const ctx = await api.repo.validateContext({ source: 'local' })
   * ctx.default_profiles // ['reviewer', 'VueDeveloper']
   */
  validateContext({ source = 'local', from_branch, to_branch, paths } = {}) {
    const search = new URLSearchParams()
    search.append('source', source)
    if (from_branch) search.append('from_branch', from_branch)
    if (to_branch) search.append('to_branch', to_branch)
    ;(paths || []).forEach((path) => search.append('paths', path))
    return API.get(`/api/git/repo/validate/context?${search.toString()}`)
  },

  /**
   * Run an AI review of the selected changes (Validator section).
   *
   * @param {Object} [params] - Options.
   * @param {string[]} [params.profiles] - Reviewer profile names.
   * @param {'local'|'branch'} [params.source] - Change source.
   * @param {string} [params.from_branch] - Base (local) or source branch.
   * @param {string} [params.to_branch] - Target branch.
   * @param {string[]} [params.paths] - Local files to restrict the review to.
   * @param {string} [params.instructions] - Extra reviewer instructions.
   * @param {number} [params.max_diff_chars] - Patch budget.
   * @returns {Promise<Object>} `{ success, review, files, profiles, tasks, ... }`.
   *
   * @example
   * const { review } = await api.repo.validate({ profiles: ['reviewer'] })
   */
  validate({
    profiles = [],
    source = 'local',
    from_branch,
    to_branch,
    paths,
    instructions,
    max_diff_chars
  } = {}) {
    return API.post('/api/git/repo/validate', {
      profiles,
      source,
      from_branch: from_branch || null,
      to_branch: to_branch || null,
      paths: paths || null,
      instructions: instructions || null,
      max_diff_chars
    })
  },

  // ── Commit graph ──────────────────────────────────────────────────────────

  /**
   * Commit graph (VSCode *Git Graph* style) with lane layout.
   *
   * @param {Object} [options] - Options.
   * @param {string} [options.branch] - Restrict to one branch.
   * @param {number} [options.limit] - Maximum commits.
   * @param {boolean} [options.includeRemote] - Include remote branches.
   * @returns {Promise<Object>} `{ rows, laneCount, commits, branches, defaultBranch, activeBranch }`.
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
      .then((result) => {
        invalidateDiffs(API)
        return result
      })
  },

  /** Remove files from the index. */
  unstage(paths) {
    return API.post('/api/git/repo/unstage', { paths: asList(paths) })
      .then((result) => {
        invalidateDiffs(API)
        return result
      })
  },

  /** Roll files back to the last commit. */
  discard(paths, includeStaged = true) {
    return API.post('/api/git/repo/discard', {
      paths: asList(paths),
      include_staged: includeStaged
    }).then((result) => {
      invalidateDiffs(API)
      return result
    })
  },

  // ── Conflicts ─────────────────────────────────────────────────────────────

  /**
   * Conflict state of the repository.
   *
   * Detects a pending merge/rebase/cherry-pick/revert (and a stalled squash
   * merge) and lists every unmerged path with its status, conflict markers and
   * content. `info()` already carries the same summary as `conflict_state`, so
   * the view can detect a conflict while loading and only call this endpoint
   * when it needs the file contents.
   *
   * @param {Object} [params] - Options.
   * @param {boolean} [params.include_content] - Include each file content.
   * @param {boolean} [params.include_sides] - Include base/ours/theirs blobs.
   * @returns {Promise<Object>} `{ in_progress, operation, conflicts, ... }`.
   *
   * @example
   * const state = await api.repo.conflicts()
   * state.conflicts[0].markers // conflict blocks with ours/theirs text
   */
  conflicts({ include_content = true, include_sides = false } = {}) {
    return API.get(
      `/api/git/repo/conflicts${toQuery({
        include_content: include_content ? 1 : 0,
        include_sides: include_sides ? 1 : 0
      })}`
    )
  },

  /**
   * Resolve one conflicted file (manual resolution / side selection).
   *
   * @param {Object} params - Options.
   * @param {string} params.path - Conflicted file path.
   * @param {string} [params.content] - Full merged content (manual strategy).
   * @param {'manual'|'ours'|'theirs'|'stage'|'delete'} [params.strategy] -
   * Resolution strategy (`stage` keeps the file edited outside the view).
   * @param {boolean} [params.stage] - Stage the file after resolving it.
   * @param {boolean} [params.allow_markers] - Allow leftover conflict markers.
   * @returns {Promise<Object>} `{ success, path, resolved, remaining, state }`.
   *
   * @example
   * await api.repo.resolveConflict({ path, content: mergedText })
   * await api.repo.resolveConflict({ path, strategy: 'theirs' })
   */
  resolveConflict({
    path,
    content,
    strategy = 'manual',
    stage = true,
    allow_markers = false
  } = {}) {
    return API.post('/api/git/repo/conflicts/resolve', {
      path,
      content,
      strategy,
      stage,
      allow_markers
    }).then((result) => {
      invalidateDiffs(API)
      return result
    })
  },

  /**
   * Resolve conflicts with the project LLM.
   *
   * The backend sends the base/ours/theirs versions and the working tree
   * markers to the model, validates the answer (no leftover markers) and, when
   * `apply` is true, writes and stages the merged file. One failing file never
   * discards the resolutions already applied to the others.
   *
   * @param {Object} [params] - Options.
   * @param {string[]} [params.paths] - Conflicts to resolve (all when omitted).
   * @param {string} [params.instructions] - Guidance for the merge decision.
   * @param {boolean} [params.apply] - Write and stage the answers.
   * @param {boolean} [params.continue_operation] - Continue once all resolved.
   * @returns {Promise<Object>} `{ success, applied, files, continued, state }`.
   *
   * @example
   * const result = await api.repo.resolveConflictsWithAI({
   *   instructions: 'keep both logging calls'
   * })
   */
  resolveConflictsWithAI({
    paths,
    instructions,
    apply = true,
    continue_operation = false
  } = {}) {
    return API.post('/api/git/repo/conflicts/ai', {
      paths: paths?.length ? paths : null,
      instructions: instructions || null,
      apply,
      continue_operation
    }).then((result) => {
      invalidateDiffs(API)
      return result
    })
  },

  /**
   * Finish the pending merge/rebase/cherry-pick/revert.
   *
   * Every conflict must be resolved and staged first. A rebase may stop again
   * on the next commit; the answer then carries `conflicted = true`.
   *
   * @param {Object} [params] - Options.
   * @param {string} [params.message] - Merge commit message.
   * @returns {Promise<Object>} `{ success, operation, commit, conflicted, state }`.
   */
  continueOperation({ message } = {}) {
    return API.post('/api/git/repo/conflicts/continue', {
      message: message || null
    }).then((result) => {
      invalidateDiffs(API)
      return result
    })
  },

  /**
   * Abort the pending operation (destructive for the resolutions already made).
   *
   * @returns {Promise<Object>} `{ success, operation, state }`.
   */
  abortOperation() {
    return API.post('/api/git/repo/conflicts/abort', {}).then((result) => {
      invalidateDiffs(API)
      return result
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
      .then((result) => {
        invalidateDiffs(API)
        return result
      })
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
      .then((result) => {
        invalidateDiffs(API)
        return result
      })
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
   * A regular merge commit is created by default. Optional modes:
   * - `squash`: collapse every source commit into a single commit.
   * - `no_commit`: leave the merge result staged instead of committing it.
   *   Combining both stages a squashed merge without creating a commit.
   * - `delete_worktree`: remove the source branch worktree after merging.
   * - `delete_branch`: remove the source worktree (when present) and the branch.
   * - `keep_conflicts`: leave a conflicting merge in progress (default) instead
   *   of aborting it, so the conflict resolver can finish it. The result then
   *   carries `conflicted = true` and `conflict_state`.
   *
   * @param {Object} params - `{ from_branch, to_branch, message, delete_branch,
   * no_commit, squash, delete_worktree, keep_conflicts }`.
   * @returns {Promise<Object>} Operation result with `committed`, `squashed`,
   * `no_commit`, `up_to_date`, `conflicted` and `worktree_removed`.
   */
  merge({
    from_branch,
    to_branch,
    message,
    delete_branch = false,
    no_commit = false,
    squash = false,
    delete_worktree = false,
    keep_conflicts = true
  } = {}) {
    return API.post('/api/git/repo/merge', {
      from_branch,
      to_branch,
      message: message || undefined,
      delete_branch,
      no_commit,
      squash,
      delete_worktree,
      keep_conflicts
    }).then((result) => {
      // The merge changes the index / working tree (and, with no_commit, leaves
      // the result staged): cached file diffs must not survive it.
      invalidateDiffs(API)
      return result
    })
  },

  /**
   * Rebase a branch onto another one.
   *
   * Rewrites the history of the rebased branch, so the UI must confirm it
   * with the user first. A conflicting rebase is left in progress
   * (`keep_conflicts`, default true) for the conflict resolver.
   *
   * @param {Object} params - `{ onto_branch, branch, keep_conflicts }`;
   * `branch` defaults to the checked out branch.
   * @returns {Promise<Object>} `{ branch, onto_branch, commit, up_to_date,
   * conflicts, conflicted, conflict_state }`.
   *
   * @example
   * await api.repo.rebase({ onto_branch: 'main', branch: 'fix-login' })
   */
  rebase({ onto_branch, branch, keep_conflicts = true } = {}) {
    return API.post('/api/git/repo/rebase', {
      onto_branch,
      branch: branch || undefined,
      keep_conflicts
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