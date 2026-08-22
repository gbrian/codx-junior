import moment from 'moment'
import Service from "./service"
import { extractCodeBlocks, hasCodeBlocksWithPaths } from '../utils/codeBlockExtractor'

export class ChatService extends Service {
  getUserMessage({ message, files, profiles, images, metadata, user, taskItem, task_item }) {
    return {
      role: "user",
      content: message,
      images: images?.map(JSON.stringify) || [],
      files,
      profiles,
      task_item: taskItem,
      user: user || this.$user.username,
      meta_data: metadata,
      done: true,
      task_item,
    }
  }

  async sendMessage({ chat, message }) {
    this.addMessage({ chat, message })
    return this.$projects.chatWihProject(chat)
  }

  async findChat({ id, owner_project_id } = {}) {
    return id
      ? await this.$chats.findProjectChat({ id, owner_project_id })
      : null
  }

  getMessageProfiles({ messageMentions, selectedUser, currentUser }) {
    const profiles = messageMentions
      .filter((m) => m.profile)
      .map((m) => m.profile.name)
    if (selectedUser?.name && selectedUser !== currentUser) {
      profiles.push(selectedUser.name)
    }
    return profiles.filter(
      (v, ix, arr) => arr.findIndex((vv) => vv === v) === ix
    )
  }

  getMessageFiles({ messageMentions, files }) {
    return [
      ...messageMentions.filter((m) => m.file).map((m) => m.file),
      ...(files || []),
    ]
  }

  addMessage({ chat, message }) {
    if (chat?.id) {
      this.$storex.chats.addMessageToChat({ chatId: chat.id, message })
    } else {
      chat.messages = [...(chat.messages || []), message]
    }
  }

  removeMessage({ chat, message }) {
    const ix = chat.messages.findIndex((m) => m.doc_id === message.doc_id)
    if (chat.mode === "task" && message.role === "assistant" && ix > 1) {
      chat.messages[ix - 1].hide = false
      if (chat.messages[ix - 2]) chat.messages[ix - 2].hide = false
    }
    chat.messages = chat.messages.filter((_, i) => i !== ix)
  }

  toggleHide({ chat, doc_id }) {
    const msg = chat.messages.find((m) => m.doc_id === doc_id)
    if (msg) msg.hide = !msg.hide
  }

  toggleAnswer({ chat, doc_id }) {
    const msg = chat.messages.find((m) => m.doc_id === doc_id)
    if (msg) msg.is_answer = !msg.is_answer
  }

  hideAll({ chat }) {
    chat.messages.forEach((m) => {
      m.hide = true
    })
  }

  updateExistingMessage({ chat, doc_id, update }) {
    const existing = chat.messages.find((m) => m.doc_id === doc_id)
    if (existing) Object.assign(existing, update)
  }

  removeFileFromMessage({ message, file }) {
    message.files = message.files.filter((f) => f !== file)
  }

  removeFileFromChat({ chat, file }) {
    chat.file_list = chat.file_list?.filter((f) => f !== file)
  }

  addFileToChat({ chat, file }) {
    if (chat.file_list?.includes(file)) return false
    chat.file_list = [...(chat.file_list || []), file]
    return true
  }

  async parseImageFromPaste(e) {
    if (!e.clipboardData?.items) return null
    return (
      [...e.clipboardData.items]
        .find((f) => f.type.indexOf("image") !== -1)
        ?.getAsFile() || null
    )
  }

  async parseTextFromPaste(e) {
    if (!e.clipboardData?.items) return null
    const textItem = [...e.clipboardData.items].find(
      (f) => f.type.indexOf("text") !== -1
    )
    if (!textItem) return null
    return new Promise((ok) => textItem.getAsString(ok))
  }

  extractImageUrlFromHtml(html) {
    if (!html.startsWith("<img")) return null
    const match = /src="([^"]+)/.exec(html)
    return match ? match[1] : null
  }

  async uploadImage({ file }) {
    const formData = new FormData()
    formData.append("file", file)
    const response = await this.$storex.api.images.upload(formData)
    return response.path
  }

  async fileToMessage({ file }) {
    const content = await this.$storex.api.files.read(file)
    const ext = file.split(".").reverse()[0]
    return ["```" + `${ext} ${file}`, content, "```"].join("\n")
  }

  async extractTextFromImage(image) {
    const byteString = atob(image.src.split(",")[1])
    const mimeString = image.src.split(",")[0].split(":")[1].split(";")[0]
    const byteArray = new Uint8Array(byteString.length)
    for (let i = 0; i < byteString.length; i++)
      byteArray[i] = byteString.charCodeAt(i)
    const blob = new Blob([byteArray], { type: mimeString })
    const file = new File([blob], "image", { type: mimeString })
    return this.$api.tools.imageToText(file)
  }

  buildSubTaskPayload({
    title,
    description,
    files,
    profiles,
    mode,
    column,
    projectId,
    parentId,
    board,
    metadata,
    user,
  }) {
    return {
      name: title,
      messages: [
        {
          role: "user",
          content: description,
          images: [],
          profiles: [],
          user: user || this.$user.username,
          meta_data: {},
          done: true,
        },
      ],
      project_id: projectId,
      parent_id: parentId,
      file_list: files || [],
      profiles: profiles || [],
      mode: mode,
      column: column,
      board: board,
      metadata: metadata || {},
      activateChat: false,
    }
  }

  getCaretWordInfo(editor) {
    if (!editor?.innerText) return {}
    const caretIndex = this._getEditorCaretCharOffset(editor)
    const text = editor.innerText
    const lastWorkIndex = text.slice(0, caretIndex).split(/\s/g).length - 1
    const word = text.split(/\s/g)[lastWorkIndex]
    return { caretIndex, lastWorkIndex, word }
  }

  _getEditorCaretCharOffset(element) {
    let caretOffset = 0
    if (window.getSelection) {
      const range = window.getSelection().getRangeAt(0)
      const preCaretRange = range.cloneRange()
      preCaretRange.selectNodeContents(element)
      preCaretRange.setEnd(range.endContainer, range.endOffset)
      caretOffset = preCaretRange.toString().length
    }
    return caretOffset
  }

  startVoiceRecognition({ lang, onResult, onEnd }) {
    const recognition = new (window.SpeechRecognition ||
      window.webkitSpeechRecognition)()
    recognition.lang = lang
    recognition.interimResults = false
    recognition.onresult = onResult
    recognition.onend = onEnd
    recognition.start()
    return recognition
  }

  async syncNotebook({ project, chat }) {
    return this.$storex.chat.syncNotebookToChat({ project, chat })
  }

  async exportNotebook({ project, chat, file }) {
    return this.$storex.chat.exportChatToNotebook({ project, chat, file })
  }

  async saveChat(chat) {
    if (!chat.temp) {
      return await this.$chats.saveChat(chat)
    }
  }

  async sendChatMessage({ chat, storex }) {
    return await storex.projects.chatWihProject(chat)
  }

  async validateFile({ file, parentChat }) {
    const fileChat = file.chat || await this.createFileChat({ file, parentChat })

    if (fileChat.messages.some(m => !m.hide)) {
      fileChat.messages.forEach(m => { m.hide = true })
      await this.saveChat(fileChat)
    }

    const message = this.getUserMessage({
      taskItem: 'review',
      message:
        [
          `Follow profiles instructions to validate the latest changes in the file: ${file.fileFullName}.`,
          "If no profiles are present, create a summary of best practices of the file with example and suggestions of how to improve file quality",
          file.diff ? 'Focus on the last changes from the diff:\n' + file.diff : ''
        ].join("\n"),
      files: [file.fileFullName]
    })

    return this.sendMessage({ chat: fileChat, message })
  }

  async validateAllFiles({ prReviewChat, files }) {
    await Promise.all(
      files.filter((f) => !f.isDeleted).map((file) =>
        this.validateFile({
          file,
          parentChat: prReviewChat,
        })
      )
    )
  }

  async createFileChat({ parentChat, file, project_id, column, message, metadata }) {
    column = column || parentChat.column
    const { fileFullName, fileShortName, profiles } = file
    const payload = this.buildSubTaskPayload({
      title: fileShortName,
      description: message,
      files: [fileFullName],
      profiles: profiles.map(p => p.name),
      mode: 'task',
      column,
      metadata,
      project_id: parentChat.project_id,
      parent_id: parentChat.id,
      board: parentChat.board,
      projectId: project_id || parentChat.project_id,
      parentId: parentChat.id,
      user: this.$user.username
    })
    file.chat = await this.$chats.createNewChat(payload)
    return file.chat
  }

  async newQuickChat(project) {
    const chat = {
      name: "Quick chat",
      mode: 'chat',
      auto_initialize: true
    }
    const quickChat = await this.$chats.createNewChatWithProject({ project, chat })
    this.$storex.ui.showApp({
        key: 'chat',
        name: 'Chat',
        component: 'chat',
        params: {
          chat: quickChat
        }
      })
  }

  async createChat({
    files,
    name,
    mode = 'chat',
    message,
    profiles = [],
    metadata = {},
    activate = false,
  }) {
    const fileNames = (files || []).map(f => f.split('/').pop())
    const chatName = name ||
      `Files: ${fileNames.slice(0, 2).join(', ')}${fileNames.length > 2 ? ` +${fileNames.length - 2}` : ''}`

    const openingMessage = message ||
      `Working with files:\n${(files || []).map(f => `- ${f}`).join('\n')}`

    const payload = {
      name: chatName,
      mode,
      file_list: files || [],
      profiles,
      metadata,
      auto_initialize: false,
      messages: [
        this.getUserMessage({
          message: openingMessage,
          files: files || [],
          profiles,
          metadata,
        })
      ]
    }

    const chat = await this.$chats.createNewChat(payload)

    if (activate) {
      await this.$chats.setActiveChat(chat)
    }

    return chat
  }

  // Get chat project from chat object or fallback to current project
  getChatProject(chat) {
    const projectId = chat?.project_id || chat?.owner_project_id
    if (projectId) {
      return this.$projects.allProjectsById[projectId] || this.$project
    }
    return this.$project
  }

  // Update chat branch metadata
  updateChatBranches({ chat, currentBranch, compareBranch }) {
    if (!chat) return
    chat.meta_data = {
      ...(chat.meta_data || {}),
      current_branch: currentBranch,
      compare_branch: compareBranch
    }
  }

  findChildChatByFile({ chat, childrenChats, file }) {
    const searchNode = (node, visited = new Set()) => {
      if (!node || visited.has(node.id)) return null
      visited.add(node.id)
      if (node.file_list?.includes(file)) return node
      if (node.children && Array.isArray(node.children)) {
        for (const child of node.children) {
          const found = searchNode(child, visited)
          if (found) return found
        }
      }
      return null
    }

    if (childrenChats && Array.isArray(childrenChats)) {
      for (const child of childrenChats) {
        const found = searchNode(child)
        if (found) return found
      }
    }

    if (chat) {
      return searchNode(chat)
    }
    return null
  }

  findChatByFileAndMessage({ chat, file, messageId }) {
    if (!file) return null
    const chats = this.$projects?.allChats || []
    
    // 1. Find directly-linked chat by file and messageId
    let found = chats.find(c => 
      c.file_list?.includes(file) && 
      (c.message_id === messageId || (messageId && c.metadata?.message_id === messageId))
    )
    if (found) return found

    // 2. Fallback to any child chat of parent chat that matches this file
    if (chat) {
      found = chats.find(c => 
        c.file_list?.includes(file) && 
        (c.parent_id === chat.id || c.metadata?.parent_id === chat.id)
      )
    }
    return found || null
  }
  
  // Add these methods to the ChatService class
  extractCodeBlocksFromMessage(message) {
    return extractCodeBlocks(message?.content || '')
  }

  hasCodeBlocksWithFilePaths(message) {
    return hasCodeBlocksWithPaths(message?.content || '')
  }

}