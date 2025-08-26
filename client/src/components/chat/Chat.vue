<script setup>
import moment from 'moment'
import { API } from '../../api/api'
import ChatEntry from '@/components/ChatEntry.vue'
import Browser from '@/components/browser/Browser.vue'
import Markdown from '@/components/Markdown.vue'
import TaskCard from '../kanban/TaskCard.vue'
import UserSelector from './UserSelector.vue'
import KnowledgeSearch from '../knowledge/KnowledgeSearch.vue'
import CheckLists from './CheckLists.vue'
</script>

<template>
  <div class="flex flex-col gap-1 grow">
    <div class="grow relative">
      <CheckLists class="mb-2" :chat="theChat" @change="saveChat" />
      <div class="overflow-y-auto overflow-x-hidden"
        :class="isBrowser && 'flex gap-1'">
        <div class="w-3/4" v-if="isBrowser">
          <Browser :token="$ui.monitors['shared']" />
        </div>
        <div class="overflow-auto h-full">
          <div class="flex flex-col" v-for="message in messages" :key="message.id">
            <div class="flex w-full flex-col gap-4 bg-base-100 p-2 mb-2 rounded-md" v-if="!message.content && !message.think">
              <div class="flex items-center gap-4">
                <div class="skeleton h-8 w-8 shrink-0 rounded-full"></div>
                <div class="flex flex-col gap-4">
                  <div class="skeleton h-4 w-20"></div>
                </div>
              </div>
              <div class="skeleton h-32 w-full"></div>
            </div>
            <ChatEntry :class="['mb-4 rounded-md',
              isChannel ? '': 'bg-base-100 py-2',
              editMessage ? editMessage === message ? 'border border-warning' : 'opacity-40' : '',
              message.hide ? 'opacity-80 border border-dashed p-2 border-warning' : '']"
              :chat="theChat"
              :message="message"
              @edit="onEditMessage(message)"
              @enhance="onEditMessage(message, true)"
              @remove="removeMessage(message)"
              @remove-file="removeFileFromMessage(message, $event)"
              @hide="toggleHide(message)"
              @answer="toggleAnswer(message)"
              @run-edit="runEdit"
              @copy="onCopy(message)"
              @add-file-to-chat="$emit('add-file', $event)"
              @image="imagePreview = { ...$event, readonly: true }"
              @generate-code="onGenerateCode"
              @reload-file="onReloadMessageFile"
              @open-file="onOpenFile"
              @save-file="onSaveFile"
              @code-file-shown.stop="console.log"
              v-else />
          </div>
          <div class="anchor" ref="anchor"></div>
          <div class="grid grid-cols-3 gap-2 mb-2" v-if="childrenChats?.length">
            <div v-for="child in childrenChats" :key="child.id" class="relative">
              <TaskCard class="click p-2 bg-base-100 h-40" :task="child" @click="$projects.setActiveChat(child)" />
            </div>
          </div>
        </div>
      </div>
    </div>
    <div class="chat chat-end" v-if="false && isBrowser">
      <div class="chat-image avatar">
        <div class="w-10 rounded-full">
          <img src="/only_icon.png" alt="logo" />
        </div>
      </div>
      <div class="chat-bubble">
        <Markdown class="max-h-40 overflow-auto" :text="lastAIMessage.content" v-if="lastAIMessage" />
        <div v-else>
          <span class="font-bold">Let's navigate together:</span>
          Use browser to navigate any web or try:
          <span class="italic text-info">Find top 5 results for ....</span>
        </div>
      </div>
    </div>
    <div class="sticky bottom-0 z-50 bg-base-300">
      <div class="text-ellipsis overflow-hidden text-nowrap text-xs text-info">
        {{  lastChatEvent }}
      </div>
      <div class="dropdown dropdown-top dropdown-open mb-1" v-if="showTermSearch">
        <div tabindex="0" role="button" class="rounded-md bg-base-300 w-fit p-2 hidden">
          <div class="flex p-1 items-center text-sky-600">
            <i class="fa-solid fa-at"></i>
            <input type="text" v-model="termSearchQuery"
              ref="termSearcher"
              class="-ml-1 input input-xs text-lg bg-transparent" placeholder="search term..."
              @keydown.down.stop="onSelNext"
              @keydown.up.stop="onSelPrev"
              @keydown.ctrl.enter.exact.stop="addSerchTerm(searchTerms[searchTermSelIx], true)"
              @keydown.enter.exact.stop="addSerchTerm(searchTerms[searchTermSelIx])"
              @keydown.esc="closeTermSearch" />
            <button class="btn btn-xs btn-circle btn-outline btn-error"
              @click="closeTermSearch"
              v-if="termSearchQuery">
              <i class="fa-solid fa-circle-xmark"></i>
            </button>
          </div>
        </div>
        <ul tabindex="0" class="dropdown-content z-[1] menu p-2 shadow bg-base-300 rounded-box w-fit">
          <li class="tooltip text-lg" :data-tip="term.tooltip" v-for="term, ix in searchTerms" :key="term.name">
            <a @click="addSerchTerm(term)">
              <div :class="[searchTermSelIx === ix ? 'underline':'']">
                <span class="text-sky-600 font-bold">@{{ term.name }}</span>
              </div>
            </a>
          </li>
        </ul>
      </div>
      <div class="flex gap-2">
        <span class="badge tooltip flex gap-2 items-center"
          :data-tip="mention.tooltip"
          :class="{ 'badge-primary': mention.project, 'badge-success badge-outline': mention.profile }"
          v-for="mention in messageMentions" :key="mention.name">
          <i class="fa-solid fa-magnifying-glass" v-if="mention.project"></i>
          <img class="w-4 rounded-full" :src="mention.profile.avatar" v-if="mention.profile?.avatar" />
          <i class="fa-solid fa-user" v-if="mention.profile && !mention.profile.avatar"></i>
          <div class="-mt-1">
            {{ mention.name }}
          </div>
        </span>
      </div>
      <div :class="['flex bg-base-300 border rounded-md shadow indicator w-full', 
            'flex-col',
            editMessage && 'border-warning',
            onDraggingOverInput ? 'bg-warning/10': '']"
        @dragover.prevent="onDraggingOverInput = true"
        @dragleave.prevent="onDraggingOverInput = false"
        @drop.prevent="onDrop">
        <KnowledgeSearch class="p-2 h-60"
          @select="onAddDocument"
          v-if="showDocumentSearchModal"
        />
        <div v-else class="editor" :class="['max-h-40 w-full px-2 py-1 overflow-auto text-wrap focus-visible:outline-none']"
          :contenteditable="!waiting"
          ref="editor"
          @paste="onContentPaste"
          @keydown="onEditMessageKeyDown"
        >
        </div>
        <div class="flex justify-between items-end px-2">
          <div class="carousel rounded-box">
            <div class="carousel-item relative click flex flex-col" v-for="image, ix in allImages" :key="image.src">
              <div class="bg-contain bg-no-repeat bg-center w-10 h-10 lg:h-20 lg:w-20 bg-base-300 mr-4"
                :style="`background-image: url(${image.src})`" @click="imagePreview = image">
              </div>
              <p class="text-xs">{{ image.alt.slice(0, 10) }}</p>
              <button class="btn btn-xs btn-circle btn-error absolute right-0 top-0"
                @click="removeImage(ix)">
                X
              </button>
            </div>
          </div>
          <span class="loading loading-dots loading-md btn btn-sm" v-if="waiting"></span>
          <div class="grow flex justify-between items-center" v-else>
            <UserSelector 
              class="dropdown-top"
              :selectedUser="selectedUser"
              @user-changed="selectedUser = $event"
            />
            <div class="flex gap-2 items-center justify-end py-2" v-if="!searchingInKnowledge">
              <button class="btn btn btn-sm btn-info btn-outline" @click="sendMessage" v-if="editMessage">
                <i class="fa-solid fa-save"></i>
                <div class="text-xs" v-if="editMessage && !showDocumentSearchModal">Edit</div>
              </button>
              <button class="btn btn btn-sm btn-outline tooltip" data-tip="Save changes" @click="onResetEdit"
                v-if="editMessage">
                <i class="fa-regular fa-circle-xmark"></i>
              </button>
              <button class="btn btn-sm btn-circle tooltip relative"
                :class="showDocumentSearchModal ? 'btn-error' : 'btn-info'"
                :data-tip="'Search documents'"
                @click="askKnowledge">
                <i class="fa-solid fa-file-lines"></i>
              </button>
              <button class="btn btn btn-sm btn-circle tooltip"
                data-tip="Ask codx-junior"
                :class="isVoiceSession && 'btn-success animate-pulse'"
                @click="sendMessage"
                ref="sendButton"
                v-if="!editMessage && !showDocumentSearchModal">
                <i class="fa-solid fa-microphone-lines" v-if="isVoiceSession"></i>
                <i class="fa-solid fa-paper-plane" v-else></i>
              </button>
              <button class="hidden btn btn btn-sm btn-circle btn-outline tooltip"
                :class="isBrowser && 'btn-warning'"
                data-tip="Ask codx-browser" @click="isBrowser = !isBrowser"
                v-if="!editMessage">
                <i class="fa-brands fa-chrome"></i>
              </button>
              <button class="hidden btn btn btn-sm btn-outline tooltip btn-warning"
                data-tip="Make code changes" @click="improveCode()" v-if="!editMessage && theChat.mode === 'chat'">
                <i class="fa-solid fa-code"></i>
              </button>

              <div class="dropdown dropdown-top dropdown-end">
                <div tabindex="1" role="button" class="btn btn-sm m-1">
                  <i class="fa-solid fa-ellipsis-vertical"></i>
                </div>
                <ul tabindex="1" class="dropdown-content menu bg-base-200 rounded-box z-[1] w-52 p-2 shadow gap-2">
                  <li class="btn btn-sm tooltip"
                    data-tip="Attach files"
                    @click="selectFile = true">
                    <a>
                      <i class="fa-solid fa-paperclip"></i> Attach files
                    </a>
                  </li>
                  <li class="btn btn-sm" @click="testProject" v-if="API.activeProject.script_test">
                    <a>
                      <i class="fa-solid fa-flask"></i>
                      Test
                    </a>
                  </li>
                  <li class="hidden btn btn-sm tooltip"
                    :class="isBrowser && 'btn-success'"
                    :data-tip="isBrowser ? 'Close browser' : 'Open browser'"
                    @click="isBrowser = !isBrowser" v-if="!editMessage">
                    <a>
                      <i class="fa-brands fa-chrome"></i>
                      {{ isBrowser ? 'Close' : 'Open' }} Browser
                    </a>
                  </li>
                  <li class="btn btn-sm tooltip"
                    :class="isVoiceSession && 'btn-success'"
                    :data-tip="$ui.voiceLanguages[$ui.voiceLanguage]"
                    @click="toggleVoiceSession" v-if="!editMessage">
                    <a>
                      <i class="fa-solid fa-microphone-lines"></i>
                      Voice mode
                    </a>
                  </li>
                </ul>
              </div>
            </div>
            <div class="flex gap-2 items-center justify-end py-2 animate-pulse" v-else>
              Searching...
            </div>
          </div>
        </div>
      </div>
    </div>
    <modal v-if="imagePreview">
      <div class="flex flex-col gap-2">
        <div class="text-2xl">Upload image</div>
        <div class="bg-contain bg-no-repeat bg-base-300/20 bg-center h-60 w-full" :style="`background-image: url(${imagePreview.src})`"></div>
        <div>
          Image alt: <span class="text-xs" v-if="imagePreview.alt?.length">{{ imagePreview.alt?.length }} chars.</span>
        </div>
        <pre class="alert alert-xs h-20 overflow-auto" v-if="imagePreview.readonly">{{ imagePreview.alt }}</pre>
        <div class="textarea input-bordered" v-else>
          <textarea class="w-full bg-transparent" v-model="imagePreview.alt" placeholder="Image content">
          </textarea>
          <div class="flex justify-end">
            <button class="btn btn-sm bg-purple-600 text-white tooltip"
              data-tip="Extract text"
              @click="onExtractTextImage(imagePreview)">
              <i class="fa-regular fa-closed-captioning"></i>
            </button>
          </div>
        </div>
        <div class="flex justify-end gap-2">
          <button class="btn" @click="imagePreview = null">
            Cancel
          </button>
          <button class="btn btn-primary" @click="onAddImage">
            Ok
          </button>
        </div>
      </div>
    </modal>
    <modal v-if="selectFile">
      <label class="file-select">
        <div class="select-button">
          <span>Select File(s)</span>
        </div>
        <input type="file" accept="image/*" multiple @change="handleFileChange" />
        <button class="btn btn-sm btn-error" @click="selectFile = false">
          Cancel
        </button>
      </label>
    </modal>

    <modal v-if="showModal">
      <div class="flex flex-col gap-2">
        <div class="text-xl">Confirm Deletion</div>
        <p>Are you sure you want to delete this task?</p>
        <div class="font-bold text-primary text-xl">{{ taskToDelete.name }}</div>
        <div class="flex justify-end gap-2">
          <button class="btn" @click="showModal = false">Cancel</button>
          <button class="btn btn-error" @click="deleteTask">Delete</button>
        </div>
      </div>
    </modal>
  </div>
</template>

<script>
const defFormater = d => JSON.stringify(d, null, 2)

export default {
  props: ['chat', 'chatId', 'showHidden', 'childrenChats'],
  data() {
    return {
      waiting: false,
      editMessage: null,
      editMessageId: null,
      termSearchQuery: null,
      searchTerms: null,
      searchTermSelIx: -1,
      files: [],
      images: [],
      previewImage: null,
      editorText: "",
      imagePreview: null,
      onDraggingOverInput: false,
      testError: null,
      previewStyle: {
        zoom: 0.6
      },
      selectFile: false,
      isVoiceSession: false,
      recognition: null,
      isBrowser: false,
      syncEditableTextInterval: null,
      showModal: false,
      taskToDelete: null,
      selectedUser: null,
      refreshngMentions: null,
      selectedDocuments: null,
      showDocumentSearchModal: false,
      searchingInKnowledge: false,
      projectContext: null
    }
  },
  created() {
    this.selectedUser = this.$user
    this.setProjectContext()
  },
  mounted() {
    this.syncEditableTextInterval = setInterval(() => this.onMessageChange(), 100)
    this.initSelectedUserFromChat()
  },
  unmounted() {
    clearInterval(this.syncEditableTextInterval)
  },
  computed: {
    theChat() {
      return this.chat || this.$projects.chats[this.chatId]
    },
    visibleMessages() {
      return this.theChat?.messages?.filter(m => !m.hide || this.showHidden) || []
    },
    lastAIMessage() {
      const { activeMessages } = this
      const lastAiMessages = activeMessages.filter(m => m.role === 'assistant').reverse()
      if (lastAiMessages.length < 2) {
        return lastAiMessages[0]
      }
      const [ last, ...previous ] = lastAiMessages  
      
      return { ...last, diffMessage: previous[0] }
    },
    lastUserMessage() {
      const { messages } = this.theChat
      const msgs = messages?.filter(m => !m.hide && m.role !== 'assistant')
      return msgs ? msgs[msgs.length - 1] : null
    },
    lastMessage() {
      const { messages } = this.theChat
      return messages ? messages[messages.length - 1] : null
    },
    diffMessage() {
      if (this.isTask) {
        const { messages } = this.theChat
        const aiMsgs = messages.filter(m => m.role === 'assistant')
        if (aiMsgs.length > 1) {
          return aiMsgs[aiMsgs.length - 2]
        }
      }
      return null
    },
    activeMessages() {
      const { messages } = this.theChat
      return messages.filter(m => !m.hide)
    },
    messages() {
      const messages = this.theChat?.messages
      if (!messages?.length) {
        return []
      }
      if (this.isTask) {
        const aiMsg = this.lastAIMessage
        const lastMsg = messages[messages.length - 1]
        const res = []
        if (aiMsg) {
          res.push(aiMsg)
        }
        if (lastMsg && lastMsg?.role !== 'assistant') {
          res.push(lastMsg)
        }
        return res
      }
      return messages.filter(message => !message.hide || this.showHidden)
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
      return this.theChat?.mode === 'task'
    },
    messageMentions() {
      const mentions = [...this.messageText.matchAll(/@([^\s]+)/mg)]
        .map(w => w[1])
      return this.$projects.mentionList.filter(m => mentions.includes(m.mention))
    },
    showTermSearch() {
      return this.searchTerms?.length
    },
    lastChatEvent() {
      const { events } = this.$storex.session
      const event = events[events.length - 1]
      if (event?.data.chat?.id === this.theChat.id) {
        const message = event.data.message?.content || ""
        return `[${moment(event.ts).format('HH:mm:ss')}] ${event.data.event_type || event.data.type || ''} ${event.data.text || ''}\n${message}`
      } 
    },
    usersList() {
      return [this.$store.state.user, ...this.projectContext.profiles]
    },
    isChannel() {
      return this.theChat.mode === 'channel'
    },
    chatProject() {
      return this.$projects.allProjects.find(p => p.project_id === this.theChat.project_id) ||
                this.$project
    },
    editor() {
      return this.$el.querySelector('.editor')
    }
  },
  watch: {
    termSearchQuery(newVal) {
      if (newVal?.length > 2) {
        this.searchKeywords()
      } else {
        this.searchTerms = null
      }
    },
    theChat() {
      this.initSelectedUserFromChat()
      this.setProjectContext()
    }
  },
  methods: {
    async setProjectContext() {
      this.projectContext = await this.$service.project.loadProjectContext(this.chatProject)
    },
    initSelectedUserFromChat() {
      const messages = this.theChat.messages.filter(m => !m.hide && m.profiles?.length)
      const lastProfileMessage = messages[messages.length - 1]
      if (lastProfileMessage) {
        const userName = lastProfileMessage.profiles[0]
        const user = this.$projects.userList.find(u => u.name === userName) 
        this.selectedUser = user
      } else if (!this.selectedUser) {
        this.selectedUser = this.$user
      }
    },
    zoomIn() {
      this.previewStyle.zoom += 0.1
    },
    zoomOut() {
      this.previewStyle.zoom -= 0.1
    },
    setEditorText(text) {
      this.editor.innerText = text
    },
    onEditMessage(message, enhance) {
      if (this.editMessage === message) {
        return this.onResetEdit()
      }
      this.editMessageId = this.theChat.messages.findIndex(m => m.doc_id === message.doc_id)
      this.editMessage = this.theChat.messages[this.editMessageId]
      const profile = this.editMessage.profiles[0]?.name
      if (profile) {
        this.selectedUser = profile
      } 
      try {
        this.images = message.images.map(JSON.parse)
      } catch { }
      this.setEditorText(this.editMessage.content)
    },
    toggleHide(message) {
      message.hide = !message.hide
      this.saveChat()
    },
    toggleAnswer(message) {
      message.is_answer = !message.is_answer
      this.saveChat()
    },
    onCopy(message) {
      navigator.permissions.query({ name: "clipboard-read" }).then(result => {
        if (result.state == "granted" || result.state == "prompt") {
          navigator.clipboard.writeText(message.content)
        }
      })
      .catch(console.error)
    },
    async improveCode() {
      this.postMyMessage(this.editorText)
      await this.$projects.codeImprove(this.theChat)
      this.testProject()
    },
    runEdit(codeSnipped) {
      this.sendApiRequest(
        () => API.run.edit({ id: "", messages: [{ role: 'user', content: codeSnipped }] }),
        data => [
          data.messages.reverse()[0].content,
          "\n\n",
          ...data.errors.map(e => ` * ${e}\n`)
        ].join("\n")
      )
    },
    addMessage(msg) {
      this.theChat.messages = [
        ...this.theChat.messages || [],
        msg
      ]
    },
    getMessageProfiles() {
      const profiles = this.messageMentions.filter(m => m.profile).map(m => m.profile.name)
      if (this.selectedUser?.isProfile) {
         profiles.push(this.selectedUser.name)
      }
      return profiles
    },
    getUserMessage(message) {
      const files = this.messageMentions.filter(m => m.file).map(m => m.file)
      const profiles = this.getMessageProfiles()
      return {
        role: 'user',
        content: message,
        images: this.images.map(JSON.stringify),
        files,
        profiles,
        user: this.$user.username,
        disable_knowledge: true,
      }
    },
    postMyMessage(message) {
      const userMessage = this.getUserMessage(message)
      userMessage.files.forEach(file => this.$emit('add-file', file))
      this.addMessage(userMessage)
      this.cleanUserInputAndWaitAnswer()
      return userMessage
    },
    cleanUserInputAndWaitAnswer() {
      this.setEditorText("")
      this.images = []
      this.scrollToBottom()
    },
    async sendMessage() {
      if (this.isVoiceSession && !this.canPost) {
        return
      }

      if (this.editMessage !== null) {
        this.updateMessage()
        this.saveChat()
      } else {
        const message = this.editor.innerText        
        if (this.canPost && this.postMyMessage(message)) {
          await this.saveChat()
        }
        if (!this.isChannel || this.lastMessage?.profiles.length) {
          await this.sendChatMessage(this.theChat)
        }
      }
    },
    getSendMessage() {
      return this.editMessage ||
        this.theChat.messages[this.theChat.messages.length - 1].content
    },
    async askKnowledge() {
      const searchTerm = this.editor.innerText
      if (!searchTerm || searchTerm.length <= 10) {
        return
      }
      const knowledgeSearch = {
        searchTerm,
        searchType: 'embeddings',
        documentSearchType: API.activeProject.knowledge_search_type,
        cutoffScore: API.activeProject.knowledge_context_cutoff_relevance_score,
        documentCount: API.activeProject.knowledge_search_document_count
      }
      this.searchingInKnowledge = true
      try {
        const { response, documents } = await API.knowledge.search(knowledgeSearch)
        const docs = documents.map(({ metadata: { score_analysis, source}}) => {
            const file = source
            const fileName = file.split("/").reverse()[0] 
            return [
                    `### ${fileName}`,
                    score_analysis,
                  ].join("\n")
          }).join("\n")
        const message = [
          response,
          "",
          docs
        ].join("\n")
        const searchMessage = {
          role: 'assistant',
          content: message,
          files: documents.map(doc => doc.metadata.source),
          disable_knowledge: true,
        }
        this.addMessage(searchMessage)
        this.saveChat()
        this.cleanUserInputAndWaitAnswer()
      } finally {
        this.searchingInKnowledge = false
      }
    },
    async sendApiRequest(apiCall, formater = defFormater) {
      try {
        this.waiting = true
        await apiCall()
        this.$emit('refresh-chat')
        this.scrollToBottom()
      } catch (ex) {
        this.addMessage({
          role: 'assistant',
          content: ex.message
        })
      }
      this.waiting = false
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
      const images = this.images.map(JSON.stringify)
      
      this.editMessage.files = this.messageMentions.filter(m => m.file).map(m => m.file)
      this.editMessage.profiles = this.getMessageProfiles()
      this.editMessage.content = innerText
      this.editMessage.images = images
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
      this.$emit("delete-message", message)
    },
    async searchKeywords() {
      const searchQuery = this.termSearchQuery?.toLowerCase()
      this.searchTerms = this.projectContext.mentionList.filter(mention => mention.searchIndex.includes(searchQuery))
      this.searchTermSelIx = 0
      if (!this.refreshngMentions) {
        this.refreshngMentions = this.$projects.loadProjectKnowledge()
        this.refreshngMentions.then(() => this.refreshngMentions = null)
      }
    },
    async fileToMessage(file) {
      const content = await this.$storex.api.files.read(file)
      const ext = file.split(".").reverse()[0]
      return [
        "```" + `${ext} ${file}`,
        content,
        "```"
      ].join("\n")
      
    },
    async addSerchTerm(term, addToMessage) {
      if (term.file) {
        this.$emit('add-file', term.file)
        if (addToMessage) {
          const message = await this.fileToMessage(term.file)
          const editorText = this.editorText += "\n" + message
          this.setEditorText(editorText)
        }
      }
      this.closeTermSearch()
    },
    getEditorCaretCharOffset() {
      let caretOffset = 0
      const element = this.editor
      if (window.getSelection) {
        var range = window.getSelection().getRangeAt(0)
        var preCaretRange = range.cloneRange()
        preCaretRange.selectNodeContents(element)
        preCaretRange.setEnd(range.endContainer, range.endOffset)
        caretOffset = preCaretRange.toString().length
      } else if (document.selection && document.selection.type != "Control") {
        var textRange = document.selection.createRange()
        var preCaretTextRange = document.body.createTextRange()
        preCaretTextRange.moveToElementText(element)
        preCaretTextRange.setEndPoint("EndToEnd", textRange)
        caretOffset = preCaretTextRange.text.length
      }
      return caretOffset
    },
    getCursorWord() {
      const text = this.editor?.innerText
      if (!text.length) {
        return ""
      }
      const caretIndex = this.getEditorCaretCharOffset()
      const lastWorkIndex = text.slice(0, caretIndex).split(/\s/g).length - 1
      return text.split(/\s/g)[lastWorkIndex]
    },
    detectSearchTerm() {
      const lastWord = this.getCursorWord()
      const mention = lastWord[0] === '@' ? lastWord?.slice(1) : null
      if (mention?.length >= 3 &&
        !this.$projects.mentionList.find(m => m.name === mention)) {
        this.termSearchQuery = mention
      }
      if (this.showTermSearch && !mention) {
        this.closeTermSearch()
      }
    },
    closeTermSearch() {
      this.searchTerms = null
      this.termSearchQuery = null
    },
    onSelNext() {
      this.searchTermSelIx++
      if (this.searchTermSelIx === this.searchTerms?.length) {
        this.searchTermSelIx = 0
      }
    },
    onSelPrev() {
      this.searchTermSelIx--
      if (this.searchTermSelIx === -1) {
        this.searchTermSelIx = this.searchTerms?.length - 1
      }
    },
    saveChat() {
      if (!this.theChat.temp) { 
        return API.chats.save(this.theChat)
      }
    },
    onDrop(e) {
      this.onDraggingOverInput = false
      if (!e.dataTransfer.files) {
        return
      }
      var file = [...e.dataTransfer.files].filter(f => f.type.indexOf("image") !== -1)[0]
      if (file) {
        this.onInputImage(file)
      }
    },
    async onContentPaste(e) {
      if (!e.clipboardData?.items) {
        return
      }
      var file = [...e.clipboardData?.items].filter(f => f.type.indexOf("image") !== -1)[0]?.getAsFile()
      if (file) {
        this.onInputImage(file)
        e.preventDefault()
        return false
      }
    },
    getFileImageUrl(file) {
      return new Promise(ok => {
        const reader = new FileReader()
        reader.onload = (event) => {
          const base64URL = event.target.result
          ok(base64URL)
        }
        reader.readAsDataURL(file)
      })
    },
    async onInputImage(file) {
      const base64URL = await this.getFileImageUrl(file)
      this.imagePreview = {
        src: base64URL,
        alt: ""
      }
    },
    onAddImage() {
      if (this.imagePreview.ix === undefined) {
        this.images.push(this.imagePreview)
        this.imagePreview.ix = this.images.length - 1
      }
      this.imagePreview = null
    },
    async onExtractTextImage(image) {
      function base64ToFile(base64Data, filename) {
        const byteString = atob(base64Data.split(',')[1])
        const mimeString = base64Data.split(',')[0].split(':')[1].split(';')[0]
        const byteArray = new Uint8Array(byteString.length)
        for (let i = 0; i < byteString.length; i++) {
          byteArray[i] = byteString.charCodeAt(i)
        }
        const blob = new Blob([byteArray], { type: mimeString })
        return new File([blob], filename, { type: mimeString })
      }

      const file = base64ToFile(image.src, "image")
      const text = await API.tools.imageToText(file)
      image.alt = text
    },
    async handleFileChange({ target: { files } }) {
      const allUrls = await Promise.all([...files].map(file => this.getFileImageUrl(file)))
      console.log("handleFileChange", allUrls)
      this.images = [
        ...this.images,
        ...allUrls.map((src, ix) => ({ src, alt: "", ix: this.images.length + 1 + ix }))
      ]
      this.selectFile = false
    },
    onGenerateCode(codeBlockInfo) {
      this.$projects.generateCode({ chat: this.theChat, codeBlockInfo })
    },
    removeImage(ix) {
      this.images = this.images.filter((i, imx) => imx !== ix)
    },
    onMessageChange() {
      if (this.editor &&
        this.editor.innerText != this.editorText) {
        this.editorText = this.editor.innerText
        this.detectSearchTerm()
      }
    },
    async testProject() {
      throw new Error('Obsolte')
      const data = await API.projects.test()
      this.testError = data
      if (this.testError) {
        this.editMessage = this.testError
        this.setEditorText(this.editMessage)
      }
    },
    removeFileFromMessage(message, file) {
      message.files = message.files.filter(f => f !== file)
      this.saveChat()
    },
    toggleVoiceSession() {
      if (this.isVoiceSession) {
        return this.stopVoiceSession()
      }
      let silents = 5
      this.isVoiceSession = true

      const recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)()
      recognition.lang = this.$ui.voiceLanguage
      recognition.interimResults = false

      recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript
        this.editor.innerText += transcript
      }

      recognition.onend = () => {
        if (this.isVoiceSession && silents--) {
          recognition.start()
        } else {
          this.stopVoiceSession()
        }
      }

      recognition.start()
      this.recognition = recognition
    },
    stopVoiceSession() {
      this.recognition?.stop()
      this.recognition = null
    },
    scrollToBottom() {
      setTimeout(() => this.$refs.anchor?.scrollIntoView(), 200)
    },
    onEditMessageKeyDown(event) {
      const stop = () => {
        event.stopPropagation()
        event.preventDefault()
        return false
      }
      if (event.key === 'Escape') {
        this.onResetEdit()
      } else if (event.key === 'Tab' && this.showTermSearch) {
        this.addSerchTerm(this.searchTerms[this.searchTermSelIx])
      } else if(event.key === 'Enter' && event.ctrlKey) {
        this.sendMessage()
      } else {
        return true
      }
      return stop()
    },
    openDocumentSearch() {
      this.showDocumentSearchModal = !this.showDocumentSearchModal
    },
    onAddDocument(doc) {
      const source = doc.metadata.source
      this.theChat.file_list = [...new Set([...this.theChat.file_list ||[], source])]
      this.saveChat()
    },
    async onReloadMessageFile({ file, message }) {
      message.content = await this.fileToMessage(file)
      this.saveChat()
    },
    onSaveFile({ file, content }) {
      this.projectContext.api.files.write(file, content)
    },
    onOpenFile(file) {
      this.projectContext.api.coder.openFile(file)
    }
  }
}
</script>