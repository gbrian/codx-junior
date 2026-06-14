import { getterTree, mutationTree, actionTree } from 'typed-vuex'
import store, { $storex } from '.'
import { API } from '../api/api'
import { v4 as uuidv4 } from 'uuid'

export const namespaced = true

export const state = () => ({
  chats: {},
  activeChat: null,
  chatEvents: {}, // { [chatId]: { updatingCount: number, updatingAt: string | null, timeoutId: number | null } }
})

// Helper to register a chat into chatsById
function registerChatById(state, chat) {
  if (chat?.id) {
    state.chats[chat.id] = chat
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

export const getters = getterTree(state, {
  allChats: state => Object.values(state.chats || {}),
  allTags: state => new Set(Object.values(state.chats || {})?.map(c => c.tags).reduce((a, b) => a.concat(b), []) || []),
  allPRs: state => Object.values(state.chats || {}).filter(c => c.pr_view?.from_branch),
  isChatUpdating: state => (chatId) => {
    return (state.chatEvents[chatId]?.updatingCount || 0) > 0
  },
  activeChat: state => state.activeChat,
})

export const mutations = mutationTree(state, {
  setChatUpdating(state, { chatId, updating }) {
    const current = state.chatEvents[chatId]?.updatingCount || 0
    const prevTimeoutId = state.chatEvents[chatId]?.timeoutId || null

    // Clear any existing auto-reset timeout
    if (prevTimeoutId) {
      clearTimeout(prevTimeoutId)
    }

    if (!updating) {
      // Done event: reset count to 0
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
      // Streaming chunk: increment count and schedule a 10s auto-reset fallback
      // in case the "done" event is missed from the server.
      // Using 10s to accommodate slow models that may have long pauses between chunks.
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
    // Replace array reference to trigger Vue reactivity
    chat.messages = [...(chat.messages || []), message]
    // Keep activeChat in sync
    if (state.activeChat?.id === chatId) {
      state.activeChat = state.chats[chatId]
    }
  },
})

export const actions = actionTree(
  { state, getters, mutations },
  {
    async init ({ state }) {
    },
    async loadChats({ state }) {
      const chats = await API.chats.list()
      state.chats = {
        ...state.chats,
        ...chats.reduce((acc, chat) => ({ ...acc, [chat.id]: chat }), {})
      }
      // Refresh activeChat reference from updated chats map
      if (state.activeChat?.id) {
        state.activeChat = state.chats[state.activeChat.id] || state.activeChat
      }
    },
    async saveChat({ state }, chat) {
      const savedChat = await API.chats.save(chat)
      registerChatById(state, savedChat)
    },
    async saveChatInfo(_, chat) {
      await API.chats.saveChatInfo({ ...chat, messages: [] })
      await $storex.chats.loadChat(chat)
    },
    async findProjectChat({ state }, { id, owner_project_id }) {
      const project = $storex.projects.allProjectsById[owner_project_id]
      const chat = state.chats[id]
      if (chat) {
        registerChatById(state, chat)
        return chat
      }
      const loadedChat = await project.$api.chats.loadChat({ id, owner_project_id })
      if (loadedChat) {
        registerChatById(state, loadedChat)
        return loadedChat
      }
      return null
    },
    async loadChat({ state }, chat) {
      if (!state.chats[chat.id]) {
        const project = getChatProject(chat)
        chat = await project.$api.chats.loadChat(chat)
        state.chats[chat.id] = chat
      }
      registerChatById(state, state.chats[chat.id])
      // Keep activeChat reference in sync if this is the active chat
      if (state.activeChat?.id === chat.id) {
        state.activeChat = state.chats[chat.id]
      }
      return state.chats[chat.id]
    },
    async reloadChat({ state }, chat) {
      const project = getChatProject(chat)
      const freshChat = await project.$api.chats.loadChat(chat)
      if (freshChat && state.chats[chat.id]) {
        // Merge fresh data into existing object to preserve Vue reactivity
        // and avoid unmounting ChatView
        Object.assign(state.chats[chat.id], freshChat)
      } else {
        state.chats[chat.id] = freshChat
      }
      // Keep activeChat reference in sync if this is the active chat
      if (state.activeChat?.id === chat.id) {
        state.activeChat = state.chats[chat.id]
      }
      return state.chats[chat.id]
    },
    async deleteChat({ state }, chat) {
      if (!chat.temp) {
        await API.chats.delete(chat)
      }
      if (state.chats[chat.id]) {
        delete state.chats[chat.id]
      }
      // Clear activeChat if the deleted chat was active
      if (state.activeChat?.id === chat.id) {
        state.activeChat = null
      }
    },
    async setActiveChat({ state }, activeChat) {
      const { id, project_id } = activeChat || {}
      if (id) {
        await $storex.chats.reloadChat({ id, project_id })
      }
      // Resolve chat from chats map — single source of truth
      const chat = (id && state.chats[id]) || null
      state.activeChat = chat

      // On desktop, notify the UI to open the chat panel
      if (!$storex.ui.isMobile && chat) {
        $storex.ui.openChat(chat)
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
        ...chat
      }
      state.chats[chat.id] = chat
      registerChatById(state, chat)
      if (!chat.temp) {
        await $storex.chats.saveChat(chat)
      }
      return state.chats[chat.id]
    },
    async createNewChatFromUrl({ state }, chat) {
      chat = {
        id: uuidv4(),
        mode: 'chat',
        profiles: [],
        chat_index: 0,
        ...chat
      }
      state.chats[chat.id] = await API.chats.fromUrl(chat)
      registerChatById(state, state.chats[chat.id])
      if (!chat.temp) {
        state.activeChat = state.chats[chat.id]
      }
      return state.chats[chat.id]
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
          const isDone = event_type === 'done'
          const currentMessage = chat.messages.find(m => m.doc_id === message.doc_id)

          if (currentMessage) {
            if (isDone) {
              Object.assign(currentMessage, message)
            } else {
              currentMessage.is_thinking = message.is_thinking
              currentMessage.done = message.done
              currentMessage.meta_data = message.meta_data
              if (message.is_thinking) {
                currentMessage.think += message.think
              } else {
                currentMessage.content += message.content
              }
              currentMessage.updated_at = new Date().toISOString()
            }
          } else {
            // Use mutation to ensure reactivity when adding new messages
            $storex.chats.addMessageToChat({ chatId, message })
          }

          // Check if all messages in the chat are done — if so, reset the updating flag.
          // This is the primary mechanism to detect completion, since the "done" event
          // per message reliably sets message.done = true.
          const allMessagesDone = chat.messages.every(m => m.done)
          if (allMessagesDone) {
            $storex.chats.setChatUpdating({ chatId, updating: false })
          } else {
            // Still streaming: keep the updating flag active with a 10s fallback timeout
            // to accommodate slow models with long pauses between chunks.
            $storex.chats.setChatUpdating({ chatId, updating: !isDone })
          }
        }
        registerChatById(state, chat)
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