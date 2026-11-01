/**
 * Profile knowledge client.
 *
 * Thin REST wrapper over the profile knowledge endpoints
 * (`codx/junior/profiles/profile_knowledge_api.py`), which expose what
 * `ProfileManager` already knows: the learned **rules** (`enrich.md`) and the
 * **knowledge files** (`knowledge/**`) of a profile for the current project.
 *
 * The API base is read from `window.CODX_API_BASE` so the UI works both served
 * by the API (empty value) and from a different origin / dev server.
 *
 * Made with ❤️ by codx-junior
 */

const API_BASE = (typeof window !== 'undefined' && window.CODX_API_BASE) || ''
const KNOWLEDGE_PATH = '/profiles/knowledge'

/** Promote a rule into an indexed knowledge file. */
export const RULE_TO_FILE = 'rule_to_file'

/** Promote a knowledge file into a short rule (always injected in the prompt). */
export const FILE_TO_RULE = 'file_to_rule'

/**
 * Read the auth token used by the API (`authentication` header).
 *
 * @return {string} Token or empty string.
 */
function getToken() {
  try {
    return (
      window.localStorage.getItem('authentication') ||
      window.localStorage.getItem('token') ||
      ''
    )
  } catch (ex) {
    return ''
  }
}

/**
 * Build the request URL with its query string.
 *
 * @param {string} path Endpoint path.
 * @param {Object} query Query parameters (empty values are skipped).
 * @return {string} Absolute URL.
 */
function buildUrl(path, query) {
  const params = new URLSearchParams()
  Object.entries(query || {}).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') {
      return
    }
    params.append(key, value)
  })
  const search = params.toString()
  return search ? `${API_BASE}${path}?${search}` : `${API_BASE}${path}`
}

/**
 * Parse a JSON body without throwing on plain-text error pages.
 *
 * @param {string} text Raw response body.
 * @return {Object} Parsed payload.
 */
function safeParse(text) {
  try {
    return JSON.parse(text)
  } catch (ex) {
    return { detail: text }
  }
}

/**
 * Perform a JSON request and normalize errors.
 *
 * @param {string} path Endpoint path.
 * @param {Object} options `method`, `query` and `body`.
 * @return {Promise<Object>} Parsed response payload.
 */
async function request(path, options = {}) {
  const { method = 'GET', query, body } = options
  const headers = { 'Content-Type': 'application/json', Accept: 'application/json' }
  const token = getToken()
  if (token) {
    headers.authentication = token
  }

  const response = await fetch(buildUrl(path, query), {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body)
  })

  const text = await response.text()
  const payload = text ? safeParse(text) : {}

  if (!response.ok) {
    const detail = (payload && (payload.detail || payload.message)) || response.statusText
    throw new Error(detail || `Request failed (${response.status})`)
  }

  return payload
}

/**
 * Normalize a knowledge file name: relative and always with a text extension.
 *
 * Mirrors `ProfileManager._validate_knowledge_file_name`, so the UI can show
 * the name the server will actually use (e.g. `guidelines/state` -> `.md`).
 *
 * @param {string} fileName Raw file name typed by the user.
 * @return {string} Normalized file name.
 */
export function normalizeFileName(fileName) {
  const name = (fileName || '').trim().replace(/^\/+/, '')
  if (!name) {
    return ''
  }
  return /\.[a-z0-9]+$/i.test(name) ? name : `${name}.md`
}

/**
 * Load what a profile has learned for a project.
 *
 * @param {Object} params `profileName` and `projectId`.
 * @return {Promise<Object>} Overview: `rules`, `knowledge_files`, `limits`, `can_write`, ...
 */
export function fetchProfileKnowledge({ profileName, projectId }) {
  return request(KNOWLEDGE_PATH, {
    query: { profile_name: profileName, project_id: projectId }
  })
}

/**
 * Read one knowledge file.
 *
 * @param {Object} params `profileName`, `projectId` and `fileName`.
 * @return {Promise<Object>} `{ file, path, source, content }`.
 */
export function readKnowledgeFile({ profileName, projectId, fileName }) {
  return request(`${KNOWLEDGE_PATH}/file`, {
    query: {
      profile_name: profileName,
      project_id: projectId,
      file_name: fileName
    }
  })
}

/**
 * Create or update a knowledge file.
 *
 * @param {Object} params `profileName`, `projectId`, `fileName`, `content`, `overwrite`.
 * @return {Promise<Object>} `{ file, path }`.
 */
export function saveKnowledgeFile({
  profileName,
  projectId,
  fileName,
  content,
  overwrite = false
}) {
  return request(`${KNOWLEDGE_PATH}/file`, {
    method: 'PUT',
    body: {
      profile_name: profileName,
      project_id: projectId,
      file_name: fileName,
      content,
      overwrite
    }
  })
}

/**
 * Delete a knowledge file owned by the project.
 *
 * @param {Object} params `profileName`, `projectId` and `fileName`.
 * @return {Promise<Object>} `{ file, path }`.
 */
export function deleteKnowledgeFile({ profileName, projectId, fileName }) {
  return request(`${KNOWLEDGE_PATH}/file`, {
    method: 'DELETE',
    query: {
      profile_name: profileName,
      project_id: projectId,
      file_name: fileName
    }
  })
}

/**
 * Create or replace a rule (upsert by title).
 *
 * @param {Object} params `profileName`, `projectId`, `title` and `content`.
 * @return {Promise<Object>} `{ title, path, created, rules }`.
 */
export function saveProfileRule({ profileName, projectId, title, content }) {
  return request(`${KNOWLEDGE_PATH}/rule`, {
    method: 'PUT',
    body: {
      profile_name: profileName,
      project_id: projectId,
      title,
      content
    }
  })
}

/**
 * Forget a rule learned by the project.
 *
 * @param {Object} params `profileName`, `projectId` and `title`.
 * @return {Promise<Object>} `{ title, path }`.
 */
export function deleteProfileRule({ profileName, projectId, title }) {
  return request(`${KNOWLEDGE_PATH}/rule`, {
    method: 'DELETE',
    query: { profile_name: profileName, project_id: projectId, title }
  })
}

/**
 * Move content between the two stores.
 *
 * @param {Object} params `profileName`, `projectId`, `direction`, `title`, `fileName`, `keepSource`.
 * @return {Promise<Object>} Promotion result.
 */
export function promoteProfileKnowledge({
  profileName,
  projectId,
  direction,
  title,
  fileName,
  keepSource = false
}) {
  return request(`${KNOWLEDGE_PATH}/promote`, {
    method: 'POST',
    body: {
      profile_name: profileName,
      project_id: projectId,
      direction,
      title,
      file_name: fileName,
      keep_source: keepSource
    }
  })
}

// Made with ❤️ by codx-junior