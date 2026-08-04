<script setup>
import Markdown from './Markdown.vue'
import moment from 'moment'
import { CodeDiff } from 'v-code-diff'
import ChatIcon from './chat/ChatIcon.vue'
import Document from './document/Document.vue'
import UserSelector from './chat/UserSelector.vue'
import ProfileAvatar from './profile/ProfileAvatar.vue'
import ChatEntryMobile from './ChatEntryMobile.vue'
import DocumentSummary from './document/DocumentSummary.vue'
import MessagePRView from './chat/MessagePRView.vue'
import ChatEntrySelectionMenu from './ChatEntrySelectionMenu.vue'
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

  <!-- Default desktop rendering -->
  <div v-else class="group chat-entry flex gap-1 items-start relative p-2"
    :class="[
      displayMessage.hide ? 'hover:bg-base-100 opacity-50 hover:opacity-100': '',
      displayMessage.hide ? 'border-l-2 border-warning' : '',
      !isDone && 'border border-dashed border-sky-800 p-1',
      displayMessage.is_answer && 'border border-dashed p-2 bg-success/10 border-success',
      isTopic && 'border-l p-2 bg-info/5 border-info/50',
    ]"
  >
    <div class="w-full">
      <div class="w-full flex flex-col gap-1 hover:rounded-md group relative">
        <progress class="progress w-full" v-if="!isDone"></progress>

        <!-- Sticky selection action bar — shown when text is selected -->
        <!-- In the ChatEntrySelectionMenu component -->
        <ChatEntrySelectionMenu
          v-if="showSelectionMenu"
          :selectedText="selectedText"
          :chatProject="chatProject"
          @copy="onSelectionCopy"
          @create-subtask="onSelectionCreateSubtask"
          @search-files="onSelectionSearchFiles"
          @close="onCloseSelectionMenu"
        />

        <!-- Floating selected text display — positioned above and centered on selection -->
        <div 
          v-if="false && showSelectionMenu && selectedText"
          ref="floatingDisplay"
          class="floating-display fixed bg-base-200 border border-base-300 rounded-lg shadow-lg p-3 z-50 pointer-events-none relative"
          :style="{ 
            top: selectionPosition.top + 'px', 
            left: selectionPosition.left + 'px',
          }"
        >
          <ChatEntrySelectionMenu
            :selectedText="selectedText"
            :chatProject="chatProject"
            @copy="onSelectionCopy"
            @create-subtask="onSelectionCreateSubtask"
            @search-files="onSelectionSearchFiles"
            @close="onCloseSelectionMenu"
          />
        </div>

        <div class="text-xs font-bold flex flex-col click" @dblclick.stop="toggleCollapse">
          <div class="flex gap-1 items-center" 
            :class="[displayMessage.hide && 'text-slate-50']">
            <span class="text-warning" v-if="displayMessage.hide">
              <i class="fa-solid fa-box-archive"></i>
            </span>
            <div 
              class="tooltip tooltip-right" 
              :data-tip="profile.name || profile.username" 
              v-for="profile in messageProfiles" 
              :key="profile.name"
            >
              <ProfileAvatar :profile="profile" width="6" />
            </div>
            <UserSelector 
              class="dropdown-bottom"
              :selectedUser="usersList.find(u => u.name === displayMessage.user)"
              :profiles="usersList"
              @user-changed="displayMessage.profiles = [$event.name]"
              v-if="false"
            />
            <i class="fa-solid fa-magnifying-glass" v-if="message.task_item === 'search'"></i>
            <div class="flex gap-2 grow">
              <span class="badge badg-xs badge-error" v-if="cancellationTime">Cancelled</span>
              [{{ formatDate(displayMessage.updated_at) }}] 
              <span v-if="timeTaken">({{ timeTaken }})</span>
              <div class="badge badge-sm badge-success flex gap-1" v-if="displayMessage.is_answer">
                <ChatIcon mode="answer" /> Knowledge 
              </div>
              <div class="badge badge-sm badge-info badge-outline flex gap-1" v-if="isTopic">
                <ChatIcon mode="topic" /> Topic 
              </div>
              <div 
                class="badge badge-sm border-dashed badge-outline flex gap-1 click" 
                @click="openThread"
                v-if="threadChat"
              >
                <ChatIcon :mode="threadChat.mode" /> Thread 
              </div>
            </div>

            <!-- Action buttons -->
            <div 
              class="@lg:opacity-0 group-hover:opacity-100 flex gap-2 items-center justify-end"
              v-if="menuLess !== true"
            >
              <div class="px-2 flex flex-col">
                <div class="gap-2 flex justify-end items-center">
                  <button
                    class="btn btn-xs btn-error tooltip tooltip-bottom"
                    data-tip="Stop generation"
                    @click="cancelMessage"
                    v-if="!isDone && cancellationTokenId"
                  >
                    <span class="loading loading-xs"></span>
                    Cancel...
                  </button>
                  <button 
                    class="btn btn-xs hover:btn-outline tooltip tooltip-bottom" 
                    data-tip="Thread" 
                    @click="$emit('thread', message)"
                  >
                    <i class="fa-solid fa-comment-dots"></i>
                  </button>      
                  <button 
                    class="btn btn-xs text-success hover:btn-outline tooltip tooltip-bottom" 
                    data-tip="Right answer!" 
                    @click="$emit('answer', message)"
                  >
                    <i class="fa-solid fa-check-double"></i>
                  </button>      
                  <button 
                    class="btn btn-xs hover:btn-outline tooltip tooltip-bottom" 
                    data-tip="Copy message" 
                    @click="copyMessageToClipboard"
                  >
                    <i class="fa-solid fa-copy"></i>
                  </button>      
                  <button 
                    class="btn btn-xs hover:btn-outline tooltip tooltip-bottom" 
                    data-tip="View diff" 
                    @click="toggleShowDiff" 
                    v-if="displayMessage.diffMessage"
                  >
                    <i class="fa-regular fa-file-lines"></i>
                    <i class="fa-regular fa-file-lines text-primary -ml-1"></i>
                  </button>
                  <button 
                    class="btn btn-xs hover:btn-outline tooltip tooltip-bottom"
                    :class="showPRView && 'btn-warning'"
                    data-tip="View PR changes" 
                    @click="togglePRView"
                    v-if="hasPRViewBlocks"
                  >
                    <i class="fa-solid fa-code-branch"></i>
                  </button>
                  <button 
                    class="btn btn-xs hover:btn-outline tooltip tooltip-bottom hover:btn-warning" 
                    data-tip="Run agents" 
                    @click="runAgents"
                  >
                    <i class="fa-solid fa-people-group"></i>
                  </button>
                  <div class="dropdown dropdown-hover dropdown-end">
                    <button tabindex="0" class="btn hover:btn-error btn-xs" @click="onRemove">
                      <i class="fa-solid fa-bars"></i>
                    </button>
                    <ul tabindex="0" class="dropdown-content menu rounded-box shadow w-32 p-2 bg-base-300 z-50">
                      <li class="text-error">
                        <a class="hover:underline" @click="confirmRemove">
                          <i class="fa-solid fa-trash-can"></i> Delete
                        </a>
                      </li>
                      <li class="text-warning" v-if="isDone">
                        <a 
                          @click.stop="$emit('hide', message)" 
                          class="text-left tooltip tooltip-bottom click"
                          :data-tip="displayMessage.hide 
                            ? 'Click to add message to conversation' 
                            : 'Click to archive message from the conversation'"
                        >
                          <i class="fa-solid fa-box-archive"></i> {{ displayMessage.hide ? 'Show' : 'Archive' }}
                        </a>                  
                      </li>
                      <li @click="toggleSrcView" v-if="isDone">
                        <a><i class="fa-solid fa-code"></i> Source</a>
                      </li>
                      <li @click="$emit('edit-message', message)" v-if="isDone">
                        <a><i class="fa-solid fa-pen"></i> Edit</a>
                      </li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Document summary TOC — documentId scopes anchors to this document instance -->
          <DocumentSummary
            v-if="isDone && messageContent"
            :content="messageContent"
            :minHeadings="3"
            :documentId="documentId"
            :scrollContainer="$refs.contentArea"
            class="mt-1"
          />
        </div>

        <!-- Skeleton loader when no content yet -->
        <div class="flex w-full flex-col gap-4 bg-base-100 p-2 mb-2 rounded-md" 
          v-if="!displayMessage.content && !displayMessage.think"
        >
          <div class="flex items-center gap-4">
            <div class="skeleton h-8 w-8 shrink-0 rounded-full"></div>
            <div class="flex flex-col gap-4">
              <div class="skeleton h-4 w-20"></div>
            </div>
          </div>
          <div class="skeleton h-32 w-full"></div>
        </div>
        
        <!-- Thinking block -->
        <div v-if="thinkText">
          <div 
            class="alert click items-start"
            @click="displayMessage.full_think = !displayMessage.full_think"
          >
            <i class="fa-solid fa-brain"></i>
            {{ thinkText }}
          </div>    
        </div>

        <!-- Message content area — ref used by DocumentSummary to scroll within -->
        <div 
          ref="contentArea"
          @copy.stop="onMessageCopy"
          @mouseup="onContentMouseUp"
          :class="[
            'max-w-full border-slate-300/20 relative', 
            (isCollapsed === undefined ? displayMessage.hide : isCollapsed) 
              ? 'h-6 overflow-hidden' 
              : 'h-fit'
          ]"
        >
          <pre v-if="srcView">{{ displayMessage.content }}</pre>

          <!-- Pass documentId so heading anchors are scoped to this message -->
          <Document 
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
            v-if="!showDiff && !srcView && !showPRView && !code_patches && !isWord" 
          />

          <div class="alert alert-error text-xs" v-if="displayMessage.error">
            {{ displayMessage.error }}
          </div>

          <CodeDiff
            :new-string="displayMessage.diffMessage.content"
            :old-string="messageContent"
            theme="dark"
            v-if="showDiff && !showPRView"
          />

          <!-- Code patches list -->
          <div v-if="code_patches && !showPRView">
            <div 
              class="mt-2 p-2 rounded-md flex flex-col gap-1 overflow-hidden" 
              v-for="patch in code_patches" 
              :key="patch.file_path"
            >
              <div class="text-xs font-bold text-primary" :title="patch.file_path">
                {{ patch.file_path.replace($project.abs_project_path, '') }}
              </div>
              <div class="">{{ patch.description }}</div>
              <Markdown :text="'```diff\n' + patch.patch + '\n```'"></Markdown>
              <div class="flex justify-end">
                <button 
                  class="btn btn-sm btn-warning" 
                  :disabled="patch.working" 
                  @click="applyPatch(patch)"
                >
                  <span class="loading loading-spinner" v-if="patch.working"></span>
                  Apply changes
                </button>
              </div>
              <div v-if="patch.res">
                <div class="text-xs text-error" v-if="patch.res.error">{{ patch.res.error }}</div>
                <div class="text-xs text-success" v-else>Patch applied</div>
              </div>
            </div>
          </div>

          <!-- PR View component -->
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

          <!-- Image carousel -->
          <div v-if="images && !showPRView">
            <div class="carousel gap-2" v-if="images?.length">
              <div 
                class="carousel-item click mt-2" 
                v-for="image in images" 
                :key="image.src" 
                @click="$emit('image', image)" 
                :alt="image.alt" 
                :title="image.alt"
              >
                <div class="flex flex-col">
                  <div 
                    class="bg-contain bg-no-repeat bg-center border rounded-md w-12 h-12 md:h-20 md:w-20" 
                    :style="`background-image: url(${image.src})`"
                  ></div>
                  <p class="badge badge-xs" v-if="image.alt">{{ image.alt.slice(0, 10) }}</p>
                </div>
              </div>
            </div>
          </div>

          <!-- Linked files list -->
          <div class="font-bold text-xs flex flex-col gap-2 mt-2" v-if="displayMessage.files?.length && !showPRView">
            Linked files:
            <div 
              v-for="file in displayMessage.files" 
              :key="file" 
              :title="file" 
              class="flex gap-2 items-center click"
            >
              <div class="flex gap-2 click hover:underline" @click="openFile(file)">
                <div 
                  class="click tooltip tooltip-right" 
                  data-tip="Attach file" 
                  @click.stop="$emit('add-file-to-chat', file)"
                >
                  <i class="fa-solid fa-file-arrow-up"></i>
                </div>
                <div class="overflow-hidden">
                  {{ file.split('/').reverse()[0] }}
                </div>
              </div>
              <div class="click hover:text-error" @click.stop="$emit('remove-file', file)">
                <i class="fa-regular fa-circle-xmark"></i>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
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
      selectionPosition: {
        top: 0,
        left: 0
      }
    }
  },
  created() {
    this.loadThreadChat()
    this.loadActiveBranch()
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
      return this.displayMessage.collapsed !== undefined
        ? this.displayMessage.collapsed
        : this.displayMessage.is_answer ? true : false
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
      const { full_think, is_thinking } = this.message 
      return null        
    },
    displayMessage() {
      return this.threadChat?.messages
        .filter(m => !m.hide)
        .reverse()[0] || this.message
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
      return `${this.displayMessage.meta_data.model} ${timeTaken}`
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
      
      // Get floating element dimensions - must be visible to measure
      const floatingEl = this.$refs.floatingDisplay
      let floatingHeight = 0
      
      if (floatingEl) {
        floatingEl.style.visibility = 'hidden'
        floatingEl.style.display = 'block'
        floatingHeight = floatingEl.offsetHeight
        floatingEl.style.visibility = 'visible'
      }
      
      // Center horizontally on selection, position above with padding
      const { x, y } = this.$el.parentNode.getBoundingClientRect()
      const left = rect.left - x
      const top = rect.top + window.scrollY - floatingHeight + rect.height
      
      return {
        top: Math.max(10, top),
        left: left
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
        // Wait for DOM update, then calculate position
        this.$nextTick(() => {
          this.selectionPosition = this.getSelectionPosition()
        })
      } else {
        this.showSelectionMenu = false
      }
    },
    onSelectionCopy(text) {
      this.copyTextToClipboard(text)
      this.$ui.showNotification('Copied to clipboard', 'success')
    },
    onSelectionCreateSubtask(content) {
      this.$emit('sub-task', {
        content,
      })
    },
    onSelectionSearchFiles({ query, fromSelection }) {
      this.$emit('search-files', {
        query,
        fromSelection: true
      })
    },
    onCloseSelectionMenu() {
      this.showSelectionMenu = false
    },
    toggleCollapse() {
      if (this.displayMessage.collapsed !== undefined) {
        this.displayMessage.collapsed = !this.displayMessage.collapsed 
      } else {
        this.displayMessage.collapsed = !this.isCollapsed
      }
    },
    toggleSrcView() {
      if (this.srcView = !this.srcView) {
        this.showDiff = false
        this.showPRView = false
        this.collapsed = false
      }
    },
    toggleShowDiff() {
      if (this.showDiff = !this.showDiff) {
        this.srcView = false
        this.showPRView = false
        this.collapsed = false
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
        patch.res = { info: 'Patch sent, please check events for updates' }
      } catch {
        patch.res = { info: '', error: 'Error applying patch' }
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
    onCopyChapter(chapterData) {
      this.copyTextToClipboard(chapterData.content)
      this.$ui.showNotification(`Copied chapter: ${chapterData.headingText}`, 'success')
    },
    onCreateTask(taskData) {
      this.$emit('sub-task', {
        content: taskData.content,
        title: taskData.headingText
      })
      this.$ui.showNotification(`Task created from: ${taskData.headingText}`, 'success')
    }
  },
  mounted() {
    this.collapsed = this.isCollapsed || this.displayMessage.hide
    this.extractImprovementData()
  }
}
</script>