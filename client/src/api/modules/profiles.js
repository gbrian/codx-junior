/**
 * Profiles API module
 *
 * Covers the profile endpoints of the active project:
 *   - definition CRUD (list, load, save, delete, available tools)
 *   - profile knowledge: the **rules** (`enrich.md`) and the **knowledge files**
 *     (`knowledge/**`) that a profile has learned for the project, plus the
 *     promotion between both stores.
 *
 * Mirrors the backend router `codx/junior/api/profiles.py` (auto-discovered and
 * mounted under `/api`). Every call is scoped by `codx_path`, which the
 * connection layer appends automatically (`connection.prepareUrl`), so the
 * module must be built over the API instance of the profile's project:
 *
 * @example
 * const api = await $storex.api.project(project)
 * const profiles = profilesModule(api)
 * const overview = await profiles.knowledge('software_developer')
 *
 * Convention (same as the backend):
 *   - the profile is part of the path: `/api/profiles/{profile}/knowledge/...`
 *   - `PUT` creates **and** updates
 *   - `DELETE` sends the resource name as a query parameter (a DELETE body is
 *     not reliably forwarded by proxies and interceptors)
 */

/** Promote a rule into an indexed knowledge file (it stops costing prompt tokens). */
export const RULE_TO_FILE = 'rule_to_file'

/** Promote a knowledge file into a short rule (always injected in the prompt). */
export const FILE_TO_RULE = 'file_to_rule'

/**
 * Build the base path of a profile resource.
 * @param {string} profileName - Profile name.
 * @returns {string} `/api/profiles/{profile}`
 */
const profilePath = (profileName) =>
  `/api/profiles/${encodeURIComponent((profileName || '').trim())}`

/**
 * Normalize a knowledge file name: relative and always with a text extension.
 *
 * Mirrors `ProfileManager._validate_knowledge_file_name`, so the UI shows the
 * name the server will actually use (`guidelines/state` -> `guidelines/state.md`).
 * @param {string} fileName - Raw file name typed by the user.
 * @returns {string} Normalized file name.
 */
export function normalizeFileName(fileName) {
  const name = (fileName || '').trim().replace(/^\/+/, '')
  if (!name) {
    return ''
  }
  return /\.[a-z0-9]+$/i.test(name) ? name : `${name}.md`
}

/**
 * Build the profiles API bound to one API instance.
 * @param {Object} API - API instance (active project or a project-scoped one).
 * @returns {Object} Profiles API.
 */
export const profilesModule = (API) => ({
  // ── Profile definition ───────────────────────────────────────────────────

  /**
   * List every profile visible from the project (project, inherited and base).
   * @returns {Promise<Object[]>}
   */
  list() {
    return API.get('/api/profiles')
  },

  /**
   * Load one profile by name.
   * @param {string} name - Profile name.
   * @returns {Promise<Object>}
   */
  load(name) {
    return API.get(profilePath(name))
  },

  /**
   * Create or update a profile definition.
   * @param {Object} profile - Profile payload (`name` is required).
   * @returns {Promise<Object>}
   */
  save(profile) {
    return API.post('/api/profiles', profile)
  },

  /**
   * Delete a profile (its enrichment and knowledge files go with it).
   * @param {string} name - Profile name.
   * @returns {Promise<void>}
   */
  async delete(name) {
    await API.del(profilePath(name))
  },

  /**
   * List the tool names available to profiles.
   * @returns {Promise<string[]>}
   */
  tools() {
    return API.get('/api/profiles/tools')
  },

  // ── Learned knowledge ────────────────────────────────────────────────────

  /**
   * What the profile has learned for this project: rules, knowledge files,
   * limits and whether the current user may edit them (`can_write`).
   * @param {string} name - Profile name.
   * @returns {Promise<Object>} `{ rules, knowledge_files, limits, can_write, ... }`
   */
  knowledge(name) {
    return API.get(`${profilePath(name)}/knowledge`)
  },

  /**
   * Read one knowledge file (base profile or any project level).
   * @param {string} name - Profile name.
   * @param {string} fileName - Path relative to the knowledge folder.
   * @returns {Promise<Object>} `{ file, source, path, content }`
   */
  readKnowledgeFile(name, fileName) {
    return API.get(
      `${profilePath(name)}/knowledge/files?file_name=${encodeURIComponent(fileName)}`
    )
  },

  /**
   * Create or update a knowledge file in the current project.
   * @param {string} name - Profile name.
   * @param {Object} payload - `{ fileName, content, overwrite }`
   * @returns {Promise<Object>} `{ file, path }`
   */
  saveKnowledgeFile(name, { fileName, content, overwrite = false }) {
    return API.put(`${profilePath(name)}/knowledge/files`, {
      file_name: fileName,
      content,
      overwrite
    })
  },

  /**
   * Delete a knowledge file owned by the current project.
   * Base and parent project files are read-only and rejected by the server.
   * @param {string} name - Profile name.
   * @param {string} fileName - Path relative to the knowledge folder.
   * @returns {Promise<Object>} `{ file, path }`
   */
  deleteKnowledgeFile(name, fileName) {
    return API.delete(
      `${profilePath(name)}/knowledge/files?file_name=${encodeURIComponent(fileName)}`
    )
  },

  /**
   * Create or replace a rule (upsert by title: writing an existing title
   * replaces that rule instead of adding a duplicate).
   * @param {string} name - Profile name.
   * @param {Object} payload - `{ title, content }`
   * @returns {Promise<Object>} `{ title, created, rules, path }`
   */
  saveRule(name, { title, content }) {
    return API.put(`${profilePath(name)}/knowledge/rules`, { title, content })
  },

  /**
   * Forget a rule learned by the current project.
   * @param {string} name - Profile name.
   * @param {string} title - Rule title.
   * @returns {Promise<Object>} `{ title, path }`
   */
  deleteRule(name, title) {
    return API.delete(
      `${profilePath(name)}/knowledge/rules?title=${encodeURIComponent(title)}`
    )
  },

  /**
   * Move content between the two stores.
   * @param {string} name - Profile name.
   * @param {Object} payload - `{ direction, title, fileName, keepSource }`
   *   `direction` is `RULE_TO_FILE` or `FILE_TO_RULE`.
   * @returns {Promise<Object>} Promotion result (`direction`, `title`, `path`, ...)
   */
  promote(name, { direction, title, fileName, keepSource = false }) {
    return API.post(`${profilePath(name)}/knowledge/promote`, {
      direction,
      title,
      file_name: fileName,
      keep_source: keepSource
    })
  }
})

// Made with ❤️ by codx-junior