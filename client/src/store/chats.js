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
})

function registerChat(state, chat) {
  if (!chat?.id) {
    console.error('[chats store] Attempted to store a null/invalid chat:', chat)
    return
  }
  const existingChat = state.chats[chat.id] || {}
  
  // Update lastMessageAt when registering a chat with messages
  const lastMessage = chat.messages?.[chat.messages.length - 1]
  const lastMessageAt = lastMessage?.timestamp || lastMessage?.created_at || chat.updated_at || new Date().toISOString()
  
  state.chats[chat.id] = {
    ...existingChat,
    ...chat,
    lastMessageAt
  }
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

  clearActiveChat(state) {
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
    state.chatLoadingStatus = {
      ...state.chatLoadingStatus,
      [chatId]: status
    }
  },

  setChatNeedsReload(state, chatId) {
    if (!chatId) return
    state.needsReload = { ...state.needsReload, [chatId]: true }
  },

  clearChatNeedsReload(state, chatId) {
    if (!chatId || !state.needsReload[chatId]) return
    const next = { ...state.needsReload }
    delete next[chatId]
    state.needsReload = next
  },

  setChatUpdating(state, { chatId, updating }) {
    const current = state.chatEvents[chatId]?.updatingCount || 0
    const prevTimeoutId = state.chatEvents[chatId]?.timeoutId || null

    if (prevTimeoutId) {
      clearTimeout(prevTimeoutId)
    }

    if (!updating) {
      state.chatEvents = {
        ...state.chatEvents,
        [chatId]: {
          ...(state.chatEvents[chatId] || {}),
          updatingCount: 0,
          updatingAt: null,
          timeoutId: null,
        }
      }
    } else {
      const timeoutId = setTimeout(() => {
        $storex.chats.setChatUpdating({ chatId, updating: false })
      }, 10000)

      state.chatEvents = {
        ...state.chatEvents,
        [chatId]: {
          ...(state.chatEvents[chatId] || {}),
          updatingCount: current + 1,
          updatingAt: new Date().toISOString(),
          timeoutId,
        }
      }
    }
  },

  clearChats(state) {
    state.chats = {}
    state.activeChatId = null
    state.chatLoadingStatus = {}
    state.needsReload = {}
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
    async reloadChat({ state }, chat) {
      const project = getChatProject(chat)
      const freshChat = await project.$api.chats.loadChat(chat)
      if (freshChat && state.chats[chat.id]) {
        Object.assign(state.chats[chat.id], freshChat)
      } else {
        registerChat(state, freshChat)
      }
      $storex.chats.clearChatNeedsReload(chat.id)
      $storex.chats.setChatLoadingStatus({ chatId: chat.id, status: ENTITY_STATUS.LOADED })
      return state.chats[chat.id]
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
    },
    async setActiveChat({ state }, activeChat) {
      const { id, project_id, owner_project_id, name } = activeChat || {}

      if (!id) {
        $storex.chats.clearActiveChat()
        return
      }

      await $storex.chats.reloadChat({ id, project_id, owner_project_id })
      $storex.chats.setActiveChatId(id)

      if (!$storex.ui.isDesktopMode) {
        const chatName = name || `chat-${id}`
        $storex.$router.$navigation.chats.open(id, chatName)
      }

      if (!$storex.ui.isMobile && $storex.ui.viewMode !== 'vibe') {
        $storex.ui.openChat($storex.chats.activeChat)
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
      let column = $storex.projects.allBoards
                        .find(({ title }) => title === boardTitle).columns.find(({ title }) => title === columnTitle)
      if (!column) {
        column = newColumn
        $storex.projects.kanban.boards[boardTitle].columns.push(column)
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
    async createNewThread(_, { chat, mode, message }) {
      const { files, profiles, doc_id: subtaskMessageId } = message
      const findChild = $storex.chats.allChats.find(c => c.message_id === subtaskMessageId)

      if (!findChild) {
        const boardTitle = chat.board
        const columnTitle = chat.column
        await $storex.chats.createNewBoardChat({
          boardTitle, columnTitle,
          chat: {
            parent: chat,
            name: `${subtaskMessageId} - thread`,
            project_id: chat.project_id,
            parent_id: chat.parent_id,
            message_id: subtaskMessageId,
            file_list: files,
            profiles: profiles,
            mode,
            board: chat.board,
            column: chat.column,
            activateChat: true,
            messages: [{ ...message, doc_id: null }]
          }
        })
      } else {
        await $storex.chats.setActiveChat(findChild)
      }
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

      if (chatId) {
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
        
        return updatedChat
      } catch (error) {
        console.error('[chats store] Failed to update chat status:', error)
      }
    },
    async createNewThread(_, { chat, mode, message }) {
      const { files, profiles, doc_id: subtaskMessageId } = message
      const findChild = $storex.chats.allChats.find(c => c.message_id === subtaskMessageId)

      // Thread already exists -> just open it
      if (findChild) {
        await $storex.chats.setActiveChat(findChild)
        return findChild
      }

      const boardTitle = chat.board
      const columnTitle = chat.column
      const newChat = await $storex.chats.createNewBoardChat({
        boardTitle, columnTitle,
        chat: {
          name: `${subtaskMessageId} - thread`,
          owner_project_id: chat.owner_project_id || chat.project_id,
          project_id: chat.project_id || chat.owner_project_id,
          parent_id: chat.id,
          message_id: subtaskMessageId,
          file_list: files,
          profiles: profiles,
          mode: mode || chat.mode || 'chat',
          board: chat.board,
          column: chat.column,
          activateChat: true,
          messages: [{ ...message, doc_id: null }]
        }
      })

      // A thread must actually run like a task: without this the new thread
      // chat is created empty and no task/answer is generated.
      await $storex.projects.chatWihProject(newChat)
      return newChat
    },
  }
)