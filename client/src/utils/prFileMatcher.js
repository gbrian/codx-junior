/**
 * Pure helpers shared by the PR ↔ chat correlation.
 *
 * Three different path spaces meet when correlating a PR with chat history:
 *
 *   1. `repoChanges.repo_path`            → `/home/x/wt-feature` (may be "", a worktree, or a clone)
 *   2. `branch_file_and_commits` keys     → `client/src/App.vue` (always repo-relative)
 *   3. chat `file_list` / code-block paths → absolute, project-relative, or just a suffix
 *
 * Everything is compared after `toRepoRelative()`, with a suffix fallback so a
 * worktree root that differs from `repo_path` still matches, and a rename map so
 * `diff --git a/old b/new` keeps pointing at the file that is in the PR.
 */

/**
 * Normalize a path so the same file compares equal across all the sources.
 *
 * - strips wrapping quotes/backticks (paths are often inline-code in messages)
 * - Windows separators → posix
 * - removes `./` prefixes, duplicate and trailing slashes
 * - optionally strips the git `a/` `b/` prefix (only in a diff context: a real
 *   top level `a/` directory must not be mangled)
 */
export function normalizePath(path, { stripGitPrefix = false } = {}) {
  if (path === null || path === undefined) return ''
  let value = String(path).trim()
  if (!value) return ''

  value = value.replace(/^[`'"]+/, '').replace(/[`'"]+$/, '')
  value = value.replace(/\\/g, '/')
  if (stripGitPrefix) value = value.replace(/^[ab]\/(?=.)/, '')
  value = value.replace(/^(\.\/)+/, '')
  value = value.replace(/\/{2,}/g, '/')
  value = value.replace(/^\/+/, '').replace(/\/+$/, '')
  return value
}

/**
 * Resolve any path to a repository-relative path.
 *
 * Absolute paths are matched against the repository root, and when the root does
 * not match (worktrees, a different clone) the repository folder name is located
 * inside the path so `/anywhere/feature-x/src/a.py` still yields `src/a.py`.
 */
export function toRepoRelative(path, repoPath) {
  const target = normalizePath(path)
  if (!target) return ''
  const base = normalizePath(repoPath)
  if (!base) return target
  if (target === base) return ''
  if (target.startsWith(`${base}/`)) return target.slice(base.length + 1)

  const baseName = base.split('/').pop()
  if (baseName) {
    const marker = `/${baseName}/`
    const index = target.indexOf(marker)
    if (index >= 0) return target.slice(index + marker.length)
  }
  return target
}

/**
 * Build the lookup structure used to resolve any candidate path to a PR file.
 *
 * @param {string[]|Object} filePaths - repo-relative PR file paths (array or object keys)
 * @param {string} repoPath           - repository/worktree root as reported by the API (may be "")
 * @param {Object} renames            - { oldPath: newPath } map for renamed files
 */
export function createPrFileIndex(filePaths, repoPath = '', renames = {}) {
  const list = Array.isArray(filePaths) ? filePaths : Object.keys(filePaths || {})
  const root = String(repoPath || '').replace(/\/+$/, '')
  const files = new Map()
  const byBasename = new Map()

  list.forEach(rawPath => {
    const path = toRepoRelative(rawPath, root) || normalizePath(rawPath)
    if (!path) return
    const entry = {
      path,
      absPath: root ? `${root}/${path}` : path,
      basename: path.split('/').pop()
    }
    files.set(path, entry)
    byBasename.set(entry.basename, [...(byBasename.get(entry.basename) || []), entry])
  })

  return {
    repoPath: normalizePath(root),
    files,
    byBasename,
    renames: new Map(
      Object.entries(renames || {}).map(([from, to]) => [normalizePath(from), normalizePath(to)])
    )
  }
}

/**
 * Resolve a candidate path (from `file_list`, a code block header or a diff) to
 * one of the PR files. Returns `{ path, absPath, basename, how }` or `null`.
 *
 * `how` is `exact` | `rename` | `suffix` | `basename` and is kept so the UI can
 * explain *why* a chat was correlated with a file.
 */
export function matchPrFile(candidate, index) {
  if (!candidate || !index?.files?.size) return null

  const relative = toRepoRelative(candidate, index.repoPath) || normalizePath(candidate)
  if (!relative) return null

  const exact = index.files.get(relative)
  if (exact) return { ...exact, how: 'exact' }

  const renamed = index.renames.get(relative)
  if (renamed && index.files.has(renamed)) {
    return { ...index.files.get(renamed), how: 'rename' }
  }

  let suffixed = null
  index.files.forEach(entry => {
    if (suffixed) return
    if (relative.endsWith(`/${entry.path}`) || entry.path.endsWith(`/${relative}`)) {
      suffixed = { ...entry, how: 'suffix' }
    }
  })
  if (suffixed) return suffixed

  // A bare basename is only trusted when it is unambiguous in the PR
  const sameName = index.byBasename.get(relative.split('/').pop()) || []
  if (sameName.length === 1) return { ...sameName[0], how: 'basename' }

  return null
}

/**
 * Extract the file pairs named by a unified diff (`diff --git a/x b/y`,
 * `--- a/x`, `+++ b/y`). `/dev/null` sides are skipped so added/deleted files
 * still produce one usable path.
 */
export function extractDiffPaths(diffText) {
  if (!diffText) return []
  const results = []
  const seen = new Set()
  let current = null

  const flush = () => {
    if (current && (current.old || current.new)) {
      const key = `${current.old}>${current.new}`
      if (!seen.has(key)) {
        seen.add(key)
        results.push(current)
      }
    }
    current = null
  }

  String(diffText)
    .split('\n')
    .forEach(line => {
      if (line.startsWith('diff --git ')) {
        flush()
        const match = line.match(/^diff --git\s+a\/(.+?)\s+b\/(.+)$/)
        current = match
          ? { old: normalizePath(match[1]), new: normalizePath(match[2]) }
          : {}
        return
      }
      if (!current) return
      if (line.startsWith('--- ') && !current.old) {
        const value = line.slice(4).trim()
        if (!value.startsWith('/dev/null')) current.old = normalizePath(value, { stripGitPrefix: true })
      } else if (line.startsWith('+++ ') && !current.new) {
        const value = line.slice(4).trim()
        if (!value.startsWith('/dev/null')) current.new = normalizePath(value, { stripGitPrefix: true })
      }
    })

  flush()
  return results
}

/**
 * Canonical form of a file/code-block content used for equality checks:
 * line endings normalized, trailing whitespace removed, outer blanks trimmed.
 */
export function normalizeCodeContent(content) {
  if (content === null || content === undefined) return ''
  return String(content)
    .replace(/\r\n?/g, '\n')
    .split('\n')
    .map(line => line.replace(/[ \t]+$/, ''))
    .join('\n')
    .trim()
}

/**
 * Whether a chat code block and a file hold the same content.
 *
 * Trivial blocks (a single import, an empty file) are rejected: they match
 * almost everything and would produce false "this chat wrote the file" claims.
 */
export function isSameContent(a, b) {
  const first = normalizeCodeContent(a)
  const second = normalizeCodeContent(b)
  if (!first || !second) return false
  if (Math.min(first.length, second.length) < 24) return false
  return first === second
}