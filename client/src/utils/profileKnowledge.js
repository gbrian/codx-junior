/**
 * Shared "extra knowledge" helpers for profiles.
 *
 * A profile learns per project (backend:
 * `codx.junior.profiles.profile_manager.ProfileManager`). What it learns is
 * stored in two places, both resolved through the project inheritance chain
 * (base profile → parent projects → current project):
 *
 *   · RULES — `<project .codx>/profiles/<Name>/enrich.md`, composed into the
 *     profile content inside invisible markers:
 *     `<!-- codx:enrich project=<name> --> … <!-- /codx:enrich -->`.
 *     Every rule is a `## <title>` block (upserted by title).
 *   · KNOWLEDGE FILES — `<project .codx>/profiles/<Name>/knowledge/**`,
 *     indexed for semantic search.
 *
 * The composed content travels with the profile payload, so the rules of the
 * current project and of every parent level are already available to the UI:
 * this module turns them into one small, reusable summary so every card shows
 * the same indicator instead of duplicating the parsing.
 *
 * When the profiles API also exposes the knowledge summary (`profile.knowledge`,
 * `profile.knowledge_summary`, `profile.knowledge_rules` /
 * `profile.knowledge_files`), those numbers win: they are authoritative and
 * include the knowledge files, which are NOT part of the content.
 */

// Enrichment blocks injected by ProfileManager.compose_profile_content()
const ENRICH_BLOCK_PATTERN =
  /<!--\s*codx:enrich\s+project=([^\s>]+)\s*-->([\s\S]*?)<!--\s*\/codx:enrich\s*-->/gi

// A learned rule is a `## <title>` heading inside enrich.md
const RULE_HEADING_PATTERN = /^##\s+\S.*$/gm

/**
 * Empty summary (a fresh object every time so callers can spread it safely).
 *
 * @returns {{hasExtraKnowledge: boolean, rules: number, files: number, total: number, sources: string[], label: string, tooltip: string, fromApi: boolean}}
 */
export function emptyKnowledge() {
  return {
    hasExtraKnowledge: false,
    rules: 0,
    files: 0,
    total: 0,
    sources: [],
    label: '',
    tooltip: '',
    fromApi: false
  }
}

/**
 * Coerce a value into a positive integer count (0 when it cannot be used).
 *
 * @param {*} value - Raw value.
 * @returns {number} Rounded count, or 0.
 */
function toCount(value) {
  const number = Number(value)
  return Number.isFinite(number) && number > 0 ? Math.round(number) : 0
}

/**
 * Return the first usable count of the given candidates.
 *
 * @param {...*} values - Candidates (numbers or arrays).
 * @returns {number} Count, or 0 when none is usable.
 */
function firstCount(...values) {
  for (const value of values) {
    const count = Array.isArray(value) ? value.length : toCount(value)
    if (count) return count
  }
  return 0
}

/**
 * Count the rules (`## <title>` blocks) of one enrichment block.
 *
 * A block written by hand (no headings) still counts as one rule.
 *
 * @param {string} text - Enrichment block content.
 * @returns {number} Number of rules.
 */
function countRules(text) {
  const content = String(text || '')
  const headings = content.match(RULE_HEADING_PATTERN)
  if (headings && headings.length) return headings.length
  return content.trim() ? 1 : 0
}

/**
 * Read the learned rules out of the composed profile content.
 *
 * @param {string} content - Composed content (enrichment markers included).
 * @returns {{rules: number, sources: string[]}} Rules and the projects that
 *          learned them (outermost parent first).
 */
function readEnrichment(content) {
  const text = String(content || '')
  if (!text.includes('codx:enrich')) {
    return { rules: 0, sources: [] }
  }

  const sources = []
  let rules = 0
  let match
  // The pattern is module-level and stateful: always restart the scan.
  ENRICH_BLOCK_PATTERN.lastIndex = 0
  while ((match = ENRICH_BLOCK_PATTERN.exec(text)) !== null) {
    const projectName = (match[1] || 'project').trim()
    if (projectName && !sources.includes(projectName)) {
      sources.push(projectName)
    }
    rules += countRules(match[2])
  }
  return { rules, sources }
}

/**
 * Read the knowledge summary when the backend already provides it.
 *
 * Accepts the shapes an API can reasonably expose:
 *   `profile.knowledge = { rules, files, levels: [{ source, rules, files }] }`
 *   `profile.knowledge_summary = { rules_count, files_count }`
 *   `profile.knowledge_rules` / `profile.knowledge_files`
 *
 * @param {Object} profile - Profile payload.
 * @returns {{rules: number, files: number, sources: string[]}} Explicit counts.
 */
function readExplicitKnowledge(profile) {
  const summary = profile.knowledge || profile.knowledge_summary || {}
  const rules = firstCount(
    summary.rules,
    summary.rules_count,
    profile.knowledge_rules
  )
  const files = firstCount(
    summary.files,
    summary.files_count,
    summary.knowledge_files,
    profile.knowledge_files
  )
  const levels = Array.isArray(summary.levels) ? summary.levels : []
  const sources = levels
    .map(level => (level && (level.source || level.project)) || '')
    .filter(Boolean)

  return { rules, files, sources: [...new Set(sources)] }
}

/**
 * Summarize the extra knowledge a profile has for the current project.
 *
 * @param {Object} profile - Profile payload as returned by the profiles API.
 * @returns {{hasExtraKnowledge: boolean, rules: number, files: number, total: number, sources: string[], label: string, tooltip: string, fromApi: boolean}}
 *
 * @example
 * profileKnowledgeInfo({ content: '…<!-- codx:enrich project=demo -->\n## A\n…' })
 * // → { hasExtraKnowledge: true, rules: 1, files: 0, total: 1,
 * //     sources: ['demo'], label: '1 rule',
 * //     tooltip: 'Extra knowledge: 1 rule — learned in demo', fromApi: false }
 */
export function profileKnowledgeInfo(profile) {
  if (!profile) return emptyKnowledge()

  const explicit = readExplicitKnowledge(profile)
  const fromApi = explicit.rules > 0 || explicit.files > 0

  // The API payload is authoritative; otherwise fall back to the enrichment
  // blocks that the content already carries (knowledge files are not there).
  const inferred = fromApi
    ? { rules: 0, sources: [] }
    : readEnrichment(profile.content || profile.parsed_content)

  const rules = fromApi ? explicit.rules : inferred.rules
  const files = explicit.files
  const total = rules + files
  if (!total) return emptyKnowledge()

  const sources = [...new Set([...explicit.sources, ...inferred.sources])]

  const parts = []
  if (rules) parts.push(`${rules} rule${rules === 1 ? '' : 's'}`)
  if (files) parts.push(`${files} file${files === 1 ? '' : 's'}`)
  const label = parts.join(' · ')

  const tooltip = [
    `Extra knowledge: ${label}`,
    sources.length ? `learned in ${sources.join(', ')}` : ''
  ].filter(Boolean).join(' — ')

  return {
    hasExtraKnowledge: true,
    rules,
    files,
    total,
    sources,
    label,
    tooltip,
    fromApi
  }
}

/**
 * Convenience predicate: does this profile have extra knowledge?
 *
 * @param {Object} profile - Profile payload.
 * @returns {boolean} True when it learned rules or has knowledge files.
 */
export function hasExtraKnowledge(profile) {
  return profileKnowledgeInfo(profile).hasExtraKnowledge
}

export default profileKnowledgeInfo

// Made with ❤️ by codx-junior