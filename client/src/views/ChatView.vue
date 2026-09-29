<script setup>
import moment from 'moment'
import AddFileDialog from '../components/chat/AddFileDialog.vue'
import Chat from '@/components/chat/Chat.vue'
import TaskSettings from '@/components/kanban/TaskSettings.vue'
import ChatSelector from '@/components/chat/ChatSelector.vue'
import ExportChat from '@/components/chat/ExportChat.vue'
import ChatHistoryViewer from '@/components/chat/ChatHistoryViewer.vue'
import ChatSidebar from '@/components/chat/ChatSidebar.vue'
import ChatViewHeader from '@/components/chat/ChatViewHeader.vue'
import ChatLogsPanel from '@/components/ChatLogsPanel.vue'
</script>

<template>
  <div class="flex h-full bg-base-300/80 overflow-hidden" v-if="theChat">
    <!-- ─────────────────────────────────────────────────────────────
         SIDEBAR: Persistent left navigation with hierarchy
         ───────────────────────────────────────────────────────────── -->
    <ChatSidebar
      :workingChat="theChat"
      :rootChat="rootChat"
      :allChats="hierarchyChats"
      :selectedChatId="theChat?.id"
      :workingChatMode="theChat?.mode"
      :chatSearch="chatSearch"
      :isCompact="compactSidebar"
      :chatProfiles="chatProfiles"
      :targetProject="targetProject"
      @select="onSelectSidebarChat"
      @add-subtask="onSidebarAddSubtask"
      @action="handleSidebarAction"
      @toggle-compact="compactSidebar = !compactSidebar"
      @delete-chat="onSidebarDeleteChat"
      @remove-attachment="onSidebarRemoveAttachment"
      @select-project="setChatProject"
    />

    <!-- ─────────────────────────────────────────────────────────────
         MAIN CONTENT AREA: Header + Chat View OR Logs View
         ───────────────────────────────────────────────────────────── -->
    <div class="flex-1 flex flex-col min-w-0 md:p-2 gap-2">
      
      <!-- MINIMAL HEADER -->
      <ChatViewHeader
        :chat="theChat"
        :rootChat="rootChat"
        :breadcrumb="breadcrumbChats"
        :messageCount="messageCount"
        :hiddenCount="hiddenCount"
        :showHidden="showHidden"
        :isSelectedChatChild="isSelectedChatChild"
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
      />

      <!-- CONTENT AREA: Logs View OR (History Wall OR Chat View) -->
      <div class="flex-1 min-h-0 rounded-lg bg-base-300">
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
        <Chat 
          v-else
          :chat="theChat" 
          :showHidden="showHidden" 
          :childrenChats="childrenChats"
          :filter="chatSearch" 
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

    <modal v-if="showTaskSettings">
      <TaskSettings :taskData="theChat" @close="showTaskSettings = false" />
    </modal>

    <modal close="true" @close="showExportChat = false" v-if="showExportChat">
      <ExportChat :chat="theChat" @close="showExportChat = false" />
    </modal>

    <modal close="true" @close="showChatSelector = false" v-if="showChatSelector">
      <ChatSelector />
    </modal>

    <add-file-dialog v-if="addNewFile" @open="onAddFile" @close="addNewFile = false" />
  </div>
</template>

<script>
export default {
  props: ['chatMode', 'chat', 'kanban', 'params'],
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
      chatSearch: null,
      targetProject: null,
      showHistoryWall: false,
      showLogs: false,
      compactSidebar: true,
      chatProfiles: [],
      activeChatId: null
    }
  },
  created() {
    this.init()
  },
  computed: {
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
        this.loadHierarchy()
        this.loadChatProfiles()
        if (newVal) {
          this.targetProject = this.$projects.allProjectsById[newVal.project_id] || this.chatProject
          if (newVal.parent_id && !this.$chats.chats[newVal.parent_id]) {
            this.$chats.ensureChatRoot(newVal)
          }
        }
      }
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
    },
    async loadHierarchy() {
      if (!this.theChat) return
      try {
        await this.$chats.loadChats()
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
      if (this.$ui.activeTab !== 'tasks') this.$ui.setActiveTab('tasks')
      this.$emit('chats', this.kanban?.title || this.theChat?.board || this.theChat?.board)
    },
    onSidebarAddSubtask(parentChat) {
      if (!parentChat) return
      this.createDirectSubtask(parentChat)
    },
    async onNewMessageSubtask({ chat, mode, message: { column, files, profiles, doc_id: subtaskMessageId } }) {
      if (!chat) return
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
      this.$ui.isMobile && this.$chats.setActiveChat(chat)
      this.$emit('chat', chat)
      if (chat && !chat.messages?.length) {
        this.$chats.reloadChat(chat)
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
    onChatModeChanged(newMode) {
      if (!this.theChat) return
      this.theChat.mode = newMode
      this.saveChatInfo(this.theChat)
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
    }
  }
}
</script>