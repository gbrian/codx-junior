<script setup>
import moment from 'moment'
import AddFileDialog from '../components/chat/AddFileDialog.vue'
import Chat from '@/components/chat/Chat.vue'
import TaskSettings from '@/components/kanban/TaskSettings.vue'
import ChatSelector from '@/components/chat/ChatSelector.vue'
import ExportChat from '@/components/chat/ExportChat.vue'
import ChatDumpDialog from '@/components/chat/ChatDumpDialog.vue'
import ChatHistoryViewer from '@/components/chat/ChatHistoryViewer.vue'
import ChatSidebar from '@/components/chat/ChatSidebar.vue'
import ChatViewHeader from '@/components/chat/ChatViewHeader.vue'
import ChatRunBar from '@/components/chat/ChatRunBar.vue'
import ChatLogsPanel from '@/components/ChatLogsPanel.vue'
</script>

<template>
  <!-- `flex-row-reverse`: the chat hierarchy sidebar sits on the RIGHT, so the
       conversation keeps a single continuous reading line and a host-supplied
       channel list (MessengerView) can live on the left. The mobile drawer is
       positioned with `fixed`, so the reversed flow does not affect it. -->
  <div class="flex flex-row-reverse h-full overflow-hidden" v-if="theChat">
    <!-- ─────────────────────────────────────────────────────────────
         SIDEBAR: Persistent on desktop, overlay drawer on mobile
         ───────────────────────────────────────────────────────────── -->
    <!-- Hidden when the host view already provides the conversation list
         (`hideChatSidebar`). In channel mode it stays as a slim action rail:
         task features are hidden inside (see ChatSidebar's `channelMode`). -->
    <ChatSidebar
      v-if="!isMobile"
      :workingChat="theChat"
      :rootChat="rootChat"
      :allChats="hierarchyChats"
      :selectedChatId="theChat?.id"
      :workingChatMode="theChat?.mode"
      :chatSearch="chatSearch"
      :isCompact="compactSidebar"
      :chatProfiles="chatProfiles"
      :channelMode="isChannelChat"
      :canDump="canDumpChat"
      @select="onSelectSidebarChat"
      @add-subtask="onSidebarAddSubtask"
      @action="handleSidebarAction"
      @toggle-compact="compactSidebar = !compactSidebar"
      @delete-chat="onSidebarDeleteChat"
      @remove-attachment="onSidebarRemoveAttachment"
    >
      <!-- Host-provided sidebar actions (e.g. MessengerView's channel members
           toggle) forwarded into ChatSidebar's `actions` footer slot. -->
      <template #actions>
        <slot name="sidebar-actions" />
      </template>
    </ChatSidebar>

    <!-- Mobile sidebar drawer -->
    <template v-if="isMobile">
      <div
        v-if="showMobileSidebar"
        class="fixed inset-0 z-40 bg-base-300/60 backdrop-blur-sm animate-fade-in"
        @click="closeMobileSidebar"
      ></div>
      <div
        v-if="showMobileSidebar"
        class="fixed left-0 top-0 bottom-0 z-50 w-64 shadow-xl flex"
      >
        <ChatSidebar
          :workingChat="theChat"
          :rootChat="rootChat"
          :allChats="hierarchyChats"
          :selectedChatId="theChat?.id"
          :workingChatMode="theChat?.mode"
          :chatSearch="chatSearch"
          :isCompact="false"
          :chatProfiles="chatProfiles"
          :channelMode="isChannelChat"
          :canDump="canDumpChat"
          @select="onSelectSidebarChat"
          @add-subtask="onSidebarAddSubtask"
          @action="handleSidebarAction"
          @toggle-compact="compactSidebar = !compactSidebar"
          @delete-chat="onSidebarDeleteChat"
          @remove-attachment="onSidebarRemoveAttachment"
        />
      </div>
    </template>

    <!-- ─────────────────────────────────────────────────────────────
         MAIN CONTENT AREA: Header + Chat View OR Logs View
         ───────────────────────────────────────────────────────────── -->
    <div
      class="flex-1 flex flex-col min-w-0"
      :class="isMobile ? 'p-0 gap-1' : 'md:p-2 gap-2'"
    >
      
      <!-- MINIMAL HEADER -->
      <!-- Mobile runs it collapsed: only back + title + details toggle. -->
      <ChatViewHeader
        :chat="theChat"
        :rootChat="rootChat"
        :breadcrumb="breadcrumbChats"
        :messageCount="messageCount"
        :hiddenCount="hiddenCount"
        :showHidden="showHidden"
        :isSelectedChatChild="isSelectedChatChild"
        :targetProject="targetProject"
        :mobile-expanded="showMobileDetails"
        :channelMode="isChannelChat"
        @toggle-mobile-details="showMobileDetails = $event"
        @update-name="saveChatInfo"
        @toggle-hidden="showHidden = !showHidden"
        @toggle-pinned="toggleChatPinned"
        @select-breadcrumb="onSelectBreadcrumbChat"
        @show-settings="showTaskSettings = true"
        @show-export="showExportChat = true"
        @confirm-delete="confirmDelete = true"
        @show-add-tag="newTag = ''"
        @remove-tag="onRemoveTag"
        @mode-changed="onChatModeChanged"
        @toggle-template="onTemplateChanged"
        @toggle-ignore-parent-knowledge="onIgnoreParentKnowledgeChanged"
        @toggle-ignore-parent-files="onIgnoreParentFilesChanged"
        @status-changed="onStatusChanged"
        @cost-changed="onCostChanged"
        @select-project="setChatProject"
        @back="onBack"
        @show-sidebar="toggleMobileSidebar"
      />

      <!-- LONG-RUNNING TASK (orchestration run) -------------------------
           `chat.run_id` is the durable process id. The bar is rendered only
           when the chat already has a run (or is in agent mode and needs one)
           and is fed by the `codx-junior-orchestration` socket event through
           the orchestration store. Start/pause/stop are the only control
           surface the human needs on this screen. -->
      <ChatRunBar
        v-if="theChat && !isChannelChat"
        :chat="theChat"
        :run="chatRun"
        :busy="runBusy"
        :error="runError"
        @start="onRunStart"
        @pause="onRunPause"
        @stop="confirmStopRun = true"
      />

      <!-- CONTENT AREA: Logs View OR (History Wall OR Chat View) -->
      <div class="flex-1 min-h-0 rounded-lg">
        <!-- Logs View (Full Screen) -->
        <ChatLogsPanel
          v-if="showLogs"
          :chatId="theChat?.id"
          @close="showLogs = false"
        />

        <!-- History Wall View (Full Screen) -->
        <ChatHistoryViewer
          v-else-if="showHistoryWall"
          :history="theChat.history || []"
          :currentDescription="computedChatDescription"
        />

        <!-- Normal Chat View -->
        <!-- On mobile the chat files strip is only rendered while the header
             details panel is expanded, so the reading area keeps the space.
             Channels have no project context files: the strip is always hidden
             through the existing `hide-files-header` prop. -->
        <Chat 
          v-else
          :chat="theChat" 
          :showHidden="showHidden" 
          :childrenChats="childrenChats"
          :filter="chatSearch" 
          :hide-files-header="isChannelChat || (isMobile && !showMobileDetails)"
          @refresh-chat="reloadChat" 
          @remove-file="onRemoveFile"
          @delete="confirmDelete = true" 
          @subtask="onNewMessageSubtask" 
        />
      </div>
    </div>

    <!-- ─────────────────────────────────────────────────────────────
         MODALS
         ───────────────────────────────────────────────────────────── -->
    <modal v-if="confirmDelete">
      <div class="p-6 space-y-4">
        <h3 class="font-bold text-lg">Confirm Delete</h3>
        <p class="text-error font-bold">Are you sure you want to delete this chat?</p>
        <div class="text-sm bg-base-200 p-3 rounded">{{ computedChatName }}</div>
        <div class="modal-action">
          <button class="btn btn-error" @click="confirmDeleteChat">Delete</button>
          <button class="btn" @click="resetConfirmDelete">Cancel</button>
        </div>
      </div>
    </modal>

    <!-- Sidebar Subtask Delete Confirmation -->
    <modal v-if="confirmDeleteSubtask">
      <div class="p-6 space-y-4">
        <h3 class="font-bold text-lg">Delete Subtask</h3>
        <p class="text-error font-bold">Are you sure you want to delete this subtask?</p>
        <div class="text-sm bg-base-200 p-3 rounded">{{ confirmDeleteSubtask.name }}</div>
        <div class="modal-action">
          <button class="btn btn-error" @click="confirmDeleteSubtaskChat">Delete</button>
          <button class="btn" @click="confirmDeleteSubtask = null">Cancel</button>
        </div>
      </div>
    </modal>

    <modal class="modal modal-open" role="dialog" v-if="showFile || addFile !== null">
      <div class="modal-box flex flex-col gap-4 p-4">
        <h3 class="font-bold text-lg" v-if="showFile">
          This file belongs to the task context:
          <div class="font-thin">{{ showFile }}</div>
        </h3>
        <div v-else>
          <input type="text" class="input input-bordered w-full" v-model="addFile" placeholder="Add file to context, full path" />
        </div>
        <div class="flex gap-2 justify-center">
          <button class="btn btn-error" @click="removeFileFromContext" v-if="showFile">Remove</button>
          <button class="btn btn-primary" @click="addFileToContext" v-else>Add</button>
          <button class="btn" @click="addFile = showFile = null">Close</button>
        </div>
      </div>
    </modal>

    <modal v-if="newTag !== null">
      <div class="flex flex-col gap-2 p-4">
        <div class="text-xl">New tag</div>
        <select class="select select-sm select-bordered" @change="newTag = $event.target.value">
          <option value="" selected>New</option>
          <option v-for="t in $projects.allTags" :key="t" :value="t">{{ t }}</option>
        </select>
        <input type="text" class="input input-sm input-bordered" v-model="newTag" />
        <div class="flex gap-2 justify-end">
          <button class="btn btn-error" @click="newTag = null">Cancel</button>
          <button class="btn" @click="addNewTag" :disabled="newTag.length === 0">Add</button>
        </div>
      </div>
    </modal>

    <modal class="w-2/3 h-2/3" v-if="showSubtasksModal">
      <div class="h-full flex flex-col gap-4 p-4">
        <h3 class="font-bold text-2xl">Split into tasks</h3>
        <textarea v-model="createTasksInstructions" class="grow textarea textarea-bordered"></textarea>
        <div class="flex gap-2 justify-end">
          <button class="btn" @click="showSubtasksModal = false">Cancel</button>
          <button class="btn bg-codx-primary" @click="createSubTasks">Create</button>
        </div>
      </div>
    </modal>

    <modal v-if="confirmStopRun">
      <div class="p-6 space-y-4">
        <h3 class="font-bold text-lg">Stop long-running task</h3>
        <p class="text-error font-bold">
          Stop this run? The in-flight turns are cancelled and a stop report is
          published. Completed steps are preserved and the run can be started
          again later.
        </p>
        <div class="text-sm bg-base-200 p-3 rounded">{{ computedChatName }}</div>
        <div class="modal-action">
          <button class="btn btn-error" :disabled="runBusy" @click="onRunStop">Stop</button>
          <button class="btn" @click="confirmStopRun = false">Cancel</button>
        </div>
      </div>
    </modal>

    <!-- Chat properties -------------------------------------------------
         `TaskSettings` owns the form; the dialog owns the frame. The title and
         the `board / column · id` subtitle live in the modal `header` slot
         (rendered by <Modal> only when there is content), and `close` wires the
         X button and the Escape key. `hideHeader` stops the child from printing
         a second, duplicated header bar. -->
    <modal v-if="showTaskSettings" close @close="showTaskSettings = false">
      <template #header>
        <div class="min-w-0">
          <h2 class="text-sm md:text-base font-semibold truncate">Chat properties</h2>
          <p class="text-[11px] text-base-content/50 truncate font-mono">
            {{ theChat?.board || '—' }}
            <span class="mx-1 opacity-50">/</span>{{ theChat?.column || 'unassigned' }}
            <template v-if="theChat?.id">
              <span class="mx-1 opacity-50">·</span>{{ String(theChat.id).slice(0, 8) }}
            </template>
          </p>
        </div>
      </template>
      <TaskSettings :taskData="theChat" hideHeader @close="showTaskSettings = false" />
    </modal>

    <modal close="true" @close="showExportChat = false" v-if="showExportChat">
      <ExportChat :chat="theChat" @close="showExportChat = false" />
    </modal>

    <!-- Admin-only raw chat dump (postmortem). The dialog builds the JSON from
         the loaded chat plus the run/environment context and offers download
         and clipboard copy. -->
    <modal class="max-w-4xl w-11/12" close="true" @close="showDumpChat = false" v-if="showDumpChat">
      <ChatDumpDialog
        :chat="theChat"
        :childrenChats="childrenChats"
        @close="showDumpChat = false"
      />
    </modal>

    <modal close="true" @close="showChatSelector = false" v-if="showChatSelector">
      <ChatSelector />
    </modal>

    <add-file-dialog v-if="addNewFile" @open="onAddFile" @close="addNewFile = false" />
  </div>
</template>

<script>
export default {
  // `hideChatSidebar` lets a host view own the conversation list (messenger
  // channels) instead of stacking ChatSidebar next to its own sidebar.
  // `channelMode` turns the view into a group conversation: task features
  // (subtasks, project context, status, cost, tags, template, chat mode) are
  // hidden inside the child components (see ChatViewHeader, ChatSidebar, Chat).
  // `dumpEnabled` is an explicit override for the admin-only chat dump: when
  // omitted the permission is read from the signed-in user (fails closed).
  // All of them default to false/undefined so every other usage of ChatView
  // stays identical.
  props: ['chatMode', 'chat', 'kanban', 'params', 'hideChatSidebar', 'channelMode', 'dumpEnabled'],
  data() {
    return {
      showFile: null,
      addFile: null,
      editName: false,
      addNewFile: null,
      showHidden: false,
      confirmDelete: false,
      confirmDeleteSubtask: null,
      newTag: null,
      showSubtasksModal: false,
      showTaskSettings: false,
      createTasksInstructions: '',
      projectContext: null,
      showChatSelector: false,
      showExportChat: false,
      // Admin-only postmortem dump dialog
      showDumpChat: false,
      chatSearch: null,
      targetProject: null,
      showHistoryWall: false,
      showLogs: false,
      compactSidebar: true,
      chatProfiles: [],
      activeChatId: null,
      showMobileSidebar: false,
      // Mobile: chat header details (and the chat files strip) stay collapsed
      // until the user expands them from the header toggle.
      showMobileDetails: false,
      // Long-running task (orchestration run) controls.
      runBusy: false,
      runError: '',
      confirmStopRun: false
    }
  },
  created() {
    this.init()
  },
  computed: {
    isMobile() {
      return this.$ui?.isMobile
    },
    // ─── Admin-only surfaces ───────────────────────────────────────────────
    // The chat dump exposes prompts, tool calls and usage data, so it is
    // restricted to admins. The flag is read defensively and FAILS CLOSED: an
    // unknown user store keeps the action hidden instead of leaking it. The
    // UI only decides whether to render the entry point; anything persisted
    // server-side must keep enforcing the role.
    isAdminUser() {
      const user = this.$storex?.user || null
      if (!user) return false
      if (user.is_admin !== undefined) return !!user.is_admin
      if (user.isAdmin !== undefined) return !!user.isAdmin
      if (Array.isArray(user.roles)) return user.roles.includes('admin')
      return user.role === 'admin'
    },
    // Host override wins so a host that already knows the role (or a test) does
    // not depend on the shape of the user store.
    canDumpChat() {
      if (this.dumpEnabled !== undefined) return !!this.dumpEnabled
      return this.isAdminUser
    },
    // Messenger / channel view: a hosted group conversation. Hosts either pass
    // `channel-mode` (MessengerView) or simply use the `channel` chat mode.
    isChannelChat() {
      return !!this.channelMode || this.theChat?.mode === 'channel'
    },
    theChat() {
      const chatId = this.activeChatId || this.chat?.id || this.params?.params?.chat?.id
      return this.$chats.chats[chatId] || null
    },
    rootChat() {
      let current = this.theChat
      if (!current) return null
      let depth = 0
      while (current?.parent_id && this.$chats.chats[current.parent_id] && depth < 20) {
        current = this.$chats.chats[current.parent_id]
        depth++
      }
      return current
    },
    hierarchyChats() {
      // Channels have no subtask hierarchy: nothing to list in the sidebar
      if (this.isChannelChat) return []
      return this.collectHierarchy(this.rootChat)
    },
    breadcrumbChats() {
      const breadcrumb = []
      let current = this.theChat?.parent_id ? this.$chats.chats[this.theChat.parent_id] : null
      while (current) {
        breadcrumb.unshift(current)
        current = current.parent_id ? this.$chats.chats[current.parent_id] : null
      }
      return breadcrumb
    },
    isThread() {
      return !!(this.theChat?.message_id)
    },
    isPRView() {
      return this.theChat?.mode === 'prview'
    },
    hiddenCount() {
      return (this.theChat?.messages || []).filter(m => m.hide).length
    },
    messageCount() {
      return (this.theChat?.messages || []).length
    },
    messages() {
      return (this.theChat?.messages || []).filter(m => !m.hide || this.showHidden)
    },
    formattedChatUpdatedDate() {
      const updatedAt = this.theChat?.updated_at
      if (!updatedAt) return ''
      return moment(updatedAt).isAfter(moment().subtract(7, 'days'))
        ? moment(updatedAt).fromNow()
        : moment(updatedAt).format('YYYY-MM-DD')
    },
    childrenChats() {
      if (this.isChannelChat) return []
      return this.getDirectChildren(this.theChat?.id)
    },
    parentChat() {
      const id = this.theChat?.parent_id
      if (!id) return null
      return this.$chats.chats[id] || null
    },
    computedChatName() {
      return this.theChat?.name || 'New Task'
    },
    computedChatDescription() {
      const chat = this.theChat
      if (!chat) return ''
      if (chat.message_id) {
        const parent = this.$chats.chats[chat.parent_id]
        const message = (parent?.messages || []).find(m => m.doc_id === chat.message_id)
        return message?.content || ''
      }
      return chat.description
    },
    isSelectedChatChild() {
      return this.theChat && this.theChat.parent_id && this.theChat.id !== this.rootChat?.id
    },
    // Run detail of the chat's long-running process (`chat.run_id`). It is
    // kept live by the orchestration store: socket events patch the cached run
    // and debounce a REST detail refresh.
    chatRun() {
      const runId = this.theChat?.run_id
      return runId ? this.$storex.orchestration.runById(runId) : null
    }
  },
  watch: {
    chat(newVal, oldVal) {
      if (oldVal && newVal && oldVal.project_id !== newVal.project_id) {
        this.init()
      }
    },
    theChat(newVal, oldVal) {
      if (!newVal) {
        return
      }
      if (!oldVal || oldVal.id !== newVal.id) {
        this.showHistoryWall = false
        this.showLogs = false
        // A freshly opened chat starts with the compact mobile header
        this.showMobileDetails = false
        this.showDumpChat = false
        this.runError = ''
        this.loadHierarchy()
        this.loadChatProfiles()
        this.loadChatRun()
        if (newVal) {
          this.targetProject = this.$projects.allProjectsById[newVal.project_id] || this.chatProject
          if (newVal.parent_id && !this.$chats.chats[newVal.parent_id]) {
            this.$chats.ensureChatRoot(newVal)
          }
        }
      }
    },
    'theChat.run_id'(newVal, oldVal) {
      if (newVal === oldVal) return
      this.runError = ''
      this.loadChatRun()
    }
  },
  methods: {
    async init() {
      const sourceChat = this.chat || this.params?.params?.chat || {}
      if (!sourceChat?.id) throw new Error('No chat id to load')

      await this.$service.chat.findChat(sourceChat)

      if (!this.theChat) {
        await this.$chats.loadChat(sourceChat)
      }

      if (!this.theChat) throw new Error('Chat not loaded')

      this.setProjectContext()

      if (!this.$storex.projects.kanban) {
        await this.$storex.projects.loadKanban()
      }

      await this.loadHierarchy()

      if (this.isPRView) await this.$projects.loadBranches()
      
      await this.loadChatProfiles()
      await this.loadChatRun()
    },
    async loadHierarchy() {
      if (!this.theChat || this.isChannelChat) return
      try {
        await this.$chats.ensureChatRoot(this.theChat)
      } catch (error) {
        console.error('Failed to load hierarchy:', error)
      }
    },
    async loadChatProfiles() {
      if (!this.theChat) return
      try {
        this.chatProfiles = await this.$chats.getChatProfiles(this.theChat)
        this.chatProfiles = this.chatProfiles.filter(p => this.theChat.profiles?.includes(p.name))
      } catch (error) {
        console.error('Failed to load chat profiles:', error)
        this.chatProfiles = []
      }
    },
    // ─── Long-running task (orchestration) ────────────────────────────────
    // `chat.run_id` is the durable process id. The store keeps the run detail
    // live from the `codx-junior-orchestration` socket event; the bar only
    // renders it, and these methods are the control surface.
    async loadChatRun({ force = true } = {}) {
      const chat = this.theChat
      if (!chat?.run_id) return null
      const run = await this.$storex.orchestration.loadRun({
        runId: chat.run_id,
        chat,
        force
      })
      const error = this.$storex.orchestration.runError(chat.run_id)
      this.runError = run ? '' : (error || '')
      return run
    },
    runObjective(chat) {
      const description = String(chat?.description || '').trim()
      if (description) return description
      const lastUserMessage = [...(chat?.messages || [])]
        .reverse()
        .find(message => message.role === 'user' && String(message.content || '').trim())
      return String(lastUserMessage?.content || chat?.name || '').trim()
    },
    notifyRun(text, type = 'info') {
      this.$ui?.addNotification?.({ text, type })
    },
    runErrorMessage(error) {
      return error?.response?.data?.detail ||
        error?.response?.data?.message ||
        error?.message ||
        String(error)
    },
    /**
     * Select "agent" mode → add the orchestrator profile (when missing) and
     * create the long-running run anchored on this task.
     *
     * Runs are budget roots; a subtask cannot own one, so the mode change is
     * refused with a clear message in that case.
     */
    async startAgentRun() {
      const chat = this.theChat
      if (!chat?.id || this.runBusy) return false
      if (chat.parent_id) {
        this.notifyRun(
          'Agent mode needs a root task: move this task to the top level before starting its run.',
          'warning'
        )
        return false
      }

      this.runBusy = true
      this.runError = ''
      try {
        if (!(chat.profiles || []).includes('orchestrator')) {
          chat.profiles = [...(chat.profiles || []), 'orchestrator']
          await this.saveChatInfo(chat)
        }

        const run = await this.$storex.orchestration.startChat({
          chat,
          objective: this.runObjective(chat),
          budget: chat.estimation_cost || 0
        })

        chat.run_id = run.run_id
        chat.run_status = run.status
        await this.$storex.chats.reloadChat(chat)
        await this.loadChatRun({ force: true })
        this.notifyRun(
          `Long-running task started (${String(run.run_id).slice(0, 8)}…)`,
          'success'
        )
        return true
      } catch (error) {
        const message = this.runErrorMessage(error)
        this.runError = message
        this.notifyRun(`Could not start the long-running task: ${message}`, 'error')
        return false
      } finally {
        this.runBusy = false
      }
    },
    async onRunStart() {
      const chat = this.theChat
      if (!chat || this.runBusy) return false
      if (!chat.run_id) return await this.startAgentRun()

      this.runBusy = true
      this.runError = ''
      try {
        const run = await this.$storex.orchestration.startRun({
          runId: chat.run_id,
          chat
        })
        chat.run_status = run?.status || chat.run_status
        await this.$storex.chats.reloadChat(chat)
        await this.loadChatRun({ force: true })
        this.notifyRun('Long-running task started', 'success')
        return true
      } catch (error) {
        const message = this.runErrorMessage(error)
        this.runError = message
        this.notifyRun(`Could not start the long-running task: ${message}`, 'error')
        return false
      } finally {
        this.runBusy = false
      }
    },
    async onRunPause() {
      const chat = this.theChat
      if (!chat?.run_id || this.runBusy) return
      this.runBusy = true
      this.runError = ''
      try {
        const run = await this.$storex.orchestration.pauseRun({
          runId: chat.run_id,
          chat,
          reason: 'Paused from chat'
        })
        chat.run_status = run?.status || chat.run_status
        await this.$storex.chats.reloadChat(chat)
        this.notifyRun('Long-running task paused', 'warning')
      } catch (error) {
        const message = this.runErrorMessage(error)
        this.runError = message
        this.notifyRun(`Could not pause the long-running task: ${message}`, 'error')
      } finally {
        this.runBusy = false
      }
    },
    async onRunStop() {
      const chat = this.theChat
      if (!chat?.run_id || this.runBusy) {
        this.confirmStopRun = false
        return
      }
      this.runBusy = true
      this.runError = ''
      try {
        const run = await this.$storex.orchestration.stopRun({
          runId: chat.run_id,
          chat,
          reason: 'Stopped from chat'
        })
        chat.run_status = run?.status || chat.run_status
        await this.$storex.chats.reloadChat(chat)
        this.notifyRun('Long-running task stopped', 'warning')
      } catch (error) {
        const message = this.runErrorMessage(error)
        this.runError = message
        this.notifyRun(`Could not stop the long-running task: ${message}`, 'error')
      } finally {
        this.runBusy = false
        this.confirmStopRun = false
      }
    },
    async setProjectContext() {
      this.projectContext = await this.$service.project.loadProjectContext(this.$project)
    },
    async reloadChat() {
      if (!this.theChat) return
      this.$chats.reloadChat(this.theChat)
    },
    async setChatProject(project) {
      if (!this.theChat) return
      this.targetProject = project
      this.theChat.project_id = project.project_id
      await this.saveChatInfo(this.theChat)
    },
    async saveChatInfo(chat) {
      this.editName = false
      chat.auto_initialize = false
      return this.$chats.saveChatInfo(chat || this.theChat)
    },
    async confirmDeleteChat() {
      const chat = this.theChat
      const parent = this.parentChat
      this.confirmDelete = false
      if (!chat) return

      await this.$chats.deleteChat(chat)

      if (parent) {
        await this.$chats.setActiveChat(parent)
        this.$emit('chat', parent)
      } else {
        this.navigateToChats()
      }
    },
    resetConfirmDelete() {
      this.confirmDelete = false
    },
    onBack() {
      const parent = this.parentChat
      if (parent) {
        this.activeChatId = parent.id
        this.$chats.setActiveChat(parent)
        this.$emit('chat', parent)
      } else {
        this.closeChat()
      }
    },
    // Leaves the current chat. On mobile a chat IS a route (see
    // QuickChatView), so clearing the store is not enough: the URL must
    // change, otherwise the reader stays on the same screen and the header
    // "back" arrow looks dead.
    closeChat() {
      this.activeChatId = null
      this.$chats.setActiveChat(null)
      this.navigateToChats()
    },
    toggleMobileSidebar() {
      this.showMobileSidebar = !this.showMobileSidebar
    },
    closeMobileSidebar() {
      this.showMobileSidebar = false
    },
    onSidebarDeleteChat(chat) {
      if (!chat) return
      this.confirmDeleteSubtask = chat
    },
    onSidebarRemoveAttachment(ix) {
      this.theChat.attachments.splice(ix, 1)
      this.saveChatInfo()
    },
    async confirmDeleteSubtaskChat() {
      const chat = this.confirmDeleteSubtask
      this.confirmDeleteSubtask = null
      if (!chat) return

      await this.$chats.deleteChat(chat)

      if (this.theChat?.id === chat.id) {
        const parent = this.$chats.chats[chat.parent_id] || this.rootChat
        if (parent) {
          this.$ui.isMobile && await this.$chats.setActiveChat(parent)
          this.$emit('chat', parent)
        }
      }

      await this.loadHierarchy()
    },
    async removeFileFromContext() {
      const chat = this.theChat
      if (!chat || !this.showFile) return
      chat.profiles = (chat.profiles || []).filter(f => f !== this.showFile)
      this.onRemoveFile(this.showFile)
      await this.reloadChat(chat)
      this.showFile = null
    },
    async addFileToContext() {
      if (!this.addFile) return
      this.onAddFile(this.addFile)
      await this.saveChatInfo(this.theChat)
      await this.reloadChat(this.theChat)
      this.showFile = null
      this.addFile = null
    },
    async onAddFile(file) {
      const chat = this.theChat
      if (!chat || !file) return
      if ((chat.file_list || []).includes(file)) return
      chat.file_list = [...(chat.file_list || []), file]
      this.addNewFile = null
      await this.saveChatInfo(chat)
    },
    async onRemoveFile(file) {
      const chat = this.theChat
      if (!chat) return
      chat.file_list = (chat.file_list || []).filter(f => f !== file)
      this.addNewFile = null
      await this.saveChatInfo(chat)
    },
    navigateToChats() {
      const board = this.kanban?.title || this.theChat?.board
      this.$emit('chats', board)

      // Desktop (dockview): the chat lives in a panel, so switching the active
      // tab is enough — the host opens the board.
      if (this.$ui.isDesktopMode) {
        if (this.$ui.activeTab !== 'tasks') this.$ui.setActiveTab('tasks')
        return
      }

      // Mobile / single mode: go back in history so the user lands where the
      // chat was opened from (activity wall, board…). The old `activeTab`
      // check made this a no-op whenever the tab was already 'tasks', which is
      // exactly why the header back arrow stopped working on mobile.
      if (window.history.state?.back) {
        this.$router.back()
        return
      }

      // Deep link / page reload (no in-app history): chat list route.
      this.$storex.$navigation?.chats?.list?.()
    },
    onSidebarAddSubtask(parentChat) {
      if (!parentChat || this.isChannelChat) return
      this.createDirectSubtask(parentChat)
    },
    async onNewMessageSubtask({ chat, mode, message: { column, files, profiles, doc_id: subtaskMessageId } }) {
      if (!chat || this.isChannelChat) return
      const findChild = () => this.$chats.allChats.find(c => c.message_id === subtaskMessageId)

      if (!findChild()) {
        await this.createSubTask({
          parent: chat,
          name: 'New task',
          project_id: chat.project_id,
          parent_id: chat.parent_id,
          message_id: subtaskMessageId,
          file_list: files,
          profiles,
          mode,
          board: chat.board,
          column,
          activateChat: true,
          auto_initialize: true,
          child_index: this.childrenChats?.length,
          ignore_parent_knowledge: true,
          ignore_parent_files: true
        })
      }

      const child = findChild()
      if (child) {
        await this.loadHierarchy()
      }
    },
    async createDirectSubtask(parentChat) {
      if (this.isChannelChat) return
      parentChat = parentChat || this.theChat
      if (!parentChat) return

      await this.createSubTask({
        parent: parentChat,
        name: 'New task',
        mode: parentChat.mode,
        description: null,
        project_id: parentChat.project_id,
        parent_id: parentChat.id,
        message_id: null,
        file_list: [],
        profiles: [],
        activateChat: false,
        auto_initialize: true,
        child_index: this.childrenChats?.length,
        column: parentChat.column,
        ignore_parent_knowledge: true,
        ignore_parent_files: true
      })

      await this.loadHierarchy()
    },
    getSubTaskParentSummary() {
      let messages = this.messages
      if (!messages.length) return ''
      if (this.theChat?.mode === 'task') {
        messages = messages.reverse()
        const lastAI = messages.find(m => m.role === 'assistant')
        if (lastAI) return lastAI.content
      }
      return messages.reduce((acc, m) => acc + '' + m.content, '')
    },
    addNewTag() {
      const chat = this.theChat
      if (!chat) return
      chat.tags = [...new Set([...(chat.tags || []), this.newTag])]
      this.newTag = null
      this.saveChatInfo(chat)
    },
    onRemoveTag(tag) {
      const chat = this.theChat
      if (!chat) return
      chat.tags = (chat.tags || []).filter(t => t !== tag)
      this.saveChatInfo(chat)
    },
    toggleChatPinned() {
      const chat = this.theChat
      if (!chat) return
      chat.pinned = !chat.pinned
      this.saveChatInfo(chat)
    },
    toggleHistoryWall() {
      this.showHistoryWall = !this.showHistoryWall
    },
    onSelectSidebarChat(chat) {
      if (!chat) return
      this.activeChatId = chat.id
      this.closeMobileSidebar()
      if (this.$ui.isMobile) {
        this.$chats.setActiveChat(chat)
      } else {
        this.$chats.loadChat(chat)
      }
    },
    onSelectBreadcrumbChat(chat) {
      if (!chat) return
      this.activeChatId = chat.id
      this.$ui.isMobile && this.$chats.setActiveChat(chat)
      this.$emit('chat', chat)
      if (chat && !chat.messages?.length) {
        this.$chats.reloadChat(chat)
      }
    },
    handleSidebarAction(action) {
      const handlers = {
        'timeline': () => this.toggleHistoryWall(),
        'logs': () => this.showLogs = !this.showLogs,
        'new-subtask': () => this.createDirectSubtask(),
        'create-subtasks': () => this.showSubtasksModal = true,
        'link-chats': () => this.showChatSelector = true,
        'new-tag': () => this.newTag = '',
        'export': () => this.showExportChat = true,
        'dump': () => this.showDumpChat = true,
        'reload': () => this.reloadChat(),
        'save': () => this.saveChatInfo(),
        'settings': () => this.showTaskSettings = true
      }
      const handler = handlers[action.type]
      if (handler) handler(action)
    },
    collectHierarchy(chat, visited = new Set()) {
      if (!chat || visited.has(chat.id)) return []
      visited.add(chat.id)
      const children = this.getDirectChildren(chat.id)
      return [chat, ...children.flatMap(child => this.collectHierarchy(child, visited))]
    },
    getDirectChildren(chatId) {
      if (!chatId) return []
      return (this.$chats.chatChildren(chatId) || [])
        .filter(Boolean)
        .sort(this.sortChats)
    },
    sortChats(a, b) {
      const ai = a.child_index == null ? 999999 : a.child_index
      const bi = b.child_index == null ? 999999 : b.child_index
      if (ai !== bi) return ai - bi
      return String(a.name || '').localeCompare(String(b.name || ''))
    },
    async createSubTask({ 
          parent, 
          name, 
          mode, 
          description, 
          project_id, 
          parent_id,
          message_id,
          file_list,
          activateChat,
          child_index,
          column,
          profiles,
          model,
          ignore_parent_knowledge,
          ignore_parent_files,
          processTask,
          auto_initialize
       }) {
      const chat = await this.$chats.createNewChat({
        board: parent.board,
        name,
        mode,
        profiles: profiles || parent.profiles,
        model: model || parent.model,
        column: column || parent.column,
        parent_id: parent_id || parent.id,
        message_id,
        owner_project_id: parent.owner_project_id || parent.project_id,
        project_id: project_id || parent.project_id,
        messages: description ? [{ role: 'user', content: description }] : [],
        file_list,
        child_index,
        auto_initialize: auto_initialize ?? true,
        ignore_parent_knowledge,
        ignore_parent_files,
      })
      await this.$chats.saveChatInfo(chat)
      if (processTask) {
        this.$storex.projects.chatWithProject(chat)
      }
      if (activateChat) {
        this.activeChatId = chat.id
        await this.loadHierarchy()
      }
    },
    async createSubTasks() {
      if (this.showSubtasksModal) {
        this.$projects.createSubtasks({ chat: this.theChat, instructions: this.createTasksInstructions })
        this.showSubtasksModal = false
        await this.loadHierarchy()
      } else {
        this.showSubtasksModal = true
        this.createTasksInstructions = ''
      }
    },
    async onChatModeChanged(newMode) {
      const chat = this.theChat
      if (!chat || chat.mode === newMode) return

      // Agent mode means "long-running task": a run owns the root task budget,
      // so a subtask cannot start one. Refuse before persisting the mode.
      if (newMode === 'agent' && chat.parent_id) {
        this.notifyRun(
          'Agent mode needs a root task: move this task to the top level before starting its run.',
          'warning'
        )
        return
      }

      chat.mode = newMode
      await this.saveChatInfo(chat)

      if (newMode !== 'agent') return

      // Selecting agent mode starts the process. When the chat already has a
      // run, only start it again if it is in a startable state; a running run
      // is left untouched and a completed one just shows its status.
      if (chat.run_id) {
        const status = this.chatRun?.status || chat.run_status
        if (['queued', 'paused', 'stalled', 'stopped', 'failed'].includes(status)) {
          await this.onRunStart()
        }
        return
      }
      await this.startAgentRun()
    },
    onTemplateChanged(isTemplate) {
      if (!this.theChat) return
      this.theChat.is_template = isTemplate
      this.saveChatInfo(this.theChat)
    },
    onIgnoreParentKnowledgeChanged(shouldIgnore) {
      if (!this.theChat) return
      this.theChat.ignore_parent_knowledge = shouldIgnore
      this.saveChatInfo(this.theChat)
    },
    onIgnoreParentFilesChanged(shouldIgnore) {
      if (!this.theChat) return
      this.theChat.ignore_parent_files = shouldIgnore
      this.saveChatInfo(this.theChat)
    },
    onStatusChanged(newStatus) {
      if (!this.theChat) return
      this.theChat.status = newStatus
      this.saveChatInfo(this.theChat)
    },
    onCostChanged(estimationCost) {
      if (!this.theChat) return
      this.theChat.estimation_cost = estimationCost
      this.saveChatInfo(this.theChat)
    }
  }
}
</script>