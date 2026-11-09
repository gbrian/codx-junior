/**
 * Companies API module.
 *
 * Thin client over `/api/companies/*` (see `codx/junior/api/company.py`).
 *
 * A company is the top-level entity above projects: it owns an organization
 * (departments/functions), hybrid teams of humans **and** AI profiles, the
 * linked projects and the missions being executed. The server owns validation,
 * journaling, dispatch and autonomy; this module only shapes the requests.
 *
 * Notes
 * -----
 * • Company endpoints are global (not project-scoped). The API layer still
 *   appends `codx_path` to every request, which the backend ignores for these
 *   routes.
 * • `DELETE` membership is sent as a comma separated `members` query parameter
 *   because some proxies drop DELETE bodies; the router accepts that form.
 * • No caching: every mutation is followed by a snapshot reload, and a short TTL
 *   would serve stale counters back.
 */

const BASE = '/api/companies'

/**
 * Build a query string, skipping empty values.
 * @param {Object} params
 * @returns {string} `?a=1&b=2` or `''`.
 */
function toQuery(params = {}) {
  const search = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') return
    search.set(key, String(value))
  })
  const query = search.toString()
  return query ? `?${query}` : ''
}

/** Join a member reference the backend understands. */
export function memberRef(member) {
  if (!member) return ''
  if (typeof member === 'string') return member
  return `${member.kind || 'profile'}:${member.name || ''}`
}

export const companiesModule = (API) => ({
  // ── Companies ────────────────────────────────────────────────────────────

  /** List every company (summary payload). */
  list({ includeArchived = true } = {}) {
    return API.get(`${BASE}${toQuery({ include_archived: includeArchived })}`)
  },

  /** Discovered projects, users and AI profiles for the pickers. */
  references({ projectId } = {}) {
    return API.get(`${BASE}/references${toQuery({ project_id: projectId })}`)
  },

  /** One company document. */
  get(companyId) {
    return API.get(`${BASE}/${encodeURIComponent(companyId)}`)
  },

  /** Create a company (optionally from the `saas` template). */
  create(payload) {
    return API.post(BASE, payload)
  },

  /** Update company-level fields. */
  update(companyId, payload) {
    return API.put(`${BASE}/${encodeURIComponent(companyId)}`, payload)
  },

  /** Delete a company and its journal. */
  remove(companyId) {
    return API.delete(`${BASE}/${encodeURIComponent(companyId)}`)
  },

  /** Dashboard payload: counts, teams, projects, missions, attention, journal. */
  snapshot(companyId, { journalLimit = 30 } = {}) {
    return API.get(
      `${BASE}/${encodeURIComponent(companyId)}/snapshot${toQuery({ journal_limit: journalLimit })}`
    )
  },

  /** Audit journal (newest last). */
  journal(companyId, { limit = 100 } = {}) {
    return API.get(
      `${BASE}/${encodeURIComponent(companyId)}/journal${toQuery({ limit })}`
    )
  },

  // ── Organization ─────────────────────────────────────────────────────────

  addOrgUnit(companyId, payload) {
    return API.post(`${BASE}/${encodeURIComponent(companyId)}/org-units`, payload)
  },

  updateOrgUnit(companyId, unitId, payload) {
    return API.put(
      `${BASE}/${encodeURIComponent(companyId)}/org-units/${encodeURIComponent(unitId)}`,
      payload
    )
  },

  deleteOrgUnit(companyId, unitId) {
    return API.delete(
      `${BASE}/${encodeURIComponent(companyId)}/org-units/${encodeURIComponent(unitId)}`
    )
  },

  // ── Teams ────────────────────────────────────────────────────────────────

  addTeam(companyId, payload) {
    return API.post(`${BASE}/${encodeURIComponent(companyId)}/teams`, payload)
  },

  updateTeam(companyId, teamId, payload) {
    return API.put(
      `${BASE}/${encodeURIComponent(companyId)}/teams/${encodeURIComponent(teamId)}`,
      payload
    )
  },

  deleteTeam(companyId, teamId, { force = false } = {}) {
    return API.delete(
      `${BASE}/${encodeURIComponent(companyId)}/teams/${encodeURIComponent(teamId)}${toQuery({ force })}`
    )
  },

  resolveTeam(companyId, teamId) {
    return API.get(
      `${BASE}/${encodeURIComponent(companyId)}/teams/${encodeURIComponent(teamId)}`
    )
  },

  addTeamMembers(companyId, teamId, members) {
    return API.post(
      `${BASE}/${encodeURIComponent(companyId)}/teams/${encodeURIComponent(teamId)}/members`,
      { members }
    )
  },

  removeTeamMembers(companyId, teamId, members) {
    const refs = (members || []).map(memberRef).filter(Boolean).join(',')
    return API.delete(
      `${BASE}/${encodeURIComponent(companyId)}/teams/${encodeURIComponent(teamId)}/members${toQuery({ members: refs })}`
    )
  },

  setTeamLead(companyId, teamId, { kind = 'profile', name = '' } = {}) {
    return API.put(
      `${BASE}/${encodeURIComponent(companyId)}/teams/${encodeURIComponent(teamId)}/lead`,
      { kind, name }
    )
  },

  // ── Projects ─────────────────────────────────────────────────────────────

  linkProject(companyId, payload) {
    return API.post(`${BASE}/${encodeURIComponent(companyId)}/projects`, payload)
  },

  unlinkProject(companyId, projectId, { force = false } = {}) {
    return API.delete(
      `${BASE}/${encodeURIComponent(companyId)}/projects/${encodeURIComponent(projectId)}${toQuery({ force })}`
    )
  },

  // ── Missions ─────────────────────────────────────────────────────────────

  addMission(companyId, payload) {
    return API.post(`${BASE}/${encodeURIComponent(companyId)}/missions`, payload)
  },

  updateMission(companyId, missionId, payload) {
    return API.put(
      `${BASE}/${encodeURIComponent(companyId)}/missions/${encodeURIComponent(missionId)}`,
      payload
    )
  },

  deleteMission(companyId, missionId, { force = false } = {}) {
    return API.delete(
      `${BASE}/${encodeURIComponent(companyId)}/missions/${encodeURIComponent(missionId)}${toQuery({ force })}`
    )
  },

  dispatchMission(companyId, missionId, { force = false } = {}) {
    return API.post(
      `${BASE}/${encodeURIComponent(companyId)}/missions/${encodeURIComponent(missionId)}/dispatch${toQuery({ force })}`,
      {}
    )
  },

  acceptMission(companyId, missionId, result = '') {
    return API.post(
      `${BASE}/${encodeURIComponent(companyId)}/missions/${encodeURIComponent(missionId)}/accept`,
      { result }
    )
  },

  rejectMission(companyId, missionId, reason = '') {
    return API.post(
      `${BASE}/${encodeURIComponent(companyId)}/missions/${encodeURIComponent(missionId)}/reject`,
      { reason }
    )
  },

  transitionMission(companyId, missionId, status, { force = false } = {}) {
    return API.post(
      `${BASE}/${encodeURIComponent(companyId)}/missions/${encodeURIComponent(missionId)}/transition`,
      { status, force }
    )
  },

  syncMissions(companyId) {
    return API.post(`${BASE}/${encodeURIComponent(companyId)}/missions/sync`, {})
  },

  // ── Autonomy ─────────────────────────────────────────────────────────────

  updateAutonomy(companyId, payload) {
    return API.put(
      `${BASE}/${encodeURIComponent(companyId)}/autonomy`,
      payload
    )
  },

  runCycle(companyId, { force = true } = {}) {
    return API.post(
      `${BASE}/${encodeURIComponent(companyId)}/cycle`,
      { force }
    )
  },

  // ── People / company users ───────────────────────────────────────────────
  // Only company admins may write these; the server enforces the role.

  members(companyId) {
    return API.get(`${BASE}/${encodeURIComponent(companyId)}/members`)
  },

  addMember(companyId, payload) {
    return API.post(`${BASE}/${encodeURIComponent(companyId)}/members`, payload)
  },

  updateMember(companyId, username, payload) {
    return API.put(
      `${BASE}/${encodeURIComponent(companyId)}/members/${encodeURIComponent(username)}`,
      payload
    )
  },

  removeMember(companyId, username) {
    return API.delete(
      `${BASE}/${encodeURIComponent(companyId)}/members/${encodeURIComponent(username)}`
    )
  },

  // ── Always-present company assistant ─────────────────────────────────────
  // The UI renders every settings/team form INSIDE the assistant window; this
  // endpoint answers a turn or executes a submitted form.
  assistant(companyId, payload) {
    return API.post(
      `${BASE}/${encodeURIComponent(companyId)}/assistant`,
      payload
    )
  }
})

export default companiesModule

// Made with ❤️ by codx-junior
