import { getterTree, mutationTree, actionTree } from 'typed-vuex'
import store, { $storex } from '.'
import { v4 as uuidv4 } from 'uuid'
import { ChatSearchRequest } from '@/api/model/ChatSearchRequest'

export const namespaced = true

export const state = () => ({
  chats: {},
  activeChatId: null,
  chatEvents: {},
  searchResults: null,
})

function registerChat(state, chat) {
  if (!chat?.id) {
    console.error('[chats store] Attempted to store a null/invalid chat:', chat)
    return
  }
  const existingChat = state.chats[chat.id] || {}
    // Merge while preserving messages
    state.chats[chat.id] = {
    ...existingChat,
      ...chat,
    messages: chat.messages || existingChat?.messages,
    status: chat.status || existingChat?.status || 'uninitialized'
  }
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
  isChatUpdating: state => (chatId) => {
    return (state.chatEvents[chatId]?.updatingCount || 0) > 0
  },
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

  addMessageToChat(state, { chatId, message }) {
    const chat = state.chats[chatId]
    if (!chat) return
      chat.messages = [...(chat.messages || []), message]
  },
  setChatStatus(state, { chatId, status }) {
    const chat = state.chats[chatId]
    if (!chat) return
    state.chats[chatId] = {
      ...chat,
      status
    }
  }
})

export const actions = actionTree(
  { state, getters, mutations },
  {
    async init ({ state }) {
    },
    async loadChats({ state }) {
      const chats = await $storex.api.chats.list()
      chats.forEach(chat => {
        if (chat.id && !state.chats[chat.id]) {
          registerChat(state, chat)
        }
      })
    },
    async searchChats({ state }, options = {}) {
      let searchRequest
      
      // Accept ChatSearchRequest instance or plain object
      if (options instanceof ChatSearchRequest) {
        searchRequest = options
      } else {
        // Validate query before creating request
        if (!options.query || options.query.trim() === '') {
          $storex.chats.clearSearchResults()
          return null
        }
        searchRequest = new ChatSearchRequest(options)
      }

      // Validate request
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

      // Skip if already loaded or currently loading
      if (storedChat.status === 'loaded') {
        return storedChat
      }

      if (storedChat.status === 'loading') {
        // Chat is already loading, return it as-is
        return storedChat
      }

      // Load if uninitialized
      if (storedChat.status === 'uninitialized') {
        return await $storex.chats.loadChat(chat)
      }

      return storedChat
    },
    async saveChat({ state }, chat) {
      $storex.chats.setChatStatus({ chatId: chat.id, status: 'saving' })
      try {
        const project = getChatProject(chat)
        await project.$api.chats.save(chat)
        await $storex.chats.loadChat(chat)
        $storex.chats.setChatStatus({ chatId: chat.id, status: 'loaded' })
      } catch (error) {
        $storex.chats.setChatStatus({ chatId: chat.id, status: 'loaded' })
      }
    },
    async saveChatInfo(_, chat) {
      $storex.chats.setChatStatus({ chatId: chat.id, status: 'saving' })
      try {
        const project = getChatProject(chat)
        await project.$api.chats.saveChatInfo({ ...chat, messages: [] })
        await $storex.chats.loadChat(chat)
        $storex.chats.setChatStatus({ chatId: chat.id, status: 'loaded' })
      } catch (error) {
        $storex.chats.setChatStatus({ chatId: chat.id, status: 'loaded' })
      }
    },
    async findProjectChat({ state }, { id, owner_project_id }) {
      const project = $storex.projects.allProjectsById[owner_project_id]
      const chat = state.chats[id]
      if (chat) {
        return chat
      }
      const loadedChat = await project.$api.chats.loadChat({ id, owner_project_id })
      registerChat(state, loadedChat)
      return state.chats[id] || null
    },
    async loadChat({ state }, chat) {
      if (!state.chats[chat.id]) {
        const project = getChatProject(chat)
        $storex.chats.setChatStatus({ chatId: chat.id, status: 'loading' })
        try {
          const loadedChat = await project.$api.chats.loadChat(chat)
          registerChat(state, loadedChat)
          $storex.chats.setChatStatus({ chatId: chat.id, status: 'loaded' })
        } catch (error) {
          $storex.chats.setChatStatus({ chatId: chat.id, status: 'uninitialized' })
        }
      } else if (state.chats[chat.id].status === 'uninitialized') {
        const project = getChatProject(chat)
        $storex.chats.setChatStatus({ chatId: chat.id, status: 'loading' })
        try {
          const loadedChat = await project.$api.chats.loadChat(chat)
          registerChat(state, loadedChat)
          $storex.chats.setChatStatus({ chatId: chat.id, status: 'loaded' })
        } catch (error) {
          $storex.chats.setChatStatus({ chatId: chat.id, status: 'uninitialized' })
        }
      }
      return state.chats[chat.id]
    },
    async reloadChat({ state }, chat) {
      const project = getChatProject(chat)
      const freshChat = await project.$api.chats.loadChat(chat)
      if (freshChat && state.chats[chat.id]) {
        Object.assign(state.chats[chat.id], { ...freshChat, status: 'loaded' })
      } else {
        registerChat(state, { ...freshChat, status: 'loaded' })
      }
      return state.chats[chat.id]
    },
    async addMessage({ state }, { chat, message }) {
      if (!chat?.id) return

      const project = getChatProject(chat)
      
      // Generate doc_id immediately if missing
      if (!message.doc_id) {
        message.doc_id = uuidv4()
      }

      // Add to local state immediately (optimistic)
      $storex.chats.addMessageToChat({ chatId: chat.id, message })

      try {
        // Persist via API (merge-safe on backend)
        const updatedChat = await project.$api.chats.addMessage(chat.id, message)
        
        // Update local store with persisted version
        if (updatedChat && updatedChat.messages) {
          state.chats[chat.id].messages = updatedChat.messages
        }
        
        return updatedChat
      } catch (error) {
        console.error('[chats store] Failed to add message:', error)
        throw error
      }
    },
    async deleteChat({ state, getters }, chat) {
      if (!chat?.id) return

      const descendants = getters.chatDescendants(chat.id) || []

      if (!chat.temp) {
        const project = getChatProject(chat)
        await project.$api.chats.delete(chat)
      }

      const ids = new Set([chat.id, ...(descendants || []).map(c => c.id)])
      ids.forEach(id => {
        delete state.chats[id]
      })

      if (ids.has(state.activeChatId)) {
        $storex.chats.clearActiveChat()
      }
    },
    async setActiveChat({ state }, activeChat) {
      const { id, project_id, owner_project_id } = activeChat || {}

      if (!id) {
        $storex.chats.clearActiveChat()
        return
      }

      await $storex.chats.reloadChat({ id, project_id, owner_project_id })

      $storex.chats.setActiveChatId(id)

      if (!$storex.ui.isMobile && $storex.ui.viewMode !== 'vibe') {
        $storex.ui.openChat($storex.chats.activeChat)
      }
    },
    async createNewChat({ state }, chat) {
      chat = {
        id: uuidv4(),
        mode: 'chat',
        profiles: [],
        chat_index: 0,
        messages: [],
        auto_initialize: !chat.name,
        owner_project_id: chat.owner_project_id || $storex.projects.activeProject.project_id,
        status: 'uninitialized',
        ...chat
      }
      registerChat(state, chat)
      if (!chat.temp) {
        await $storex.chats.saveChat(chat)
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
    async createNewChatFromUrl({ state }, chat) {
      chat = {
        id: uuidv4(),
        mode: 'chat',
        profiles: [],
        chat_index: 0,
        status: 'uninitialized',
        ...chat
      }
      const project = getChatProject(chat)
      const savedChat = await project.$api.chats.fromUrl(chat)
      registerChat(state, { ...savedChat, status: 'loaded' })
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
        /* // We have a conflict with the relaodChat disabled until fixing, the reload will update the chat messages 
        const chat = state.chats[chatId]
        if (chat && message) {
          const isDone = event_type === 'done'
          const currentMessage = chat.messages.find(m => m.doc_id === message.doc_id)

          const allMessagesDone = chat.messages.every(m => m.done)
          if (allMessagesDone) {
            $storex.chats.setChatUpdating({ chatId, updating: false })
          } else {
            $storex.chats.setChatUpdating({ chatId, updating: !isDone })
          }
        }
        */
      }
    },
    async readFile({ state }, { chat, file }) {
      const project = getChatWorkingProject(chat)
      return project.$api.files.read(file)
    },
    async writeFile({ state }, { chat, file, content }) {
      const project = getChatWorkingProject(chat)
      return project.$api.files.write(file, content)
    }
  }
)