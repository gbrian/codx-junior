<script setup>
import moment from 'moment'
import { v4 as uuidv4 } from 'uuid'
import AddFileDialog from '../components/chat/AddFileDialog.vue'
import Chat from '@/components/chat/Chat.vue'
import TaskSettings from '@/components/kanban/TaskSettings.vue'
import ChatSelector from '@/components/chat/ChatSelector.vue'
import ProjectDetailt from '@/components/ProjectDetailt.vue'
import ExportChat from '@/components/chat/ExportChat.vue'
import ChatHistoryViewer from '@/components/chat/ChatHistoryViewer.vue'
import ChatSidebar from '@/components/chat/ChatSidebar.vue'
import ChatViewHeader from '@/components/chat/ChatViewHeader.vue'
</script>

<template>
  <div class="flex h-full bg-base-300/80 overflow-hidden" v-if="workingChat">
    <!-- ─────────────────────────────────────────────────────────────
         SIDEBAR: Persistent left navigation with hierarchy
         ───────────────────────────────────────────────────────────── -->
    <ChatSidebar
      :rootChat="rootChat"
      :allChats="hierarchyChats"
      :selectedChatId="workingChat?.id"
      :workingChatMode="workingChat?.mode"
      :chatSearch="chatSearch"
      :isCompact="compactSidebar"
      :chatProfiles="chatProfiles"
      @select="onSelectSidebarChat"
      @add-subtask="onSidebarAddSubtask"
      @action="handleSidebarAction"
      @mode-changed="onChatModeChanged"
      @parent-flags-changed="onParentFlagsChanged"
      @toggle-compact="compactSidebar = !compactSidebar"
    />

    <!-- ─────────────────────────────────────────────────────────────
         MAIN CONTENT AREA: Header + Chat View
         ───────────────────────────────────────────────────────────── -->
    <div class="flex-1 flex flex-col min-w-0 md:p-2 gap-2">
      
      <!-- MINIMAL HEADER -->
      <ChatViewHeader
        :chat="workingChat"
        :rootChat="rootChat"
        :breadcrumb="breadcrumbChats"
        :messageCount="messageCount"
        :hiddenCount="hiddenCount"
        :showHidden="showHidden"
        :targetProject="targetProject"
        @update-name="saveChatInfo"
        @toggle-hidden="showHidden = !showHidden"
        @toggle-pinned="toggleChatPinned"
        @select-project="setChatProject"
        @show-settings="showTaskSettings = true"
        @show-export="showExportChat = true"
        @confirm-delete="confirmDelete = true"
        @show-add-tag="newTag = ''"
        @remove-tag="onRemoveTag"
      />

      <!-- CONTENT AREA: History Wall OR Chat View -->
      <div class="flex-1 min-h-0 rounded-lg bg-base-300">
        <!-- History Wall View (Full Screen) -->
        <ChatHistoryViewer
          v-if="showHistoryWall"
          :history="workingChat.history || []"
          :currentDescription="computedChatDescription"
        />

        <!-- Normal Chat View -->
        <Chat 
          v-else
          :chat="workingChat" 
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

    <modal v-if="showSubtaskModal">
      <div class="flex flex-col gap-4 p-4 w-96">
        <h3 class="font-bold text-lg">Create New Subtask</h3>
        <div class="text-sm text-base-content/70">
          Parent: <span class="font-semibold">{{ subtaskParentContext?.name || 'Unknown' }}</span>
        </div>
        <input v-model="subtaskName" type="text" class="input input-bordered" placeholder="Subtask Name" />
        <div class="form-control">
          <label class="label"><span class="label-text">Select Subtask Mode</span></label>
          <select class="select select-bordered" v-model="subtaskMode">
            <option value="task" selected>Task</option>
            <option value="chat">Chat</option>
            <option value="topic">Topic</option>
            <option value="prview">PR View</option>
            <option value="browser">Browser</option>
            <option value="slides">Slides</option>
          </select>
        </div>
        <textarea v-model="subtaskDescription" class="textarea textarea-bordered" rows="3"></textarea>
        <ProjectDetailt v-model="subtaskProject" :options="{ showFolders: false, showIcon: true, showSelector: true }" />
        <div class="flex gap-2 justify-end">
          <button class="btn btn-error" @click="cancelSubtask">Cancel</button>
          <button class="btn btn-primary" @click="onCreateSubtask">Create</button>
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
      <TaskSettings :taskData="workingChat" @close="showTaskSettings = false" />
    </modal>

    <modal close="true" @close="showExportChat = false" v-if="showExportChat">
      <ExportChat :chat="workingChat" @close="showExportChat = false" />
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
      newTag: null,
      showSubtaskModal: false,
      showSubtasksModal: false,
      showTaskSettings: false,
      subtaskProfiles: [],
      subtaskName: '',
      subtaskDescription: '',
      subtaskMode: 'task',
      subtaskFiles: [],
      subtaskProject: null,
      subtaskParentId: null,
      subtaskParentContext: null,
      subtaskMessageId: null,
      subtaskColumn: '',
      showAddProfile: false,
      createTasksInstructions: '',
      projectContext: null,
      showChatSelector: false,
      showExportChat: false,
      chatSearch: null,
      targetProject: null,
      showHistoryWall: false,
      compactSidebar: true,
      chatProfiles: []
    }
  },
  created() {
    this.init()
  },
  computed: {
    theChat() {
      const chatId = this.chat?.id || this.params?.params?.chat?.id
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
    workingChat() {
      return this.theChat || null
    },
    hierarchyChats() {
      return this.collectHierarchy(this.rootChat)
    },
    breadcrumbChats() {
      const breadcrumb = []
      let current = this.workingChat?.parent_id ? this.$chats.chats[this.workingChat.parent_id] : null
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
      return this.workingChat?.mode === 'prview'
    },
    hiddenCount() {
      return (this.workingChat?.messages || []).filter(m => m.hide).length
    },
    messageCount() {
      return (this.workingChat?.messages || []).length
    },
    messages() {
      return (this.workingChat?.messages || []).filter(m => !m.hide || this.showHidden)
    },
    formattedChatUpdatedDate() {
      const updatedAt = this.workingChat?.updated_at
      if (!updatedAt) return ''
      return moment(updatedAt).isAfter(moment().subtract(7, 'days'))
        ? moment(updatedAt).fromNow()
        : moment(updatedAt).format('YYYY-MM-DD')
    },
    childrenChats() {
      return this.getDirectChildren(this.workingChat?.id)
    },
    parentChat() {
      const id = this.workingChat?.parent_id
      if (!id) return null
      return this.$chats.chats[id] || null
    },
    computedChatName() {
      return this.workingChat?.name || this.theChat?.name || 'New Task'
    },
    computedChatDescription() {
      const chat = this.workingChat || this.theChat
      if (!chat) return ''
      if (chat.message_id) {
        const parent = this.$chats.chats[chat.parent_id]
        const message = (parent?.messages || []).find(m => m.doc_id === chat.message_id)
        return message?.content || ''
      }
      return chat.description
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
        this.loadHierarchy()
        this.loadChatProfiles()
      }
    },
    workingChat(newVal) {
      if (newVal) {
        this.targetProject = this.$projects.allProjectsById[newVal.project_id] || this.chatProject
        this.subtaskProject = this.targetProject
        if (newVal.parent_id && !this.$chats.chats[newVal.parent_id]) {
          this.$chats.ensureChatRoot(newVal)
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
      if (!this.workingChat) return
      try {
        this.chatProfiles = await this.$chats.getChatProfiles(this.workingChat)
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
      if (!this.workingChat) return
      this.$chats.reloadChat(this.workingChat)
    },
    async setChatProject(project) {
      if (!this.workingChat) return
      this.targetProject = project
      this.workingChat.project_id = project.project_id
      await this.saveChatInfo(this.workingChat)
    },
    async saveChatInfo(chat) {
      this.editName = false
      return this.$chats.saveChatInfo(chat || this.workingChat)
    },
    async confirmDeleteChat() {
      const chat = this.workingChat
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
    async removeFileFromContext() {
      const chat = this.workingChat
      if (!chat || !this.showFile) return
      chat.profiles = (chat.profiles || []).filter(f => f !== this.showFile)
      this.onRemoveFile(this.showFile)
      await this.reloadChat(chat)
      this.showFile = null
    },
    async addFileToContext() {
      if (!this.addFile) return
      this.onAddFile(this.addFile)
      await this.saveChatInfo(this.workingChat)
      await this.reloadChat(this.workingChat)
      this.showFile = null
      this.addFile = null
    },
    async onAddFile(file) {
      const chat = this.workingChat
      if (!chat || !file) return
      if ((chat.file_list || []).includes(file)) return
      chat.file_list = [...(chat.file_list || []), file]
      this.addNewFile = null
      await this.saveChatInfo(chat)
    },
    async onRemoveFile(file) {
      const chat = this.workingChat
      if (!chat) return
      chat.file_list = (chat.file_list || []).filter(f => f !== file)
      this.addNewFile = null
      await this.saveChatInfo(chat)
    },
    navigateToChats() {
      if (this.$ui.activeTab !== 'tasks') this.$ui.setActiveTab('tasks')
      this.$emit('chats', this.kanban?.title || this.workingChat?.board || this.theChat?.board)
    },
    onSidebarAddSubtask(parentChat) {
      if (!parentChat) return
      this.newSubChat(parentChat)
    },
    async onNewMessageSubtask({ chat, mode, message: { column, files, profiles, doc_id: subtaskMessageId } }) {
      if (!chat) return
      const findChild = () => this.$chats.allChats.find(c => c.message_id === subtaskMessageId)

      if (!findChild()) {
        await this.createSubTask({
          parent: chat,
          name: `${subtaskMessageId} - thread`,
          project_id: chat.project_id,
          parent_id: chat.parent_id,
          message_id: subtaskMessageId,
          file_list: files,
          profiles,
          mode,
          board: chat.board,
          column,
          activateChat: true,
          child_index: this.childrenChats?.length
        })
      }

      const child = findChild()
      if (child) this.$chats.setActiveChat(child)
    },
    newSubChat(parentChat) {
      const chat = parentChat || this.workingChat
      if (!chat) return
      this.subtaskParentId = chat.id
      this.subtaskParentContext = chat
      this.subtaskMessageId = null
      this.subtaskName = null
      this.subtaskDescription = null
      this.subtaskFiles = []
      this.subtaskProfiles = []
      this.subtaskMode = chat.mode
      this.subtaskColumn = chat.column
      this.subtaskProject = this.targetProject
      this.showSubtaskModal = true
    },
    getSubTaskParentSummary() {
      let messages = this.messages
      if (!messages.length) return ''
      if (this.workingChat?.mode === 'task') {
        messages = messages.reverse()
        const lastAI = messages.find(m => m.role === 'assistant')
        if (lastAI) return lastAI.content
      }
      return messages.reduce((acc, m) => acc + '' + m.content, '')
    },
    async onCreateSubtask() {
      if (!this.subtaskName?.trim()) return
      if (this.subtaskDescription) {
        const parentContent = this.getSubTaskParentSummary()
        this.subtaskDescription = `${parentContent}

${this.subtaskDescription}`
      }
      const parent = this.subtaskParentContext || this.workingChat || this.theChat
      if (!parent) return

      await this.createSubTask({
        parent,
        name: this.subtaskName,
        description: this.subtaskDescription,
        project_id: this.subtaskProject?.project_id || this.targetProject?.project_id,
        parent_id: this.subtaskParentId || parent.id,
        message_id: this.subtaskMessageId,
        file_list: this.subtaskFiles,
        profiles: this.subtaskProfiles,
        mode: this.subtaskMode,
        board: parent.board,
        column: this.subtaskColumn,
        activateChat: true,
        child_index: this.childrenChats.length
      })
      this.resetSubtaskModal()
    },
    cancelSubtask() {
      this.resetSubtaskModal()
    },
    resetSubtaskModal() {
      this.showSubtaskModal = false
      this.subtaskName = ''
      this.subtaskDescription = ''
      this.subtaskMode = 'chat'
      this.subtaskFiles = []
      this.subtaskProfiles = []
      this.subtaskColumn = ''
      this.subtaskParentId = null
      this.subtaskParentContext = null
    },
    addNewTag() {
      const chat = this.workingChat
      if (!chat) return
      chat.tags = [...new Set([...(chat.tags || []), this.newTag])]
      this.newTag = null
      this.saveChatInfo(chat)
    },
    onRemoveTag(tag) {
      const chat = this.workingChat
      if (!chat) return
      chat.tags = (chat.tags || []).filter(t => t !== tag)
      this.saveChatInfo(chat)
    },
    toggleChatPinned() {
      const chat = this.workingChat
      if (!chat) return
      chat.pinned = !chat.pinned
      this.saveChatInfo(chat)
    },
    toggleHistoryWall() {
      this.showHistoryWall = !this.showHistoryWall
    },
    onSelectSidebarChat(chat) {
      if (!chat) return
      this.$chats.setActiveChat(chat)
      this.$emit('chat', chat)
      if (chat && !chat.messages?.length) {
        this.$chats.reloadChat(chat)
      }
    },
    handleSidebarAction(action) {
      const handlers = {
        'timeline': () => this.toggleHistoryWall(),
        'new-subtask': () => this.newSubChat(),
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
    async createSubTask({ parent, name, mode, description, project_id, parent_id, message_id, file_list, activateChat, child_index, column, profiles }) {
      const chat = await this.$chats.createNewChat({
        id: uuidv4(),
        board: parent.board,
        name,
        mode,
        profiles,
        column: column || parent.column,
        parent_id: parent_id || parent.id,
        message_id,
        owner_project_id: parent.owner_project_id || parent.project_id,
        project_id: project_id || parent.project_id,
        messages: description ? [{ role: 'user', content: description }] : [],
        file_list,
        child_index
      })
      await this.$chats.saveChatInfo(chat)
      if (description) {
        this.$storex.projects.chatWihProject(chat)
      }
      if (activateChat) {
        await this.$chats.setActiveChat(chat)
      }
    },
    async createSubTasks() {
      if (this.showSubtasksModal) {
        this.$projects.createSubtasks({ chat: this.theChat, instructions: this.createTasksInstructions })
        this.showSubtasksModal = false
      } else {
        this.showSubtasksModal = true
        this.createTasksInstructions = ''
      }
    },
    onChatModeChanged({ chat, mode }) {
      chat.mode = mode
      this.saveChatInfo(chat)
    },
    onParentFlagsChanged({ chat, flag, value }) {
      this.saveChatInfo(chat)
    }
  }
}
</script>