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
import ChatEntrySelectionMenu from './ChatEntrySelectionMenu.vue'
import Collapsible from './Collapsible.vue'
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

  <!-- Desktop rendering with Rich Header -->
  <Collapsible
    v-else
    :modelValue="!isCollapsed"
    @update:modelValue="collapsed = !$event"
    class="group chat-entry"
    :class="[
      // !isDone && 'border-dashed border-sky-800/30',
      displayMessage.is_answer && 'border-success/50 bg-success/5',
      isTopic && 'border-info/50 bg-info/5',
      displayMessage.hide && isCollapsed && 'opacity-50 hover:opacity-100',
      displayMessage.hide && 'border-l border-l-warning pl-2'
    ]"
  >
    <!-- Icon: Avatar stack -->
    <template #title>
      <div class="flex items-center -space-x-2"
        :class="[
          displayMessage.hide && 'border-l border-warning pl-2'
        ]"
      >
        <div 
          class="tooltip tooltip-right" 
          :data-tip="profile.name || profile.username" 
          v-for="profile in messageProfiles" 
          :key="profile.name"
        >
          <ProfileAvatar :profile="profile" width="6" />
        </div>
      </div>
    </template>

    <!-- Title: User + Timestamp + Model -->
    <template #icon>
      <div class="flex items-center gap-2">
        <span class="text-xs text-neutral-500">{{ formatDate(displayMessage.updated_at) }}</span>
        <span v-if="timeTaken" class="text-xs text-neutral-400">{{ timeTaken }}</span>
        <span class="font-semibold text-sm">{{ displayMessage.user }}</span>
      </div>
    </template>

    <!-- Summary: Status badges -->
    <template #summary>
      <span v-if="cancellationTime" class="badge badge-xs badge-error">
        <i class="fa-solid fa-ban"></i> Cancelled
      </span>
      <div class="badge badge-xs badge-success gap-1" v-if="displayMessage.is_answer">
        <ChatIcon mode="answer" /> Knowledge
      </div>
      <div class="badge badge-xs badge-info badge-outline gap-1" v-if="isTopic">
        <ChatIcon mode="topic" /> Topic
      </div>
      <div 
        class="badge badge-xs badge-outline gap-1 cursor-pointer hover:badge-info" 
        @click.stop="openThread"
        v-if="threadChat"
      >
        <ChatIcon :mode="threadChat.mode" /> {{ threadChat.messages?.length || 0 }} replies
      </div>
      <span v-if="displayMessage.hide" class="text-xs text-warning/60 gap-1">
        <i class="fa-solid fa-box-archive"></i> Archived
      </span>
    </template>

    <!-- Action buttons group -->
    <template #actions>
      <div class="flex gap-2 items-center">
        <button
          class="btn btn-xs btn-error gap-1 tooltip tooltip-bottom"
          data-tip="Stop generation"
          @click.stop="cancelMessage"
          v-if="!isDone && cancellationTokenId"
        >
          <span class="loading loading-xs"></span>
          Stop
        </button>
        
        <!-- Primary actions row -->
        <div class="flex gap-1 border-l border-base-300 pl-2">
          <button 
            class="btn btn-xs text-warning hover:btn-outline tooltip tooltip-bottom" 
            :data-tip="displayMessage.hide ? 'Unarchive' : 'Archive'" 
            @click.stop="$emit('hide', message)"
            v-if="isDone"
          >
            <i class="fa-solid fa-box-archive"></i>
          </button>

          <button 
            class="btn btn-xs hover:btn-outline tooltip tooltip-bottom" 
            data-tip="Create thread" 
            @click.stop="$emit('thread', message)"
          >
            <i class="fa-solid fa-comment-dots"></i>
          </button>
          <button 
            class="btn btn-xs text-success hover:btn-outline tooltip tooltip-bottom" 
            data-tip="Mark as best answer" 
            @click.stop="$emit('answer', message)"
          >
            <i class="fa-solid fa-check-double"></i>
          </button>
          <button 
            class="btn btn-xs hover:btn-outline tooltip tooltip-bottom" 
            data-tip="Copy to clipboard" 
            @click.stop="copyMessageToClipboard"
          >
            <i class="fa-solid fa-copy"></i>
          </button>
          <button 
            class="btn btn-xs hover:btn-outline tooltip tooltip-bottom" 
            data-tip="Show diff" 
            @click.stop="toggleShowDiff" 
            v-if="displayMessage.diffMessage"
          >
            <i class="fa-regular fa-file-lines"></i>
          </button>
          <button 
            :class="showPRView && 'btn-active'"
            class="btn btn-xs hover:btn-outline tooltip tooltip-bottom"
            data-tip="Review code changes" 
            @click.stop="togglePRView"
            v-if="hasPRViewBlocks"
          >
            <i class="fa-solid fa-code-branch"></i>
          </button>
        </div>

        <!-- More menu -->
        <div class="dropdown dropdown-end" @click.stop>
          <button tabindex="0" class="btn btn-xs btn-ghost">
            <i class="fa-solid fa-ellipsis-vertical"></i>
          </button>
          <ul tabindex="0" class="dropdown-content menu rounded-box shadow w-48 p-1 bg-base-200 z-50">
            <li><a @click.stop="runAgents" class="text-info"><i class="fa-solid fa-people-group"></i> Run agents</a></li>
            <li v-if="isDone"><a @click.stop="toggleSrcView()"><i class="fa-solid fa-code"></i> View source</a></li>
            <li v-if="isDone"><a @click.stop="$emit('edit-message', message)"><i class="fa-solid fa-pen"></i> Edit</a></li>
            <li><a @click.stop="confirmRemove" class="text-error"><i class="fa-solid fa-trash-can"></i> Delete</a></li>
          </ul>
        </div>
      </div>
    </template>

    <!-- Content: Full message body -->
    <div class="p-3 flex flex-col gap-3 border-t border-base-300">
      <!-- Loading indicator -->
      <progress class="progress progress-sm w-full" v-if="!isDone"></progress>

      <!-- Selection menu -->
      <ChatEntrySelectionMenu
        v-if="showSelectionMenu"
        :selectedText="selectedText"
        :chatProject="chatProject"
        @copy="onSelectionCopy"
        @create-subtask="onSelectionCreateSubtask"
        @search-files="onSelectionSearchFiles"
        @close="onCloseSelectionMenu"
      />

      <!-- Thinking section -->
      <div 
        v-if="thinkText" 
        class="alert alert-info items-start cursor-pointer"
        @click="displayMessage.full_think = !displayMessage.full_think"
      >
        <i class="fa-solid fa-brain"></i>
        <span>{{ thinkText }}</span>
      </div>

      <!-- Skeleton loader -->
      <div v-if="!displayMessage.content && !displayMessage.think" class="space-y-2">
        <div class="skeleton h-12 w-full"></div>
        <div class="skeleton h-12 w-full"></div>
        <div class="skeleton h-8 w-2/3"></div>
      </div>

      <!-- TOC for long documents -->
      <DocumentSummary
        v-if="!srcView && isDone && messageContent && !showPRView"
        :content="messageContent"
        :minHeadings="3"
        :documentId="documentId"
        :scrollContainer="$refs.contentArea"
      />

      <!-- Message content container -->
      <div 
        ref="contentArea"
        @copy.stop="onMessageCopy"
        @mouseup="onContentMouseUp"
        class="max-w-full bg-base-50 rounded-md p-2"
      >
        <pre v-if="srcView" class="text-xs overflow-auto bg-base-200 p-2 rounded">{{ displayMessage.content }}</pre>

        <Document 
          v-if="!showDiff && !srcView && !showPRView && !code_patches && !isWord"
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
            <button class="btn btn-sm btn-ghost gap-2" @click="copyChapterMarkdown(chapter, fullContent)">
              <i class="fa-solid fa-copy"></i> Copy
            </button>
            <button class="btn btn-sm btn-ghost gap-2" @click="createTaskFromChapter(chapter, fullContent)">
              <i class="fa-solid fa-plus"></i> Task
            </button>
          </template>
        </Document>

        <div class="alert alert-error text-xs" v-if="displayMessage.error">
          {{ displayMessage.error }}
        </div>

        <CodeDiff
          v-if="showDiff && !showPRView"
          :new-string="displayMessage.diffMessage.content"
          :old-string="messageContent"
          theme="dark"
        />

        <!-- Code patches section -->
        <div v-if="code_patches && !showPRView" class="space-y-3">
          <div 
            v-for="patch in code_patches" 
            :key="patch.file_path"
            class="border border-base-300 rounded-md p-2"
          >
            <div class="text-xs font-bold text-primary mb-2" :title="patch.file_path">
              {{ patch.file_path.replace($project.abs_project_path, '') }}
            </div>
            <div class="text-xs text-neutral-600 mb-2">{{ patch.description }}</div>
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
              <div class="text-success" v-else>✓ Patch applied successfully</div>
            </div>
          </div>
        </div>

        <!-- PR View -->
        <MessagePRView
          v-if="showPRView && !srcView && !showDiff"
          :codeBlocks="prViewCodeBlocks"
          :chat="chat"
          :message="message"
          :activeBranch="activeBranch"
          @save-file="$emit('save-file', $event)"
          @add-file="$emit('add-file', $event)"
          @open-file="$emit('open-file', $event)"
          @sub-task="$emit('sub-task', $event)"
        />

        <!-- Images carousel -->
        <div v-if="images && !showPRView && images?.length" class="mt-3">
          <p class="text-xs font-semibold mb-2">Images</p>
          <div class="carousel gap-2">
            <div 
              class="carousel-item cursor-pointer"
              v-for="image in images" 
              :key="image.src" 
              @click="$emit('image', image)"
            >
              <div class="flex flex-col gap-1">
                <div 
                  class="bg-cover bg-center border-2 border-base-300 rounded-md w-20 h-20"
                  :style="`background-image: url(${image.src})`"
                ></div>
                <p class="badge badge-xs" v-if="image.alt">{{ image.alt.slice(0, 12) }}</p>
              </div>
            </div>
          </div>
        </div>

        <!-- Linked files -->
        <div v-if="displayMessage.files?.length && !showPRView" class="mt-3 p-2 bg-base-200 rounded-md">
          <p class="text-xs font-semibold mb-2">Linked files</p>
          <div class="space-y-1">
            <div 
              v-for="file in displayMessage.files" 
              :key="file"
              class="flex gap-2 items-center text-xs"
            >
              <i class="fa-solid fa-file text-primary"></i>
              <a class="hover:underline cursor-pointer flex-1 truncate" @click="openFile(file)" :title="file">
                {{ file.split('/').reverse()[0] }}
              </a>
              <i class="fa-regular fa-circle-xmark cursor-pointer hover:text-error" @click.stop="$emit('remove-file', file)"></i>
            </div>
          </div>
        </div>
      </div>
    </div>
  </Collapsible>
</template>

<script>
export default {
  props: ['chat', 'message', 'mentionList', 'menu-less', 'usersList'],
  emits: [
    'generate-code', 'reload-file', 'open-file', 'save-file',
    'add-file', 'sub-task', 'thread', 'hide',
    'remove', 'answer', 'enhance', 'copy', 'add-file-to-chat',
    'remove-file', 'image', 'run-agents', 'edit-message', 'search-files'
  ],
  data() {
    return {
      srcView: false,
      isRemove: false,
      improvementData: null,
      showDiff: false,
      showPRView: false,
      documentId: 'doc-' + Math.random().toString(36).slice(2, 8),
      activeBranch: null,
      branchLoading: false,
      showSelectionMenu: false,
      selectedText: '',
      selectionPosition: { top: 0, left: 0 },
      collapsed: false
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
    prViewCodeBlocks() {
      return this.$service.chat.extractCodeBlocksFromMessage(this.displayMessage)
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
      return moment(date).format('DD/MMM HH:mm:ss')
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
      }
    },
    toggleShowDiff() {
      this.showDiff = !this.showDiff
      if (this.showDiff) {
        this.srcView = false
        this.showPRView = false
      }
    },
    togglePRView() {
      this.showPRView = !this.showPRView
      if (this.showPRView) {
        this.srcView = false
        this.showDiff = false
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