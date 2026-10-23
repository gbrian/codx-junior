<script setup>
import CheckLists from './CheckLists.vue'
import PRChangesPanel from '@/components/vibe/panels/PRChangesPanel.vue'
import ChatFileList from './ChatFileList.vue'
import ChatInputBox from './ChatInputBox.vue'
import ChatFileSelectorModal from './ChatFileSelectorModal.vue'
import ChatMessageList from './ChatMessageList.vue'
import ChatIntelliSense from './ChatIntelliSense.vue'
import ChatFilePreview from './ChatFilePreview.vue'
import ChatProfileSelector from './ChatProfileSelector.vue'
import ChatFileUploadConfirmModal from './ChatFileUploadConfirmModal.vue'
import ChatAttachmentPreview from './ChatAttachmentPreview.vue'
import { ENTITY_STATUS } from '@/store/entityStatuses'
import ChatAttachment from '@/api/model/ChatAttachment.js'
import Collapsible from '../Collapsible.vue'
import { extractCodeBlocks } from '@/utils/codeBlockExtractor'
</script>

<template>
  <div class="h-full flex flex-col gap-1 overflow-hidden"
    @dragover.prevent="onDragOver"
    @dragleave.prevent="handleDragLeave"
    @drop.prevent="onDropChat"
    :class="draggingOver && 'ring-2 ring-primary ring-inset rounded-lg'"
  >
    <!-- Loading Skeleton -->
    <div v-if="isChatLoading" class="h-full flex flex-col gap-2 p-4">
      <div class="shrink-0 flex gap-2 items-center justify-between">
        <div class="skeleton h-10 w-32"></div>
        <div class="skeleton h-10 w-20"></div>
      </div>
      <div class="grow flex flex-col gap-3 overflow-y-auto">
        <div class="flex gap-2">
          <div class="skeleton h-8 w-8 rounded-full shrink-0"></div>
          <div class="flex-1 flex flex-col gap-2">
            <div class="skeleton h-4 w-24"></div>
            <div class="skeleton h-12 w-full"></div>
          </div>
        </div>
        <div class="flex gap-2 justify-end">
          <div class="flex-1 flex flex-col gap-2">
            <div class="skeleton h-4 w-20 ml-auto"></div>
            <div class="skeleton h-12 w-full"></div>
          </div>
        </div>
        <div class="flex gap-2">
          <div class="skeleton h-8 w-8 rounded-full shrink-0"></div>
          <div class="flex-1 flex flex-col gap-2">
            <div class="skeleton h-4 w-32"></div>
            <div class="skeleton h-16 w-full"></div>
          </div>
        </div>
      </div>
      <div class="shrink-0 flex flex-col gap-2">
        <div class="skeleton h-20 w-full"></div>
        <div class="skeleton h-10 w-24"></div>
      </div>
    </div>

    <!-- Normal Chat Content -->
    <template v-else>

      <!-- ── Files + profiles strip ──
           Hidden on mobile while the chat header details panel is collapsed
           (`hideFilesHeader`, owned by ChatView) so the reading area keeps the
           vertical space. Always rendered on desktop / expanded mobile. -->
      <Collapsible v-if="!hideFilesHeader" :defaultOpen="false" class="w-full">
        <!-- Icon -->
        <template #icon>
          <span></span>
        </template>

        <!-- Title -->
        <template #title>
          <div class="flex flex-wrap items-center gap-2 text-xs text-base-content/50 mt-0.5">
            <i class="fa-solid fa-file"></i>
            Files: {{ allFilesCount }} +
          </div>
        </template>

        <!-- Actions -->
        <template #actions>
          <div class="flex items-center gap-2" v-if="!isVibe && !isPRView">
            <ChatProfileSelector
              :project="chatProject"
              :selected-profiles="chat.profiles"
              :use-modal="true"
              @profiles-changed="onProfilesChanged"
            />
            <CheckLists :chat="chat" :readOnly="readOnly" />
          </div>
        </template>

        <!-- File list + profile selector header -->
        <div class="shrink-0 flex gap-2 items-center justify-between overflow-auto">
          <div class="w-full" v-if="chatFiles.length || messageFiles.length">
            <ChatFileList
              :files="chatFiles"
              :message-files="messageFiles"
              :chat-project="chatProject"
              @remove-file="removeFileFromChat"
              @add-file="onAddFileToChat"
              @add-as-message="addFileContentAsMessage"
              @sync-notebook="syncNotebook"
              @export-notebook="exportNotebook"
              @preview-file="openFilePreview"
              v-if="(chatFiles?.length || messageFiles?.length) && !isPRView"
            />
          </div>
        </div>
      </Collapsible>

      <!-- PR View Section -->
      <div class="grow overflow-auto" v-show="isPRView">
        <PRChangesPanel
          class="h-full flex flex-col overflow-auto"
          :chat="chat"
          @comment="onPRFileComment"
        />
      </div>

      <!-- Main Chat View -->
      <div class="grow flex gap-2 min-h-0 overflow-hidden" v-show="!isPRView">

        <div class="flex flex-col min-h-0 min-w-0" :class="previewFile ? 'w-1/2' : 'w-full'">

          <!-- ── Unified scroll container: messages + composer ── -->
          <ChatMessageList
            ref="messageList"
            class="w-full h-full"
            :chat="chat"
            :messages="messages"
            :edit-message="editMessage"
            :mention-list="mentionList"
            :read-only="readOnly"
            :users-list="usersList"
            :children-chats="childrenChats"
            :processing="isProcessing"
            @edited="onMessageEdited"
            @remove="removeMessage"
            @remove-file="removeFileFromMessage($event.message, $event.file)"
            @hide="toggleHide"
            @answer="toggleAnswer"
            @run-edit="runEdit"
            @copy="onCopy"
            @add-file-to-chat="onAddFile"
            @image="onMessageImagePreview"
            @generate-code="onGenerateCode"
            @reload-file="onReloadMessageFile"
            @open-file="onOpenFile"
            @save-file="onSaveFile"
            @add-file="onAddFile"
            @edit-message="onEditMessage"
            @thread="onNewThread"
            @sub-task="onChatEntryCreateSubtask"
            @set-active-chat="$chats.setActiveChat($event)"
            @message-changed="onMessageChanged"
            @run-agents="onMessageRunAgents"
            @preview-file="handleFilePreview"
            @search-files="onSelectionSearchFiles"
            @update-attachment="onMessageAttachmentUpdated"
          >
            <!-- IntelliSense slot — floats above the composer -->
            <template #intellisense>
              <ChatIntelliSense
                ref="intelliSense"
                :suggestions="intelliSenseSuggestions"
                :active-index="intelliSenseIndex"
                :query="intelliSenseQuery"
                :search-controller="searchController"
                :progress="intelliSenseProgress"
                @select="onIntelliSenseSelect"
                @hover="intelliSenseIndex = $event"
                @accept-multi="onIntelliSenseAcceptMulti"
                @cancel="cancelIntelliSense"
              />
            </template>

            <!-- Input box slot -->
            <template #input>
              <!-- Edit mode banner -->
              <div v-if="editMessage" class="flex items-center gap-2 px-3 py-1.5 mb-1 bg-warning/10 border border-warning/30 rounded-lg text-xs text-warning">
                <i class="fa-solid fa-pen-to-square"></i>
                <span>Editing message from <strong>{{ editMessage.user }}</strong></span>
                <button class="ml-auto btn btn-xs btn-ghost text-warning" @click="onResetEdit">
                  <i class="fa-solid fa-xmark"></i> Cancel
                </button>
              </div>
              <ChatInputBox
                ref="inputBox"
                :waiting="waiting"
                :is-editing="!!editMessage"
                :is-voice-session="isVoiceSession"
                :searching="searchingInKnowledge"
                :read-only="readOnly"
                :selected-model="chat.llm_model"
                :ai-models="aiModels"
                :profiles="profiles"
                :selected-profiles="selectedProfiles"
                :project="messageTargetProject"
                :chat-project="chatProject"
                :cursor-word="cursorWord"
                :voice-language-label="$ui.voiceLanguages?.[$ui.voiceLanguage]"
                :chat="chat"
                :collapsed="inputCollapsed"
                :attachment-count="attachments?.length || 0"
                :file-count="files?.length || 0"
                @send="sendMessage"
                @add-message="addNewMessage()"
                @search-message="addSearchMessage"
                @cancel-edit="onResetEdit"
                @paste="onContentPaste"
                @keydown="onChatInputKeyDown"
                @drop.stop="onDropInputBox"
                @model-changed="onLLMModelChanged"
                @profiles-selected="onProfilesSelected"
                @project-changed="onMessageProjectChanged"
                @upload-files="onUploadFiles"
                @toggle-voice="toggleVoiceSession"
                @toggle-collapsed="toggleInputCollapsed"
              />
              <!-- Hidden while the composer is collapsed on mobile (reading mode) -->
              <ChatAttachmentPreview
                :attachments="attachments"
                @remove-attachment="removeAttachment"
                @update-attachment="onAttachmentUpdated"
                v-if="attachments?.length && !composerCollapsed"
              />
            </template>

            <!-- Per-message files slot (files attached to the current message being composed) -->
            <template #files>
              <!-- Hidden while the composer is collapsed on mobile (reading mode) -->
              <ChatFileList
                :files="files"
                :message-files="noMessageFiles"
                :chat-project="chatProject"
                @remove-file="removeFileFromFiles"
                @add-file="addFileContentAsMessage"
                @preview-file="handleFilePreview"
                v-if="files?.length && !composerCollapsed"
              />
            </template>
          </ChatMessageList>

        </div>

        <!-- File Preview Panel -->
        <div class="w-1/2 min-h-0 flex flex-col" v-if="previewFile && !isVibe">
          <ChatFilePreview
            class="h-full"
            :file-path="previewFile"
            :chat-project="chatProject"
            @close="closeFilePreview"
            @saved="onPreviewFileSaved"
          />
        </div>

      </div>

      <!-- Modals -->
      <ChatFileSelectorModal
        :show="selectFile"
        :file-path="uploadProjectFile"
        @update:filePath="uploadProjectFile = $event"
        @close="selectFile = false"
        @add-file="addChatFile"
        @file-change="handleFileChange"
      />

      <ChatFileUploadConfirmModal
        :show="showUploadConfirmModal"
        :files="pendingUploadFiles"
        :upload-path="uploadPath"
        @confirm="confirmUpload"
        @cancel="cancelUpload"
      />

      <!-- Notification Toast -->
      <div v-if="notebookStatus" class="toast toast-top toast-center z-50">
        <div class="alert alert-info text-xs">
          <i class="fa-solid fa-book-open mr-1"></i>
          <span>{{ notebookStatus }}</span>
        </div>
      </div>
    </template>
  </div>
</template>

<script>
import ChatAttachment from '@/api/model/ChatAttachment.js'

// Stable empty list. Returning a brand new `[]` from a computed — or writing an
// array literal in the template — gives the file list a NEW identity on every
// render, which makes <ChatFileList> rebuild its chips and re-check every file
// on the server (see ChatFileList.syncFiles).
const EMPTY_FILE_LIST = Object.freeze([])

export default {
  props: [
    'chat',
    'filter',
    'showHidden',
    'childrenChats',
    'readOnly',
    'message',
    'input-only',
    // Mobile: hide the files/profiles strip while the chat header details panel
    // is collapsed (see ChatView), so the reading area keeps the vertical space.
    'hideFilesHeader'
  ],
  data() {
    return {
      waiting: false,
      editMessage: null,
      editMessageId: null,
      files: [],
      attachments: [],
      draggingOver: false,
      onDraggingOverInput: false,
      dragoverTimeout: null,
      selectFile: false,
      isVoiceSession: false,
      recognition: null,
      syncEditableTextInterval: null,
      selectedUser: null,
      // Project the next message is addressed to (message.project_id).
      // `null` keeps the chat's project, which is the default behaviour.
      messageProject: null,
      // True once the project picker was used while composing/editing. The
      // message being edited only rewrites its `project_id` when the selection
      // really changed, so an untouched edit never drops the stored project
      // (see updateMessage).
      messageProjectTouched: false,
      showDocumentSearchModal: false,
      searchingInKnowledge: false,
      uploadProjectFile: null,
      metadata: null,
      pasteWithShift: false,
      mentions: [],
      selectorProfileNames: [],
      textProfileNames: [],
      cursorWord: {},
      notebookStatus: null,
      editorText: "",
      previewFile: null,
      intelliSenseSuggestions: [],
      intelliSenseIndex: 0,
      intelliSenseQuery: '',
      intelliSenseProgress: '',
      intelliSenseDebounce: null,
      intelliSenseDismissed: false,
      searchController: null,
      previousQuery: null,
      previousEditorText: '',
      showUploadConfirmModal: false,
      pendingUploadFiles: [],
      uploadPath: '',
      uploadContext: null,
      MAX_IMAGE_SIZE_MB: 50,
      dragCounter: 0,
      inputCollapsed: false,
      // In-flight attachment conversions (FileReader) — see flushPendingAttachments()
      attachmentTasks: [],
      // (chatId::projectId) the project state was last initialised for. The
      // chat record is REPLACED by the store on every update (reload, socket
      // event, list refresh), so this key — not the object — tells a real
      // navigation apart from a mere refresh (see the `chat` watcher).
      projectInitKey: null
    }
  },
  created() {
    this.selectedUser = this.$user
    this.metadata = this.message?.metadata
    this.editorText = this.message?.content
    // Collapse the composer by default on mobile to leave more room for reading
    this.inputCollapsed = this.$ui.isMobile
    this.initProject()
  },
  mounted() {
    this.syncEditableTextInterval = setInterval(() => this.onMessageChange(), 100)
    this.editorText && this.setEditorText(this.editorText)
  },
  unmounted() {
    clearInterval(this.syncEditableTextInterval)
    clearTimeout(this.dragoverTimeout)
    this.cancelIntelliSense()
  },
  computed: {
    chatSvc() {
      return this.$service.chat
    },
    isChatLoading() {
      return !this.chat?.id || this.chat?.status === ENTITY_STATUS.LOADING
    },
    // True while the chat is being processed (waiting for the server's first
    // chunk or streaming). Driven by the shared chats store flag, which is set
    // immediately on send and auto-resets on a timeout if the server never replies.
    isProcessing() {
      return !!this.chat?.id && this.$chats.isChatUpdating(this.chat.id)
    },
    aiModels() {
      return this.isTopic ? [] : this.$projects.ai.models || []
    },
    // Files attached to the chat. `file_list` belongs to the chat record, so its
    // identity is stable until the list really changes; EMPTY_FILE_LIST keeps the
    // "no files" case stable too (`|| []` used to return a new array on every
    // evaluation, re-arming the <ChatFileList> watcher).
    chatFiles() {
      return this.chat?.file_list || EMPTY_FILE_LIST
    },
    // Files referenced by the conversation: the ones linked to each message plus
    // the paths found in its code blocks / <file_change> envelopes.
    //
    // This is evaluated on EVERY message update (streaming included), so it must
    // not produce new data when nothing changed:
    //  * the (expensive) markdown parsing is cached per message and only re-runs
    //    when that message's content changes;
    //  * the resulting array keeps its identity while the file list is the same,
    //    otherwise <ChatFileList> would rebuild its chips — and re-check every
    //    file on the server — on each streamed chunk.
    messageFiles() {
      const parseCache = this.parsedMessageFiles || (this.parsedMessageFiles = new Map())
      const nextParseCache = new Map()
      const files = new Set()

      ;(this.messages || []).forEach(message => {
        const key = message.doc_id || message.id || null
        const content = message.content || ''
        const cached = key ? parseCache.get(key) : null
        const parsed = cached && cached.content === content
          ? cached.files
          : this.extractFilesFromCodeBlocks(content)
        if (key) nextParseCache.set(key, { content, files: parsed })

        ;(message.files || []).forEach(file => files.add(file))
        parsed.forEach(file => files.add(file))
      })

      this.parsedMessageFiles = nextParseCache

      const next = Array.from(files)
      // Same list → keep the very same array (no prop change downstream)
      if (this.lastMessageFiles && this.sameList(this.lastMessageFiles, next)) {
        return this.lastMessageFiles
      }
      this.lastMessageFiles = next
      return next
    },
    // Number of distinct files shown in the files strip header. A count, not a
    // collection, so nothing is recreated when the conversation updates.
    allFilesCount() {
      return new Set([...this.chatFiles, ...this.messageFiles]).size
    },
    isPRView() {
      return this.chat.mode === 'prview'
    },
    isVibe() {
      return this.chat.mode === 'vibe'
    },
    isGroup() {
      return this.chat.mode === 'group'
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
    // Messages rendered by the list.
    //
    // The chats store patches the conversation IN PLACE (see `mergeMessages`),
    // so a refresh streaming a new chunk mutates `message.content` without
    // touching the array. This computed filters — and a `filter()` always
    // returns a NEW array — which would give the whole message list a new prop
    // identity and re-render every child of `ChatMessageList`: the composer,
    // the intellisense dropdown and every modal living in its slots. Keeping
    // the previous array while the items are the same prevents that cascade.
    messages() {
      const next = this.activeMessages.filter(message => !message.hide || this.showHidden)
      if (this.lastMessages && this.sameList(this.lastMessages, next)) return this.lastMessages
      this.lastMessages = next
      return next
    },
    canPost() {
      return this.editorText || this.attachments?.length
    },
    isTask() {
      return this.chat?.mode === 'task'
    },
    isTopic() {
      return this.chat?.mode === 'topic'
    },
    chatProject() {
      return this.$projects.allProjectsById[this.chat.project_id || this.chat.owner_project_id]
        || this.$project
    },
    // Project the message being composed is addressed to: the explicitly selected
    // one or, by default, the chat's working project.
    messageTargetProject() {
      return this.messageProject || this.chatProject
    },
    // Identity of the (chat, working project) pair the project state belongs to.
    // Stable across store refreshes: `registerChat()` replaces the chat object
    // but never this key, which is exactly what the `chat` watcher needs.
    chatProjectKey() {
      return `${this.chat?.id || ''}::${this.chatProject?.project_id || ''}`
    },
    mentionList() {
      // Mentions resolve against the same project the message is addressed to
      return this.messageTargetProject?.$state?.mentionList
        || this.chatProject?.$state?.mentionList
        || this.$projects.mentionList
    },
    // On mobile the composer collapses while reading the messages; the image/files
    // previews are hidden too so the reading area stays clean.
    composerCollapsed() {
      return this.$ui.isMobile && this.inputCollapsed
    },
    // Stable empty list handed to the composer's file list: an inline `[]` in the
    // template would be a brand new array on every render of this component.
    noMessageFiles() {
      return EMPTY_FILE_LIST
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
    hasIntelliSense() {
      return this.intelliSenseSuggestions.length > 0
    },
    selectedProfiles() {
      const allSelectedNames = [...new Set([...this.selectorProfileNames, ...this.textProfileNames])]
      return this.profiles.filter(p => allSelectedNames.includes(p.name))
    },
    groupMessageHasProfileMention() {
      if (!this.isGroup) return false
      const allProfileNames = this.profiles.map(p => p.name)
      const mentionedNames = [...this.editorText?.matchAll(/@([^\s]+)/mg) || []].map(m => m[1])
      return mentionedNames.some(name => allProfileNames.includes(name))
    }
  },
  watch: {
    // The store REPLACES the chat object on every update (load, reload, socket
    // "changed" event, chats-list refresh). Initialising the project state on
    // each of those re-entered the loaders that produce those updates
    // (`initProjectState` → reload chats/kanban → registerChat → new object),
    // which cascaded into an endless rebuild of every column and task of the
    // board. Only a real navigation (another chat / another working project)
    // may initialise the project state.
    chat() {
      if (this.projectInitKey === this.chatProjectKey) return
      this.initProject()
    },
    uploadProjectFile(newVal, oldVal) {
      if (newVal?.length >= 3 && newVal?.length > oldVal?.length) {
        this.detectSearchTerm()
      }
    },
    editorText() {
      this.updateCursorWord()
      this.updateProfileMentionsFromText()
      this.scheduleIntelliSense()
    },
    editMessage(newVal) {
      // Always expand the composer while editing a message
      if (newVal) this.inputCollapsed = false
    },
    // Suggestions belong to the project they were searched in: drop them when
    // the message starts targeting another project (message.project_id).
    messageProject() {
      this.cancelIntelliSense()
      this.intelliSenseDismissed = false
    }
  },
  methods: {
    toggleInputCollapsed() {
      this.inputCollapsed = !this.inputCollapsed
      if (!this.inputCollapsed) {
        this.$nextTick(() => this.$refs.inputBox?.focusEditor())
      }
    },
    initProject() {
      // Remember what was initialised so the `chat` watcher can tell a store
      // refresh (same key → ignore) from a real navigation (new key → init).
      this.projectInitKey = this.chatProjectKey
      this.$projects.initProjectState(this.chatProject)
    },
    extractFilesFromCodeBlocks(content) {
      return extractCodeBlocks(content)
        .map(block => block.filePath)
        .filter(Boolean)
    },
    // Same items, same order. Used to keep collection identities stable so
    // downstream components are not re-rendered with identical data.
    sameList(previous, next) {
      if (previous === next) return true
      if (!previous || !next || previous.length !== next.length) return false
      return next.every((item, index) => item === previous[index])
    },
    updateProfileMentionsFromText() {
      const mentionMatches = [...this.editorText?.matchAll(/@([^\s]+)/mg) || []]
      const mentionedNames = mentionMatches.map(m => m[1])
      const profileNames = this.profiles.map(p => p.name)
      const detectedProfiles = mentionedNames.filter(name => profileNames.includes(name))
      const previousMentionMatches = [...this.previousEditorText?.matchAll(/@([^\s]+)/mg) || []]
      const previousMentionedNames = previousMentionMatches.map(m => m[1])
      const previousDetectedProfiles = previousMentionedNames.filter(name => profileNames.includes(name))
      const profilesToRemove = previousDetectedProfiles.filter(
        name => !detectedProfiles.includes(name) && !this.selectorProfileNames.includes(name)
      )
      profilesToRemove.forEach(name => {
        const idx = this.textProfileNames.indexOf(name)
        if (idx > -1) this.textProfileNames.splice(idx, 1)
      })
      detectedProfiles.forEach(name => {
        if (!this.textProfileNames.includes(name)) this.textProfileNames.push(name)
      })
      this.previousEditorText = this.editorText
    },
    hasFile(fileToCheck, fileList) {
      return fileList.some(f => this.normalizeFilePath(f) === this.normalizeFilePath(fileToCheck))
    },
    normalizeFilePath(path) {
      return path?.toLowerCase().trim() || ''
    },
    hasFileInChat(file) {
      return this.hasFile(file, this.chatFiles)
    },
    hasFileInMessage(file) {
      return this.hasFile(file, this.files)
    },
    isProjectFile(textContent) {
      return this.$projects.allProjects.find(p => textContent.startsWith(p.abs_project_path))
    },
    async processFilePath(filePath, chatDrop) {
      if (!this.isProjectFile(filePath)) return false
      if (chatDrop) {
        await this.onAddFile(filePath)
      } else {
        this.addFileToMessage(filePath)
      }
      return true
    },
    async processMultipleFilePaths(textContent, chatDrop) {
      const filePaths = textContent
        .split('\n')
        .map(p => p.trim())
        .filter(p => p && p.length > 0 && this.isProjectFile(p))
      if (filePaths.length === 0) return false
      for (const filePath of filePaths) {
        await this.processFilePath(filePath, chatDrop)
      }
      return true
    },
    async processJsonFileList(jsonData, chatDrop) {
      try {
        const { files } = JSON.parse(jsonData)
        if (!files || files.length === 0) return false
        for (const file of files) {
          if (!file.is_dir) await this.processFilePath(file.path, chatDrop)
        }
        return true
      } catch (ex) {
        console.error('[DROP] Error parsing file list JSON', ex)
        return false
      }
    },
    validateImageSize(file) {
      const maxSizeBytes = this.MAX_IMAGE_SIZE_MB * 1024 * 1024
      if (file.size > maxSizeBytes) {
        const errorMsg = `File exceeds maximum size of ${this.MAX_IMAGE_SIZE_MB}MB`
        this.$ui?.addNotification?.({ text: errorMsg, type: 'error' })
        return false
      }
      return true
    },
    async prepareAttachmentFromFile(file) {
      if (!this.validateImageSize(file)) return null
      try {
        const attachment = await ChatAttachment.fromFile(file)
        return attachment
      } catch (error) {
        console.error("Error preparing attachment:", error)
        this.$ui?.addNotification?.({ text: "Failed to process file", type: 'error' })
        return null
      }
    },
    async prepareAttachmentFromUrl(imgUrl) {
      try {
        const response = await fetch(imgUrl)
        if (!response.ok) {
          console.error(`Failed to fetch image from URL: ${imgUrl}`)
          return null
        }
        const blob = await response.blob()
        const file = new File([blob], this.extractFileNameFromUrl(imgUrl), { type: blob.type })
        return await ChatAttachment.fromFile(file)
      } catch (error) {
        console.error("Error preparing image URL:", error)
        this.$ui?.addNotification?.({ text: "Failed to process image URL", type: 'error' })
        return null
      }
    },
    extractFileNameFromUrl(url) {
      try {
        const pathname = new URL(url).pathname
        const fileName = pathname.split('/').pop()
        return fileName && fileName.length > 0 ? fileName : 'image.png'
      } catch {
        return 'image.png'
      }
    },
    onInputAttachmentPreview(file) {
      this.pendingImage = file
    },
    onMessageImagePreview(imageFile) {
      this.imagePreview = imageFile
    },
    async processMultipleImages(imageFiles, isMessage) {
      const validImageFiles = imageFiles.filter(f => this.validateImageSize(f))
      if (validImageFiles.length === 0) return false
      for (const imageFile of validImageFiles) {
        const attachment = await this.prepareAttachmentFromFile(imageFile)
        if (attachment) {
          if (isMessage) {
            this.attachments.push(attachment)
          } else {
            this.chat.attachments.push(attachment)
          }
        }
      }
      return validImageFiles.length > 0
    },
    async onUploadFiles(files) {
      // Reading the file is asynchronous (FileReader). Keep the task around so a
      // save triggered right after stopping a recording can wait for it instead
      // of dropping the attachment.
      const task = this.addAttachmentsFromFiles(files)
      this.attachmentTasks.push(task)
      try {
        await task
      } finally {
        this.attachmentTasks = this.attachmentTasks.filter(t => t !== task)
      }
    },
    async addAttachmentsFromFiles(files) {
      for (const file of files) {
        const attachment = await this.prepareAttachmentFromFile(file)
        if (attachment) this.attachments = [...this.attachments, attachment]
      }
    },
    // A voice note stopped right before saving may still be being read.
    // Never persist (or post) a message before its attachments are ready.
    async flushPendingAttachments() {
      if (!this.attachmentTasks.length) return
      await Promise.allSettled([...this.attachmentTasks])
    },
    showUploadConfirmation(fileList, uploadPath, context) {
      this.pendingUploadFiles = Array.from(fileList)
      this.uploadPath = uploadPath
      this.uploadContext = context
      this.showUploadConfirmModal = true
    },
    async confirmUpload() {
      this.showUploadConfirmModal = false
      const uploadedPaths = await this.performUpload(this.pendingUploadFiles, this.uploadPath)
      if (this.uploadContext.chatDrop) {
        uploadedPaths.forEach(path => this.onAddFile(path))
      } else {
        uploadedPaths.forEach(path => this.addFileToMessage(path))
      }
      this.pendingUploadFiles = []
      this.uploadPath = ''
      this.uploadContext = null
    },
    cancelUpload() {
      this.showUploadConfirmModal = false
      this.pendingUploadFiles = []
      this.uploadPath = ''
      this.uploadContext = null
    },
    async performUpload(fileList, uploadPath) {
      const uploadedFilePaths = []
      for (const file of fileList) {
        try {
          const result = await this.$storex.api.files.upload(file, uploadPath)
          const filePath = result?.path || result
          uploadedFilePaths.push(filePath)
        } catch (error) {
          console.error('[UPLOAD] Failed to upload file:', file.name, error)
          this.$ui?.addNotification?.({ text: `Failed to upload ${file.name}: ${error.message}`, type: 'error' })
        }
      }
      return uploadedFilePaths
    },
    async uploadLocalFiles(fileList, chatDrop) {
      const uploadPath = this.chatProject?.upload_path || '/upload'
      this.showUploadConfirmation(fileList, uploadPath, { chatDrop })
    },
    handleFilePreview(filePath) {
      if (this.$ui.isVibeMode) {
        this.openFilePreview(filePath)
      } else {
        this.$storex.ui.openFileInViewer(filePath)
      }
    },
    openFilePreview(filePath) {
      if (this.$ui.isVibeMode) {
        this.previewFile = this.previewFile === filePath ? null : filePath
      } else {
        this.$ui.openFileInViewer(filePath)
      }
    },
    closeFilePreview() {
      this.previewFile = null
    },
    onPreviewFileSaved({ file, content }) {
      this.$ui?.addNotification?.({ text: `Saved: ${file.split('/').reverse()[0]}`, type: 'success' })
    },
    scheduleIntelliSense(word = null) {
      if (this.intelliSenseDismissed) {
        const currentWord = word || this.cursorWord.word
        if (currentWord !== this.intelliSenseQuery) this.intelliSenseDismissed = false
      }
      clearTimeout(this.intelliSenseDebounce)
      this.intelliSenseDebounce = setTimeout(() => this.runIntelliSense(word), 220)
    },
    async runIntelliSense(word = null) {
      if (this.intelliSenseDismissed) return
      const searchWord = word || this.cursorWord.word
      if (!searchWord?.startsWith('@')) { this.cancelIntelliSense(); return }
      const rawQuery = searchWord.slice(1)
      if (!rawQuery || rawQuery.trim().length < 3) { this.cancelIntelliSense(); return }
      if (this.previousQuery !== rawQuery && this.searchController) this.cancelIntelliSense()
      this.previousQuery = rawQuery
      // Messages can override the chat's working project (message.project_id):
      // suggestions must come from the project the message is addressed to.
      const project = await this.resolveMentionProject()
      if (!project) { this.cancelIntelliSense(); return }
      this.searchController = await this.$storex.projects.createSearchController()
      this.intelliSenseQuery = rawQuery
      this.intelliSenseIndex = 0
      this.searchController.onProgress = ({ stage, project: progressProject }) => {
        this.intelliSenseProgress = `${stage}: ${progressProject}`
      }
      try {
        await project.$state.searchMentions({
          query: rawQuery,
          limit: 10,
          controller: this.searchController,
          onResults: (results) => {
            if (!this.searchController.isCancelled) {
              if (results.length === 1 && results[0].name === rawQuery) {
                this.onIntelliSenseSelect(results[0])
              } else {
                this.intelliSenseSuggestions = results
                this.intelliSenseIndex = 0
              }
            }
          }
        })
      } catch (error) {
        if (error.message !== 'Search cancelled') console.error('[IntelliSense] Search error:', error)
      }
      this.intelliSenseProgress = ''
    },
    /**
     * Project whose mentions are searched: the message's own project when the
     * composer overrides it (message.project_id), the chat's working project
     * otherwise. Only the chat's project is initialised up front, so the target
     * is prepared on demand before querying its `searchMentions`.
     */
    async resolveMentionProject() {
      const target = this.messageTargetProject
      if (target && !target.$state?.searchMentions) {
        await this.$projects.initProjectState(target)
      }
      if (target?.$state?.searchMentions) return target
      // Fall back to the chat's project when the target could not be prepared
      const chatTarget = this.chatProject
      if (chatTarget && chatTarget !== target && !chatTarget.$state?.searchMentions) {
        await this.$projects.initProjectState(chatTarget)
      }
      return chatTarget?.$state?.searchMentions ? chatTarget : null
    },
    cancelIntelliSense() {
      if (this.searchController) { this.searchController.cancel(); this.searchController = null }
      this.intelliSenseSuggestions = []
      this.intelliSenseQuery = ''
      this.previousQuery = null
    },
    onIntelliSenseSelect(suggestion) {
      const { file, name } = suggestion
      const { caretIndex, word } = this.cursorWord
      const text = this.$refs.inputBox?.getEditorText() || ''
      const left = text.slice(0, caretIndex - word.length)
      const right = text.slice(caretIndex)
      let insert = '@' + name
      if (file) {
        if (!this.hasFileInMessage(file)) this.addFileToMessage(file)
        insert = ""
      }
      this.setEditorText(left + insert + ' ' + right)
      this.dismissIntelliSense()
      this.$nextTick(() => this.$refs.inputBox?.focusEditor())
    },
    onIntelliSenseAcceptMulti(items) {
      const { caretIndex, word } = this.cursorWord
      const text = this.$refs.inputBox?.getEditorText() || ''
      const left = text.slice(0, caretIndex - word.length)
      const right = text.slice(caretIndex)
      const mentionInserts = []
      items.forEach(({ file, name }) => {
        if (file) {
          if (!this.hasFileInMessage(file)) this.addFileToMessage(file)
        } else {
          mentionInserts.push('@' + name)
        }
      })
      const insert = mentionInserts.join(' ')
      this.setEditorText(left + insert + (insert ? ' ' : '') + right)
      this.dismissIntelliSense()
      this.$nextTick(() => this.$refs.inputBox?.focusEditor())
    },
    dismissIntelliSense() {
      this.intelliSenseDismissed = true
    },
    onChatInputKeyDown(event) {
      const hasSuggestions = this.intelliSenseSuggestions.length > 0
      if (hasSuggestions) {
        if (event.key === 'Tab') {
          event.preventDefault(); event.stopPropagation()
          this.onIntelliSenseSelect(this.intelliSenseSuggestions[this.intelliSenseIndex])
          return
        }
        if (event.key === 'Escape') { this.dismissIntelliSense(); return }
        if (event.key === ' ' && event.ctrlKey) {
          event.preventDefault(); event.stopPropagation()
          this.$refs.intelliSense?.toggleSelected(this.intelliSenseSuggestions[this.intelliSenseIndex])
          return
        }
        if (event.key === 'ArrowUp') {
          event.preventDefault()
          this.intelliSenseIndex = Math.max(0, this.intelliSenseIndex - 1)
          return
        }
        if (event.key === 'ArrowDown') {
          event.preventDefault()
          this.intelliSenseIndex = Math.min(this.intelliSenseSuggestions.length - 1, this.intelliSenseIndex + 1)
          return
        }
      }
      this.onEditMessageKeyDown(event)
    },
    onLLMModelChanged(modelName) {
      this.chat.llm_model = modelName
      this.saveChatInfo()
    },
    updateCursorWord() {
      this.cursorWord = this.$refs.inputBox?.getCaretWordInfo() ?? {}
    },
    setEditorText(text) {
      this.$refs.inputBox?.setEditorText(text)
    },
    onEditMessage(message) {
      if (this.editMessage?.doc_id === message.doc_id) {
        this.onResetEdit()
        return
      }
      this.editMessage = message
      this.setEditorText(message.content || '')
      this.selectorProfileNames = [...(message.profiles || [])]
      // Start from the project the message already targets. The stored value is
      // NOT written back unless the user picks another one (see updateMessage),
      // so an edit never clears a project_id it did not touch.
      this.messageProjectTouched = false
      this.messageProject = message.project_id
        ? this.$projects.allProjectsById[message.project_id] || null
        : null
      this.files = [...(message.files || [])]
      this.attachments = (message.attachments || []).map(a => {
        try { return typeof a === 'string' ? JSON.parse(a) : a } catch { return a }
      }).filter(Boolean)
      this.$nextTick(() => this.$refs.inputBox?.focusEditor())
    },
    onResetEdit() {
      this.editMessage = null
      this.editMessageId = null
      this.setEditorText('')
      this.files = []
      this.attachments = []
      this.messageProject = null
      this.messageProjectTouched = false
      this.selectorProfileNames = []
      this.textProfileNames = []
      this.previousEditorText = ''
    },
    async updateMessage() {
      const message = this.editMessage
      if (!message?.doc_id) return
      // A voice note stopped right before clicking Edit may still be being read:
      // wait for it, otherwise the audio is dropped from the saved message.
      await this.flushPendingAttachments()
      const content = this.$refs.inputBox?.getEditorText() ?? ''
      const profiles = [...new Set([...this.selectorProfileNames, ...this.textProfileNames])]
      const files = this.messageMentions.filter(m => m.file).map(m => m.file)
      const update = {
        content,
        profiles,
        files,
        attachments: this.attachments.map(a => a.toJSON?.() || a),
        updated_at: new Date().toISOString()
      }
      // A message can be addressed to its own project (message.project_id).
      // Persist the selection whenever the user changed it, `null` included:
      // picking the chat's project must CLEAR the stored override, while an
      // untouched edit keeps the project the message already had.
      if (this.messageProjectTouched) {
        update.project_id = this.messageProject?.project_id || null
      }
      try {
        await this.chatSvc.updateExistingMessage({
          chat: this.chat,
          doc_id: message.doc_id,
          update
        })
      } catch (error) {
        // Stay in edit mode (attachments included) so the user can retry
        // instead of silently losing the recorded audio.
        console.error('[chat] Failed to update message', error)
        this.$ui?.addNotification?.({ text: 'Failed to save the message, please retry', type: 'error' })
        return
      }
      this.onResetEdit()
    },
    toggleHide({ doc_id, is_answer, hide }) {
      // Answer messages can not be hidden.
      if (!is_answer) {
        this.chatSvc.updateExistingMessage({ chat: this.chat, doc_id, update: { hide: !hide } })
      }
    },
    toggleAnswer({ doc_id, is_answer }) {
      this.chatSvc.updateExistingMessage({ chat: this.chat, doc_id, update: { is_answer: !is_answer } })
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
    onGenerateCode({ codeSnippet, language }) {
      this.waiting = true
      this.$storex.api.run.generate({ id: "", code: codeSnippet, language })
        .then(data => {
          const content = data.code || codeSnippet
          const codeBlock = `\`\`\`${language || 'text'}\n${content}\n\`\`\``
          this.chatSvc.addMessage({ chat: this.chat, message: { role: 'assistant', content: codeBlock } })
        })
        .catch(ex => this.chatSvc.addMessage({ chat: this.chat, message: { role: 'assistant', content: `Error: ${ex.message}` } }))
        .finally(() => { this.waiting = false })
    },
    handleFileChange(fileData) {
      if (fileData) {
        this.uploadProjectFile = fileData
      }
    },
    getUserMessage({ message, task_item }) {
      return this.chatSvc.getUserMessage({
        message,
        project_id: this.messageProject?.project_id,
        files: this.chatSvc.getMessageFiles({ messageMentions: this.messageMentions, files: this.files }),
        profiles: [...new Set([...this.selectorProfileNames, ...this.textProfileNames])],
        attachments: this.attachments.map(a => a.toJSON?.() || a),
        metadata: this.metadata,
        user: this.$user.username,
        task_item
      })
    },
    async postMyMessage({ message, task_item }) {
      const userMessage = this.getUserMessage({ message, task_item })
      await this.chatSvc.addMessage({ chat: this.chat, message: userMessage })
      this.cleanUserInputAndWaitAnswer()
      return userMessage
    },
    cleanUserInputAndWaitAnswer() {
      this.setEditorText("")
      this.attachments = []
      this.files = []
      this.mentions = []
      this.messageProject = null
      this.messageProjectTouched = false
      this.textProfileNames = []
      this.metadata = null
      this.previousEditorText = ''
    },
    async addNewMessage({ task_item } = {}) {
      // Never post without a voice note that is still being read
      await this.flushPendingAttachments()
      if (this.isVoiceSession && !this.canPost) return false
      if (this.editMessage !== null) {
        await this.updateMessage()
        return false
      }
      const message = this.editorText
      if (message) await this.postMyMessage({ message, task_item })
      return true
    },
    async addSearchMessage() {
      return this.addNewMessage({ task_item: 'search' })
    },
    async sendMessage() {
      if (this.editMessage !== null) {
        await this.updateMessage()
        return
      }
      if (await this.addNewMessage()) {
        if (this.isGroup) {
          if (this.lastMessage?.profiles?.length) {
            await this.sendChatMessage(this.chat)
            this.$emit('send-message', this.lastMessage)
          }
          return
        }
        if (!this.isChannel || this.lastMessage?.profiles.length) {
          await this.sendChatMessage(this.chat)
          this.$emit('send-message', this.lastMessage)
        }
      }
    },
    async sendChatMessage(chat) {
      this.waiting = true

      // Notify the UI immediately that the chat is processing, before the
      // server streams its first chunk back (which can take several seconds).
      // The store auto-resets this after a timeout if the server never replies.
      if (chat?.id) {
        this.$chats.startChatProcessing({ chatId: chat.id })
      }

      try {
        return await this.$storex.projects.chatWihProject(chat)
      } finally {
        this.waiting = false
      }
    },
    removeMessage(message) {
      this.chatSvc.removeMessage({ chat: this.chat, message })
    },
    onMessageChange() {
      const text = this.$refs.inputBox?.getEditorText() ?? ''
      if (text !== this.editorText) this.editorText = text
    },
    onDragOver() {
      this.draggingOver = true
      this.dragCounter++
      clearTimeout(this.dragoverTimeout)
      this.dragoverTimeout = setTimeout(() => {
        this.draggingOver = false
        this.dragCounter = 0
      }, 500)
    },
    handleDragLeave(e) {
      this.dragCounter--
      if (this.dragCounter === 0) {
        this.draggingOver = false
        clearTimeout(this.dragoverTimeout)
      }
    },
    onDropInputBox(e) {
      this.onDrop(e, false)
    },
    onDropChat(e) {
      this.draggingOver = false
      this.dragCounter = 0
      clearTimeout(this.dragoverTimeout)
      this.onDrop(e, true)
    },
    async onDrop(e, chatDrop) {
      let itemsAdded = false

      if (e.dataTransfer.files?.length) {
        const imageFiles = [...e.dataTransfer.files].filter(f => f.type.startsWith("image/"))
        if (imageFiles.length > 0) {
          if (await this.processMultipleImages(imageFiles, !chatDrop)) itemsAdded = true
        }

        const nonImageFiles = [...e.dataTransfer.files].filter(f => !f.type.startsWith("image/"))
        if (nonImageFiles.length > 0) {
          await this.uploadLocalFiles(nonImageFiles, chatDrop)
          itemsAdded = true
        }
      }

      const textContent = e.dataTransfer.getData('text/plain')
      if (textContent) {
        const decodedContent = decodeURIComponent(textContent)
        if (await this.processMultipleFilePaths(decodedContent, chatDrop)) {
          itemsAdded = true
        } else if (this.isProjectFile(decodedContent) && !this.pasteWithShift) {
          await this.processFilePath(decodedContent, chatDrop)
          this.setEditorText(this.editorText.replace(decodedContent, ""))
          itemsAdded = true
        }
      }

      const jsonData = e.dataTransfer.getData('application/x-file-list-json')
      if (jsonData && !itemsAdded && await this.processJsonFileList(jsonData, chatDrop)) itemsAdded = true

      this.processDropUrls(e.dataTransfer, chatDrop)
      if (e.dataTransfer.getData("resourceurls")) itemsAdded = true

      if (!itemsAdded) {
        this.$ui?.addNotification?.({ text: 'No valid content was added from the dropped items', type: 'warning' })
      }
    },
    processDropUrls(dataTransfer, chatDrop) {
      const urls = dataTransfer.getData("resourceurls")
      if (urls) {
        JSON.parse(urls).map(url => {
          try {
            const { pathname } = new URL(url)
            this.processInputTextContent(pathname, chatDrop)
          } catch (ex) { console.error(ex) }
        })
      }
    },
    async onContentPaste(e) {
      if (!e.clipboardData?.items) return
      const stop = () => { e.preventDefault(); e.stopPropagation(); return false }
      const imageFile = await this.chatSvc.parseImageFromPaste(e)
      if (imageFile) {
        const attachment = await this.prepareAttachmentFromFile(imageFile)
        if (attachment) this.attachments.push(attachment)
        return stop()
      }
      const textContent = await this.chatSvc.parseTextFromPaste(e)
      if (!textContent) return
      const handled = this.processInputTextContent(textContent)
      if (handled) return stop()
    },
    async processInputTextContent(textContent, chatDrop) {
      const decodedContent = decodeURIComponent(textContent)
      const imgUrl = this.chatSvc.extractImageUrlFromHtml(decodedContent)
      if (imgUrl) {
        const attachment = await this.prepareAttachmentFromUrl(imgUrl)
        if (attachment) {
          this.attachments.push(attachment)
          return true
        }
        return false
      }
      const isProjectFile = this.$projects.allProjects.find(p => decodedContent.startsWith(p.abs_project_path))
      if (isProjectFile && !this.pasteWithShift) {
        if (chatDrop) {
          this.onAddFile(decodedContent)
        } else {
          this.addFileToMessage(decodedContent)
        }
        this.setEditorText(this.editorText.replace(decodedContent, ""))
        return true
      }
      return false
    },
    addFileToMessage(file) {
      if (!this.hasFileInMessage(file) && !this.files.includes(file)) {
        this.files = [...this.files, file]
      }
    },
    removeAttachment(idx) {
      this.attachments = this.attachments.filter((_, ix) => ix !== idx)
    },
    onAttachmentUpdated({ index, attachment }) {
      this.attachments.splice(index, 1, attachment)
      if (this.editMessage) {
        this.chatSvc.updateExistingMessage({
          chat: this.chat,
          doc_id: this.editMessage.doc_id,
          update: {
            attachments: this.attachments.map(a => a.toJSON?.() || a),
            updated_at: new Date().toISOString()
          }
        })
      }
    },
    onMessageAttachmentUpdated({ message, index, attachment }) {
      const attachments = (message.attachments || []).map(a => a.toJSON?.() || a)
      attachments.splice(index, 1, attachment.toJSON?.() || attachment)
      this.chatSvc.updateExistingMessage({
        chat: this.chat,
        doc_id: message.doc_id || message.id,
        update: {
          attachments,
          updated_at: new Date().toISOString()
        }
      })
    },
    removeAttachmentByIndex(idx) {
      this.removeAttachment(idx)
    },
    removeFileFromMessage({ doc_id, files }, file) {
      this.chatSvc.updateExistingMessage({
        chat: this.chat, doc_id, update: { files: files.filter(f => f !== file) }
      })
    },
    removeFileFromChat(file) {
      this.chatSvc.removeFileFromChat({ chat: this.chat, file })
    },
    removeFileFromFiles(file) {
      this.files = this.files.filter(f => f !== file)
    },
    showNotebookStatus(msg) {
      this.notebookStatus = msg
      setTimeout(() => { this.notebookStatus = null }, 3000)
    },
    async syncNotebook(file) {
      try {
        this.showNotebookStatus(`Syncing ${file.split('/').reverse()[0]}...`)
        await this.chatSvc.syncNotebook({ project: this.chatProject, chat: this.chat, file })
        this.showNotebookStatus(`Notebook synced: ${file.split('/').reverse()[0]}`)
      } catch (err) {
        this.showNotebookStatus(`Error syncing notebook: ${err.message}`)
      }
    },
    async exportNotebook(file) {
      try {
        this.showNotebookStatus(`Exporting to ${file.split('/').reverse()[0]}...`)
        await this.chatSvc.exportNotebook({ project: this.chatProject, chat: this.chat, file })
        this.showNotebookStatus(`Notebook exported: ${file.split('/').reverse()[0]}`)
      } catch (err) {
        this.showNotebookStatus(`Error exporting notebook: ${err.message}`)
      }
    },
    toggleVoiceSession() {
      if (this.isVoiceSession) return this.stopVoiceSession()
      let silents = 5
      this.isVoiceSession = true
      this.recognition = this.chatSvc.startVoiceRecognition({
        lang: this.$ui.voiceLanguage,
        onResult: (event) => { this.$refs.inputBox?.appendEditorText(event.results[0][0].transcript) },
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
      this.visibleMessages.forEach(m => this.toggleHide(m))
    },
    toggleDocumentSearch() {
      this.showDocumentSearchModal = !this.showDocumentSearchModal
    },
    closeDocumentSearch() {
      this.showDocumentSearchModal = false
    },
    onAddDocument(doc) {
      const source = doc.file || doc.metadata?.source
      if (source && !this.hasFileInMessage(source)) this.addFileToMessage(source)
    },
    async onReloadMessageFile({ file, message }) {
      message.content = await this.chatSvc.fileToMessage({ file })
    },
    // Persist a code block coming from the viewer/save button.
    //
    // The block belongs to a project and its path is relative to THAT project:
    // `project` travels with the `save-file` event (CodeViewer resolves it from
    // `Message.project_id` when the message overrides the chat's working
    // project). Writing through the chat's project — as before — sent the
    // request with another `codx_path` and the write failed, so the project's
    // own API instance is used, falling back to the chats store.
    async onSaveFile({ file, content, project }) {
      const target = project || this.chatProject
      const name = file.split("/").reverse()[0]
      try {
        if (target?.$api?.files?.write) {
          await target.$api.files.write(file, content)
        } else {
          await this.$storex.chats.writeFile({ chat: this.chat, file, content })
        }
        this.$ui.addNotification({ text: `File ${name} saved`, type: 'success' })
      } catch (error) {
        console.error('[chat] Failed to save file', { file, project: target?.project_id, error })
        this.$ui.addNotification({ text: `Error saving ${name}: ${error?.message || error}`, type: 'error' })
      }
    },
    onOpenFile(file) {
      const project = this.chatProject
      project.$api.coder.openFile(file)
    },
    addChatFile() {
      this.onAddFile(this.uploadProjectFile)
      this.uploadProjectFile = null
      this.selectFile = false
    },
    async onAddFile(file) {
      if (!this.hasFileInChat(file) && this.chatSvc.addFileToChat({ chat: this.chat, file })) {}
    },
    async onAddFileToChat(file) {
      await this.onAddFile(file)
    },
    onMessageEdited({ doc_id, content, profiles, llm_model }) {
      this.chatSvc.updateExistingMessage({ chat: this.chat, doc_id, update: { content, profiles, llm_model } })
      this.editMessage = null
    },
    onMessageChanged({ doc_id, content }) {
      this.chatSvc.updateExistingMessage({ chat: this.chat, doc_id, update: { content } })
    },
    removeMessageMention(mention) {
      const orgMention = this.mentionList?.find(m => m === mention)
      if (orgMention) {
        this.setEditorText(this.editorText.replace("@" + mention.name, ""))
      } else {
        this.files = this.files.filter(f => f !== mention.file)
      }
    },
    onPRFileComment({ file, lineNumber, comment, diff }) {
      const description = `Comment on ${file} (line ${lineNumber}):\n${diff ? diff + '\n' : ''}${comment}`
      this.createChatSubTask({
        title: `Review: ${file.split('/').reverse()[0]}`,
        description,
        files: [file]
      })
    },
    onChatEntryCreateSubtask({ file, content, title }) {
      const existingChat = file ? this.chatSvc.findChildChatByFile({
        chat: this.chat,
        childrenChats: this.childrenChats,
        file
      }) : null
      if (existingChat) { this.$chats.setActiveChat(existingChat); return }
      this.createChatSubTask({
        title: title || file?.split("/").reverse()[0] || content.split("\n")[0],
        description: content,
        files: file ? [file] : []
      })
    },
    async createChatSubTask({ title, files, description, metadata, profiles, mode, column, project_id, parent_id, auto_initialize }) {
      const payload = this.chatSvc.buildSubTaskPayload({
        title, description, files, profiles,
        mode: mode || this.chat.mode,
        column: column || this.chat.column,
        board: this.chat.board,
        metadata,
        projectId: project_id || this.chatProject.project_id,
        parentId: parent_id || this.chat.id,
        user: this.$user.username,
        auto_initialize: auto_initialize ?? true
      })
      await this.$chats.createNewChat(payload)
    },
    createBlock() {
      this.setEditorText(this.editorText + "```\n\n```")
    },
    async onNewThread(message) {
      await this.$chats.createNewThread({
        chat: this.chat,
        mode: this.chat.mode,
        message
      })
    },
    async addFileContentAsMessage(file) {
      const { content } = await this.$storex.chats.readFile({ chat: this.chat, file })
      const codeBlock = ["```" + file.split(".")[1] + " " + file, content, "```"].join("\n")
      this.chatSvc.addMessage({ chat: this.chat, message: this.getUserMessage({ message: codeBlock }) })
    },
    addMention(mention) {
      this.mentions.push({ ...mention, active: true })
    },
    onProfilesSelected(selectedProfiles) {
      this.selectorProfileNames = selectedProfiles.map(p => p.name || p)
    },
    // Selecting the chat's own project (or clearing it) falls back to the default
    // instead of storing a redundant copy on the message. The selection is
    // flagged so `updateMessage` persists it — `null` included, which is how a
    // message stops overriding the chat's project.
    onMessageProjectChanged(project) {
      const projectId = project?.project_id
      this.messageProject = !projectId || projectId === this.chatProject?.project_id
        ? null
        : project
      this.messageProjectTouched = true
    },
    onProfilesChanged(selectedProfiles) {
      this.chat.profiles = selectedProfiles.map(p => p.name || p)
      return this.saveChatInfo()
    },
    saveChatInfo(chat) {
      return this.chatSvc.saveChatInfo(chat || this.chat)
    },
    replaceEmoji({ emoji }) {
      const { caretIndex, word } = this.cursorWord
      const text = this.$refs.inputBox?.getEditorText() ?? ''
      const left = text.slice(0, caretIndex - word.length)
      const right = text.slice(caretIndex)
      this.setEditorText(left + emoji + right)
    },
    async onMessageRunAgents(message) {
      this.$projects.createSubTasks({ chat: this.chat, message, instructions: "" })
    },
    async onSelectionSearchFiles({ query }) {
      this.scheduleIntelliSense("@" + query)
    }
  }
}
</script>