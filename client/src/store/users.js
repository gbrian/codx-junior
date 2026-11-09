import { getterTree, mutationTree, actionTree } from 'typed-vuex'
import { $storex } from '.'

export const namespaced = true

import { API } from '../api/api'
export const state = () => ({
  onlineUsers: {},
  users: [],
  metrics: null,
  // Incremented whenever API.user changes. Vuex getters are cached computed
  // values; the user object itself lives on the (non-reactive) API singleton,
  // so every getter that reads it must also touch this revision to invalidate.
  userRevision: 0
})

export const getters = getterTree(state, {
  user: (state) => {
    state.userRevision
    return API.user
  },
  isAdmin: (state) => {
    state.userRevision
    return API.user?.role === 'admin'
  },

  // ── Company shell ────────────────────────────────────────────────────────
  // codx-junior has two product shells. A user enters the simplified company
  // workspace when their role/memberships say so; otherwise they stay in
  // today's project workspace. `workspace_mode` is an explicit override kept
  // on the user document (auto | company | work).
  companyMemberships: (state) => {
    state.userRevision
    return API.user?.companies || []
  },
  companyIds: (state) => {
    state.userRevision
    return (API.user?.companies || []).map(item => item.company_id)
  },
  companyRole: (state) => companyId => {
    state.userRevision
    return (API.user?.companies || [])
      .find(item => item.company_id === companyId)?.role || ''
  },
  isCompanyMode: (state) => {
    state.userRevision
    const user = API.user
    if (!user) return false
    if (user.workspace_mode === 'company') return true
    if (user.workspace_mode === 'work') return false
    if (['company_admin', 'manager'].includes(user.role)) return true
    return (user.companies || []).length > 0
  },
  isCompanyAdmin: (state) => {
    state.userRevision
    const user = API.user
    if (!user) return false
    if (['admin', 'company_admin'].includes(user.role)) return true
    return (user.companies || []).some(item => item.role === 'admin')
  },
  isCompanyManager: (state) => {
    state.userRevision
    const user = API.user
    if (!user) return false
    if (['admin', 'company_admin', 'manager'].includes(user.role)) return true
    return (user.companies || []).some(item => ['admin', 'manager'].includes(item.role))
  },
  primaryCompanyId: (state) => {
    state.userRevision
    const companies = API.user?.companies || []
    return companies.find(item => item.role === 'admin')?.company_id ||
      companies[0]?.company_id || ''
  },

  allUsers: ({ codxJunior, users }) => codxJunior ? [ codxJunior, ...users ] : [],
  codxJunior: () => (state.codxJunior = { 
    userName: "codx-junior", 
    avatar: API.globalSettings?.codx_junior_avatar
  }),
  projectRole: () => $storex.users.isAdmin ? 'admin' : API.user?.projects.find(p => p.project_id === $storex.projects.activeProject?.project_id)?.permissions,
  isProjectAdmin: () => $storex.users.isAdmin || $storex.users.projectRole === 'admin',
  canShowCoder: () => $storex.users.isAdmin || $storex.users.user?.apps.includes("coder"),
  canShowBrowser: () => $storex.users.isAdmin || $storex.users.user?.apps.includes("viewer")
})

export const mutations = mutationTree(state, {
  setOnlineUsers(state, users) {
    state.onlineUsers = users
  },
  setUsers(state, users) {
    state.users = users
  },
  setMetrics(state, metrics) {
    state.metrics = metrics
  },
  // Invalidates every getter that reads the (non-reactive) API.user.
  bumpUserRevision(state) {
    state.userRevision = state.userRevision + 1
  }
})

export const actions = actionTree(
  { state, getters, mutations },
  {
    async init ({ state }, $storex) {
    },
    async loadUsers({ state }) {
      const users = await $storex.api.users.list()
      $storex.users.setUsers(users || [])
    },
    async loadMetrics() {
      const metrics = await API.analytics.me()
      $storex.users.setMetrics(metrics)
    },
    async login({ _ }, user) {
      try {
        await API.users.login(user)
      } catch(ex) {
        $storex.session.onError("Login error")
      }
      $storex.users.bumpUserRevision()
      $storex.init()
    },
    async oauthLogin({ _ }, { provider, code, state }) {
      try {
        await API.oauth.oauthLogin({ oauth_provider: provider, code, state })
        $storex.users.bumpUserRevision()
        window.location.reload()
      } catch (ex) {
        $storex.session.onError("OAuth login error")
        throw ex
      }
      $storex.init()
    },
    async logout() {
      await API.users.logout()
      $storex.users.bumpUserRevision()
      $storex.init()
    },
    async saveUser({ state }, user) {
      await API.users.save(user)
      $storex.users.bumpUserRevision()
      $storex.session.onInfo("User account updated")
    },
    /**
     * Switch between the simplified company shell and today's project
     * workspace. The preference lives on the user document, so it follows the
     * account across browsers.
     *
     * @param {string} mode - 'auto' | 'company' | 'work'
     */
    async setWorkspaceMode(_, mode) {
      const value = ['auto', 'company', 'work'].includes(mode) ? mode : 'auto'
      await API.users.save({ ...API.user, workspace_mode: value })
      $storex.users.bumpUserRevision()
      $storex.session.onInfo(
        value === 'company'
          ? 'Company workspace enabled'
          : value === 'work'
            ? 'Working workspace enabled'
            : 'Workspace mode is automatic'
      )
      return value
    }
  }
)