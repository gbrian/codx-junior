/**
 * Chats API module
 * Handles all chat-related API operations: list, search, CRUD, export, streaming
 */

export const chatsModule = (API) => ({
  stream() {
    return API.get('/api/stream')
  },

  async list(filters) {
    let qs = ""
    if (filters) {
      const params = Object.entries(filters)
        .map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(value)}`)
        .join("&")
      qs = `?${params}`
    }
    return API.get(`/api/chats${qs}`)
  },

  async loadChat({ id, file_path }) {
    return API.get(`/api/chats?file_path=${file_path || ''}&id=${id || ''}`)
  },

  async search(searchRequest) {
    // Accept ChatSearchRequest object or plain object
    const payload = searchRequest.toJSON ? searchRequest.toJSON() : searchRequest
    return API.post('/api/chats/search', payload)
  },

  async exportChat({ id, exportFormat, clipboard }) {
    const path = `/api/chats?export_format=${exportFormat}&id=${id}`
    if (clipboard) {
      return API.get(path)
    } else {
      const url = API.connection.prepareUrl(path)
      window.open(url)
    }
  },

  async newChat() {
    return {
      id: new Date().getTime(),
      name: "New chat"
    }
  },

  async message(chat) {
    return API.post('/api/chats', chat)
  },

  async addMessage(chatId, message) {
    return API.post('/api/chats/message', { chat_id: chatId, message })
  },

  async updateMessage(chatId, message) {
    return API.put('/api/chats/message', { chat_id: chatId, message })
  },

  async removeMessage(chatId, messageDocId) {
    return API.delete(`/api/chats/message?chat_id=${chatId}&message_doc_id=${messageDocId}`)
  },

  async updateMetadata(chatId, metadata) {
    return API.post('/api/chats/metadata', { chat_id: chatId, metadata })
  },

  async fromUrl(chat) {
    return API.post('/api/chats/from-url', chat)
  },

  async subTasks(chat) {
    return API.post('/api/chats/sub-tasks', chat)
  },

  save(chat) {
    return API.put(`/api/chats?chat_only=0`, chat)
  },

  saveChatInfo(chat) {
    return API.put(`/api/chats?chat_only=1`, chat)
  },

  delete(chat) {
    return API.delete(`/api/chats?chat_id=${chat.id}`)
  },

  cancelMessage(cancellationTokenId) {
    return API.post(`/api/chat/cancel`, { token_id: cancellationTokenId })
  },

  // ── Message Archive Endpoints ──────────────────────────────────────────

  async getArchivedMessages(chatId, filters = {}) {
    let qs = ""
    if (filters) {
      const params = new URLSearchParams(filters).toString()
      qs = params ? `?${params}` : ""
    }
    return API.get(`/api/analytics/chat-sessions/${chatId}/messages${qs}`)
  },

  async getCompleteContext(chatId, filters = {}) {
    let qs = ""
    if (filters) {
      const params = new URLSearchParams(filters).toString()
      qs = params ? `?${params}` : ""
    }
    return API.get(`/api/analytics/chat-sessions/${chatId}/complete-context${qs}`)
  },

  // ── Admin Message Archive Endpoints ────────────────────────────────────

  async adminGetArchivedMessages(chatId, filters = {}) {
    let qs = ""
    if (filters) {
      const params = new URLSearchParams(filters).toString()
      qs = params ? `?${params}` : ""
    }
    return API.get(`/api/analytics/admin/chat-sessions/${chatId}/messages${qs}`)
  },

  async adminGetCompleteContext(chatId, filters = {}) {
    let qs = ""
    if (filters) {
      const params = new URLSearchParams(filters).toString()
      qs = params ? `?${params}` : ""
    }
    return API.get(`/api/analytics/admin/chat-sessions/${chatId}/complete-context${qs}`)
  },

  kanban: {
    async load() {
      return API.get('/api/kanban')
    },

    async save(kanban) {
      return API.post('/api/kanban', kanban)
    },

    delete(kanban_title) {
      return API.delete('/api/kanban?kanban_title=' + kanban_title)
    }
  }
})