import { getterTree, mutationTree, actionTree } from 'typed-vuex'
import { $storex } from '.'

export const namespaced = true

const STORAGE_KEY = 'codx-teams-store'
const DEFAULT_TEAM_COLOR = '#6366f1'

// ── Data type factories ───────────────────────────────────────────────────────

export const createTeam = (overrides = {}) => ({
  id: crypto.randomUUID(),
  name: '',
  description: '',
  icon: null,
  color: DEFAULT_TEAM_COLOR,
  profiles: [], // AI profiles (backend: `profiles`)
  tags: [], // free-form labels (backend: `tags`)
  createdAt: new Date().toISOString(),
  updatedAt: new Date().toISOString(),
  categories: [],
  members: [],
  directMessages: {},
  ...overrides
})

export const createCategory = (overrides = {}) => ({
  id: crypto.randomUUID(),
  name: 'General',
  collapsed: false,
  channels: [],
  ...overrides
})

export const createChannel = (overrides = {}) => ({
  id: crypto.randomUUID(),
  name: '',
  description: '',
  mode: 'topic',
  chatId: null,
  categoryId: null,
  unread: 0,
  pinned: false,
  createdAt: new Date().toISOString(),
  ...overrides
})

export const createMember = (overrides = {}) => ({
  id: crypto.randomUUID(),
  username: '',
  role: 'member',
  status: 'online',
  joinedAt: new Date().toISOString(),
  ...overrides
})

// ── Backend API mapping ───────────────────────────────────────────────────────
// The backend team model (codx/junior/teams/model.py) is intentionally small:
//   { id, project_id, name, description, avatar, profiles, users, tags, ... }
// while the UI team also carries view-only state (colour, categories, channels,
// direct-message links and per-member role/status). The helpers below translate
// between the two so the API stays the source of truth for team identity and
// membership, while the local view state survives reloads.

/** Default categories, used when a team (e.g. created elsewhere) has none. */
function defaultCategories() {
  return [
    createCategory({ name: 'General' }),
    createCategory({ name: 'Topics' })
  ]
}

/** Serialise a UI team into the payload accepted by the backend. */
function toApiTeam(team) {
  return {
    id: team.id,
    name: team.name,
    description: team.description || '',
    avatar: team.icon || '',
    profiles: team.profiles || [],
    users: (team.members || []).map(m => m.username).filter(Boolean),
    tags: team.tags || []
  }
}

/**
 * Rebuild the human members for an API team, preserving the local role/status
 * (the backend only stores usernames, so those attributes stay local).
 */
function membersFromApi(apiTeam, localMembers = []) {
  const localByUsername = new Map((localMembers || []).map(m => [m.username, m]))
  return (apiTeam.users || []).map(username => {
    const local = localByUsername.get(username) || {}
    return {
      id: local.id || crypto.randomUUID(),
      username,
      role: local.role || 'member',
      status: local.status || 'offline',
      joinedAt: local.joinedAt || new Date().toISOString()
    }
  })
}

/** Build a UI team from an API team, preserving local view-only state. */
function fromApiTeam(apiTeam, localTeam = null) {
  const local = localTeam || {}
  return createTeam({
    id: apiTeam.id,
    name: apiTeam.name || '',
    description: apiTeam.description || '',
    icon: apiTeam.avatar || local.icon || null,
    color: local.color || DEFAULT_TEAM_COLOR,
    profiles: apiTeam.profiles || [],
    tags: apiTeam.tags || [],
    createdAt: apiTeam.created_at || local.createdAt || new Date().toISOString(),
    updatedAt: apiTeam.updated_at || local.updatedAt || new Date().toISOString(),
    categories: local.categories?.length ? local.categories : defaultCategories(),
    members: membersFromApi(apiTeam, local.members),
    directMessages: local.directMessages || {}
  })
}

/** The teams API bound to the active project, or `null` when unavailable. */
function getTeamsApi() {
  try {
    return $storex.projects?.activeProject?.$api?.teams || null
  } catch {
    return null
  }
}

// ── Persistence helpers ───────────────────────────────────────────────────────

function persist(state) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({
      teams: state.teams,
      activeTeamId: state.activeTeamId,
      activeChannelId: state.activeChannelId,
      activeDmMemberId: state.activeDmMemberId
    }))
  } catch (e) {
    console.warn('[teams] persist error', e)
  }
}

function load() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}')
  } catch {
    return {}
  }
}

// ── Store ─────────────────────────────────────────────────────────────────────

export const state = () => ({
  teams: [],
  activeTeamId: null,
  activeChannelId: null,
  activeDmMemberId: null
})

export const getters = getterTree(state, {
  activeTeam: state => state.teams.find(t => t.id === state.activeTeamId) || null,
  activeChannel: state => {
    const team = state.teams.find(t => t.id === state.activeTeamId)
    if (!team) return null
    for (const cat of team.categories) {
      const ch = cat.channels.find(c => c.id === state.activeChannelId)
      if (ch) return ch
    }
    return null
  },
  activeDmMember: state => {
    const team = state.teams.find(t => t.id === state.activeTeamId)
    if (!team || !state.activeDmMemberId) return null
    return team.members.find(m => m.id === state.activeDmMemberId) || null
  },
  teamById: state => id => state.teams.find(t => t.id === id) || null,
  channelById: state => (teamId, channelId) => {
    const team = state.teams.find(t => t.id === teamId)
    if (!team) return null
    for (const cat of team.categories) {
      const ch = cat.channels.find(c => c.id === channelId)
      if (ch) return ch
    }
    return null
  }
})

export const mutations = mutationTree(state, {
  setTeams(state, teams) {
    state.teams = teams
  },
  setActiveTeamId(state, id) {
    state.activeTeamId = id
  },
  setActiveChannelId(state, id) {
    state.activeChannelId = id
    state.activeDmMemberId = null
  },
  setActiveDmMemberId(state, id) {
    state.activeDmMemberId = id
    state.activeChannelId = null
  },
  upsertTeam(state, team) {
    const idx = state.teams.findIndex(t => t.id === team.id)
    if (idx >= 0) {
      state.teams = state.teams.map((t, i) => i === idx ? { ...t, ...team, updatedAt: new Date().toISOString() } : t)
    } else {
      state.teams = [...state.teams, team]
    }
    persist(state)
  },
  removeTeam(state, teamId) {
    state.teams = state.teams.filter(t => t.id !== teamId)
    if (state.activeTeamId === teamId) {
      state.activeTeamId = state.teams[0]?.id || null
      state.activeChannelId = null
      state.activeDmMemberId = null
    }
    persist(state)
  },
  upsertCategory(state, { teamId, category }) {
    state.teams = state.teams.map(t => {
      if (t.id !== teamId) return t
      const idx = t.categories.findIndex(c => c.id === category.id)
      const categories = idx >= 0
        ? t.categories.map((c, i) => i === idx ? { ...c, ...category } : c)
        : [...t.categories, category]
      return { ...t, categories }
    })
    persist(state)
  },
  removeCategory(state, { teamId, categoryId }) {
    state.teams = state.teams.map(t => {
      if (t.id !== teamId) return t
      return { ...t, categories: t.categories.filter(c => c.id !== categoryId) }
    })
    persist(state)
  },
  upsertChannel(state, { teamId, categoryId, channel }) {
    state.teams = state.teams.map(t => {
      if (t.id !== teamId) return t
      const categories = t.categories.map(cat => {
        if (cat.id !== categoryId) return cat
        const idx = cat.channels.findIndex(c => c.id === channel.id)
        const channels = idx >= 0
          ? cat.channels.map((c, i) => i === idx ? { ...c, ...channel } : c)
          : [...cat.channels, { ...channel, categoryId }]
        return { ...cat, channels }
      })
      return { ...t, categories }
    })
    persist(state)
  },
  removeChannel(state, { teamId, categoryId, channelId }) {
    state.teams = state.teams.map(t => {
      if (t.id !== teamId) return t
      const categories = t.categories.map(cat => {
        if (cat.id !== categoryId) return cat
        return { ...cat, channels: cat.channels.filter(c => c.id !== channelId) }
      })
      return { ...t, categories }
    })
    if (state.activeChannelId === channelId) state.activeChannelId = null
    persist(state)
  },
  upsertMember(state, { teamId, member }) {
    state.teams = state.teams.map(t => {
      if (t.id !== teamId) return t
      const idx = t.members.findIndex(m => m.id === member.id)
      const members = idx >= 0
        ? t.members.map((m, i) => i === idx ? { ...m, ...member } : m)
        : [...t.members, member]
      return { ...t, members }
    })
    persist(state)
  },
  removeMember(state, { teamId, memberId }) {
    state.teams = state.teams.map(t => {
      if (t.id !== teamId) return t
      return { ...t, members: t.members.filter(m => m.id !== memberId) }
    })
    persist(state)
  },
  setDmChatId(state, { teamId, memberId, chatId }) {
    state.teams = state.teams.map(t => {
      if (t.id !== teamId) return t
      const directMessages = { ...(t.directMessages || {}), [memberId]: chatId }
      return { ...t, directMessages }
    })
    persist(state)
  },
  markChannelRead(state, { teamId, channelId }) {
    state.teams = state.teams.map(t => {
      if (t.id !== teamId) return t
      const categories = t.categories.map(cat => ({
        ...cat,
        channels: cat.channels.map(ch =>
          ch.id === channelId ? { ...ch, unread: 0 } : ch
        )
      }))
      return { ...t, categories }
    })
    persist(state)
  },
  toggleCategoryCollapsed(state, { teamId, categoryId }) {
    state.teams = state.teams.map(t => {
      if (t.id !== teamId) return t
      const categories = t.categories.map(cat =>
        cat.id === categoryId ? { ...cat, collapsed: !cat.collapsed } : cat
      )
      return { ...t, categories }
    })
    persist(state)
  }
})

export const actions = actionTree(
  { state, getters, mutations },
  {
    async init({ state }) {
      // Restore the locally cached view state first (instant, works offline)…
      const saved = load()
      if (saved.teams?.length) {
        state.teams = saved.teams
        state.activeTeamId = saved.activeTeamId || null
        state.activeChannelId = saved.activeChannelId || null
        state.activeDmMemberId = saved.activeDmMemberId || null
      }
      // …then refresh teams from the backend (best effort).
      await $storex.teams.loadTeams()
    },

    /**
     * Load teams for the active project from the backend and merge them with
     * the locally cached view state (colour, categories, channels, DMs…).
     * A no-op when no project/API is available yet, so the local cache keeps
     * working offline.
     */
    async loadTeams({ state }) {
      const api = getTeamsApi()
      if (!api) return state.teams

      const localById = new Map(state.teams.map(t => [t.id, t]))
      try {
        const apiTeams = await api.list()
        state.teams = (apiTeams || []).map(apiTeam => fromApiTeam(apiTeam, localById.get(apiTeam.id)))

        if (!state.teams.some(t => t.id === state.activeTeamId)) {
          state.activeTeamId = state.teams[0]?.id || null
          state.activeChannelId = null
          state.activeDmMemberId = null
        }
        persist(state)
      } catch (error) {
        console.error('[teams] Failed to load teams:', error)
      }
      return state.teams
    },

    // ── Teams ─────────────────────────────────────────────────────────────────
    async createTeam({ state }, overrides = {}) {
      const draft = createTeam({
        name: 'New Team',
        categories: defaultCategories(),
        members: [],
        directMessages: {},
        profiles: [],
        ...overrides
      })

      // Persist through the API (the server assigns the real id); fall back to
      // the local draft when the API is unavailable.
      let team = draft
      const api = getTeamsApi()
      if (api) {
        try {
          const saved = await api.create(toApiTeam(draft))
          team = fromApiTeam(saved, draft)
        } catch (error) {
          console.error('[teams] Failed to create team:', error)
        }
      }

      state.teams = [...state.teams, team]
      state.activeTeamId = team.id
      state.activeChannelId = null
      state.activeDmMemberId = null
      persist(state)
      return team
    },

    async updateTeam({ state, commit }, team) {
      // Optimistic local update for instant feedback…
      commit('upsertTeam', team)

      const api = getTeamsApi()
      if (!api || !team.id) return team

      // …then persist and reconcile with the server response.
      try {
        const saved = await api.update(toApiTeam(team))
        const local = state.teams.find(t => t.id === team.id) || team
        const merged = fromApiTeam(saved, local)
        commit('upsertTeam', merged)
        return merged
      } catch (error) {
        console.error('[teams] Failed to update team:', error)
        return team
      }
    },

    async deleteTeam({ commit }, teamId) {
      commit('removeTeam', teamId)

      const api = getTeamsApi()
      if (!api || !teamId) return
      try {
        await api.delete(teamId)
      } catch (error) {
        console.error('[teams] Failed to delete team:', error)
      }
    },

    selectTeam({ state }, teamId) {
      state.activeTeamId = teamId
      state.activeChannelId = null
      state.activeDmMemberId = null
      persist(state)
    },

    // ── Categories ────────────────────────────────────────────────────────────
    createCategory({ commit }, { teamId, name = 'New Category' }) {
      const category = createCategory({ name })
      commit('upsertCategory', { teamId, category })
      return category
    },

    updateCategory({ commit }, { teamId, category }) {
      commit('upsertCategory', { teamId, category })
    },

    deleteCategory({ commit }, { teamId, categoryId }) {
      commit('removeCategory', { teamId, categoryId })
    },

    // ── Channels ──────────────────────────────────────────────────────────────
    async createChannel({ state, commit }, { teamId, categoryId, channelData = {} }) {
      const channel = createChannel({
        name: 'new-channel',
        ...channelData,
        categoryId
      })
      const chat = await $storex.chats.createNewChat({
        name: `team:${teamId}/${channel.name}`,
        mode: channel.mode,
        board: `team:${teamId}`,
        column: categoryId,
        messages: []
      })
      channel.chatId = chat.id
      commit('upsertChannel', { teamId, categoryId, channel })
      return channel
    },

    updateChannel({ commit }, { teamId, categoryId, channel }) {
      commit('upsertChannel', { teamId, categoryId, channel })
    },

    deleteChannel({ commit }, { teamId, categoryId, channelId }) {
      commit('removeChannel', { teamId, categoryId, channelId })
    },

    async selectChannel({ state, commit }, { teamId, channelId }) {
      state.activeTeamId = teamId
      state.activeChannelId = channelId
      state.activeDmMemberId = null
      commit('markChannelRead', { teamId, channelId })
      persist(state)
    },

    // ── Direct Messages ───────────────────────────────────────────────────────
    async openDirectMessage({ state, commit }, { teamId, member }) {
      const team = state.teams.find(t => t.id === teamId)
      if (!team) return null

      // Return existing DM chat if available
      const existingChatId = (team.directMessages || {})[member.id]
      if (existingChatId) {
        commit('setActiveDmMemberId', member.id)
        state.activeTeamId = teamId
        persist(state)
        return existingChatId
      }

      // Create a new DM chat
      const chat = await $storex.chats.createNewChat({
        name: `dm:${teamId}/${member.username}`,
        mode: 'chat',
        board: `team:${teamId}`,
        messages: []
      })
      commit('setDmChatId', { teamId, memberId: member.id, chatId: chat.id })
      commit('setActiveDmMemberId', member.id)
      state.activeTeamId = teamId
      persist(state)
      return chat.id
    },

    // ── Members (human users) ─────────────────────────────────────────────────
    async addMember({ state, commit }, { teamId, memberData }) {
      const member = createMember(memberData)
      commit('upsertMember', { teamId, member })

      const api = getTeamsApi()
      if (api && teamId && member.username) {
        try {
          const saved = await api.addMembers(teamId, { users: [member.username] })
          const local = state.teams.find(t => t.id === teamId)
          if (local) commit('upsertTeam', fromApiTeam(saved, local))
        } catch (error) {
          console.error('[teams] Failed to add member:', error)
        }
      }
      return member
    },

    async updateMember({ state, commit }, { teamId, member }) {
      const team = state.teams.find(t => t.id === teamId)
      const previous = (team?.members || []).find(m => m.id === member.id)

      commit('upsertMember', { teamId, member })

      const api = getTeamsApi()
      // Only the username is synced to the backend; role/status stay local.
      if (api && previous?.username && previous.username !== member.username) {
        try {
          await api.removeMembers(teamId, { users: [previous.username] })
          const saved = await api.addMembers(teamId, { users: [member.username] })
          const local = state.teams.find(t => t.id === teamId)
          if (local) commit('upsertTeam', fromApiTeam(saved, local))
        } catch (error) {
          console.error('[teams] Failed to update member:', error)
        }
      }
      return member
    },

    async removeMember({ state, commit }, { teamId, memberId }) {
      const team = state.teams.find(t => t.id === teamId)
      const member = (team?.members || []).find(m => m.id === memberId)

      commit('removeMember', { teamId, memberId })

      const api = getTeamsApi()
      if (api && member?.username) {
        try {
          const saved = await api.removeMembers(teamId, { users: [member.username] })
          const local = state.teams.find(t => t.id === teamId)
          if (local) commit('upsertTeam', fromApiTeam(saved, local))
        } catch (error) {
          console.error('[teams] Failed to remove member:', error)
        }
      }
    },

    // ── AI profiles ───────────────────────────────────────────────────────────
    // AI profiles are stored on the team's `profiles` list (see the backend
    // `Team` model) and are managed through the same membership endpoint.
    async addProfile({ state, commit }, { teamId, profileName }) {
      const team = state.teams.find(t => t.id === teamId)
      if (!team || !profileName) return null

      if (!(team.profiles || []).includes(profileName)) {
        commit('upsertTeam', { ...team, profiles: [...(team.profiles || []), profileName] })
      }

      const api = getTeamsApi()
      if (api) {
        try {
          const saved = await api.addMembers(teamId, { profiles: [profileName] })
          const local = state.teams.find(t => t.id === teamId)
          if (local) commit('upsertTeam', fromApiTeam(saved, local))
        } catch (error) {
          console.error('[teams] Failed to add AI profile:', error)
        }
      }
      return profileName
    },

    async removeProfile({ state, commit }, { teamId, profileName }) {
      const team = state.teams.find(t => t.id === teamId)
      if (!team) return

      commit('upsertTeam', {
        ...team,
        profiles: (team.profiles || []).filter(p => p !== profileName)
      })

      const api = getTeamsApi()
      if (api) {
        try {
          const saved = await api.removeMembers(teamId, { profiles: [profileName] })
          const local = state.teams.find(t => t.id === teamId)
          if (local) commit('upsertTeam', fromApiTeam(saved, local))
        } catch (error) {
          console.error('[teams] Failed to remove AI profile:', error)
        }
      }
    }
  }
)
