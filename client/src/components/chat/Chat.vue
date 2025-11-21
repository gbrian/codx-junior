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
import MentionSelector from '../mentions/MentionSelector.vue'
import PRView from '@/components/repo/PRView.vue'
import ProjectResourcesAutoCompleteVue from '../autocomplete/ProjectResourcesAutoComplete.vue'
import EditableVue from '../autocomplete/Editable.vue'
</script>

<template>
  <div class="h-full flex flex-col gap-1">
    <div class="grow relative flex flex-col">
      <div class="flex gap-2 items-center justify-bnetween">
        <ProjectResourcesAutoCompleteVue 
          class=""
          :project="projectContext"
          @select="onAddDocument"
          @close="closeDocumentSearch"
          v-if="showDocumentSearchModal"
        />
        <button class="btn btn-sm btn-outline" @click="closeDocumentSearch" v-else>
          <i class="fa-solid fa-magnifying-glass"></i>
        </button>
        <div class="w-full" v-if="chatFiles.length">
          <div class="my-2 text-xs">
            <span>
              <i class="fa-solid fa-paperclip"></i>
            </span>
            <a v-for="file in chatFiles" :key="file" :data-tip="file" class="group text-nowrap ml-2 hover:underline hover:bg-base-300 cursor-pointer text-accent" @click="$ui.openFile(file)">
              <span class="click mr-1" @click.stop="$ui.copyTextToClipboard(file)"><i class="fa-solid fa-copy"></i></span>
              <span :title="file" >{{ file?.split('/').reverse()[0] || '---error---' }}</span>
              <span class="ml-2 cursor-pointer" @click.stop="removeFileFromChat(file)">
                <i class="fa-regular fa-circle-xmark"></i>
              </span>
            </a>
          </div>
        </div>
        <CheckLists class="" :chat="chat" @change="saveChat" />
        
      </div>
      <div class="grow overflow-y-auto overflow-x-hidden">
        <Browser class="" :token="$ui.monitors['shared']" v-if="isBrowser"/>
        <PRView class="h-full overflow-auto" 
          :fromBranch="chat.pr_view?.from_branch"
          :toBranch="chat.pr_view?.to_branch"
          :chat="chat"
          @select="onPRViewBranchChanged"
          @comment="onPRFileComment"
          @change-column="$emit('change-column', $event)"
          @new-chat="onPRFileCreateChat"
          @chat-message="onPRChatMessage"
          v-if="isPRView" />
        
        <div class="overflow-auto h-full" v-if="!isBrowser && !isPRView">
          <div class="flex flex-col gap-1 mb-2">
            <ChatEntry v-for="knowledgeMessage in knowledgeMessages"
                class="rounded-lg overflow-hidden"
                :key="knowledgeMessage.id"
                :chat="chat"
                :message="knowledgeMessage"
                :isTopic="isTopic && !ix"
                :mentionList="mentionList"
                :menu-less="readOnly"
              />
          </div>
          <div class="flex flex-col" v-for="message, ix in messages" :key="message.id">
            <ChatEntry :class="['mb-4 rounded-md',
              isChannel ? '': 'py-2',
              editMessage ? editMessage === message ? 'border border-warning' : 'opacity-40' : '']"
              :chat="chat"
              :message="message"
              :isTopic="isTopic && !ix"
              :mentionList="mentionList"
              :menu-less="readOnly"
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
              @subtask="$emit('subtask', { chat: chat, message })"
            />
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
    <div class="sticky bottom-0 z-50 bg-base-300">
      <div class="flex gap-2">
        <span class="badge tooltip flex gap-2 items-center"
          :data-tip="mention.tooltip"
          :class="{ 'badge-primary': mention.project, 'badge-success badge-outline': mention.profile }"
          v-for="mention in messageMentions" :key="mention.name"
          :title="mention.file || mention.name"
          >
          <i class="fa-solid fa-magnifying-glass" v-if="mention.project"></i>
          <img class="w-4 rounded-full" :src="mention.profile.avatar" v-if="mention.profile?.avatar" />
          <i class="fa-solid fa-user" v-if="mention.profile && !mention.profile.avatar"></i>
          <i class="fa-solid fa-file-lines" v-if="mention.file"></i>
          <i class="fa-solid fa-file-arrow-up" @click="onAddFile(mention.file)" v-if="mention.file"></i>
          
          <div class="-mt-1">
            {{ mention.name }}
          </div>
          <span class="click" @click="removeMessageMention(mention)">X</span>
        </span>
      </div>

      <MentionSelector
        :content="editorText" 
        :project="projectContext || $projects" 
        @select="onMentionReplace" />

      <div class="border border-primary rounded-md bg-base-100 mt-2 pb-2" :class="['flex shadow indicator w-full', 
            'flex-col',
            editMessage && 'border-warning',
            onDraggingOverInput ? 'bg-warning/10': '']"
        @dragover.prevent="onDraggingOverInput = true"
        @dragleave.prevent="onDraggingOverInput = false"
        @drop.prevent="onDrop"
        v-if="!isBrowser && !isPRView && readOnly !== true"
        >
        <div class="editor" :class="['max-h-40 w-full px-2 py-1 overflow-auto text-wrap focus-visible:outline-none']"
          :contenteditable="!waiting"
          ref="editor"
          @paste="onContentPaste"
          @keydown="onEditMessageKeyDown"
          
        >
        </div>
        <EditableVue class="w-full h-96 border border-warning" :suggestCallback="() => 'AAAAAAAAAAAAAAAAA'"></EditableVue>
        <div class="flex justify-between items-end px-2 bg-base-300 rounded-b-md">
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
          <div class="grow flex gap-2 items-end" v-else>
            <UserSelector 
              class="dropdown-top"
              :selectedUser="selectedUser"
              :profiles="profiles"
              @user-changed="selectedUser = $event"
            />
            <div class="text-xs">Find: ctrl+f</div>
            <div class="grow"></div>
            <div class="flex gap-2 items-center justify-end" v-if="!searchingInKnowledge">
              <button class="btn btn btn-sm btn-info btn-outline" @click="sendMessage" v-if="editMessage">
                <i class="fa-solid fa-save"></i>
                <div class="text-xs" v-if="editMessage && !showDocumentSearchModal">Edit</div>
              </button>
              <button class="btn btn btn-sm btn-outline tooltip" data-tip="Save changes" @click="onResetEdit"
                v-if="editMessage">
                <i class="fa-regular fa-circle-xmark"></i>
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
              <button class="hidden btn btn btn-sm btn-outline tooltip btn-warning"
                data-tip="Make code changes" @click="improveCode()" v-if="!editMessage && chat.mode === 'chat'">
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
                  <li class="btn btn-sm tooltip"
                    :class="isVoiceSession && 'btn-success'"
                    :data-tip="$ui.voiceLanguages[$ui.voiceLanguage]"
                    @click="toggleVoiceSession" v-if="!editMessage">
                    <a>
                      <i class="fa-solid fa-microphone-lines"></i>
                      Voice mode
                    </a>
                  </li>
                  <li class="btn btn-sm btn-error tooltip"
                    :class="isVoiceSession && 'btn-success'"
                    :data-tip="$ui.voiceLanguages[$ui.voiceLanguage]"
                    @click="showDeleteModal = true" v-if="enableDelete">
                    <a>
                      <i class="fa-solid fa-trash-can"></i>
                      Delete
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
    <modal class="w-10/12 lg:w-3/4 h-10/12 lg:h-3/4" v-if="imagePreview">
      <div class="h-full flex flex-col gap-2 justify-between">
        <div class="text-2xl">Upload image</div>
        <div class="grow">
          <div class="bg-contain bg-no-repeat bg-base-300/20 bg-center h-full w-full" :style="`background-image: url(${imagePreview.src})`"></div>
        </div>
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
      <div class="flex flex-col">
        <div class="text-xl">Project file</div>
        
        <input type="text" class="input input-bordered"
          placeholder="File path" 
          v-model="uploadProjectFile" 
          />
        <button class="btn btn-sm" @click="addChatFile">
          Add file
        </button>
        
        
        <label class="file-select">
          <div class="select-button">
            <span>Select File(s)</span>
          </div>
          <input type="file" accept="image/*" multiple @change="handleFileChange" />
          <button class="btn btn-sm btn-error" @click="selectFile = false">
            Cancel
          </button>
        </label>
      </div>
    </modal>
    <modal v-if="showDeleteModal">
      <div class="flex flex-col gap-2">
        <div class="text-xl">Confirm Deletion</div>
        <p>Are you sure you want to delete this task?</p>
        <div class="font-bold text-primary text-xl">{{ taskToDelete.name }}</div>
        <div class="flex justify-end gap-2">
          <button class="btn" @click="showDeleteModal = false">Cancel</button>
          <button class="btn btn-error" @click="deleteTask">Delete</button>
        </div>
      </div>
    </modal>
  </div>
</template>

<script>
const defFormater = d => JSON.stringify(d, null, 2)

export default {
  props: ['chat', 'showHidden', 'childrenChats', 'readOnly', 'enableDelete'],
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
      previewStyle: {
        zoom: 0.6
      },
      selectFile: false,
      isVoiceSession: false,
      recognition: null,
      syncEditableTextInterval: null,
      showDeleteModal: false,
      taskToDelete: null,
      selectedUser: null,
      refreshngMentions: null,
      selectedDocuments: null,
      showDocumentSearchModal: false,
      searchingInKnowledge: false,
      projectContext: this.$project,
      uploadProjectFile: null,
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
      if (!lastAiMessages?.length) {
        return null
      }
      if (lastAiMessages.length < 2) {
        return lastAiMessages[0]
      }
      const [ last, ...previous ] = lastAiMessages  
      
      return { ...last, diffMessage: previous[0] }
    },
    lastUserMessage() {
      const { messages } = this
      const msgs = messages?.filter(m => m.role !== 'assistant')
      return msgs ? msgs[msgs.length - 1] : null
    },
    lastMessage() {
      const { messages } = this
      return messages?.length ? messages[messages.length - 1] : null
    },
    diffMessage() {
      if (this.isTask) {
        const { messages } = this.chat
        const aiMsgs = messages.filter(m => m.role === 'assistant')
        if (aiMsgs.length > 1) {
          return aiMsgs[aiMsgs.length - 2]
        }
      }
      return null
    },
    activeMessages() {
      const messages = this.chat?.messages
      return messages?.filter(m => !m.hide || this.showHidden) || []
    },
    knowledgeMessages() {
      return this.chat?.messages?.filter(m => !m.hide && m.is_answer)
    },
    messages() {
      const { activeMessages } = this
      if (!activeMessages.length) {
        return []
      }
      if (this.isTask && !this.showHidden && activeMessages?.length) {
        const aiMsg = this.lastAIMessage
        const lastMsg = activeMessages[activeMessages.length - 1]
        const res = []
        if (aiMsg) {
          res.push(aiMsg)
        }
        if (lastMsg && lastMsg?.role !== 'assistant') {
          res.push(lastMsg)
        }
        return res
      }
      return activeMessages.filter(message => (!message.hide || this.showHidden) && !message.is_answer)
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
    topicMessage() {
      return this.messages[0]
    },
    chatProject() {
      return this.projectContext || this.$project
    },
    mentionList() {
      return (this.projectContext?.$state || this.$projects).mentionList
    },
    messageMentions() {
      const mentions = [...this.messageText.matchAll(/@([^\s]+)/mg)]
        .map(w => w[1])
      return [...this.mentionList.filter(m => mentions.includes(m.mention)), 
              ...this.files.map(file => ({
                name: file.split("/").reverse()[0],
                file
              }))]
    },
    lastChatEvent() {
      const { events } = this.$storex.session
      const event = events[events.length - 1]
      if (event?.data.chat?.id === this.chat.id) {
        const message = event.data.message?.content || ""
        return `[${moment(event.ts).format('HH:mm:ss')}] ${event.data.event_type || event.data.type || ''} ${event.data.text || ''}\n${message}`
      } 
    },
    profiles() {
      return this.projectContext?.profiles || []
    },
    usersList() {
      return [this.$store.state.user, ...this.profiles]
    },
    isChannel() {
      return this.chat.mode === 'topic'
    },
    chatProject() {
      return this.$projects.allProjectsById[this.chat.project_id] ||
                this.$project
    },
    editor() {
      return this.$el.querySelector('.editor')
    }
  },
  watch: {
    chat() {
      this.initSelectedUserFromChat()
      this.setProjectContext()
    },
    uploadProjectFile(newVal, oldVal) {
      if (newVal?.length >= 3 && newVal?.length > oldVal?.length) {
        this.detectSearchTerm()
      }
    }
  },
  methods: {
    async setProjectContext() {
      if (this.projectContext?.project_id !== this.chatProject.project_id) {
        this.projectContext = await this.$projects.loadProject(this.chatProject)
      }
    },
    initSelectedUserFromChat() {
      const messages = this.chat.messages.filter(m => !m.hide && m.profiles?.length)
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
      this.editMessageId = this.chat.messages.findIndex(m => m.doc_id === message.doc_id)
      this.editMessage = this.chat.messages[this.editMessageId]
      const profile = this.editMessage.profiles[0]?.name
      if (profile) {
        this.selectedUser = profile
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
      })
      .catch(console.error)
    },
    async improveCode() {
      this.postMyMessage(this.editorText)
      await this.$projects.codeImprove(this.chat)
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
      this.chat.messages = [
        ...this.chat.messages || [],
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
      const files = [...this.messageMentions.filter(m => m.file).map(m => m.file),
                      ...(this.files ||[])]
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
      this.addMessage(userMessage)
      this.cleanUserInputAndWaitAnswer()
      return userMessage
    },
    cleanUserInputAndWaitAnswer() {
      this.setEditorText("")
      this.images = []
      this.files = []
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
        const message = this.editorText        
        if (message?.length &&
          this.canPost && this.postMyMessage(message)) {
          await this.saveChat()
        }
        if (!this.isChannel || this.lastMessage?.profiles.length) {
          await this.sendChatMessage(this.chat)
        }
      }
    },
    getSendMessage() {
      return this.editMessage ||
        this.chat.messages[this.chat.messages.length - 1].content
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
        const { response, documents } = await this.projectContext.api.knowledge.search(knowledgeSearch)
        const docs = documents.map(({ page_content, metadata: { language, score_analysis, source}}) => {
            const file = source
            const fileName = file.split("/").reverse()[0] 
            return [
                    "```" + language + " " + fileName,
                    page_content,
                    "```",
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
      const ix = this.chat.messages.findIndex(m => m.doc_id === message.doc_id)
      if (this.chat.mode == 'task' && message.role === "assistant" && ix > 1) {
        this.chat.messages[ix - 1].hide = false
      }
      this.chat.messages = this.chat.messages.filter((_, i) => i !== ix)
      this.saveChat()
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
    async addSerchTerm({ mention, orgText }) {
      if (mention.file) {
        this.onAddFile(mention.file)
      } else {
        this.setEditorText(
          this.editorText.split(" ")
              .map(w => w === orgText ? "@" + mention.name : w)
              .join(" ")
        )
      }
    },
    onMentionReplace({ mention, orgText }) {
      this.addSerchTerm({ mention, orgText })
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
    async saveChat() {
      if (!this.chat.temp) { 
        return await this.$projects.saveChat(this.chat)
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
      const stop = () => {
        e.preventDefault()
        return false
      }
      var file = [...e.clipboardData?.items].filter(f => f.type.indexOf("image") !== -1)[0]?.getAsFile()
      if (file) {
        this.onInputImage(file)
        return stop()
      }
      const text = [...e.clipboardData?.items].filter(f => f.type.indexOf("text") !== -1)[0]
      if (text) {
        const textContent = await new Promise(ok => text.getAsString(ok))
        const fileMention = this.mentionList.find(m => m.file === textContent)
        if (fileMention) {
          this.addFileToMessage(fileMention.file)
          e.preventDefault()
          return stop()
        }
        const isProjectFile = this.$projects.allProjects.find(p => textContent.startsWith(p.project_path))
        if (isProjectFile) {
          this.addFileToMessage(textContent)
          this.setEditorText(this.editorText.replace(textContent, ""))
          return stop()
        }
      }
    },
    addFileToMessage(file) {
      if (!this.files.includes(file)) {
        this.files.push(file)
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
      this.$projects.generateCode({ chat: this.chat, codeBlockInfo })
    },
    removeImage(ix) {
      this.images = this.images.filter((i, imx) => imx !== ix)
    },
    onMessageChange() {
      if (this.editor &&
        this.editor.innerText != this.editorText) {
        this.editorText = this.editor.innerText
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
    removeFileFromChat(file) {
      this.chat.file_list = this.chat.file_list?.filter(f => f !== file)
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
      } else if(event.key === 'Enter' && event.ctrlKey) {
        this.sendMessage()
      } else if(event.key === 'f' && event.ctrlKey) {
        this.toggleDocumentSearch()
      }  else {
        return true
      }
      return stop()
    },
    toggleDocumentSearch() {
      this.showDocumentSearchModal = !this.showDocumentSearchModal
    },
    openDocumentSearch() {
      this.showDocumentSearchModal = true
    },
    closeDocumentSearch() {
      this.showDocumentSearchModal = false
    },
    onAddDocument(doc) {
      const source = doc.file || doc.metadata?.source
      if (source) {
        this.addFileToMessage(source)
        this.saveChat()
      }
    },
    addFileToChat(filePath) {
      this.chat.file_list = [...new Set([...this.chat.file_list ||[], filePath])]
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
    },
    addChatFile() {
      this.onAddFile(this.uploadProjectFile)
      this.uploadProjectFile = null
      this.selectFile = false
    },
    async onAddFile(file) {
      if (this.chat.file_list?.includes(file)) {
        return
      }
      this.chat.file_list = [...(this.chat.file_list || []), file]
      this.addNewFile = null
      await this.saveChat()
    },
    onEditMessage({ orgContent, newContent }, message) {
      message.content = message.content.replace(orgContent, newContent)
      this.saveChat()
    },
    onMessageEdited({ doc_id, content }) {
      this.updateExistingMessage({ doc_id }, { content })
      this.saveChat()
    },
    updateExistingMessage(message, update) {
      const existng = this.chat.messages.find(m => m.doc_id === message.doc_id)
      Object.assign(existng, update)
      this.saveChat()
    },
    removeMessageMention(mention) {
      const orgMention = this.mentionList.find(m => m === mention)
      if (orgMention) {
        this.setEditorText(this.editorText.replace("@"+mention.name, ""))
      } else {
        this.files = this.files.filter(f => f !== mention.file)
      }
    },
    onPRViewBranchChanged({ fromBranch: from_branch, toBranch: to_branch }) {
      this.chat.pr_view = {
        from_branch, to_branch
      }
      this.saveChat()
    },
    async refreshPRView() {
      await this.saveChat()
      await this.$storex.api.repo.changes(this.chat) 
    },
    async onPRFileComment({ chat, title, files, description, profiles, mode, column }) {
      if (chat) {
        chat.messages.push({
          user: this.$user.username,
          role: "user",
          content: description
        })
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
    async onPRFileCreateChat({ title, files, description, profiles, mode, column }) {
      this.$emit('sub-task', {
          parent: this.chat,
          name: title,
          description,
          project_id: this.chatProject.id,
          parent_id: this.chat.id,
          file_list: files,
          profiles,
          mode,
          column,
          activateChat: false
        })
    },
    onPRChatMessage({ file, message, metadata }) {
      file.chat.messages.push({})
    }
  }
}
</script>