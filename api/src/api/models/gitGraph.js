/**
 * Git graph models — client-side definitions for the repository graph view.
 *
 * Mirrors the backend payload of `GET /api/git/repo/graph`
 * (`codx/junior/engine/git_graph.py::GitGraphEngine.get_repo_graph`):
 *
 * ```json
 * {
 *   "default_branch": "main",
 *   "active_branch": "codx-junior/fix-login",
 *   "branches": [{ "name": "main", "type": "local", "commit": "a2d3b55" }],
 *   "commits": [{
 *     "hash": "a2d3b55",
 *     "parents": ["3b5a11ec"],
 *     "subject": "Merge pull request #14198",
 *     "author": { "name": "Marius Wenzel", "email": "mw@example.com" },
 *     "date": "2019-09-03T23:27:00Z",
 *     "refs": [{ "name": "upstream/main", "type": "remote" }]
 *   }]
 * }
 * ```
 *
 * Model hierarchy
 * ---------------
 *  Graph
 *  ├── rows        GraphRow[]   one row per commit, already laid out
 *  ├── laneCount   number       number of lanes to reserve
 *  ├── commits     GitCommit[]  normalized commits
 *  ├── defaultBranch / activeBranch string
 *  └── branches    GitRef[]     refs with the commit they point to
 *
 *  GraphRow
 *  ├── commit      GitCommit
 *  ├── lane        number       column of the commit node
 *  ├── color       string       lane color
 *  ├── before      number[]     lanes arriving from the row above
 *  ├── after       number[]     lanes continuing below
 *  └── edges       GraphEdge[]  geometry primitives to draw
 *
 *  GraphEdge
 *  ├── fromLane / toLane  number
 *  ├── fromY / toY        number   0 = top, 0.5 = node, 1 = bottom
 *  └── color              string
 *
 *  GitCommit
 *  ├── hash / short   string
 *  ├── subject / body string
 *  ├── author         { name, email }
 *  ├── date           ISO-8601 string
 *  ├── parents        string[]
 *  ├── refs           GitRef[]
 *  └── isMerge / isHead / isRemote boolean
 *
 *  GitRef
 *  ├── name    string   branch or tag name (remote prefix kept: "origin/main")
 *  ├── type    "local" | "remote" | "tag" | "head"
 *  └── isHead? boolean  set on the ref matching the checked out branch
 *
 * Nothing here performs requests: the module (`api/modules/repo.js`) owns the
 * transport and this file only normalizes what the API returns.
 */

/** Height in pixels of a graph row (matches the 8pt grid: 24 + 2 hairline). */
export const GRAPH_ROW_HEIGHT = 26

/** Horizontal spacing between two graph lanes. */
export const GRAPH_LANE_WIDTH = 14

/** Lane colors, indexed by lane so a branch keeps its color along the graph. */
export const GRAPH_LANE_COLORS = [
  '#6366f1', // indigo (primary)
  '#10b981', // success
  '#f59e0b', // warning
  '#3b82f6', // info
  '#ec4899', // pink
  '#a855f7', // purple
  '#14b8a6', // teal
  '#f97316' // orange
]

/** Valid ref types. */
export const GIT_REF_TYPES = /** @type {('local'|'remote'|'tag'|'head')[]} */ ([
  'local',
  'remote',
  'tag',
  'head'
])

/** Remote prefixes used to detect remote-tracking branches by name. */
const REMOTE_PREFIXES = ['origin/', 'upstream/']

/**
 * Color of a lane.
 *
 * @param {number} lane - Lane index.
 * @returns {string} CSS color.
 *
 * @example
 * laneColor(1) // '#10b981'
 */
export function laneColor(lane = 0) {
  const index = Math.abs(Number(lane) || 0) % GRAPH_LANE_COLORS.length
  return GRAPH_LANE_COLORS[index]
}

/**
 * Whether a branch name looks like a remote-tracking branch.
 *
 * @param {string} name - Branch name, e.g. "origin/main".
 * @returns {boolean}
 */
export function isRemoteBranch(name = '') {
  return REMOTE_PREFIXES.some((prefix) => String(name).startsWith(prefix))
}

// ── Normalization ───────────────────────────────────────────────────────────

/**
 * Normalize the different parent shapes a backend may return.
 *
 * Accepts `parents: ["a", "b"]`, `parent: "a"`, `parents: [{ hash: "a" }]`
 * and the `%P` style `"a b"` string.
 *
 * @param {Object} raw - Raw commit object.
 * @returns {string[]} Parent hashes.
 */
function normalizeParents(raw = {}) {
  const value = raw.parents ?? raw.parent ?? raw.parent_hashes ?? []
  if (Array.isArray(value)) {
    return value
      .map((parent) => (typeof parent === 'string' ? parent : parent?.hash || parent?.commit || ''))
      .filter(Boolean)
  }
  if (typeof value === 'string') {
    return value.split(/\s+/).filter(Boolean)
  }
  return []
}

/**
 * Normalize a single ref (string or object) into a typed ref.
 *
 * @param {string|Object} entry - Ref name or `{ name, type, commit }`.
 * @returns {{name: string, type: string, remote: string}}
 */
export function normalizeRef(entry) {
  const ref = typeof entry === 'string' ? { name: entry } : entry || {}
  const name = String(ref.name || ref.branch || ref.ref || '')
    .replace(/^refs\/heads\//, '')
    .replace(/^refs\/remotes\//, '')
    .replace(/^refs\/tags\//, '')
    .replace(/^remotes\//, '')
    .replace(/^[*+\s]+/, '')
    .trim()

  const type = ref.type || (ref.tag ? 'tag' : isRemoteBranch(name) ? 'remote' : 'local')
  return { name, type, remote: ref.remote || '' }
}

/**
 * Normalize a list of refs.
 *
 * @param {Array|string|Object} refs - One ref or a list of refs.
 * @returns {Array<{name: string, type: string}>} Normalized refs.
 */
export function normalizeRefs(refs = []) {
  const list = Array.isArray(refs) ? refs : [refs]
  return list
    .filter(Boolean)
    .map(normalizeRef)
    .filter((ref) => !!ref.name)
}

/**
 * Normalize a raw commit (git log line, backend dict, mock object).
 *
 * @param {Object} raw - Raw commit.
 * @param {Object} [options] - Options.
 * @param {Object} [options.refsByHash] - Refs keyed by commit hash.
 * @returns {Object} Normalized commit.
 *
 * @example
 * normalizeCommit({ hash: 'abc123', subject: 'fix: login', author: { name: 'me' } })
 */
export function normalizeCommit(raw = {}, { refsByHash = {} } = {}) {
  const hash = raw.hash || raw.commit || raw.commit_id || raw.id || ''
  const parents = normalizeParents(raw)
  const author =
    typeof raw.author === 'object' && raw.author !== null
      ? { name: raw.author.name || '', email: raw.author.email || '' }
      : { name: raw.author || raw.author_name || '', email: raw.email || raw.author_email || '' }

  const date = raw.date || raw.committed_date || raw.authored_date || ''
  const message = String(raw.subject || raw.message || raw.comment || '')
  const lines = message.split('\n')
  const refs = normalizeRefs([...(raw.refs || []), ...(refsByHash[hash] || [])])

  return {
    hash,
    short: raw.short_commit || raw.short || hash.slice(0, 8),
    subject: (lines[0] || '').trim(),
    body: lines.slice(1).join('\n').trim(),
    author,
    date,
    parents,
    refs,
    isMerge: parents.length > 1,
    isHead: refs.some((ref) => ref.type === 'head' || ref.isHead),
    isRemote: refs.length > 0 && refs.every((ref) => ref.type === 'remote')
  }
}

/**
 * Group refs by commit hash.
 *
 * @param {Array} refs - `[{ name, type, commit }]`.
 * @returns {Object} Map of hash -> refs.
 */
export function buildRefsByHash(refs = []) {
  const map = {}
  ;(Array.isArray(refs) ? refs : []).forEach((entry) => {
    const ref = typeof entry === 'string' ? { name: entry } : entry || {}
    const hash = ref.commit || ref.hash || ref.target || ''
    if (!hash) return
    map[hash] = [...(map[hash] || []), ...normalizeRefs([ref])]
  })
  return map
}

/**
 * Flag the commit holding the checked out branch as `HEAD`.
 *
 * @param {Object[]} commits - Normalized commits.
 * @param {string} activeBranch - Checked out branch name.
 * @returns {Object[]} The same commits, with `isHead` updated.
 */
export function applyHead(commits = [], activeBranch = '') {
  if (!activeBranch) return commits
  commits.forEach((commit) => {
    commit.refs = (commit.refs || []).map((ref) => {
      if (ref.type === 'local' && ref.name === activeBranch) {
        return { ...ref, isHead: true }
      }
      return ref
    })
    commit.isHead = commit.isHead || commit.refs.some((ref) => ref.isHead)
  })
  return commits
}

// ── Layout ──────────────────────────────────────────────────────────────────

/** Occupied lane indexes of a lanes array. */
const laneIndexes = (lanes = []) =>
  lanes.map((hash, lane) => (hash ? lane : -1)).filter((lane) => lane >= 0)

/**
 * Lay out commits as a graph (lane assignment + edge geometry).
 *
 * Commits must be ordered newest → oldest (the order of `git log`). Lanes are
 * assigned so a commit keeps the lane of its first parent, and every merge
 * parent gets (or joins) another lane.
 *
 * @param {Object[]} rawCommits - Commits, newest first.
 * @param {Object} [options] - Options.
 * @param {Object} [options.refsByHash] - Refs keyed by commit hash.
 * @param {string} [options.activeBranch] - Branch checked out in the repo.
 * @returns {{rows: Object[], laneCount: number, commits: Object[]}} Layout.
 *
 * @example
 * const { rows, laneCount } = buildGraphLayout([{ hash: 'a', parents: ['b'] }, { hash: 'b' }])
 * rows[0].lane // 0
 */
export function buildGraphLayout(rawCommits = [], options = {}) {
  const { refsByHash = {}, activeBranch = '' } = options
  const commits = applyHead(
    rawCommits.map((raw) => normalizeCommit(raw, { refsByHash })),
    activeBranch
  )

  const lanes = []
  const rows = []
  let laneCount = 1

  commits.forEach((commit, index) => {
    // Lanes arriving from the row above (before the commit consumes one)
    const before = laneIndexes(lanes)
    // Every lane already waiting for this commit converges on its node
    const incoming = []
    lanes.forEach((hash, lane) => {
      if (hash && hash === commit.hash) incoming.push(lane)
    })

    let lane = incoming.length ? incoming[0] : lanes.indexOf(null)
    if (lane < 0) {
      lanes.push(null)
      lane = lanes.length - 1
    }
    incoming.forEach((value) => {
      lanes[value] = null
    })
    lanes[lane] = null

    // First parent continues the commit lane, merge parents join another lane
    const parentLanes = []
    commit.parents.forEach((parent, position) => {
      if (!parent) return
      const existing = lanes.indexOf(parent)
      if (existing >= 0) {
        parentLanes.push(existing)
        return
      }
      let target = position === 0 ? lane : lanes.indexOf(null)
      if (target < 0 || lanes[target]) {
        target = lanes.indexOf(null)
      }
      if (target < 0) {
        lanes.push(null)
        target = lanes.length - 1
      }
      lanes[target] = parent
      parentLanes.push(target)
    })

    // Drop trailing free lanes so the graph does not grow without reason
    while (lanes.length && lanes[lanes.length - 1] === null) lanes.pop()

    const after = laneIndexes(lanes)
    const edges = []

    // Lanes passing through this row
    after.forEach((value) => {
      if (value !== lane && before.includes(value)) {
        edges.push({
          fromLane: value,
          fromY: 0,
          toLane: value,
          toY: 1,
          color: laneColor(value)
        })
      }
    })
    // Lanes feeding the commit node
    incoming.forEach((value) => {
      edges.push({
        fromLane: value,
        fromY: 0,
        toLane: lane,
        toY: 0.5,
        color: laneColor(value)
      })
    })
    // Parents leaving the commit node
    parentLanes.forEach((value) => {
      edges.push({
        fromLane: lane,
        fromY: 0.5,
        toLane: value,
        toY: 1,
        color: laneColor(value)
      })
    })

    const maxLane = Math.max(lane, 0, ...before, ...after)
    laneCount = Math.max(laneCount, maxLane + 1)

    rows.push({
      index,
      commit,
      lane,
      color: laneColor(lane),
      incoming,
      before,
      after,
      parentLanes,
      edges,
      maxLane
    })
  })

  return { rows, laneCount, commits }
}

/**
 * Keep only the commits reachable from a branch/tag ref.
 *
 * Parents outside of the reachable set are dropped, so re-laying out the
 * result produces a clean, linear graph for the selected branch.
 *
 * @param {Object[]} commits - Normalized commits.
 * @param {string} refName - Ref to walk from (`''` returns every commit).
 * @returns {Object[]} Reachable commits.
 *
 * @example
 * filterCommitsByRef(commits, 'origin/main')
 */
export function filterCommitsByRef(commits = [], refName = '') {
  if (!refName) return commits

  const byHash = new Map(commits.map((commit) => [commit.hash, commit]))
  const reachable = new Set()
  const stack = commits
    .filter((commit) => (commit.refs || []).some((ref) => ref.name === refName))
    .map((commit) => commit.hash)

  while (stack.length) {
    const hash = stack.pop()
    if (!hash || reachable.has(hash) || !byHash.has(hash)) continue
    reachable.add(hash)
    ;(byHash.get(hash).parents || []).forEach((parent) => stack.push(parent))
  }

  return commits
    .filter((commit) => reachable.has(commit.hash))
    .map((commit) => ({
      ...commit,
      parents: (commit.parents || []).filter((parent) => reachable.has(parent))
    }))
}

/**
 * Normalize a `/api/git/repo/graph` payload into rows + commits.
 *
 * @param {Object|Object[]} payload - `{ commits, branches, ... }` or an array of commits.
 * @param {Object} [options] - Options.
 * @param {string} [options.activeBranch] - Overrides `payload.active_branch`.
 * @returns {Object} Graph model.
 */
export function normalizeGraphPayload(payload = {}, options = {}) {
  const commits = Array.isArray(payload) ? payload : payload.commits || payload.rows || []
  const activeBranch = options.activeBranch || payload.active_branch || ''
  const refsByHash = buildRefsByHash(
    payload.refs || payload.branch_refs || payload.branches || []
  )
  const layout = buildGraphLayout(commits, { refsByHash, activeBranch })

  return {
    rows: layout.rows,
    laneCount: layout.laneCount,
    commits: layout.commits,
    branches: payload.branches || [],
    defaultBranch: payload.default_branch || '',
    activeBranch
  }
}

export default {
  GRAPH_ROW_HEIGHT,
  GRAPH_LANE_WIDTH,
  GRAPH_LANE_COLORS,
  laneColor,
  isRemoteBranch,
  normalizeRef,
  normalizeRefs,
  normalizeCommit,
  buildRefsByHash,
  applyHead,
  buildGraphLayout,
  filterCommitsByRef,
  normalizeGraphPayload
}