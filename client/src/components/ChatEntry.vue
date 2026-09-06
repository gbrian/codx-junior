<script setup>
import Markdown from './Markdown.vue'
import moment from 'moment'
import { CodeDiff } from 'v-code-diff'
import ChatIcon from './chat/ChatIcon.vue'
import Document from './document/Document.vue'
import ProfileAvatar from './profile/ProfileAvatar.vue'
import ChatEntryMobile from './ChatEntryMobile.vue'
import DocumentSummary from './document/DocumentSummary.vue'
import MessagePRView from './chat/MessagePRView.vue'
import MessageFileView from './chat/MessageFileView.vue'
import ChatEntrySelectionMenu from './ChatEntrySelectionMenu.vue'
import Collapsible from './Collapsible.vue'
import ChatEntryDrawer from './ChatEntryDrawer.vue'
</script>

<template>
  <!-- Mobile rendering -->
  <ChatEntryMobile
    v-if="$ui.isMobile"
    :chat="chat"
    :message="message"
    :mentionList="mentionList"
    :usersList="usersList"
    :displayMessage="displayMessage"
    :messageProfiles="messageProfiles"
    :chatFiles="chatFiles"
    :chatProject="chatProject"
    :messageContent="messageContent"
    :isDone="isDone"
    :srcView="srcView"
    :showDiff="showDiff"
    :timeTaken="timeTaken"
    :thinkText="thinkText"
    :cancellationTokenId="cancellationTokenId"
    :cancellationTime="cancellationTime"
    :threadChat="threadChat"
    :isTopic="isTopic"
    :isWord="isWord"
    :isCollapsed="isCollapsed"
    :images="images"
    :code_patches="code_patches"
    :menuLess="menuLess"
    @thread="$emit('thread', $event)"
    @hide="$emit('hide', $event)"
    @remove="onRemove"
    @confirm-remove="confirmRemove"
    @toggle-src-view="toggleSrcView"
    @toggle-show-diff="toggleShowDiff"
    @cancel-message="cancelMessage"
    @copy-message="copyMessageToClipboard"
    @generate-code="onGenerateCode"
    @reload-file="$emit('reload-file', $event)"
    @open-file="$emit('open-file', $event)"
    @save-file="$emit('save-file', $event)"
    @add-file="$emit('add-file', $event)"
    @sub-task="$emit('sub-task', $event)"
    @open-thread="openThread"
    @add-file-to-chat="$emit('add-file-to-chat', $event)"
    @remove-file="$emit('remove-file', $event)"
    @message-copy="onMessageCopy"
    @answer="$emit('answer', $event)"
    @run-agents="runAgents"
    @apply-patch="applyPatch"
    @image="$emit('image', $event)"
  />

  <!-- =============================================
       NOTION-STYLE DESKTOP BLOCK RENDERING
       ============================================= -->
  <div
    v-else
    class="notion-entry group/entry relative w-full"
    :class="[
      displayMessage.hide && 'opacity-40 hover:opacity-100 transition-opacity',
    ]"
  >
    <!-- ── Row: Avatar + Header + Content ── -->
    <div class="flex gap-3 items-start w-full">

      <!-- Avatar column -->
      <div class="w-7 shrink-0 flex flex-col items-center gap-1 pt-0.5">
        <template v-if="isNewSpeaker">
          <div
            v-for="profile in messageProfiles"
            :key="profile.name"
            class="tooltip tooltip-right"
            :data-tip="profile.name || profile.username"
          >
            <ProfileAvatar :profile="profile" width="6" />
          </div>
        </template>
        <!-- Connecting line for grouped messages -->
        <div
          v-if="!isNewSpeaker"
          class="w-px flex-1 bg-base-300/40 mt-0.5 min-h-[1rem]"
        ></div>
        <!-- Events button -->
        <button
          v-if="hasEvents"
          class="mt-4 btn btn-xs btn-ghost tooltip tooltip-bottom gap-1"
          :class="drawerOpen && 'btn-active text-warning'"
          data-tip="Events"
          @click.stop="drawerOpen = !drawerOpen"
        >
          <i class="fa-solid fa-wrench text-warning/70"></i>
          <span class="text-[10px]">{{ toolEventCount }}</span>
        </button>
      </div>

      <!-- Main block column -->
      <div class="flex-1 min-w-0 pb-0.5">

        <!-- Header row: only shown on first message of a speaker group -->
        <div v-if="isNewSpeaker" class="flex items-center gap-2 mb-1 leading-none">
          <span class="font-semibold text-sm text-base-content">{{ displayMessage.user }}</span>
          <span class="text-[11px] text-base-content/40 tabular-nums">{{ formatDate(displayMessage.updated_at) }}</span>
          <span v-if="timeTaken" class="text-[11px] text-base-content/30 tabular-nums">{{ timeTaken }}</span>

          <!-- State badges inline with header -->
          <span v-if="cancellationTime" class="badge badge-xs badge-error">
            <i class="fa-solid fa-ban mr-0.5"></i>Cancelled
          </span>
          <span v-if="displayMessage.is_answer" class="badge badge-xs badge-success gap-1">
            <ChatIcon mode="answer" /> Knowledge
          </span>
          <span v-if="isTopic" class="badge badge-xs badge-info gap-1">
            <ChatIcon mode="topic" /> Topic
          </span>
          <span v-if="displayMessage.hide" class="text-[11px] text-warning/50">
            <i class="fa-solid fa-box-archive"></i> Archived
          </span>
        </div>

        <!-- ── Floating Notion Toolbar (appears on hover, top-right of block) ── -->
        <div
          class="absolute right-0 top-0 z-20
                 opacity-0 group-hover/entry:opacity-100
                 transition-all duration-150 translate-y-0
                 flex items-center gap-0.5
                 bg-base-100/95 backdrop-blur-sm
                 border border-base-300 rounded-lg shadow-md px-1 py-0.5"
        >
          <!-- Stop generation -->
          <button
            v-if="!isDone && cancellationTokenId"
            class="btn btn-xs btn-error gap-1"
            @click.stop="cancelMessage"
          >
            <span class="loading loading-xs"></span>Stop
          </button>

          <!-- Core actions -->
          <button
            class="btn btn-xs btn-ghost tooltip tooltip-bottom"
            :data-tip="displayMessage.hide ? 'Unarchive' : 'Archive'"
            @click.stop="$emit('hide', message)"
            v-if="isDone"
          >
            <i class="fa-solid fa-box-archive text-warning/70"></i>
          </button>
          <button
            class="btn btn-xs btn-ghost tooltip tooltip-bottom"
            data-tip="Thread"
            @click.stop="$emit('thread', message)"
          >
            <i class="fa-solid fa-comment-dots"></i>
          </button>
          <button
            class="btn btn-xs btn-ghost tooltip tooltip-bottom"
            data-tip="Mark as answer"
            @click.stop="$emit('answer', message)"
          >
            <i class="fa-solid fa-check-double text-success/70"></i>
          </button>
          <button
            class="btn btn-xs btn-ghost tooltip tooltip-bottom"
            data-tip="Copy"
            @click.stop="copyMessageToClipboard"
          >
            <i class="fa-solid fa-copy"></i>
          </button>
          <button
            v-if="displayMessage.diffMessage"
            class="btn btn-xs btn-ghost tooltip tooltip-bottom"
            :class="showDiff && 'btn-active'"
            data-tip="Diff"
            @click.stop="toggleShowDiff"
          >
            <i class="fa-regular fa-file-lines"></i>
          </button>
          <button
            v-if="hasCodeBlocksOrFiles"
            class="btn btn-xs btn-ghost tooltip tooltip-bottom"
            :class="showFileView && 'btn-active'"
            data-tip="Files"
            @click.stop="toggleFileView"
          >
            <i class="fa-solid fa-file-code"></i>
          </button>
          <button
            v-if="hasPRViewBlocks"
            class="btn btn-xs btn-ghost tooltip tooltip-bottom"
            :class="showPRView && 'btn-active'"
            data-tip="Review"
            @click.stop="togglePRView"
          >
            <i class="fa-solid fa-code-branch"></i>
          </button>

          <!-- Divider -->
          <div class="w-px h-4 bg-base-300 mx-0.5"></div>

          <!-- More dropdown -->
          <div class="dropdown dropdown-end" @click.stop>
            <button tabindex="0" class="btn btn-xs btn-ghost">
              <i class="fa-solid fa-ellipsis-vertical"></i>
            </button>
            <ul
              tabindex="0"
              class="dropdown-content menu rounded-box shadow-lg w-44 p-1 bg-base-200 z-50 text-sm"
            >
              <li><a @click.stop="runAgents" class="text-info"><i class="fa-solid fa-people-group w-4"></i> Run agents</a></li>
              <li v-if="isDone"><a @click.stop="toggleSrcView()"><i class="fa-solid fa-code w-4"></i> View source</a></li>
              <li v-if="isDone"><a @click.stop="$emit('edit-message', message)"><i class="fa-solid fa-pen w-4"></i> Edit</a></li>
              <li><a @click.stop="confirmRemove" class="text-error"><i class="fa-solid fa-trash-can w-4"></i> Delete</a></li>
            </ul>
          </div>
        </div>

        <!-- ── Thread / Reply badge (always visible if exists) ── -->
        <div
          v-if="threadChat"
          class="mb-1 inline-flex"
        >
          <button
            class="flex items-center gap-1 text-[11px] text-info hover:text-info hover:underline cursor-pointer"
            @click.stop="openThread"
          >
            <ChatIcon :mode="threadChat.mode" />
            <span>{{ threadChat.messages?.length || 0 }} replies</span>
          </button>
        </div>

        <!-- ── Loading bar ── -->
        <progress
          v-if="!isDone"
          class="progress progress-xs w-full mb-2 opacity-50"
        ></progress>

        <!-- ── Selection context menu ── -->
        <ChatEntrySelectionMenu
          v-if="showSelectionMenu"
          :selectedText="selectedText"
          :chatProject="chatProject"
          @copy="onSelectionCopy"
          @create-subtask="onSelectionCreateSubtask"
          @search-files="onSelectionSearchFiles"
          @close="onCloseSelectionMenu"
        />

        <!-- ── Skeleton loader ── -->
        <div v-if="!displayMessage.content && !displayMessage.think" class="space-y-2 py-1">
          <div class="skeleton h-4 w-full rounded"></div>
          <div class="skeleton h-4 w-4/5 rounded"></div>
          <div class="skeleton h-4 w-2/3 rounded"></div>
        </div>

        <!-- ── Answer / Topic accent bar ── -->
        <div
          v-if="displayMessage.is_answer || isTopic"
          class="absolute left-0 top-0 bottom-0 w-0.5 rounded-full"
          :class="[
            displayMessage.is_answer && 'bg-success',
            isTopic && !displayMessage.is_answer && 'bg-info',
          ]"
        ></div>

        <!-- ── TOC for long documents ── -->
        <DocumentSummary
          v-if="!srcView && isDone && messageContent && !showPRView && !showFileView && !hasEvents"
          :content="messageContent"
          :minHeadings="3"
          :documentId="documentId"
          :scrollContainer="$refs.contentArea"
          class="mb-3"
        />

        <!-- ── Main content area ── -->
        <div
          ref="contentArea"
          @copy.stop="onMessageCopy"
          @mouseup="onContentMouseUp"
          class="min-w-0 w-full notion-content"
          :class="[
            displayMessage.is_answer && 'pl-3 border-l-2 border-success/30',
            isTopic && !displayMessage.is_answer && 'pl-3 border-l-2 border-info/30',
          ]"
        >
          <!-- Source view -->
          <pre v-if="srcView" class="text-xs overflow-auto bg-base-200 p-3 rounded-lg">{{ displayMessage.content }}</pre>

          <!-- Document / Markdown -->
          <Document
            v-if="!showDiff && !srcView && !showPRView && !showFileView && !code_patches && !isWord"
            :content="messageContent"
            :files="chatFiles"
            :project="chatProject"
            :chat="chat"
            :loading="!message.done"
            :documentId="documentId"
            :message="message"
            @generate-code="onGenerateCode"
            @reload-file="$emit('reload-file', { file: $event, message })"
            @open-file="$emit('open-file', $event)"
            @save-file="$emit('save-file', $event)"
            @add-file="$emit('add-file', $event)"
            @sub-task="$emit('sub-task', $event)"
            @copy-chapter="onCopyChapter"
            @create-task="onCreateTask"
            :mentionList="mentionList"
          >
            <template #chapter-actions="{ chapter, fullContent }">
              <button class="btn btn-sm btn-ghost gap-1" @click="copyChapterMarkdown(chapter, fullContent)">
                <i class="fa-solid fa-copy"></i> Copy
              </button>
              <button class="btn btn-sm btn-ghost gap-1" @click="createTaskFromChapter(chapter, fullContent)">
                <i class="fa-solid fa-plus"></i> Task
              </button>
            </template>
          </Document>

          <!-- Error -->
          <div class="alert alert-error text-xs mt-2" v-if="displayMessage.error">
            {{ displayMessage.error }}
          </div>

          <!-- Diff view -->
          <CodeDiff
            v-if="showDiff && !showPRView && !showFileView"
            :new-string="displayMessage.diffMessage.content"
            :old-string="messageContent"
            theme="dark"
          />

          <!-- Code patches -->
          <div v-if="code_patches && !showPRView && !showFileView" class="space-y-3 mt-2">
            <div
              v-for="patch in code_patches"
              :key="patch.file_path"
              class="border border-base-300 rounded-lg p-3 bg-base-200/50"
            >
              <div class="text-xs font-bold text-primary mb-1" :title="patch.file_path">
                {{ patch.file_path.replace($project.abs_project_path, '') }}
              </div>
              <div class="text-xs text-base-content/50 mb-2">{{ patch.description }}</div>
              <Markdown :text="'```diff\n' + patch.patch + '\n```'"></Markdown>
              <div class="flex justify-end mt-2">
                <button
                  class="btn btn-sm btn-warning gap-1"
                  :disabled="patch.working"
                  @click="applyPatch(patch)"
                >
                  <span class="loading loading-spinner" v-if="patch.working"></span>
                  Apply changes
                </button>
              </div>
              <div v-if="patch.res" class="text-xs mt-2">
                <div class="text-error" v-if="patch.res.error">{{ patch.res.error }}</div>
                <div class="text-success" v-else>
                  <i class="fa-solid fa-check"></i> Applied
                </div>
              </div>
            </div>
          </div>

          <!-- File View -->
          <MessageFileView
            v-if="showFileView && !srcView && !showDiff && !showPRView"
            :codeBlocks="prViewCodeBlocks"
            :linkedFiles="displayMessage.files"
            :chat="chat"
            :message="message"
            @save-file="$emit('save-file', $event)"
            @add-file="$emit('add-file', $event)"
            @open-file="$emit('open-file', $event)"
            @sub-task="$emit('sub-task', $event)"
            @remove-file="$emit('remove-file', $event)"
          />

          <!-- PR View -->
          <MessagePRView
            v-if="showPRView && !srcView && !showDiff && !showFileView"
            :codeBlocks="prViewCodeBlocks"
            :chat="chat"
            :message="message"
            :activeBranch="activeBranch"
            @save-file="$emit('save-file', $event)"
            @add-file="$emit('add-file', $event)"
            @open-file="$emit('open-file', $event)"
            @sub-task="$emit('sub-task', $event)"
          />

          <!-- Images -->
          <div v-if="images && !showPRView && !showFileView && images?.length" class="mt-3">
            <p class="text-xs text-base-content/40 mb-2">
              <i class="fa-solid fa-images mr-1"></i>Images
            </p>
            <div class="carousel gap-2">
              <div
                class="carousel-item cursor-pointer"
                v-for="image in images"
                :key="image.src"
                @click="$emit('image', image)"
              >
                <div class="flex flex-col gap-1">
                  <div
                    class="bg-cover bg-center border border-base-300 rounded-lg w-20 h-20 hover:border-primary transition-colors"
                    :style="`background-image: url(${image.src})`"
                  ></div>
                  <p class="badge badge-xs" v-if="image.alt">{{ image.alt.slice(0, 12) }}</p>
                </div>
              </div>
            </div>
          </div>

          <!-- Linked files -->
          <div
            v-if="displayMessage.files?.length && !showPRView && !showFileView"
            class="mt-3 pt-2 border-t border-base-300/50"
          >
            <p class="text-[11px] text-base-content/40 mb-1.5">
              <i class="fa-solid fa-paperclip mr-1"></i>Linked files
            </p>
            <div class="flex flex-wrap gap-1">
              <div
                v-for="file in displayMessage.files"
                :key="file"
                class="flex items-center gap-1 text-xs bg-base-200 hover:bg-base-300 rounded-md px-2 py-0.5 transition-colors group/file"
              >
                <i class="fa-solid fa-file text-primary/60 text-[10px]"></i>
                <a
                  class="hover:underline cursor-pointer max-w-[180px] truncate"
                  @click="openFile(file)"
                  :title="file"
                >
                  {{ file.split('/').reverse()[0] }}
                </a>
                <button
                  class="opacity-0 group-hover/file:opacity-100 ml-0.5 hover:text-error transition-all"
                  @click.stop="$emit('add-file', file)"
                  title="Add to chat"
                >
                  <i class="fa-solid fa-plus text-[10px]"></i>
                </button>
                <button
                  class="opacity-0 group-hover/file:opacity-100 hover:text-error transition-all"
                  @click.stop="$emit('remove-file', file)"
                >
                  <i class="fa-regular fa-circle-xmark text-[10px]"></i>
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- ── Collapsed toggle (for archived messages) ── -->
        <div
          v-if="isCollapsed && displayMessage.hide"
          class="mt-1 text-[11px] text-base-content/30 cursor-pointer hover:text-base-content/60 transition-colors"
          @click="collapsed = false"
        >
          <i class="fa-solid fa-chevron-down mr-1"></i>Show archived content
        </div>
      </div>
    </div>

    <!-- Events Drawer -->
    <ChatEntryDrawer
      :isOpen="drawerOpen"
      :lifecycleEvents="message.lifecycle_events"
      :toolEvents="message.tool_events"
      :metadata="message.meta_data"
      @close="drawerOpen = false"
    />
  </div>
</template>

<script>
export default {
  props: ['chat', 'message', 'mentionList', 'menu-less', 'usersList', 'isNewSpeaker'],
  emits: [
    'generate-code',
    'reload-file',
    'open-file',
    'save-file',
    'add-file',
    'sub-task',
    'thread',
    'hide',
    'remove',
    'answer',
    'enhance',
    'copy',
    'add-file-to-chat',
    'remove-file',
    'image',
    'run-agents',
    'edit-message',
    'search-files',
    'edited',
    'run-edit',
    'code-file-shown',
    'message-changed',
    'preview-file'
  ],
  data() {
    return {
      srcView: false,
      isRemove: false,
      improvementData: null,
      showDiff: false,
      showPRView: false,
      showFileView: false,
      documentId: 'doc-' + Math.random().toString(36).slice(2, 8),
      activeBranch: null,
      branchLoading: false,
      showSelectionMenu: false,
      selectedText: '',
      selectionPosition: { top: 0, left: 0 },
      collapsed: false,
      drawerOpen: false
    }
  },
  created() {
    this.loadThreadChat()
    this.loadActiveBranch()
    this.collapsed = this.displayMessage.hide
  },
  computed: {
    isDone() {
      return this.displayMessage.done
    },
    isWord() {
      return this.chat?.mode === 'word'
    },
    isTopic() {
      return this.chat?.mode === 'topic'
    },
    isSlackStyle() {
      return this.chat?.mode === 'topic'
    },
    isCollapsed() {
      return this.collapsed !== undefined
        ? this.collapsed
        : this.displayMessage.hide ? true : false
    },
    isMyMessage() {
      return this.displayMessage.user === this.$user.username
    },
    isChannelMessage() {
      return this.chat.mode === 'channel'
    },
    canEditMessage() {
      return !this.isChannelMessage ||
        this.isMyMessage ||
        this.message.role === 'assistant'
    },
    thinkText() {
      return null
    },
    displayMessage() {
      const message = this.threadChat?.messages
          .filter(m => !m.hide)
          .reverse()[0] || this.message
      return message
    },
    messageProfiles() {
      let profiles = this.$projects.profiles
        ?.filter(p => this.displayMessage.profiles?.includes(p.name)) || []
      const user = this.$project.users
        .find(({ username }) => username === this.displayMessage.user)
      return [user, ...profiles].filter(u => !!u)
    },
    images() {
      return this.message?.images?.map(i => {
        try {
          return JSON.parse(i)
        } catch {
          return { src: i }
        }
      })
    },
    messageContent() {
      return this.displayMessage.content
    },
    code_changes() {
      return this.improvementData?.code_changes
    },
    code_patches() {
      return this.improvementData?.code_patches
    },
    timeTaken() {
      if (!this.displayMessage.meta_data) return null
      let timeTaken = '--'
      if (this.displayMessage.meta_data?.time_taken) {
        const seconds = Math.floor(this.displayMessage.meta_data.time_taken)
        const baseMoment = moment({ h: 0, m: 0, s: 0, ms: 0 })
        timeTaken = baseMoment.add(seconds, 'seconds').format('mm:ss')
      } else if (this.displayMessage.meta_data?.start_time) {
        timeTaken = moment(this.displayMessage.meta_data?.start_time).fromNow()
      }
      return timeTaken ? `${this.displayMessage.meta_data.model} ${timeTaken}` : null
    },
    chatProject() {
      if (this.chat.project_id) {
        return this.$projects.allProjects.find(p => p.project_id === this.chat.project_id)
      }
      return this.$project
    },
    chatFiles() {
      return this.chat.file_list
    },
    threadChat() {
      return this.$projects.allChats.find(c => c.message_id === this.message.doc_id)
    },
    cancellationTokenId() {
      return this.displayMessage.meta_data?.cancellation_token_id
    },
    cancellationTime() {
      return this.displayMessage.meta_data?.cancelled_at
    },
    hasPRViewBlocks() {
      return this.$service.chat.hasCodeBlocksWithFilePaths(this.displayMessage)
    },
    hasCodeBlocksOrFiles() {
      return this.prViewCodeBlocks.length > 0 || this.displayMessage.files?.length > 0
    },
    prViewCodeBlocks() {
      return this.$service.chat.extractCodeBlocksFromMessage(this.displayMessage)
    },
    toolEventCount() {
      const toolEvents = this.message?.tool_events
      if (Array.isArray(toolEvents)) {
        return toolEvents.length
      }
      return this.message?.tool_event ? 1 : 0
    },
    lifecycleEventCount() {
      const lifecycleEvents = this.message?.lifecycle_events
      if (Array.isArray(lifecycleEvents)) {
        return lifecycleEvents.length
      }
      return this.message?.lifecycle_event ? 1 : 0
    },
    hasEvents() {
      return this.toolEventCount > 0
    }
  },
  watch: {
    message() {
      this.loadThreadChat()
    },
    'message.content': function() {
      this.extractImprovementData()
    }
  },
  methods: {
    formatDate(date) {
      return moment(date).format('DD/MMM HH:mm')
    },
    extractImprovementData() {
      this.improvementData = null
      if (this.displayMessage.content?.startsWith('```json')) {
        try {
          const lines = this.displayMessage.content.split('\n')
          const jsBlock = lines.slice(1, lines.length - 1).join('\n')
          this.improvementData = JSON.parse(jsBlock)
        } catch (ex) {
          console.error('Failed to parse improvement data', ex)
        }
      }
    },
    copyTextToClipboard(text) {
      this.$ui.copyTextToClipboard(text)
    },
    onMessageCopy(ev) {
      const text = window.getSelection().toString()
      if (text) {
        this.copyTextToClipboard(text)
        ev.preventDefault()
      }
    },
    getSelectionPosition() {
      const selection = window.getSelection()
      if (selection.rangeCount === 0) return { top: 0, left: 0 }
      const range = selection.getRangeAt(0)
      const rect = range.getBoundingClientRect()
      return {
        top: Math.max(10, rect.top + window.scrollY - 60),
        left: rect.left
      }
    },
    onContentMouseUp() {
      function getSelectedHTML() {
        const selection = window.getSelection()
        if (selection.rangeCount > 0) {
          const range = selection.getRangeAt(0)
          const clonedContent = range.cloneContents()
          const div = document.createElement('div')
          div.appendChild(clonedContent)
          return div.innerHTML
        }
        return ""
      }

      const selectedText = getSelectedHTML()
      if (selectedText.length > 0) {
        this.selectedText = selectedText
        this.showSelectionMenu = true
      } else {
        this.showSelectionMenu = false
      }
    },
    onSelectionCopy(text) {
      this.copyTextToClipboard(text)
    },
    onSelectionCreateSubtask(content) {
      this.$emit('sub-task', { content })
    },
    onSelectionSearchFiles({ query }) {
      this.$emit('search-files', { query, fromSelection: true })
    },
    onCloseSelectionMenu() {
      this.showSelectionMenu = false
    },
    toggleSrcView() {
      this.srcView = !this.srcView
      if (this.srcView) {
        this.showDiff = false
        this.showPRView = false
        this.showFileView = false
      }
    },
    toggleShowDiff() {
      this.showDiff = !this.showDiff
      if (this.showDiff) {
        this.srcView = false
        this.showPRView = false
        this.showFileView = false
      }
    },
    toggleFileView() {
      this.showFileView = !this.showFileView
      if (this.showFileView) {
        this.srcView = false
        this.showDiff = false
        this.showPRView = false
      }
    },
    togglePRView() {
      this.showPRView = !this.showPRView
      if (this.showPRView) {
        this.srcView = false
        this.showDiff = false
        this.showFileView = false
        this.loadActiveBranch()
      }
    },
    onRemove() {
      if (this.isRemove) {
        this.$emit('remove')
      } else {
        this.isRemove = true
      }
    },
    confirmRemove() {
      this.isRemove = true
      this.$emit('remove')
    },
    copyMessageToClipboard() {
      this.copyTextToClipboard(this.displayMessage.content)
    },
    async applyPatch(patch) {
      patch.working = true
      try {
        const code_changes = this.code_changes.filter(cc => cc.file_path === patch.file_path)
        await this.$projects.codeImprovePatch({
          chat: this.chat,
          code_generator: { code_changes, code_patches: [patch] }
        })
        patch.res = { info: 'Patch sent' }
      } catch {
        patch.res = { error: 'Error applying patch' }
      }
      delete patch.working
    },
    onGenerateCode(codeBlockInfo) {
      this.$emit('generate-code', codeBlockInfo)
    },
    openFile(file) {
      this.$emit('preview-file', file)
    },
    openThread() {
      this.$chats.setActiveChat(this.threadChat)
    },
    loadThreadChat() {
      if (this.threadChat) {
        this.$chats.reloadChat(this.threadChat)
      }
    },
    runAgents() {
      this.$emit('run-agents', this.message)
    },
    async cancelMessage() {
      const tokenId = this.cancellationTokenId
      if (!tokenId) return
      try {
        await this.$storex.api.chats.cancelMessage(tokenId)
      } catch (ex) {
        console.error('Failed to cancel message', ex)
      }
    },
    async loadActiveBranch() {
      if (this.branchLoading) return
      this.branchLoading = true
      try {
        const repoInfo = await this.chatProject.$api.repo.info()
        this.activeBranch = repoInfo?.active_branch
      } catch (ex) {
        console.error('Failed to load active branch', ex)
        this.activeBranch = null
      } finally {
        this.branchLoading = false
      }
    },
    copyChapterMarkdown(chapter, fullContent) {
      this.copyTextToClipboard(fullContent)
    },
    createTaskFromChapter(chapter, fullContent) {
      this.$emit('sub-task', { content: fullContent, title: chapter.title })
    },
    onCopyChapter(chapterData) {
      this.copyTextToClipboard(chapterData.content)
    },
    onCreateTask(taskData) {
      this.$emit('sub-task', { content: taskData.content, title: taskData.title })
    }
  },
  mounted() {
    this.collapsed = this.isCollapsed || this.displayMessage.hide
    this.extractImprovementData()
  }
}
</script>