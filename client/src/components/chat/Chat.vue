<script setup>
import { API } from '../../api/api'
import ChatEntry from '@/components/ChatEntry.vue'
import Browser from '@/components/browser/Browser.vue'
import TaskCard from '../kanban/TaskCard.vue'
import CheckLists from './CheckLists.vue'
import PRView from '@/components/repo/PRView.vue'
import ChatFileList from './ChatFileList.vue'
import ChatMentionBar from './ChatMentionBar.vue'
import ChatInputBox from './ChatInputBox.vue'
import ChatImagePreviewModal from './ChatImagePreviewModal.vue'
import ChatFileSelectorModal from './ChatFileSelectorModal.vue'
</script>

<template>
  <div class="h-full flex flex-col gap-1 overflow-auto">
    <!-- Main content area -->
    <div class="grow relative flex flex-col gap-1" v-if="!inputOnly">
      <div class="flex gap-2 items-center justify-between">
        <div class="w-full" v-if="chatFiles.length">
          <ChatFileList
            :files="chatFiles"
            @remove="removeFileFromChat"
            @add-as-message="addFileContentAsMessage"
          />
        </div>
        <CheckLists :chat="chat" :readOnly="readOnly" @change="saveChat" />
      </div>

      <div class="grow overflow-y-auto overflow-x-hidden pr-2">
        <!-- Browser view -->
        <Browser :token="$ui.monitors['shared']" v-if="isBrowser" />

        <!-- PR diff view -->
        <PRView
          class="h-full overflow-auto"
          :fromBranch="chat.pr_view?.from_branch"
          :toBranch="chat.pr_view?.to_branch"
          :chat="chat"
          @select-branch="onPRViewBranchChanged"
          @comment="onPRFileComment"
          @change-column="$emit('change-column', $event)"
          @new-chat="onPRFileCreateChat"
          @chat-message="onPRChatMessage"
          @validate-files="onValidateChanges"
          v-if="isPRView"
        />

        <!-- Messages list -->
        <div class="overflow-y-auto w-full h-full" v-if="!isBrowser && !isPRView">
          <div
            class="flex flex-col overflow-y-auto overflow-x-hidden w-full"
            v-for="(message, ix) in messages"
            :key="message.id"
          >
            <ChatEntry
              :class="[
                'max-w-full mb-4 rounded-md hover:bg-base-200 border border-slate-600/0 hover:border-slate-600/70 rounded-lg',
                isChannel ? '' : 'py-2',
                editMessage
                  ? editMessage === message
                    ? 'border border-warning'
                    : 'opacity-40'
                  : ''
              ]"
              :chat="chat"
              :message="message"
              :isTopic="isTopic && !ix"
              :mentionList="mentionList"
              :menu-less="readOnly"
              :usersList="usersList"
              @edited="onMessageEdited"
              @enhance="onEditMessage(message, true)"
              @remove="removeMessage(message)"
              @remove-file="removeFileFromMessage(message, $event)"
              @hide="toggleHide(message)"
              @answer="toggleAnswer(message)"
              @run-edit="runEdit"
              @copy="onCopy(message)"
              @add-file-to-chat="onAddFile($event)"
              @image="imagePreview = { ...$event, readonly: true }"
              @generate-code="onGenerateCode"
              @reload-file="onReloadMessageFile"
              @open-file="onOpenFile"
              @save-file="onSaveFile"
              @add-file="onAddFile"
              @edit-message="onEditMessage($event, message)"
              @code-file-shown.stop="console.log"
              @thread="onNewThread"
            />
          </div>
          <div class="anchor" ref="anchor"></div>

          <!-- Child chats grid -->
          <div class="grid grid-cols-3 gap-2 mb-2" v-if="childrenChats?.length">
            <div v-for="child in childrenChats" :key="child.id" class="relative">
              <TaskCard
                class="click p-2 bg-base-100 h-40"
                :task="child"
                @click="$projects.setActiveChat(child)"
              />
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Bottom sticky input area -->
    <div class="sticky bottom-0 z-2" v-if="!isPRView">
      <ChatMentionBar
        :suggestions="mentionSuggestions"
        :active-mentions="messageMentions"
        @add-mention="addMention"
        @remove-mention="removeMessageMention"
        @add-file="onAddFile"
        v-if="!inputOnly"
      />

      <ChatInputBox
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
        @send="sendMessage"
        @add-message="addNewMessage"
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
        v-if="!isBrowser && readOnly !== true"
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
  </div>
</template>

<script>
const defFormater = d => JSON.stringify(d, null, 2)

export default {
  props: ['chat', 'filter', 'showHidden', 'childrenChats', 'readOnly', 'message', 'input-only'],
  data() {
    return {
      waiting: false,
      editMessage: null,
      editMessageId: null,
      files: [],
      images: [],
      previewImage: null,
      editorText: "",
      imagePreview: null,
      onDraggingOverInput: false,
      testError: null,
      selectFile: false,
      isVoiceSession: false,
      recognition: null,
      syncEditableTextInterval: null,
      selectedUser: null,
      selectedDocuments: null,
      showDocumentSearchModal: false,
      searchingInKnowledge: false,
      uploadProjectFile: null,
      metadata: null,
      pasteWithShift: false,
      mentionSuggestions: [],
      mentions: [],
      cursorWord: {}
    }
  },
  created() {
    this.selectedUser = this.$user
    this.metadata = this.message?.metadata
    this.editorText = this.message?.content
  },
  mounted() {
    this.syncEditableTextInterval = setInterval(() => this.onMessageChange(), 100)
    this.editorText && this.setEditorText(this.editorText)
  },
  unmounted() {
    clearInterval(this.syncEditableTextInterval)
  },
  computed: {
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
      return this.chat.mode === 'browser'
    },
    visibleMessages() {
      return this.chat?.messages?.filter(m => !m.hide || this.showHidden) || []
    },
    lastAIMessage() {
      const { activeMessages } = this
      const lastAiMessages = activeMessages?.filter(m => m.role === 'assistant').reverse()
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
      const { activeMessages } = this
      if (!activeMessages.length) return []
      // Task mode: show only last AI + last user message
      // if (this.isTask && !this.showHidden && activeMessages?.length) {
      //   const aiMsg = this.lastAIMessage
      //   const lastMsg = activeMessages[activeMessages.length - 1]
      //   const res = []
      //   if (aiMsg) res.push(aiMsg)
      //   if (lastMsg && lastMsg?.role !== 'assistant') res.push(lastMsg)
      //   return res
      // }
      return activeMessages.filter(message => !message.hide || this.showHidden)
    },
    multiline() {
      return this.editorText?.split("\n").length > 1 || this.images?.length
    },
    allImages() {
      return this.images
    },
    messageText() {
      return this.editorText
    },
    canPost() {
      return this.messageText || this.images?.length
    },
    isTask() {
      return this.chat?.mode === 'task'
    },
    isTopic() {
      return this.chat?.mode === 'topic'
    },
    chatProject() {
      return this.$projects.allProjects.find(p => p.project_id === this.chat.project_id)
        || this.$project
    },
    mentionList() {
      return (this.chatProject?.$state || this.$projects).mentionList
    },
    messageMentions() {
      const mentions = [...this.messageText?.matchAll(/@([^\s]+)/mg) || []].map(w => w[1]) || []
      return [
        ...this.mentionList?.filter(m => mentions.includes(m.mention)) || [],
        ...this.mentions,
        ...this.files.map(file => ({ name: file.split("/").reverse()[0], file }))
      ]
    },
    profiles() {
      return this.chatProject?.$state.profiles || []
    },
    usersList() {
      return [this.$user, ...this.profiles]
    },
    isChannel() {
      return this.chat.mode === 'topic'
    },
    // Resolve editor DOM element via child ref
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
    messageText() {
      this.loadMentionSuggestions()
      this.updateCursorWord()
    }
  },
  methods: {
    onLLMModelChanged(modelName) {
      this.chat.llm_model = modelName
      this.saveChat()
    },
    updateCursorWord() {
      const text = this.editor?.innerText
      this.cursorWord = {}
      if (text?.length) {
        const caretIndex = this.getEditorCaretCharOffset()
        const lastWorkIndex = text.slice(0, caretIndex).split(/\s/g).length - 1
        const word = text.split(/\s/g)[lastWorkIndex]
        this.cursorWord = { caretIndex, lastWorkIndex, word }
      }
    },
    loadMentionSuggestions() {
      this.mentionSuggestions = []
      const replaceWord = this.cursorWord.word
      if (replaceWord?.startsWith("@")) {
        this.mentionSuggestions = [
          ...this.mentions,
          ...this.chatProject.$state.searchMentions(replaceWord.slice(1))
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
      try {
        this.images = message.images.map(JSON.parse)
      } catch { }
      this.setEditorText(this.editMessage.content)
    },
    toggleHide({ doc_id, hide }) {
      this.updateExistingMessage({ doc_id }, { hide: !hide })
    },
    toggleAnswer({ doc_id, is_answer }) {
      this.updateExistingMessage({ doc_id }, { is_answer: !is_answer })
    },
    onCopy(message) {
      navigator.permissions.query({ name: "clipboard-read" }).then(result => {
        if (result.state == "granted" || result.state == "prompt") {
          navigator.clipboard.writeText(message.content)
        }
      }).catch(console.error)
    },
    runEdit(codeSnipped) {
      this.sendApiRequest(
        () => API.run.edit({ id: "", messages: [{ role: 'user', content: codeSnipped }] }),
        data => [data.messages.reverse()[0].content, "\n\n", ...data.errors.map(e => ` * ${e}\n`)].join("\n")
      )
    },
    addMessage(msg) {
      this.chat.messages = [...this.chat.messages || [], msg]
    },
    getMessageProfiles() {
      const profiles = this.messageMentions.filter(m => m.profile).map(m => m.profile.name)
      if (this.selectedUser?.name && this.selectedUser !== this.$user) {
        profiles.push(this.selectedUser.name)
      }
      return profiles.filter((v, ix, arr) => arr.findIndex(vv => vv === v) === ix)
    },
    getUserMessage(message) {
      const files = [
        ...this.messageMentions.filter(m => m.file).map(m => m.file),
        ...(this.files || [])
      ]
      return {
        role: 'user',
        content: message,
        images: this.images.map(JSON.stringify),
        files,
        profiles: this.getMessageProfiles(),
        user: this.$user.username,
        meta_data: this.metadata,
        done: true
      }
    },
    postMyMessage(message) {
      const userMessage = this.getUserMessage(message)
      this.addMessage(userMessage)
      this.cleanUserInputAndWaitAnswer()
      return userMessage
    },
    cleanUserInputAndWaitAnswer() {
      this.setEditorText("")
      this.images = []
      this.files = []
      this.mentions = []
      this.metadata = null
      this.scrollToBottom()
    },
    async addNewMessage() {
      if (this.isVoiceSession && !this.canPost) return false
      if (this.editMessage !== null) {
        this.updateMessage()
        this.saveChat()
        return false
      }
      const message = this.editorText
      if (message?.length && this.canPost && this.postMyMessage(message)) {
        await this.saveChat()
      }
      return true
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
      this.editMessage.profiles = this.getMessageProfiles()
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
      const ix = this.chat.messages.findIndex(m => m.doc_id === message.doc_id)
      if (this.chat.mode == 'task' && message.role === "assistant" && ix > 1) {
        this.chat.messages[ix - 1].hide = false
        if (this.chat.messages[ix - 2]) this.chat.messages[ix - 2].hide = false
      }
      this.chat.messages = this.chat.messages.filter((_, i) => i !== ix)
      this.saveChat()
    },
    async fileToMessage(file) {
      const content = await this.$storex.api.files.read(file)
      const ext = file.split(".").reverse()[0]
      return ["```" + `${ext} ${file}`, content, "```"].join("\n")
    },
    getEditorCaretCharOffset() {
      let caretOffset = 0
      const element = this.editor
      if (window.getSelection) {
        const range = window.getSelection().getRangeAt(0)
        const preCaretRange = range.cloneRange()
        preCaretRange.selectNodeContents(element)
        preCaretRange.setEnd(range.endContainer, range.endOffset)
        caretOffset = preCaretRange.toString().length
      }
      return caretOffset
    },
    async saveChat() {
      if (!this.chat.temp) {
        return await this.$projects.saveChat(this.chat)
      }
    },
    onDrop(e) {
      if (!e.dataTransfer.files) return
      const file = [...e.dataTransfer.files].filter(f => f.type.indexOf("image") !== -1)[0]
      if (file) this.onInputImage(file)
    },
    async onContentPaste(e) {
      if (!e.clipboardData?.items) return
      const stop = () => { e.preventDefault(); return false }

      const imageFile = [...e.clipboardData.items].find(f => f.type.indexOf("image") !== -1)?.getAsFile()
      if (imageFile) { this.onInputImage(imageFile); return stop() }

      const textItem = [...e.clipboardData.items].find(f => f.type.indexOf("text") !== -1)
      if (textItem) {
        const textContent = await new Promise(ok => textItem.getAsString(ok))
        if (textContent.startsWith("<img")) {
          const imageUrl = /src="([^"]+)/.exec(textContent)
          if (imageUrl) { this.images.push(imageUrl[1]); return stop() }
        }
        const fileMention = this.mentionList.find(m => m.file === textContent)
        if (fileMention) { 
          this.addFileToMessage(fileMention.file); 
          e.preventDefault(); 
          return stop() 
        }
        const isProjectFile = this.$projects.allProjects.find(p => textContent.startsWith(p.abs_project_path))
        if (isProjectFile && !this.pasteWithShift) {
          this.addFileToMessage(textContent)
          this.setEditorText(this.editorText.replace(textContent, ""))
          e.preventDefault()
          return stop()
        }
      }
    },
    addFileToMessage(file) {
      if (!this.files.includes(file)) {
        this.files.push(file)
      }
    },
    async onInputImage(file) {
      this.imagePreview = { file }
    },
    async onAddImage() {
      if (!this.imagePreview) return
      const formData = new FormData()
      formData.append('file', this.imagePreview.file)
      try {
        const response = await this.$storex.api.images.upload(formData)
        this.images.push(response.path)
      } catch (error) {
        console.error("Error uploading image:", error)
      } finally {
        this.imagePreview = null
      }
    },
    async onExtractTextImage(image) {
      // Convert base64 to File then extract text via API
      const byteString = atob(image.src.split(',')[1])
      const mimeString = image.src.split(',')[0].split(':')[1].split(';')[0]
      const byteArray = new Uint8Array(byteString.length)
      for (let i = 0; i < byteString.length; i++) byteArray[i] = byteString.charCodeAt(i)
      const blob = new Blob([byteArray], { type: mimeString })
      const file = new File([blob], "image", { type: mimeString })
      image.alt = await API.tools.imageToText(file)
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
    onMessageChange() {
      if (this.editor && this.editor.innerText != this.editorText) {
        this.editorText = this.editor.innerText
      }
    },
    async testProject() {
      throw new Error('Obsolete')
    },
    removeFileFromMessage(message, file) {
      message.files = message.files.filter(f => f !== file)
      this.saveChat()
    },
    removeFileFromChat(file) {
      this.chat.file_list = this.chat.file_list?.filter(f => f !== file)
      this.saveChat()
    },
    toggleVoiceSession() {
      if (this.isVoiceSession) return this.stopVoiceSession()
      let silents = 5
      this.isVoiceSession = true
      const recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)()
      recognition.lang = this.$ui.voiceLanguage
      recognition.interimResults = false
      recognition.onresult = (event) => {
        this.editor.innerText += event.results[0][0].transcript
      }
      recognition.onend = () => {
        if (this.isVoiceSession && silents--) recognition.start()
        else this.stopVoiceSession()
      }
      recognition.start()
      this.recognition = recognition
    },
    stopVoiceSession() {
      this.recognition?.stop()
      this.recognition = null
      this.isVoiceSession = false
    },
    scrollToBottom() {
      setTimeout(() => this.$refs.anchor?.scrollIntoView(), 200)
    },
    onEditMessageKeyDown(event) {
      const stop = () => { event.stopPropagation(); event.preventDefault(); return false }
      if (event.key === 'Escape') { this.onResetEdit(); return stop() }
      else if (event.key === 'Enter' && event.ctrlKey) { this.sendMessage(); return stop() }
      else if (event.key === 'f' && event.ctrlKey) { this.toggleDocumentSearch(); return stop() }
      else if (event.key === 'A' && event.ctrlKey && event.shiftKey) { this.hideAll(); return stop() }
      else if (event.key === 'b' && event.ctrlKey) { this.createBlock(); return stop() }
      else if (event.key === 'v' && event.ctrlKey) { this.pasteWithShift = false; return true }
      else if (event.key === 'V' && event.ctrlKey) { this.pasteWithShift = true; return true }
      return true
    },
    hideAll() {
      this.chat.messages.forEach(m => { m.hide = true })
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
      message.content = await this.fileToMessage(file)
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
      if (this.chat.file_list?.includes(file)) return
      this.chat.file_list = [...(this.chat.file_list || []), file]
      await this.saveChat()
    },
    onMessageEdited({ doc_id, content }) {
      this.updateExistingMessage({ doc_id }, { content })
      this.saveChat()
    },
    updateExistingMessage(message, update) {
      const existing = this.chat.messages.find(m => m.doc_id === message.doc_id)
      Object.assign(existing, update)
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
        await this.$projects.saveChatInfo(chat)
        await this.$storex.projects.chatWihProject(chat)
      } else {
        this.subtaskName = title
        this.subtaskDescription = description
        this.subtaskFiles = files
        this.subtaskProfiles = profiles
        this.subtaskMode = mode
        this.subtaskColumn = column
        this.createSubtask(false)
      }
    },
    async onPRFileCreateChat({ title, files, description, metadata, profiles, mode, column, project_id, parent_id }) {
      await this.$projects.createNewChat({
        name: title,
        description,
        project_id: project_id || this.chatProject.project_id,
        parent_id: parent_id || this.chat.id,
        file_list: files,
        profiles,
        mode,
        column: column || this.chat.column,
        board: this.chat.board,
        metadata,
        activateChat: false
      })
    },
    onPRChatMessage({ file }) {
      file.chat.messages.push({})
    },
    onValidateChanges(files) {
      const filesChanges = files.map(file => [
        "```diff " + file.fileFullName, file.diff, "```"
      ]).join("\n")
      const validateMessage = [
        filesChanges, "\n\n",
        `@wiki Validate these file changes and highlight:\n * Possible errors or issues\n * Missing functionality`
      ].join("\n")
      this.chat.messages.map(m => { m.hide = true })
      this.editorText = validateMessage
      this.sendMessage()
    },
    createBlock() {
      this.setEditorText(this.editorText + "```\n\n```")
    },
    onNewThread(message) {
      this.$projects.createNewThread({ chat: this.chat, message })
    },
    async addFileContentAsMessage(file) {
      const content = await this.$storex.chats.readFile({ chat: this.chat, file })
      const codeBlock = [
        "```" + file.split(".")[1] + " " + file, 
        content, 
        "```"]
        .join("\n")
      this.addMessage(this.getUserMessage(codeBlock))
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
    },
    async sendApiRequest(apiCall, formater = defFormater) {
      try {
        this.waiting = true
        await apiCall()
        this.$emit('refresh-chat')
        this.scrollToBottom()
      } catch (ex) {
        this.addMessage({ role: 'assistant', content: ex.message })
      }
      this.waiting = false
    }
  }
}
</script>