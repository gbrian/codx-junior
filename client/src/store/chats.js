import { getterTree, mutationTree, actionTree } from 'typed-vuex'
import store, { $storex } from '.'
import { ChatSearchRequest } from '@/api/model/ChatSearchRequest'
import { ENTITY_STATUS } from './entityStatuses'

export const namespaced = true

// ─── Chat Mode Configuration ───────────────────────────────────────────────
export const CHAT_MODES = {
  chat: { value: 'chat', label: 'Chat', icon: 'fa-comments' },
  agent: { value: 'agent', label: 'Agent', icon: 'fa-solid fa-arrows-spin' },
  task: { value: 'task', label: 'Task', icon: 'fa-tasks' },
  topic: { value: 'topic', label: 'Topic', icon: 'fa-lightbulb' },
  preview: { value: 'preview', label: 'Preview', icon: 'fa-eye' },
  browser: { value: 'browser', label: 'Browser', icon: 'fa-globe' },
  slides: { value: 'slides', label: 'Slides', icon: 'fa-presentation' },
  tutorial: { value: 'tutorial', label: 'Tutorial', icon: 'fa-graduation-cap' },
  channel: { value: 'channel', label: 'Channel', icon: 'fa-hashtag' }
}

// ─── Status Configuration (single source of truth) ───────────────────────────
export const CHAT_STATUS_CONFIG = {
  todo:     { value: 'todo',     label: 'To Do',    icon: 'fa-solid fa-circle-dot',   textColor: 'text-info/60',    borderColor: 'border-l-info',    btnClass: 'btn-info btn-outline' },
  doing:    { value: 'doing',    label: 'Doing',    icon: 'fa-solid fa-circle-play',   textColor: 'text-primary/60', borderColor: 'border-l-primary', btnClass: 'btn-primary btn-outline' },
  onhold:   { value: 'onhold',   label: 'On Hold',  icon: 'fa-solid fa-circle-pause',  textColor: 'text-warning/60', borderColor: 'border-l-warning', btnClass: 'btn-warning btn-outline' },
  done:     { value: 'done',     label: 'Done',     icon: 'fa-solid fa-circle-check',  textColor: 'text-success/60', borderColor: 'border-l-success', btnClass: 'btn-success btn-outline' },
  rejected: { value: 'rejected', label: 'Rejected', icon: 'fa-solid fa-circle-xmark',  textColor: 'text-error/60',   borderColor: 'border-l-error',   btnClass: 'btn-error btn-outline' },
}

const DEFAULT_STATUS = 'todo'

// In-flight chat reloads, keyed by chat id.
// Socket events arrive in bursts (one per chat change while the agent streams)
// and every path that opens a chat asks for a fresh copy. Firing them in
// parallel fetched the SAME chat several times and each response replaced the
// chat object, cascading a full re-render of every consumer (board columns,
// cards, message list). One request per chat at a time keeps references stable.
const reloadsInFlight = {}

// Auto-reset timers of `setChatUpdating`, kept OUT of the store state: refreshing
// the safety timeout of a chat that is ALREADY flagged as updating must not
// invalidate `isChatUpdating()` — that re-rendered every card of the board on
// each streamed chunk.
const updatingTimeouts = {}

export const state = () => ({
  chats: {},
  activeChatId: null,
  chatEvents: {},
  chatLoadingStatus: {}, // { [chatId]: ENTITY_STATUS }
  needsReload: {}, // { [chatId]: true } chat only carries a summary (last message) and must be fully reloaded before display
  searchResults: null,
  recentChatIds: [],
  recentChatsPage: 1,
  recentChatsHasMore: true,
  recentChatsLoading: false,
  // Last "a chat document was created or updated" signal, cached by the store
  // so components do not have to scan the transient socket log
  // (`session.events`, whose entries expire after a few seconds).
  // `revision` is a monotonic counter: consumers WATCH it and compare numbers,
  // they never diff the chat list or the event log themselves.
  chatActivity: { revision: 0, chatId: null, kind: null, at: null },
})

// Same values, same order. The API answers with brand-new arrays on every read,
// so a reference check alone reports a change for the collections the board
// derives its columns/tasks from (`sprints`, `board`, `profiles`…).
function sameArrayValues(current, next) {
  if (current === next) return true
  if (!Array.isArray(current) || !Array.isArray(next)) return false
  if (current.length !== next.length) return false
  return current.every((value, index) => value === next[index])
}

// Collections that ARE the payload: the freshly loaded ones always win.
const CHAT_PAYLOAD_FIELDS = ['messages', 'attachments']

// Merge `source` INTO `target`, keeping `target`'s identity and the identity of
// every collection whose values did not really change.
//
// The chat object identity is what the board compares to decide whether anything
// changed (`SprintBoardCanvas.sameColumns` / `SprintBoardColumn.sameTasks`), so
// replacing it turned a plain "history refreshed" into a full rebuild of every
// column, every card and every derived getter — which is what made opening a
// chat in the sprint board cascade into a render loop.
function mergeChat(target, source) {
  Object.keys(source).forEach(key => {
    const next = source[key]
    const current = target[key]
    if (current === next) return
    if (CHAT_PAYLOAD_FIELDS.includes(key)) {
      target[key] = next
      return
    }
    if (sameArrayValues(current, next)) return
    target[key] = next
  })
}

function registerChat(state, chat) {
  if (!chat?.id) {
    console.error('[chats store] Attempted to store a null/invalid chat:', chat)
    return
  }

  // Update lastMessageAt when registering a chat with messages
  const lastMessage = chat.messages?.[chat.messages.length - 1]
  const lastMessageAt = lastMessage?.timestamp || lastMessage?.created_at || chat.updated_at || new Date().toISOString()

  const existingChat = state.chats[chat.id]
  if (!existingChat) {
    state.chats[chat.id] = {
      ...chat,
      lastMessageAt
    }
    return state.chats[chat.id]
  }

  // Merge INTO the existing object so the chat keeps its identity (see
  // `mergeChat`). Only the fields that really changed are written, so a chat
  // refresh no longer invalidates the getters the board is built from.
  mergeChat(existingChat, chat)
  if (existingChat.lastMessageAt !== lastMessageAt) {
    existingChat.lastMessageAt = lastMessageAt
  }
  return existingChat
}

// Register a chat that only carries a summary (e.g. from list()/search() — the
// last message only).
// - If the full history is already loaded, keep its messages and only refresh
//   the rest of the chat info from the summary.
// - If a full load is in flight, leave the chat untouched.
// - Otherwise flag it so the full history is fetched before the chat is shown.
function registerChatSummary(state, chat) {
  if (!chat?.id) return

  const status = state.chatLoadingStatus[chat.id]

  // A full load is in flight — the summary would only clobber the incoming
  // full history, so leave the chat untouched.
  if (status === ENTITY_STATUS.LOADING) {
    return
  }

  // Full history already loaded: keep its messages, refresh the chat info.
  if (status === ENTITY_STATUS.LOADED) {
    const existingChat = state.chats[chat.id] || {}
    registerChat(state, { ...chat, messages: existingChat.messages })
    return
  }

  // Summary only (last message) or unknown chat: register it and flag for a
  // full reload before it is displayed.
  registerChat(state, chat)
  $storex.chats.setChatNeedsReload(chat.id)
  $storex.chats.setChatLoadingStatus({ chatId: chat.id, status: ENTITY_STATUS.UNINITIALIZED })
}

function getChatWorkingProject({ owner_project_id, project_id }) {
  return $storex.projects.allProjectsById[project_id || owner_project_id] ||
            $storex.projects.activeProject
}

function getChatProject({ owner_project_id }) {
  return $storex.projects.allProjectsById[owner_project_id] ||
            $storex.projects.activeProject
}

// Whether a chat is owned by the CURRENTLY ACTIVE project. The chats store is
// scoped to the active project (it is cleared whenever the project changes), so
// chats owned by another project must never be cached here. Doing so would leak
// their cards into the current board whenever a board is copied/moved to another
// project, because boards are keyed by title and an imported board keeps the
// same title until the next reload.
// When the owner cannot be determined, previous behaviour is preserved (true).
function isActiveProjectChat(chat) {
  if (!chat) return false
  const ownerProjectId = chat.owner_project_id || chat.project_id
  const activeProjectId = $storex.projects.activeProject?.project_id
  if (!ownerProjectId || !activeProjectId) return true
  return ownerProjectId === activeProjectId
}

function getRootChat(state, chatId) {
  let current = state.chats?.[chatId]
  if (!current) return null
  let depth = 0
  while (current?.parent_id && state.chats?.[current.parent_id] && depth < 20) {
    current = state.chats[current.parent_id]
    depth++
  }
  return current
}

// Human readable thread name derived from the message the thread answers.
// Falls back to the message id so a thread never ends up unnamed.
function threadChatName(message) {
  const text = `${message?.content || ''}`.replace(/\s+/g, ' ').trim()
  const base = text || message?.doc_id || 'thread'
  return `Thread: ${base.slice(0, 60)}`
}

export const getters = getterTree(state, {
  allChats: state => Object.values(state.chats || {}),
  allTags: state => new Set(Object.values(state.chats || {})?.map(c => c.tags).reduce((a, b) => a.concat(b), []) || []),
  allPRs: state => Object.values(state.chats || {}).filter(c => c.pr_view?.from_branch),
  allTemplates: state => Object.values(state.chats || {}).filter(c => c.is_template),

  // ─── Chat Mode Helpers ────────────────────────────────────────────────────
  availableChatModes: () => Object.values(CHAT_MODES),
  chatModeConfig: () => (mode) => CHAT_MODES[mode] || CHAT_MODES.chat,
  chatModeLabel: () => (mode) => (CHAT_MODES[mode] || CHAT_MODES.chat).label,
  chatModeIcon: () => (mode) => (CHAT_MODES[mode] || CHAT_MODES.chat).icon,

  // ─── Channel Helpers ──────────────────────────────────────────────────────
  channels: state => {
    return Object.values(state.chats || {})
      .filter(c => c.mode === 'channel')
      .sort((a, b) => {
        const timeA = new Date(a.lastMessageAt || a.updated_at || 0).getTime()
        const timeB = new Date(b.lastMessageAt || b.updated_at || 0).getTime()
        return timeB - timeA
      })
  },

  isChatUpdating: state => (chatId) => {
    return (state.chatEvents[chatId]?.updatingCount || 0) > 0 ||
      state.chatLoadingStatus[chatId] === ENTITY_STATUS.LOADING
  },
  chatLoadingStatus: state => (chatId) => {
    return state.chatLoadingStatus[chatId] || ENTITY_STATUS.UNINITIALIZED
  },
  chatNeedsReload: state => (chatId) => !!state.needsReload[chatId],
  activeChat: state => state.activeChatId ? (state.chats[state.activeChatId] || null) : null,
  chatProject: state => ({ project_id, owner_project_id }) => {
    return $storex.projects.allProjectsById[project_id || owner_project_id]
  },
  chatChildren: state => (chatId) => {
    const children = Object.values(state.chats || {}).filter(c => c.parent_id === chatId)
    return children
  },
  chatDescendants: (state, getters) => (chatId) => {
    const direct = getters.chatChildren(chatId)
    const indirect = direct.flatMap(child => getters.chatDescendants(child.id))
    return [...direct, ...indirect]
  },
  rootChat: state => (chatId) => getRootChat(state, chatId),
  searchResults: state => state.searchResults,
  getChatProject: () => getChatProject,
  getChatWorkingProject: () => getChatWorkingProject,
  recentChats: state => {
    return state.recentChatIds
      .map(id => state.chats[id])
      .filter(Boolean)
      .sort((a, b) => {
        const timeA = new Date(a.lastMessageAt || a.updated_at || 0).getTime()
        const timeB = new Date(b.lastMessageAt || b.updated_at || 0).getTime()
        return timeB - timeA
      })
  },
  recentChatsHasMore: state => state.recentChatsHasMore,
  recentChatsLoading: state => state.recentChatsLoading,

  // ─── Activity signal ──────────────────────────────────────────────────────
  // Monotonic counter bumped by `setChatActivity` on every socket
  // "changed"/"done" chat event and on every local chat write. Components that
  // must refresh when a chat/ticket changes watch this number.
  activityRevision: state => state.chatActivity.revision,
  lastActivity: state => state.chatActivity,

  // ─── Status helpers ────────────────────────────────────────────────────────
  statusList: () => Object.values(CHAT_STATUS_CONFIG),
  statusConfig: () => (status) => CHAT_STATUS_CONFIG[status] || CHAT_STATUS_CONFIG[DEFAULT_STATUS],
  statusIcon: () => (status) => (CHAT_STATUS_CONFIG[status] || CHAT_STATUS_CONFIG[DEFAULT_STATUS]).icon,
  statusLabel: () => (status) => (CHAT_STATUS_CONFIG[status] || CHAT_STATUS_CONFIG[DEFAULT_STATUS]).label,
  statusTextColor: () => (status) => (CHAT_STATUS_CONFIG[status] || CHAT_STATUS_CONFIG[DEFAULT_STATUS]).textColor,
  statusBorderColor: () => (status) => (CHAT_STATUS_CONFIG[status] || CHAT_STATUS_CONFIG[DEFAULT_STATUS]).borderColor,
  statusBtnClass: () => (status) => (CHAT_STATUS_CONFIG[status] || CHAT_STATUS_CONFIG[DEFAULT_STATUS]).btnClass,
})

export const mutations = mutationTree(state, {
  setActiveChatId(state, chatId) {
    state.activeChatId = chatId || null
  },

  clearActiveChat() {
    state.activeChatId = null
  },

  setSearchResults(state, results) {
    state.searchResults = results
  },

  clearSearchResults(state) {
    state.searchResults = null
  },

  setRecentChatIds(state, ids) {
    state.recentChatIds = ids
  },

  appendRecentChatIds(state, ids) {
    const existing = new Set(state.recentChatIds)
    ids.forEach(id => existing.add(id))
    state.recentChatIds = Array.from(existing)
  },

  setRecentChatsPage(state, page) {
    state.recentChatsPage = page
  },

  setRecentChatsHasMore(state, hasMore) {
    state.recentChatsHasMore = hasMore
  },

  setRecentChatsLoading(state, loading) {
    state.recentChatsLoading = loading
  },

  setChatLoadingStatus(state, { chatId, status }) {
    if (!chatId) return
    // Writing an unchanged status recreated the whole map and invalidated every
    // `isChatUpdating()` / `chatLoadingStatus()` consumer (every card of the
    // board) for nothing.
    if (state.chatLoadingStatus[chatId] === status) return
    state.chatLoadingStatus = {
      ...state.chatLoadingStatus,
      [chatId]: status
    }
  },

  setChatNeedsReload(state, chatId) {
    if (!chatId || state.needsReload[chatId]) return
    state.needsReload = { ...state.needsReload, [chatId]: true }
  },

  clearChatNeedsReload(state, chatId) {
    if (!chatId || !state.needsReload[chatId]) return
    const next = { ...state.needsReload }
    delete next[chatId]
    state.needsReload = next
  },

  // Cache the "a chat document was created or updated" signal.
  // Only WRITE paths reach this mutation (socket "changed"/"done" events plus
  // the local save/update/delete actions) — never the read paths
  // (`loadChats`, `loadChat`, `reloadChat`, `registerChat*`). That is what keeps
  // a consumer from re-arming its own refresh: reading chats does not signal.
  setChatActivity(state, { chatId = null, kind = 'changed', ts = Date.now() } = {}) {
    state.chatActivity = {
      revision: (state.chatActivity?.revision || 0) + 1,
      chatId,
      kind,
      at: new Date(ts).toISOString()
    }
  },

  setChatUpdating(state, { chatId, updating }) {
    if (!chatId) return

    // Single safety timer per chat, refreshed on every event
    clearTimeout(updatingTimeouts[chatId])
    delete updatingTimeouts[chatId]

    if (updating) {
      // Safety net: a chat that stops receiving events must not stay "updating"
      updatingTimeouts[chatId] = setTimeout(() => {
        delete updatingTimeouts[chatId]
        $storex.chats.setChatUpdating({ chatId, updating: false })
      }, 10000)

      // Already flagged: nothing changes for the UI, so skip the write that
      // would re-render every `isChatUpdating()` consumer (cards, columns, tabs).
      if (state.chatEvents[chatId]?.updatingCount > 0) return

      state.chatEvents = {
        ...state.chatEvents,
        [chatId]: {
          updatingCount: 1,
          updatingAt: new Date().toISOString(),
          timeoutId: null,
        }
      }
      return
    }

    // Already idle: nothing to reset
    if (!state.chatEvents[chatId]?.updatingCount) return

    state.chatEvents = {
      ...state.chatEvents,
      [chatId]: {
        ...(state.chatEvents[chatId] || {}),
        updatingCount: 0,
        updatingAt: null,
        timeoutId: null,
      }
    }
  },

  clearChats(state) {
    state.chats = {}
    state.activeChatId = null
    state.chatLoadingStatus = {}
    state.needsReload = {}
    // Drop the pending "updating" safety timers of the previous project
    Object.keys(updatingTimeouts).forEach(chatId => {
      clearTimeout(updatingTimeouts[chatId])
      delete updatingTimeouts[chatId]
    })
  },

  updateChatLastMessageAt(state, { chatId, timestamp }) {
    if (state.chats[chatId]) {
      state.chats[chatId].lastMessageAt = timestamp
    }
  }
})

export const actions = actionTree(
  { state, getters, mutations },
  {
    async init ({ state }) {
    },
    async loadChats({ state }) {
      const activeProject = $storex.projects.activeProject
      if (!activeProject?.$api) return

      const chats = await activeProject.$api.chats.list()
      chats.forEach(chat => registerChatSummary(state, chat))
    },
    async loadRecentChats({ state }, { userId, page, pageSize, append = false } = {}) {
      if (state.recentChatsLoading) return

      $storex.chats.setRecentChatsLoading(true)

      try {
        const activeProject = $storex.projects.activeProject
        if (!activeProject?.$api) return

        const response = await activeProject.$api.chats.getRecentChats({
          filters: { user_id: userId },
          page,
          pageSize
        })

        if (response.error) {
          console.error('[chats store] Error loading recent chats:', response.error)
          return
        }

        // Register every chat so they are available in state.chats
        response.chats.forEach(chat => registerChatSummary(state, chat))

        const ids = response.chats.map(c => c.id)

        if (append) {
          $storex.chats.appendRecentChatIds(ids)
        } else {
          $storex.chats.setRecentChatIds(ids)
        }

        $storex.chats.setRecentChatsHasMore(response.has_next)
        $storex.chats.setRecentChatsPage(page)
      } catch (error) {
        console.error('[chats store] Error loading recent chats:', error)
      } finally {
        $storex.chats.setRecentChatsLoading(false)
      }
    },
    async searchChats({ state }, options = {}) {
      let searchRequest

      if (options instanceof ChatSearchRequest) {
        searchRequest = options
      } else {
        const hasDateRange = !!(options.from_date || options.to_date)
        // Allow date-range-only searches (planning/follow-up), not just text queries.
        if ((!options.query || options.query.trim() === '') && !hasDateRange) {
          $storex.chats.clearSearchResults()
          return null
        }
        searchRequest = new ChatSearchRequest(options)
      }

      const validationErrors = searchRequest.getValidationErrors()
      if (validationErrors.length > 0) {
        console.error('[chats store] Search validation failed:', validationErrors)
        return {
          error: validationErrors[0],
          results: [],
          total: 0,
          page: 1,
          page_size: searchRequest.page_size,
          total_pages: 0,
          has_next: false,
          has_prev: false,
        }
      }

      const project = $storex.projects.activeProject
      const results = await project.$api.chats.search(searchRequest)

      // Search returns chat summaries (last message only) — register them so
      // they get a full reload when opened.
      if (Array.isArray(results?.results)) {
        results.results.forEach(chat => registerChatSummary(state, chat))
      }

      $storex.chats.setSearchResults(results)
      return results
    },
    async clearChatSearch() {
      $storex.chats.clearSearchResults()
    },
    async ensureChatRoot({ state }, chat) {
      if (!chat?.id) return null
      let current = state.chats[chat.id] || {
        id: chat.id,
        owner_project_id: chat.owner_project_id,
        project_id: chat.project_id
      }
      let depth = 0
      while (current?.parent_id && depth < 20) {
        const parent = state.chats[current.parent_id]
        if (!parent) {
          const loadedParent = await $storex.chats.loadChat({
            id: current.parent_id,
            owner_project_id: current.owner_project_id || current.project_id
          })
          if (!loadedParent) break
          current = loadedParent
        } else {
          current = parent
        }
        depth++
      }
      return getRootChat(state, current.id) || current
    },
    async loadChildrenHierarchy({ state, getters }, rootChat, maxDepth = 5) {
      if (!rootChat?.id) return []

      const loadRecursive = async (parentChat, depth = 0) => {
        if (depth >= maxDepth) return []
        const children = getters.chatChildren(parentChat.id) || []
        const result = [...children]
        for (const child of children) {
          result.push(...(await loadRecursive(child, depth + 1)))
        }
        return result
      }

      const descendants = await loadRecursive(rootChat)
      return [rootChat, ...descendants]
    },
    async loadUninitialized({ state }, chat) {
      if (!chat?.id) return null

      const storedChat = state.chats[chat.id]
      if (!storedChat) return null

      const status = state.chatLoadingStatus[chat.id] || ENTITY_STATUS.UNINITIALIZED
      const needsReload = !!state.needsReload[chat.id]

      if (status === ENTITY_STATUS.LOADING) {
        return storedChat
      }

      // A chat loaded from a summary (list/search) must be fully reloaded before
      // being shown, even if its record status is already LOADED.
      if (status === ENTITY_STATUS.UNINITIALIZED || needsReload) {
        return await $storex.chats.loadChat(chat)
      }

      return storedChat
    },
    async saveChat({ state }, chat) {
      const savedChat = await $storex.chats.saveChatInfo(chat)
      if (!savedChat) return null
      if (chat.messages?.length) {
        await $storex.chats.updateMessages({ chat: savedChat, messages: chat.messages })
      }
      return state.chats[savedChat.id] || savedChat
    },
    async saveChatInfo({ state }, chat) {
      const isNew = !chat.id
      if (!isNew) {
        $storex.chats.setChatLoadingStatus({ chatId: chat.id, status: ENTITY_STATUS.SAVING })
      }
      try {
        const project = getChatProject(chat)
        const updatedChat = await project.$api.chats.saveChatInfo({ ...chat, messages: [] })
        registerChat(state, updatedChat)
        $storex.chats.setChatLoadingStatus({ chatId: updatedChat.id, status: ENTITY_STATUS.LOADED })
        // A chat was created or its metadata was written: signal the change so
        // activity feeds (e.g. the solopreneur summary) refresh.
        $storex.chats.setChatActivity({ chatId: updatedChat.id, kind: isNew ? 'created' : 'saved' })
        return state.chats[updatedChat.id]
      } catch (error) {
        console.error('[chats store] Failed to save chat info:', error)
        if (!isNew && chat.id) {
          $storex.chats.setChatLoadingStatus({ chatId: chat.id, status: ENTITY_STATUS.LOADED })
        }
      }
      return null
    },
    async findProjectChat({ state }, { id, owner_project_id }) {
      const project = $storex.projects.allProjectsById[owner_project_id]
      const chat = state.chats[id]
      if (chat) {
        return chat
      }
      const loadedChat = await project.$api.chats.loadChat({ id, owner_project_id })
      registerChat(state, loadedChat)
      // A full chat was fetched — mark it as loaded so later list/search
      // summaries keep its messages instead of clobbering them.
      $storex.chats.setChatLoadingStatus({ chatId: id, status: ENTITY_STATUS.LOADED })
      return state.chats[id] || null
    },
    async loadChat({ state }, chat) {
      if (!chat.id) {
        throw Error(`Can't load a chat without id: ${chat}`)
      }

      const existingChat = state.chats[chat.id]
      const status = state.chatLoadingStatus[chat.id] || ENTITY_STATUS.UNINITIALIZED
      const needsReload = !!state.needsReload[chat.id]

      // Reload unless the full history is already loaded and still fresh.
      if (existingChat && status === ENTITY_STATUS.LOADED && !needsReload) {
        return existingChat
      }

      const project = getChatProject(chat)
      $storex.chats.setChatLoadingStatus({ chatId: chat.id, status: ENTITY_STATUS.LOADING })
      try {
        const loadedChat = await project.$api.chats.loadChat(chat)
        registerChat(state, loadedChat)
        $storex.chats.clearChatNeedsReload(chat.id)
        $storex.chats.setChatLoadingStatus({ chatId: chat.id, status: ENTITY_STATUS.LOADED })
      } catch (error) {
        $storex.chats.setChatLoadingStatus({ chatId: chat.id, status: ENTITY_STATUS.UNINITIALIZED })
      }

      return state.chats[chat.id]
    },
    // Reloads a chat from the server. COALESCED per chat: concurrent calls share
    // the same request. Socket events arrive in bursts while an agent streams and
    // several open paths ask for a fresh copy, so without this the same chat was
    // fetched N times and each response replaced the chat object — cascading a
    // full re-render of every consumer (board columns, cards, message list).
    async reloadChat({ state }, chat) {
      const chatId = chat?.id
      if (!chatId) return null

      // A reload for this chat is already in flight — share its result instead
      // of firing another request that would replace the chat object again.
      if (reloadsInFlight[chatId]) return reloadsInFlight[chatId]

      const project = getChatProject(chat)
      // `.finally()` always runs asynchronously, so the bookkeeping entry is
      // never cleared before it is stored (see the assignment below).
      const request = (async () => {
        const freshChat = await project.$api.chats.loadChat(chat)
        if (freshChat && state.chats[chatId]) {
          // Merge in place, keeping the chat identity AND the identity of the
          // collections that did not change (`sprints`, `board`, `profiles`…).
          // A plain `Object.assign` re-assigned them with brand-new arrays, which
          // invalidated `sprintBoardChats`/`sprintColumns` (and therefore every
          // column and card of the board) on every socket event.
          mergeChat(state.chats[chatId], freshChat)
          if (freshChat.lastMessageAt) state.chats[chatId].lastMessageAt = freshChat.lastMessageAt
        } else if (freshChat && isActiveProjectChat(freshChat)) {
          // Only cache chats owned by the ACTIVE project. The chats store is
          // scoped to it, so caching another project's chat would leak its card
          // into the current board — boards are keyed by title and a board that
          // is copied/moved to another project keeps its title — until the next
          // project reload (that is what produced the transient duplicated cards).
          registerChat(state, freshChat)
        }
        $storex.chats.clearChatNeedsReload(chatId)
        $storex.chats.setChatLoadingStatus({ chatId, status: ENTITY_STATUS.LOADED })
        return state.chats[chatId]
      })().finally(() => {
        delete reloadsInFlight[chatId]
      })

      reloadsInFlight[chatId] = request
      return request
    },
    async addMessage({ state }, { chat, message }) {
      if (!chat?.id) return
      if (!message.content) {
        throw new Error("No empty messages allowed")
      }
      const project = getChatProject(chat)

      try {
        const updatedChat = await project.$api.chats.addMessage(chat.id, message)

        if (updatedChat && updatedChat.messages) {
          state.chats[chat.id].messages = updatedChat.messages
          // Update lastMessageAt with the latest message timestamp
          const lastMessage = updatedChat.messages[updatedChat.messages.length - 1]
          if (lastMessage) {
            const timestamp = lastMessage.timestamp || lastMessage.created_at || new Date().toISOString()
            $storex.chats.updateChatLastMessageAt({ chatId: chat.id, timestamp })
          }
        }

        return updatedChat
      } catch (error) {
        console.error('[chats store] Failed to add message:', error)
        throw error
      }
    },
    async removeMessage({ state }, { chat, messageDocId }) {
      if (!chat?.id || !messageDocId) return

      const project = getChatProject(chat)

      try {
        const updatedChat = await project.$api.chats.removeMessage(chat.id, messageDocId)

        if (updatedChat && updatedChat.messages) {
          state.chats[chat.id].messages = updatedChat.messages
        }

        return updatedChat
      } catch (error) {
        console.error('[chats store] Failed to remove message:', error)
      }
    },
    async updateMessage({ state }, { chat, message }) {
      if (!chat?.id) return

      if (!message?.doc_id) {
        return $storex.chats.addMessage({ chat, message })
      }

      const project = getChatProject(chat)

      try {
        const updatedChat = await project.$api.chats.updateMessage(chat.id, message)
        registerChat(state, updatedChat)
        $storex.chats.setChatLoadingStatus({ chatId: chat.id, status: ENTITY_STATUS.LOADED })

        return updatedChat
      } catch (error) {
        console.error('[chats store] Failed to update message:', error)
        throw error
      }
    },
    // Update only the `content` of an existing message (e.g. an edited canva
    // code block), keeping every other field of the message untouched.
    async updateMessageContent({ state }, { chat, doc_id, content }) {
      if (!chat?.id || !doc_id) return null

      const chatState = state.chats[chat.id]
      const message = chatState?.messages?.find(m => m.doc_id === doc_id)
        || chat.messages?.find(m => m.doc_id === doc_id)
      if (!message) return null

      const updated_at = new Date().toISOString()
      // Optimistic local update so the message refreshes immediately
      message.content = content
      message.updated_at = updated_at

      return await $storex.chats.updateMessage({
        chat,
        message: { ...message, content, updated_at }
      })
    },
    async updateMessages({ state }, { chat, messages }) {
      if (!chat?.id || !messages?.length) return

      const project = getChatProject(chat)

      try {
        let lastResult = null
        for (const message of messages) {
          if (message.doc_id) {
            lastResult = await project.$api.chats.updateMessage(chat.id, message)
          } else {
            lastResult = await project.$api.chats.addMessage(chat.id, message)
          }
        }

        if (lastResult?.messages) {
          state.chats[chat.id].messages = lastResult.messages
          // Update lastMessageAt with the latest message timestamp
          const lastMessage = lastResult.messages[lastResult.messages.length - 1]
          if (lastMessage) {
            const timestamp = lastMessage.timestamp || lastMessage.created_at || new Date().toISOString()
            $storex.chats.updateChatLastMessageAt({ chatId: chat.id, timestamp })
          }
        } else {
          await $storex.chats.reloadChat(chat)
        }

        return state.chats[chat.id]
      } catch (error) {
        console.error('[chats store] Failed to update messages:', error)
        throw error
      }
    },
    async updateChatInfo({ state }, { chat, updates }) {
      if (!chat?.id) return

      const project = getChatProject(chat)

      try {
        const updatedChat = await project.$api.chats.updateMetadata(chat.id, updates)

        if (updatedChat && state.chats[chat.id]) {
          Object.assign(state.chats[chat.id], updates)
        }

        // Metadata written (status, name, board/column …): signal the change.
        // Chats of other projects are not cached here, but the signal is still
        // emitted so feeds that read several projects can refresh.
        $storex.chats.setChatActivity({ chatId: chat.id, kind: 'updated' })

        return updatedChat
      } catch (error) {
        console.error('[chats store] Failed to update chat info:', error)
      }
    },
    async markMessageAsSeen({ state }, { chat_id, message_id, username }) {
      if (!chat_id || !message_id || !username) {
        console.warn('[chats store] markMessageAsSeen called with missing parameters:', { chat_id, message_id, username })
        return null
      }

      const chat = state.chats[chat_id]
      if (!chat) {
        console.warn('[chats store] Chat not found for markMessageAsSeen:', chat_id)
        return null
      }

      const project = getChatProject(chat)

      try {
        const response = await project.$api.chats.markMessageAsSeen({
          chat_id,
          message_id,
          username
        })

        if (response && chat.messages) {
          const messageIndex = chat.messages.findIndex(m => m.doc_id === message_id)
          if (messageIndex !== -1) {
            const message = chat.messages[messageIndex]
            if (!Array.isArray(message.read_by)) {
              message.read_by = []
            }
            if (!message.read_by.includes(username)) {
              message.read_by = [...message.read_by, username]
            }
          }
        }

        return response
      } catch (error) {
        console.error('[chats store] Failed to mark message as seen:', error)
        return null
      }
    },
    async deleteChat({ state, getters }, chat) {
      if (!chat?.id) return

      const descendants = getters.chatDescendants(chat.id) || []
      const chatIds = [chat.id, ...(descendants || []).map(c => c.id)]

      if (!chat.temp) {
        const project = getChatProject(chat)
        await project.$api.chats.delete(chat)
      }

      chatIds.forEach(id => {
        try {
          $storex.views.removePanelFromDesktop(id)
        } catch (error) {
          console.warn(`[chats store] Could not remove panel for chat ${id}:`, error)
        }
      })

      chatIds.forEach(id => {
        const app = Object.values($storex.ui.openApps).find(app => app.tabId === id)
        if (app) {
          $storex.ui.closeApp(app)
        }
      })

      chatIds.forEach(id => {
        delete state.chats[id]
        delete state.chatLoadingStatus[id]
        delete state.needsReload[id]
      })

      if (chatIds.includes(state.activeChatId)) {
        $storex.chats.clearActiveChat()
      }

      // A deleted ticket is a change too: feeds must drop the row.
      $storex.chats.setChatActivity({ chatId: chat.id, kind: 'deleted' })
    },
    async setActiveChat({ state }, activeChat) {
      const { id, project_id, owner_project_id, name } = activeChat || {}

      if (!id) {
        $storex.chats.clearActiveChat()
        return
      }

      // Load/reload the chat data without triggering setActiveChat again
      await $storex.chats.reloadChat({ id, project_id, owner_project_id })

      // Set the active chat id — activeChat getter will resolve it from chats map
      $storex.chats.setActiveChatId(id)

      // Desktop "vibe" mode renders its own layout, so it must not force an app
      // to open on top of it.
      if (!$storex.ui.isMobile && $storex.ui.viewMode === 'vibe') {
        return
      }

      // Unified opener: a dockview panel on desktop, its own route on mobile.
      // `openChat` → `openApp('chat', …)` decides which, so the store no longer
      // branches on isDesktopMode / navigation.chats.open itself.
      const chat = $storex.chats.activeChat
      if (chat) {
        $storex.ui.openChat({ ...chat, name: name || chat.name })
      }
    },
    async createNewChat({ state }, chat) {
      chat = {
        mode: 'chat',
        profiles: [],
        chat_index: 0,
        messages: [],
        auto_initialize: !chat.name,
        owner_project_id: chat.owner_project_id || $storex.projects.activeProject.project_id,
        ...chat
      }

      // A child chat (subtask / thread) belongs to the SAME sprint(s) as its
      // parent when it does not define its own sprint info. The parent may be
      // passed inline (chat.parent) or only referenced by parent_id.
      if (chat.parent_id && !chat.sprints?.length) {
        const parentChat = chat.parent || state.chats?.[chat.parent_id]
        if (parentChat?.sprints?.length) {
          chat.sprints = [...parentChat.sprints]
        }
      }

      $storex.chats.setChatLoadingStatus({ chatId: chat.id, status: ENTITY_STATUS.UNINITIALIZED })
      if (!chat.temp) {
        return await $storex.chats.saveChat(chat)
      }
      return state.chats[chat.id]
    },
    async createNewChatWithProject({ state }, { project, chat = {} }) {
      const chatData = {
        ...chat,
        owner_project_id: project?.project_id || $storex.projects.activeProject.project_id
      }
      return await $storex.chats.createNewChat(chatData)
    },
    async createChatFromTemplate({ state }, { template, project }) {
      if (!template?.id) {
        console.error('[chats store] Cannot create chat from invalid template')
        return null
      }

      const newMessages = (template.messages || []).map(msg => ({
        ...msg,
        doc_id: null,
        id: null
      }))

      const newChat = {
        ...template,
        is_template: false,
        id: null,
        messages: newMessages,
        owner_project_id: project?.project_id || $storex.projects.activeProject.project_id
      }

      return await $storex.chats.createNewChat(newChat)
    },
    // Persist a fully-populated chat (used by board import) in a SINGLE request
    // and register it in the store. Unlike `createNewChat` — which saves the
    // metadata first and then writes each message with its own request — this
    // sends the whole message history inline (PUT /api/chats?chat_only=0), so
    // importing a board with hundreds of tasks stays fast.
    async importChat({ state }, chat) {
      if (!chat?.id) return null
      const project = getChatProject(chat) || $storex.projects.activeProject
      if (!project?.$api) return null

      const savedChat = await project.$api.chats.save(chat)
      const saved = savedChat || chat

      // Only cache chats that belong to the ACTIVE project: the chats store is
      // scoped to it (it is cleared on project change), so caching another
      // project's chats would leak the imported cards into the current
      // project's board views — and let `deleteBoard` destroy them on a move.
      if (project.project_id !== $storex.projects.activeProject?.project_id) {
        $storex.chats.setChatActivity({ chatId: saved.id, kind: 'created' })
        return saved
      }

      registerChat(state, saved)
      $storex.chats.clearChatNeedsReload(saved.id)
      $storex.chats.setChatLoadingStatus({ chatId: saved.id, status: ENTITY_STATUS.LOADED })
      $storex.chats.setChatActivity({ chatId: saved.id, kind: 'created' })
      return state.chats[saved.id]
    },
    async createNewChatFromUrl({ state }, chat) {
      chat = {
        mode: 'chat',
        profiles: [],
        chat_index: 0,
        ...chat
      }
      const project = getChatProject(chat)
      const savedChat = await project.$api.chats.fromUrl(chat)
      registerChat(state, savedChat)
      $storex.chats.setChatLoadingStatus({ chatId: savedChat.id, status: ENTITY_STATUS.LOADED })
      $storex.chats.setChatActivity({ chatId: savedChat.id, kind: 'created' })
      if (!chat.temp) {
        await $storex.chats.setActiveChat(savedChat)
      }
      return state.chats[savedChat?.id]
    },
    async createNewBoardChat({ state }, { boardTitle, columnTitle, chat }) {
      boardTitle = boardTitle || chat.board
      columnTitle = columnTitle || chat.column
      const newColumn = {
        title: columnTitle,
        chats: []
      }
      if (!$storex.projects.kanban) {
        await $storex.projects.loadKanban()
      }
      if (!$storex.projects.kanban.boards[boardTitle]) {
        $storex.projects.kanban.boards = {
          ...$storex.projects.kanban.boards,
          [boardTitle]: {
            columns: [newColumn]
          }
        }
      }
      // The board may be missing from the kanban state, have no columns yet, or
      // not have the target column — never assume the lookups resolve, a chat
      // must still be created when the board layout is incomplete.
      const board = $storex.projects.allBoards.find(({ title }) => title === boardTitle)
      let column = board?.columns?.find(({ title }) => title === columnTitle)
      if (!column) {
        const boardState = $storex.projects.kanban.boards[boardTitle] || { columns: [] }
        boardState.columns = [...(boardState.columns || []), newColumn]
        $storex.projects.kanban.boards = {
          ...$storex.projects.kanban.boards,
          [boardTitle]: boardState
        }
        column = newColumn
      }

      const newChat = await $storex.chats.createNewChat({
        board: boardTitle,
        column: columnTitle,
        ...chat
      })
      await $storex.chats.setActiveChat(newChat)
      column.chats = [...column?.chats || [], newChat.id]
      $storex.projects.saveKanban($storex.projects.kanban)
      return newChat
    },
    // Mark a chat as "processing" the moment the user sends a message, before
    // the server streams its first chunk back. This gives immediate UI feedback
    // and is shared by the chat list, kanban and tab indicators. The underlying
    // `setChatUpdating` mutation schedules an auto-reset timeout, so a
    // non-responsive server falls back to the idle state automatically.
    startChatProcessing(_, { chatId }) {
      if (!chatId) return
      $storex.chats.setChatUpdating({ chatId, updating: true })
    },
    async onChatEvent({ state }, { event, data }) {
      const {
        chat: {
          id: chatId,
          owner_project_id
        },
        message,
        event_type,
        type,
        codx_path
      } = data

      if (event_type === 'error') {
        $storex.ui.addNotification({ text: message, type: event_type })
      }

      // Cache the activity signal BEFORE the active-project guard below: socket
      // events are broadcast for EVERY project, and the consumers of this signal
      // (e.g. the solopreneur summary) read the activity of several projects.
      // This replaces the old approach of scanning the transient
      // `session.events` log from every interested component.
      if (chatId && (type === 'changed' || event_type === 'done')) {
        $storex.chats.setChatActivity({
          chatId,
          kind: event_type === 'done' ? 'done' : 'changed'
        })
      }

      if (chatId) {
        // Socket events are broadcast for EVERY project. Ignore chats that do
        // not belong to the active project: the chats store is scoped to it, so
        // caching a foreign chat would inject duplicate cards into the current
        // board. This happens while copying/moving a board to another project —
        // each imported chat is saved there and emits a "changed" event, and
        // `importChat` already refuses to cache it, but this event path used to
        // re-register it (transient duplicates that vanish after a reload).
        if (!state.chats[chatId] && !isActiveProjectChat({ owner_project_id })) {
          return
        }

        if (type === 'changed' || !state.chats[chatId]) {
          await $storex.chats.reloadChat({ id: chatId, owner_project_id })
        }
        const chat = state.chats[chatId]
        if (chat && message) {
          const allMessagesDone = chat.messages.every(m => m.done)
          if (allMessagesDone) {
            $storex.chats.setChatUpdating({ chatId, updating: false })
          } else {
            $storex.chats.setChatUpdating({ chatId, updating: true })
          }
        }
      }
    },
    async readFile({ state }, { chat, file }) {
      const project = getChatWorkingProject(chat)
      return project.$api.files.read(file)
    },
    async writeFile({ state }, { chat, file, content }) {
      const project = getChatWorkingProject(chat)
      return project.$api.files.write(file, content)
    },
    async getChatProfiles({}, chat) {
      if (!chat?.id) return []

      const projectId = chat.project_id || chat.owner_project_id
      if (!projectId) return []

      const project = $storex.projects.allProjectsById[projectId]
      if (!project) return []

      if (!$storex.profiles.profilesByProject[projectId]) {
        await $storex.profiles.loadProjectProfiles(project)
      }

      return $storex.profiles.profilesByProject[projectId] || []
    },
    async updateChatStatus({ state }, { chat, status }) {
      if (!chat?.id) return

      const project = getChatProject(chat)

      try {
        const updatedChat = await project.$api.chats.updateMetadata(chat.id, { status })

        if (updatedChat && state.chats[chat.id]) {
          state.chats[chat.id].status = updatedChat.status
        }

        // Status change of a ticket: same activity signal as a metadata write.
        $storex.chats.setChatActivity({ chatId: chat.id, kind: 'status' })

        return updatedChat
      } catch (error) {
        console.error('[chats store] Failed to update chat status:', error)
      }
    },
    // ── Threads ─────────────────────────────────────────────────────────────
    // A thread is a chat bound to ONE message of its parent chat:
    //   parent_id  → the chat that owns the message
    //   message_id → the message the thread answers
    // Creating is idempotent: when a thread already exists for that message it
    // is just opened. The thread starts empty, so creating it never triggers a
    // model run — the user writes the first thread message.
    async createNewThread({ getters }, { chat, mode, message }) {
      if (!chat?.id) return null

      const messageId = message?.doc_id || message?.id
      if (!messageId) return null

      // Prefer a child of this chat, then any already loaded chat bound to the
      // same message (covers threads created before parent_id was set right).
      const existingThread = getters.chatChildren(chat.id)
        .find(c => c.message_id === messageId) ||
        $storex.chats.allChats.find(c => c.message_id === messageId)

      if (existingThread) {
        await $storex.chats.setActiveChat(existingThread)
        return existingThread
      }

      const threadData = {
        name: threadChatName(message),
        mode: mode || chat.mode || 'chat',
        parent_id: chat.id,
        message_id: messageId,
        owner_project_id: chat.owner_project_id || chat.project_id,
        project_id: chat.project_id || chat.owner_project_id,
        board: chat.board,
        column: chat.column,
        file_list: [...(chat.file_list || [])],
        profiles: [...(chat.profiles || [])],
        messages: []
      }

      // Threads live in the same board/column as their parent so they stay in
      // the same kanban context. Chats without a board are still created (and
      // opened) — they just don't show up as a card.
      const threadChat = chat.board
        ? await $storex.chats.createNewBoardChat({
            boardTitle: chat.board,
            columnTitle: chat.column,
            chat: threadData
          })
        : await $storex.chats.createNewChat(threadData)

      if (!threadChat) return null

      // createNewBoardChat already activates the new chat
      if (!chat.board) {
        await $storex.chats.setActiveChat(threadChat)
      }
      return threadChat
    },
  }
)