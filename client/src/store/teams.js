import { getterTree, mutationTree, actionTree } from 'typed-vuex'

export const namespaced = true

const STORAGE_KEY = 'codx-teams-store'

// ── Data type factories ───────────────────────────────────────────────────────

export const createTeam = (overrides = {}) => ({
  id: crypto.randomUUID(),
  name: '',
  description: '',
  icon: null,
  color: '#6366f1',
  createdAt: new Date().toISOString(),
  updatedAt: new Date().toISOString(),
  categories: [],
  members: [],
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
  mode: 'topic', // topic | chat | task
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
  role: 'member', // admin | moderator | member | guest
  status: 'online', // online | away | busy | offline
  joinedAt: new Date().toISOString(),
  ...overrides
})

// ── Persistence helpers ───────────────────────────────────────────────────────

function persist(state) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({
      teams: state.teams,
      activeTeamId: state.activeTeamId,
      activeChannelId: state.activeChannelId
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
  activeChannelId: null
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
    init({ state }) {
      const saved = load()
      if (saved.teams?.length) {
        state.teams = saved.teams
        state.activeTeamId = saved.activeTeamId || null
        state.activeChannelId = saved.activeChannelId || null
      }
    },

    // ── Teams ─────────────────────────────────────────────────────────────────
    createTeam({ state }, overrides = {}) {
      const team = createTeam({
        name: 'New Team',
        categories: [
          createCategory({ name: 'General', channels: [] }),
          createCategory({ name: 'Topics', channels: [] })
        ],
        members: [],
        ...overrides
      })
      state.teams = [...state.teams, team]
      state.activeTeamId = team.id
      state.activeChannelId = null
      persist(state)
      return team
    },

    updateTeam({ commit }, team) {
      commit('upsertTeam', team)
    },

    deleteTeam({ commit }, teamId) {
      commit('removeTeam', teamId)
    },

    selectTeam({ state }, teamId) {
      state.activeTeamId = teamId
      state.activeChannelId = null
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
      // Create backing chat via chats store
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
      commit('markChannelRead', { teamId, channelId })
      persist(state)
    },

    // ── Members ───────────────────────────────────────────────────────────────
    addMember({ commit }, { teamId, memberData }) {
      const member = createMember(memberData)
      commit('upsertMember', { teamId, member })
      return member
    },

    updateMember({ commit }, { teamId, member }) {
      commit('upsertMember', { teamId, member })
    },

    removeMember({ commit }, { teamId, memberId }) {
      commit('removeMember', { teamId, memberId })
    }
  }
)