<script setup>
import { API } from '../../api/api'
import CheckLists from './CheckLists.vue'
import PRView from '@/components/repo/PRView.vue'
import ChatFileList from './ChatFileList.vue'
import ChatMentionBar from './ChatMentionBar.vue'
import ChatInputBox from './ChatInputBox.vue'
import ChatImagePreviewModal from './ChatImagePreviewModal.vue'
import ChatFileSelectorModal from './ChatFileSelectorModal.vue'
import ChatMessageList from './ChatMessageList.vue'
</script>

<template>
  <div class="h-full flex flex-col gap-1 overflow-auto">
    <!-- Main content area -->
    <div class="grow relative flex flex-col gap-1 min-h-0" v-if="!inputOnly">
      <div class="flex gap-2 items-center justify-between">
        <div class="w-full" v-if="chatFiles.length">
          <ChatFileList
            :files="chatFiles"
            @remove="removeFileFromChat"
            @add-as-message="addFileContentAsMessage"
            @sync-notebook="syncNotebook"
            @export-notebook="exportNotebook"
          />
        </div>
        <CheckLists :chat="chat" :readOnly="readOnly" @change="saveChat" v-if="!isVibe" />
      </div>

      <!-- PR diff view: rendered but hidden when inactive to avoid remount -->
      <div class="grow" v-show="isPRView">
        <PRView
          class="h-full overflow-auto"
          :fromBranch="chat.pr_view?.from_branch"
          :toBranch="chat.pr_view?.to_branch"
          :chat="chat"
          @select-branch="onPRViewBranchChanged"
          @comment="onPRFileComment"
          @change-column="$emit('change-column', $event)"
          @new-chat="createChatSubTask"
          @chat-message="onPRChatMessage"
        />
      </div>

      <!-- Messages + browser side-by-side layout, always mounted -->
      <div class="grow flex gap-2 min-h-0 overflow-hidden" v-show="!isPRView">
        <div class="flex flex-col min-h-0 w-full">
          <div class="h-full flex flex-col relative">
            <!-- Messages list: stable key prevents full rebuild -->
            <ChatMessageList
              ref="messageList"
              class="w-full grow overflow-y-auto overflow-x-hidden"
              :chat="chat"
              :messages="stableMessages"
              :edit-message="editMessage"
              :mention-list="mentionList"
              :read-only="readOnly"
              :users-list="usersList"
              :children-chats="childrenChats"
              :is-channel="isChannel"
              :is-topic="isTopic"
              @edited="onMessageEdited"
              @enhance="onEditMessage($event, true)"
              @remove="removeMessage"
              @remove-file="removeFileFromMessage($event.message, $event.file)"
              @hide="toggleHide"
              @answer="toggleAnswer"
              @run-edit="runEdit"
              @copy="onCopy"
              @add-file-to-chat="onAddFile"
              @image="imagePreview = $event"
              @generate-code="onGenerateCode"
              @reload-file="onReloadMessageFile"
              @open-file="onOpenFile"
              @save-file="onSaveFile"
              @add-file="onAddFile"
              @edit-message="onEditMessage($event.event, $event.message)"
              @thread="onNewThread"
              @sub-task="onChatEntryCreateSubtask"
              @set-active-chat="$chats.setActiveChat($event)"
            />

            <!-- Input box always inside the left panel column -->
            <ChatInputBox
              v-if="readOnly !== true"
              ref="inputBox"
              :waiting="waiting"
              :is-editing="!!editMessage"
              :is-voice-session="isVoiceSession"
              :searching="searchingInKnowledge"
              :read-only="readOnly"
              :has-test-script="!!API.activeProject.script_test"
              :show-document-search="showDocumentSearchModal"
              :chat-project="chatProject"
              :selected-user="selectedUser"
              :users-list="usersList"
              :selected-model="chat.llm_model"
              :ai-models="aiModels"
              :images="images"
              :cursor-word="cursorWord"
              :voice-language-label="$ui.voiceLanguages?.[$ui.voiceLanguage]"
              @close.knowledge="showDocumentSearchModal = false"
              @send="sendMessage"
              @add-message="addNewMessage()"
              @search-message="addSearchMessage"
              @cancel-edit="onResetEdit"
              @paste="onContentPaste"
              @keydown="onEditMessageKeyDown"
              @drop="onDrop"
              @add-document="onAddDocument"
              @close-search="closeDocumentSearch"
              @replace-emoji="replaceEmoji"
              @user-changed="selectedUser = $event"
              @model-changed="onLLMModelChanged"
              @toggle-search="toggleDocumentSearch"
              @hide-all="hideAll"
              @attach-files="selectFile = true"
              @test-project="testProject"
              @toggle-voice="toggleVoiceSession"
              @remove-image="removeImage"
              @preview-image="imagePreview = $event"
            />
          </div>
        </div>
      </div>
    </div>

    <!-- Bottom sticky mention bar -->
    <div class="sticky bottom-0 z-2" v-if="!isPRView && !inputOnly">
      <ChatMentionBar
        :suggestions="mentionSuggestions"
        :active-mentions="messageMentions"
        @add-mention="addMention"
        @remove-mention="removeMessageMention"
        @add-file="onAddFile"
      />
    </div>

    <!-- Modals -->
    <ChatImagePreviewModal
      :image-preview="imagePreview"
      @cancel="imagePreview = null"
      @confirm="onAddImage"
      @extract-text="onExtractTextImage"
    />

    <ChatFileSelectorModal
      :show="selectFile"
      :file-path="uploadProjectFile"
      @update:filePath="uploadProjectFile = $event"
      @close="selectFile = false"
      @add-file="addChatFile"
      @file-change="handleFileChange"
    />

    <!-- Notebook sync feedback toast -->
    <div v-if="notebookStatus" class="toast toast-top toast-center z-50">
      <div class="alert alert-info text-xs">
        <i class="fa-solid fa-book-open mr-1"></i>
        <span>{{ notebookStatus }}</span>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  props: ['chat', 'filter', 'showHidden', 'childrenChats', 'readOnly', 'message', 'input-only'],
  data() {
    return {
      waiting: false,
      editMessage: null,
      editMessageId: null,
      files: [],
      images: [],
      imagePreview: null,
      onDraggingOverInput: false,
      selectFile: false,
      isVoiceSession: false,
      recognition: null,
      syncEditableTextInterval: null,
      selectedUser: null,
      showDocumentSearchModal: false,
      searchingInKnowledge: false,
      uploadProjectFile: null,
      metadata: null,
      pasteWithShift: false,
      mentionSuggestions: [],
      mentions: [],
      cursorWord: {},
      notebookStatus: null,
      editorText: "",
      // Stable snapshot of messages to avoid triggering re-renders on every poll tick
      stableMessages: []
    }
  },
  created() {
    this.selectedUser = this.$user
    this.metadata = this.message?.metadata
    this.editorText = this.message?.content
    // Seed stable messages immediately
    this.stableMessages = this.messages
  },
  mounted() {
    // Poll editor text at 100ms; messages sync at a slower rate to avoid blink
    this.syncEditableTextInterval = setInterval(() => this.onMessageChange(), 100)
    this.editorText && this.setEditorText(this.editorText)
  },
  unmounted() {
    clearInterval(this.syncEditableTextInterval)
  },
  computed: {
    chatSvc() {
      return this.$service.chat
    },
    aiModels() {
      return this.$projects.ai.models || []
    },
    chatFiles() {
      return this.chat.file_list || []
    },
    isPRView() {
      return this.chat.mode === 'prview'
    },
    isBrowser() {
      return this.chat.mode === 'vibe'
    },
    visibleMessages() {
      return this.chat?.messages?.filter(m => !m.hide || this.showHidden) || []
    },
    lastAIMessage() {
      const lastAiMessages = this.activeMessages?.filter(m => m.role === 'assistant').reverse()
      if (!lastAiMessages?.length) return null
      if (lastAiMessages.length < 2) return lastAiMessages[0]
      const [last, ...previous] = lastAiMessages
      return { ...last, diffMessage: previous[0] }
    },
    lastUserMessage() {
      const msgs = this.messages?.filter(m => m.role !== 'assistant')
      return msgs ? msgs[msgs.length - 1] : null
    },
    lastMessage() {
      return this.messages?.length ? this.messages[this.messages.length - 1] : null
    },
    activeMessages() {
      const messages = this.chat?.messages
      if (this.filter) {
        return messages?.filter(m => m.content?.toLowerCase().includes(this.filter.toLowerCase()))
      }
      return messages?.filter(m => !m.hide || this.showHidden) || []
    },
    messages() {
      return this.activeMessages.filter(message => !message.hide || this.showHidden)
    },
    canPost() {
      return this.editorText || this.images?.length
    },
    isTask() {
      return this.chat?.mode === 'task'
    },
    isTopic() {
      return this.chat?.mode === 'topic'
    },
    isVibe() {
      return this.chat?.mode === 'vibe'
    },
    chatProject() {
      return this.$projects.allProjectsById[this.chat.project_id || this.chat.owner_project_id]
        || this.$project
    },
    mentionList() {
      return (this.chatProject?.$state || this.$projects).mentionList
    },
    messageMentions() {
      const mentions = [...this.editorText?.matchAll(/@([^\s]+)/mg) || []].map(w => w[1]) || []
      return [
        ...this.mentionList?.filter(m => mentions.includes(m.mention)) || [],
        ...this.mentions,
        ...this.files.map(file => ({ name: file.split("/").reverse()[0], file }))
      ]
    },
    profiles() {
      return this.chatProject?.$state?.profiles || []
    },
    usersList() {
      return [this.$user, ...this.profiles]
    },
    isChannel() {
      return this.chat.mode === 'topic'
    },
    editor() {
      return this.$refs.inputBox?.getEditor() || this.$el?.querySelector('.editor')
    }
  },
  watch: {
    uploadProjectFile(newVal, oldVal) {
      if (newVal?.length >= 3 && newVal?.length > oldVal?.length) {
        this.detectSearchTerm()
      }
    },
    editorText() {
      this.loadMentionSuggestions()
      this.updateCursorWord()
    },
    // Sync stableMessages only when the message count or last message id changes
    // This avoids re-renders triggered by content mutations during streaming
    messages(newMessages) {
      this.syncStableMessages(newMessages)
    }
  },
  methods: {
    // Only update stableMessages when structure changes (add/remove), not on content edits
    syncStableMessages(newMessages) {
      const newIds = newMessages.map(m => m.doc_id).join(',')
      const oldIds = this.stableMessages.map(m => m.doc_id).join(',')
      if (newIds !== oldIds) {
        this.stableMessages = newMessages
      } else {
        // Update existing message objects in-place to preserve Vue's vnodes
        newMessages.forEach((msg, i) => {
          const stable = this.stableMessages[i]
          if (stable && msg !== stable) {
            Object.assign(stable, msg)
          }
        })
      }
    },
    onLLMModelChanged(modelName) {
      this.chat.llm_model = modelName
      this.saveChat()
    },
    updateCursorWord() {
      this.cursorWord = this.chatSvc.getCaretWordInfo(this.editor)
    },
    loadMentionSuggestions() {
      this.mentionSuggestions = []
      const { word } = this.cursorWord
      if (word?.startsWith("@")) {
        this.mentionSuggestions = [
          ...this.mentions,
          ...this.chatProject.$state.searchMentions(word.slice(1))
        ]
      }
    },
    setEditorText(text) {
      if (this.editor && this.editor.innerText !== undefined) {
        this.editor.innerText = text
      }
    },
    onEditMessage(message, enhance) {
      if (this.editMessage === message) return this.onResetEdit()
      this.editMessageId = this.chat.messages.findIndex(m => m.doc_id === message.doc_id)
      this.editMessage = this.chat.messages[this.editMessageId]
      const profile = this.editMessage.profiles?.[0]
      if (profile) {
        this.selectedUser = this.usersList.find(u => u.name === profile) || this.$user
      }
      try { this.images = message.images.map(JSON.parse) } catch { }
      this.setEditorText(this.editMessage.content)
    },
    toggleHide({ doc_id }) {
      this.chatSvc.toggleHide({ chat: this.chat, doc_id })
      this.saveChat()
    },
    toggleAnswer({ doc_id }) {
      this.chatSvc.toggleAnswer({ chat: this.chat, doc_id })
      this.saveChat()
    },
    onCopy(message) {
      navigator.permissions.query({ name: "clipboard-read" }).then(result => {
        if (result.state === "granted" || result.state === "prompt") {
          navigator.clipboard.writeText(message.content)
        }
      }).catch(console.error)
    },
    runEdit(codeSnipped) {
      this.waiting = true
      this.$storex.api.run.edit({ id: "", messages: [{ role: 'user', content: codeSnipped }] })
        .then(data => {
          const content = [data.messages.reverse()[0].content, "\n\n", ...data.errors.map(e => ` * ${e}\n`)].join("\n")
          this.chatSvc.addMessage({ chat: this.chat, message: { role: 'assistant', content } })
        })
        .catch(ex => this.chatSvc.addMessage({ chat: this.chat, message: { role: 'assistant', content: ex.message } }))
        .finally(() => { this.waiting = false })
    },
    getUserMessage({ message, task_item }) {
      return this.chatSvc.getUserMessage({
        message,
        files: this.chatSvc.getMessageFiles({ messageMentions: this.messageMentions, files: this.files }),
        profiles: this.chatSvc.getMessageProfiles({ messageMentions: this.messageMentions, selectedUser: this.selectedUser, currentUser: this.$user }),
        images: this.images,
        metadata: this.metadata,
        user: this.$user.username,
        task_item
      })
    },
    postMyMessage({ message, task_item }) {
      const userMessage = this.getUserMessage({ message, task_item })
      this.chatSvc.addMessage({ chat: this.chat, message: userMessage })
      this.cleanUserInputAndWaitAnswer()
      return userMessage
    },
    cleanUserInputAndWaitAnswer() {
      this.setEditorText("")
      this.images = []
      this.files = []
      this.mentions = []
      this.metadata = null
    },
    async addNewMessage({ task_item } = {}) {
      if (this.isVoiceSession && !this.canPost) return false
      if (this.editMessage !== null) {
        this.updateMessage()
        this.saveChat()
        return false
      }
      const message = this.editorText
      if (message?.length && this.canPost && this.postMyMessage({ message, task_item })) {
        await this.saveChat()
      }
      return true
    },
    async addSearchMessage() {
      return this.addNewMessage({ task_item: 'search' })
    },
    async sendMessage() {
      if (await this.addNewMessage()) {
        if (!this.isChannel || this.lastMessage?.profiles.length) {
          await this.sendChatMessage(this.chat)
          this.$emit('send-message', this.lastMessage)
        }
      }
    },
    async sendChatMessage(chat) {
      this.waiting = true
      try {
        return await this.$storex.projects.chatWihProject(chat)
      } finally {
        this.waiting = false
      }
    },
    async updateMessage() {
      const { innerText } = this.editor
      this.editMessage.files = this.messageMentions.filter(m => m.file).map(m => m.file)
      this.editMessage.profiles = this.chatSvc.getMessageProfiles({ messageMentions: this.messageMentions, selectedUser: this.selectedUser, currentUser: this.$user })
      this.editMessage.content = innerText
      this.editMessage.images = this.images.map(JSON.stringify)
      this.editMessage.updated_at = new Date().toISOString()
      this.onResetEdit()
    },
    onResetEdit() {
      this.editMessage = null
      this.setEditorText("")
      this.editMessageId = null
      this.images = []
    },
    removeMessage(message) {
      this.chatSvc.removeMessage({ chat: this.chat, message })
      this.saveChat()
    },
    // Polls the DOM editor for text changes; avoids heavy reactivity on the input
    onMessageChange() {
      if (this.editor && this.editor.innerText !== this.editorText) {
        this.editorText = this.editor.innerText
      }
    },
    async saveChat() {
      return this.chatSvc.saveChat(this.chat)
    },
    onDrop(e) {
      if (!e.dataTransfer.files) return
      const file = [...e.dataTransfer.files].filter(f => f.type.indexOf("image") !== -1)[0]
      if (file) this.onInputImage(file)
    },
    async onContentPaste(e) {
      if (!e.clipboardData?.items) return
      const stop = () => { e.preventDefault(); return false }

      const imageFile = await this.chatSvc.parseImageFromPaste(e)
      if (imageFile) { this.onInputImage(imageFile); return stop() }

      const textContent = await this.chatSvc.parseTextFromPaste(e)
      if (!textContent) return

      const imgUrl = this.chatSvc.extractImageUrlFromHtml(textContent)
      if (imgUrl) { this.images.push(imgUrl); return stop() }

      const fileMention = this.mentionList.find(m => m.file === textContent)
      if (fileMention) { this.addFileToMessage(fileMention.file); return stop() }

      const isProjectFile = this.$projects.allProjects.find(p => textContent.startsWith(p.abs_project_path))
      if (isProjectFile && !this.pasteWithShift) {
        this.addFileToMessage(textContent)
        this.setEditorText(this.editorText.replace(textContent, ""))
        return stop()
      }
    },
    addFileToMessage(file) {
      if (!this.files.includes(file)) this.files.push(file)
    },
    onInputImage(file) {
      this.imagePreview = { file }
    },
    async onAddImage() {
      if (!this.imagePreview) return
      try {
        const path = await this.chatSvc.uploadImage({ file: this.imagePreview.file })
        this.images.push(path)
      } catch (error) {
        console.error("Error uploading image:", error)
      } finally {
        this.imagePreview = null
      }
    },
    async onExtractTextImage(image) {
      image.alt = await this.chatSvc.extractTextFromImage(image)
    },
    async handleFileChange({ target: { files } }) {
      const imageFiles = [...files].filter(file => file.type.startsWith("image/"))
      for (const file of imageFiles) {
        this.imagePreview = { file }
        await this.onAddImage()
      }
      this.selectFile = false
    },
    onGenerateCode(codeBlockInfo) {
      this.$projects.generateCode({ chat: this.chat, codeBlockInfo })
    },
    removeImage(ix) {
      this.images = this.images.filter((_, imx) => imx !== ix)
    },
    async testProject() {
      throw new Error('Obsolete')
    },
    removeFileFromMessage(message, file) {
      this.chatSvc.removeFileFromMessage({ message, file })
      this.saveChat()
    },
    removeFileFromChat(file) {
      this.chatSvc.removeFileFromChat({ chat: this.chat, file })
      this.saveChat()
    },
    showNotebookStatus(msg) {
      this.notebookStatus = msg
      setTimeout(() => { this.notebookStatus = null }, 3000)
    },
    async syncNotebook(file) {
      try {
        this.showNotebookStatus(`Syncing ${file.split('/').reverse()[0]}...`)
        await this.chatSvc.syncNotebook({ project: this.chatProject, chat: this.chat, file })
        await this.saveChat()
        this.showNotebookStatus(`Notebook synced: ${file.split('/').reverse()[0]}`)
      } catch (err) {
        console.error('syncNotebook error', err)
        this.showNotebookStatus(`Error syncing notebook: ${err.message}`)
      }
    },
    async exportNotebook(file) {
      try {
        this.showNotebookStatus(`Exporting to ${file.split('/').reverse()[0]}...`)
        await this.chatSvc.exportNotebook({ project: this.chatProject, chat: this.chat, file })
        this.showNotebookStatus(`Notebook exported: ${file.split('/').reverse()[0]}`)
      } catch (err) {
        console.error('exportNotebook error', err)
        this.showNotebookStatus(`Error exporting notebook: ${err.message}`)
      }
    },
    toggleVoiceSession() {
      if (this.isVoiceSession) return this.stopVoiceSession()
      let silents = 5
      this.isVoiceSession = true
      this.recognition = this.chatSvc.startVoiceRecognition({
        lang: this.$ui.voiceLanguage,
        onResult: (event) => { this.editor.innerText += event.results[0][0].transcript },
        onEnd: () => {
          if (this.isVoiceSession && silents--) this.recognition.start()
          else this.stopVoiceSession()
        }
      })
    },
    stopVoiceSession() {
      this.recognition?.stop()
      this.recognition = null
      this.isVoiceSession = false
    },
    onEditMessageKeyDown(event) {
      const stop = () => { event.stopPropagation(); event.preventDefault(); return false }
      if (event.key === 'Escape') { this.onResetEdit(); return stop() }
      else if (event.key === 'Enter' && event.ctrlKey) { this.sendMessage(); return stop() }
      else if (event.key === 'f' && event.ctrlKey) { this.addSearchMessage(); return stop() }
      else if (event.key === 'A' && event.ctrlKey && event.shiftKey) { this.hideAll(); return stop() }
      else if (event.key === 'b' && event.ctrlKey) { this.createBlock(); return stop() }
      else if (event.key === 'v' && event.ctrlKey) { this.pasteWithShift = false; return true }
      else if (event.key === 'V' && event.ctrlKey) { this.pasteWithShift = true; return true }
      return true
    },
    hideAll() {
      this.chatSvc.hideAll({ chat: this.chat })
      this.saveChat()
    },
    toggleDocumentSearch() {
      this.showDocumentSearchModal = !this.showDocumentSearchModal
    },
    closeDocumentSearch() {
      this.showDocumentSearchModal = false
    },
    onAddDocument(doc) {
      const source = doc.file || doc.metadata?.source
      if (source) this.addFileToMessage(source)
    },
    async onReloadMessageFile({ file, message }) {
      message.content = await this.chatSvc.fileToMessage({ file })
      this.saveChat()
    },
    async onSaveFile({ file, content }) {
      await this.$storex.chats.writeFile({ chat: this.chat, file, content })
      this.$ui.addNotification({ text: `File ${file.split("/").reverse()[0]} saved` })
    },
    onOpenFile(file) {
      this.chatProject.$api.coder.openFile(file)
    },
    addChatFile() {
      this.onAddFile(this.uploadProjectFile)
      this.uploadProjectFile = null
      this.selectFile = false
    },
    async onAddFile(file) {
      if (this.chatSvc.addFileToChat({ chat: this.chat, file })) {
        await this.saveChat()
      }
    },
    onMessageEdited({ doc_id, content }) {
      this.chatSvc.updateExistingMessage({ chat: this.chat, doc_id, update: { content } })
      this.saveChat()
    },
    removeMessageMention(mention) {
      const orgMention = this.mentionList?.find(m => m === mention)
      if (orgMention) {
        this.setEditorText(this.editorText.replace("@" + mention.name, ""))
      } else {
        this.files = this.files.filter(f => f !== mention.file)
      }
    },
    onPRViewBranchChanged({ fromBranch: from_branch, toBranch: to_branch }) {
      this.chat.pr_view = { from_branch, to_branch }
      this.saveChat()
    },
    async onPRFileComment({ chat, title, files, description, profiles, mode, column }) {
      if (chat) {
        chat.messages.push({ user: this.$user.username, role: "user", content: description })
        chat.profiles = profiles.map(p => p.name)
        await this.$chats.saveChatInfo(chat)
        await this.$storex.projects.chatWihProject(chat)
      } else {
        this.createSubTask({ title, description, files, profiles, mode, column })
      }
    },
    onChatEntryCreateSubtask({ file, content }) {
      this.createChatSubTask({
        title: file.split("/").reverse()[0],
        description: content,
        files: [file]
      })
    },
    async createChatSubTask({ title, files, description, metadata, profiles, mode, column, project_id, parent_id }) {
      const payload = this.chatSvc.buildSubTaskPayload({
        title,
        description,
        files,
        profiles,
        mode: mode || this.chat.mode,
        column: column || this.chat.column,
        board: this.chat.board,
        metadata,
        projectId: project_id || this.chatProject.project_id,
        parentId: parent_id || this.chat.id,
        user: this.$user.username
      })
      await this.$chats.createNewChat(payload)
    },
    onPRChatMessage({ file }) {
      file.chat.messages.push({})
    },
    createBlock() {
      this.setEditorText(this.editorText + "```\n\n```")
    },
    onNewThread(message) {
      this.$projects.createNewThread({ chat: this.chat, message })
    },
    async addFileContentAsMessage(file) {
      const content = await this.$storex.chats.readFile({ chat: this.chat, file })
      const codeBlock = ["```" + file.split(".")[1] + " " + file, content, "```"].join("\n")
      this.chatSvc.addMessage({ chat: this.chat, message: this.getUserMessage({ message: codeBlock }) })
    },
    addMention(mention) {
      this.mentions.push({ ...mention, active: true })
    },
    replaceEmoji({ emoji }) {
      const { caretIndex, word } = this.cursorWord
      const text = this.editor?.innerText
      const left = text.slice(0, caretIndex - word.length)
      const right = text.slice(caretIndex)
      this.setEditorText(left + emoji + right)
    }
  }
}
</script>