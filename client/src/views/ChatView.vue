<script setup>
import moment from 'moment'
import { v4 as uuidv4 } from 'uuid'
import AddFileDialog from '../components/chat/AddFileDialog.vue'
import Chat from '@/components/chat/Chat.vue'
import UserSelector from '@/components/chat/UserSelector.vue'
import TaskSettings from '@/components/kanban/TaskSettings.vue'
import ChatIcon from '@/components/chat/ChatIcon.vue'
import ChatSelector from '@/components/chat/ChatSelector.vue'
import ProjectDetailt from '@/components/ProjectDetailt.vue'
import ExportChat from '@/components/chat/ExportChat.vue'
import Markdown from '../components/Markdown.vue'
import Collapsible from '../components/Collapsible.vue'
</script>

<template>
  <div class="p-2 flex flex-col h-full bg-base-300/80 p-1" v-if="workingChat">
    <div class="grow flex gap-2 h-full justify-between">
      <div class="grow flex flex-col w-full min-w-0">

        <!-- ── HEADER ─────────────────────────────────────────────────────── -->
        <div class="flex flex-col gap-1 w-full" v-if="!chatMode">
          <div class="flex items-center gap-2 w-full">
            <div class="flex items-center gap-2 text-sm shrink-0">
              <span class="hover:underline cursor-pointer font-bold text-primary" @click="navigateToParent()">
                <i class="fa-brands fa-trello"></i>
                {{ kanban?.title || theChat.board }}
              </span>
              <template v-if="parentChat">
                <span class="text-base-content/40">/</span>
                <span class="hover:underline cursor-pointer font-bold text-secondary truncate max-w-[120px]"
                  :title="parentChat.name" @click="navigateToParent(parentChat)">
                  {{ parentChat.name }}
                </span>
              </template>
            </div>
            <div class="grow"></div>
            <div class="flex items-center gap-1 shrink-0">
              <div class="flex input input-sm input-bordered items-center gap-1 w-36">
                <input v-model="chatSearch" class="bg-transparent w-full min-w-0" placeholder="Search..." />
                <span class="text-error cursor-pointer" @click="chatSearch = null" v-if="chatSearch">
                  <i class="fa-regular fa-circle-xmark"></i>
                </span>
                <span v-else><i class="fa-solid fa-magnifying-glass"></i></span>
              </div>
              <button class="btn btn-sm" @click="showHidden = !showHidden">
                <div class="flex items-center gap-1 tooltip" data-tip="Archived messages"
                  :class="showHidden ? 'text-warning' : ''">
                  <i class="fa-regular fa-message"></i>
                  {{ messageCount - hiddenCount }}
                  <span v-if="hiddenCount"><i class="fa-regular fa-eye-slash"></i> {{ hiddenCount }}</span>
                </div>
              </button>
              <div class="dropdown dropdown-end">
                <div tabindex="0" role="button" class="btn btn-sm"><ChatIcon :mode="workingChat.mode" /></div>
                <ul tabindex="0" class="dropdown-content menu bg-base-100 rounded-box z-[1] w-52 p-2 shadow">
                  <li @click="setChatMode('chat')"><a><ChatIcon mode="chat" /> Conversation</a></li>
                  <li @click="setChatMode('task')"><a><ChatIcon mode="task" /> Document</a></li>
                  <li @click="setChatMode('topic')"><a><ChatIcon mode="topic" /> Group chat</a></li>
                  <li @click="setChatMode('vibe')"><a><ChatIcon mode="vibe" /> Vibe</a></li>
                  <li @click="setChatMode('prview')"><a><ChatIcon mode="prview" /> Changes review</a></li>
                  <li @click="setChatMode('browser')"><a><ChatIcon mode="browser" /> Browser</a></li>
                </ul>
              </div>
              <div class="dropdown dropdown-end dropdown-bottom">
                <div tabindex="0" class="btn btn-sm"><i class="fa-solid fa-bars"></i></div>
                <ul tabindex="0" class="dropdown-content menu bg-base-300 border rounded-box z-[1] p-2 w-64 shadow">
                  <li @click="newSubChat()"><a><i class="fa-solid fa-plus"></i> New sub task</a></li>
                  <li @click="createSubTasks()"><a><i class="fa-solid fa-wand-magic-sparkles"></i> Create sub tasks</a></li>
                  <li @click="showExportChat = true"><a><i class="fa-solid fa-file-arrow-down"></i> Export</a></li>
                  <li @click="showChatSelector = true"><a><i class="fa-solid fa-link"></i> Link chats</a></li>
                  <li @click="newTag = true"><a><i class="fa-solid fa-plus"></i> New #tag</a></li>
                  <hr>
                  <li @click="reloadChat(workingChat)"><a><i class="fa-solid fa-recycle"></i> Load</a></li>
                  <li @click="saveChat"><a><i class="fa-solid fa-floppy-disk"></i> Save</a></li>
                  <hr>
                  <li @click="showTaskSettings = true"><a><i class="fa-solid fa-gear"></i> Settings</a></li>
                </ul>
              </div>
            </div>
          </div>

          <div class="flex items-start gap-2 w-full min-w-0">
            <div class="flex items-center gap-1 shrink-0">
              <ProjectDetailt v-model="targetProject" :iconify="true"
                :options="{ showFolders: false, showIcon: true, showSelector: true }"
                @select="setChatProject" />
              <UserSelector class="dropdown-bottom" :allUsers="true" @user-changed="onAddProfile($event)" />
            </div>
            <div class="flex-1 min-w-0 flex flex-col gap-0.5">
              <input v-if="editName" type="text" class="input input-sm input-bordered w-full"
                @keydown.enter.stop="saveChatInfo(theChat)" @keydown.esc="editName = false" v-model="theChat.name" />
              <template v-else>
                <div class="flex items-center gap-2 min-w-0 w-full">
                  <span class="click tooltip shrink-0" @click.stop="toggleChatPinned" data-tip="Bookmark">
                    <i class="text-warning fa-solid fa-bookmark" v-if="theChat.pinned"></i>
                    <i class="fa-regular fa-bookmark" v-else></i>
                  </span>
                  <div class="flex-1 min-w-0">
                    <span class="font-bold text-base truncate block min-w-0 cursor-pointer"
                      :title="computedChatName" @dblclick="editName = true" @click="showChildChat = null">
                      {{ computedChatName }}
                    </span>
                    <div class="flex flex-wrap gap-2 text-xs text-base-content/50 mt-0.5">
                      <span v-if="showTaskProjectName">
                        <i class="fa-solid fa-house text-xs"></i> {{ ownerProject?.title }}
                      </span>
                      <span>[{{ formattedChatUpdatedDate }}]</span>
                      <span v-if="computedChatDescription" class="cursor-pointer hover:underline"
                        :class="showDescription ? 'text-error/70' : 'text-info'"
                        @click.stop="showDescription = !showDescription">
                        [{{ showDescription ? 'close' : 'description' }}]
                      </span>
                    </div>
                  </div>
                </div>
                <div class="text-xs mt-1" v-if="showDescription">
                  <markdown class="prose-sm" :text="computedChatDescription || '-- no description yet --'" />
                </div>
              </template>
            </div>
          </div>

          <div class="flex gap-2 flex-wrap" v-if="theChat.tags?.length">
            <div class="text-xs font-bold" v-for="tag in theChat.tags" :key="tag">#{{ tag }}</div>
          </div>

          <!-- ── SUBTASKS: Collapsible kanban-style progress card strip ──── -->
          <template v-if="childrenChats.length">
            <Collapsible :defaultOpen="subtasksOpen" @update:modelValue="subtasksOpen = $event">
              <!-- Icon -->
              <template #icon>
                <i class="fa-solid fa-layer-group text-xs opacity-60"></i>
              </template>

              <!-- Title -->
              <template #title>
                <span>Subtasks</span>
                <span class="text-xs font-normal text-base-content/50 ml-1">({{ childrenChats.length }})</span>
              </template>

              <!-- Summary: column pills shown when collapsed -->
              <template #summary>
              </template>

              <!-- Actions: add button always visible -->
              <template #actions>
                <button
                  class="btn btn-xs btn-ghost text-base-content/50 hover:text-primary"
                  @click.stop="newSubChat()"
                >
                  <i class="fa-solid fa-plus text-xs"></i>
                </button>
              </template>

              <!-- Body: scrollable card row -->
              <div class="flex gap-2 overflow-x-auto p-2 scrollbar-thin">
                <!-- Parent card -->
                <div
                  class="flex flex-col gap-1 p-2 rounded-lg border-2 cursor-pointer shrink-0 w-36 transition-all"
                  :class="!showChildChat
                    ? 'border-primary bg-primary/10'
                    : 'border-base-content/10 bg-base-200 hover:border-base-content/30'"
                  @click="selectChildChat(null)"
                  v-if="showChildChat"
                >
                  <div class="flex items-center gap-1">
                    <img class="w-4 h-4 rounded-full"
                      :src="($projects.allProjectsById[theChat.project_id] || $project).project_icon" />
                    <span class="text-xs font-bold truncate flex-1">Parent</span>
                    <i class="fa-solid fa-house text-xs text-base-content/30"></i>
                  </div>
                  <div class="text-xs truncate text-base-content/70 leading-tight">{{ computedChatName }}</div>
                  <div class="text-xs text-base-content/40">
                    {{ (theChat.messages || []).length }} msgs
                  </div>
                </div>

                <!-- Subtask cards -->
                <div
                  v-for="(childChat, idx) in childrenChats"
                  :key="childChat.id"
                  class="flex flex-col gap-1 p-2 rounded-lg border-2 cursor-pointer shrink-0 w-36 transition-all"
                  :class="showChildChat?.id === childChat.id
                    ? 'border-warning bg-warning/10'
                    : 'border-base-content/10 bg-base-200 hover:border-base-content/30'"
                  @click="selectChildChat(childChat)"
                >
                  <div class="flex items-center gap-1">
                    <span class="text-xs text-base-content/40 font-mono w-4">{{ idx + 1 }}</span>
                    <ChatIcon :mode="childChat.mode" class="text-xs opacity-70" />
                    <img class="w-3 h-3 rounded-full ml-auto"
                      :src="($projects.allProjectsById[childChat.project_id] || $project).project_icon" />
                  </div>
                  <div class="text-xs truncate text-base-content/80 font-medium leading-tight" :title="childChat.name">
                    {{ childChat.name }}
                  </div>
                  <div class="flex items-center justify-between">
                    <span class="text-xs text-base-content/40">
                      {{ (childChat.messages || []).length }} msgs
                    </span>
                    <span class="badge badge-xs"
                      :class="childChat.column === 'Done' ? 'badge-success' : childChat.column === 'In Progress' ? 'badge-warning' : 'badge-ghost'">
                      {{ childChat.column || '?' }}
                    </span>
                  </div>
                </div>

                <!-- Add card -->
                <div
                  class="flex flex-col items-center justify-center gap-1 p-2 rounded-lg border-2 border-dashed border-base-content/20 cursor-pointer shrink-0 w-20 hover:border-primary hover:text-primary transition-all text-base-content/40"
                  @click="newSubChat()"
                >
                  <i class="fa-solid fa-plus text-lg"></i>
                  <span class="text-xs">Add</span>
                </div>
              </div>
            </Collapsible>
          </template>

          <!-- No children: simple add button -->
          <div v-else class="flex">
            <button class="btn btn-xs btn-ghost gap-1 text-base-content/40 hover:text-primary" @click="newSubChat()">
              <i class="fa-solid fa-plus text-xs"></i>
              <span class="text-xs">Add subtask</span>
            </button>
          </div>
        </div>
        <!-- ── END HEADER ─────────────────────────────────────────────────── -->

        <!-- Active subtask breadcrumb -->
        <div class="flex items-center gap-1 text-xs text-base-content/50 mt-1" v-if="showChildChat">
          <button class="hover:underline hover:text-base-content" @click="selectChildChat(null)">
            {{ computedChatName }}
          </button>
          <i class="fa-solid fa-chevron-right"></i>
          <span class="text-warning font-semibold">{{ showChildChat.name }}</span>
        </div>

        <Chat class="mt-2" :chat="workingChat" :showHidden="showHidden" :childrenChats="childrenChats"
          :filter="chatSearch" @refresh-chat="reloadChat(workingChat)" @remove-file="onRemoveFile"
          @delete="confirmDelete = true" @subtask="onNewMessageSubtask" />

        <!-- MODALS -->
        <modal v-if="confirmDelete">
          <div>
            <h3 class="font-bold text-lg">Confirm Delete</h3>
            <p class="text-error font-bold">Are you sure you want to delete this chat?</p>
            <div class="text-xl p-1">{{ computedChatName }}</div>
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
          <div class="flex flex-col gap-2">
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
          <div class="flex flex-col gap-4 p-4">
            <h3 class="font-bold text-lg">Create New Subtask</h3>
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
            <textarea v-model="createTasksInstructions" class="grow textarea textarea-bordered" rows="3"></textarea>
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
      </div>

      <modal close="true" @close="showChatSelector = false" v-if="showChatSelector">
        <ChatSelector />
      </modal>
      <add-file-dialog v-if="addNewFile" @open="onAddFile" @close="addNewFile = false" />
    </div>
  </div>
</template>

<script>
export default {
  components: { Markdown, Collapsible },
  props: ['chatMode', 'chat', 'kanban', 'params'],
  data() {
    return {
      showFile: null,
      addFile: null,
      showChatsTree: false,
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
      subtaskMessageId: null,
      showAddProfile: false,
      createTasksInstructions: '',
      chatProfiles: [],
      showDescription: false,
      projectContext: null,
      showChatSelector: false,
      showChildChat: null,
      showExportChat: false,
      chatSearch: null,
      ownerProject: null,
      targetProject: null,
      // Track collapsible open state so summary pills update correctly
      subtasksOpen: false
    }
  },
  created() { this.init() },
  computed: {
    theChat() {
      return this.$chats.chats[this.chat?.id || this.params?.params.chat?.id]
    },
    isThread() { return !!this.theChat.message_id },
    isPRView() { return this.workingChat?.mode === 'prview' },
    aiModels() { return this.$projects.ai.models },
    showTaskProjectName() {
      return this.ownerProject && this.ownerProject.project_id !== this.$project.project_id
    },
    hiddenCount() { return this.workingChat.messages?.filter(m => m.hide).length },
    messageCount() { return this.workingChat.messages?.length },
    messages() { return this.theChat.messages.filter(m => !m.hide || this.showHidden) },
    formattedChatUpdatedDate() {
      const updatedAt = this.theChat.updated_at
      return moment(updatedAt).isAfter(moment().subtract(7, 'days'))
        ? moment(updatedAt).fromNow()
        : moment(updatedAt).format('YYYY-MM-DD')
    },
    childrenChats() {
      return this.$chats.allChats
        .filter(c => c.parent_id === this.theChat.id)
        .sort((a, b) => a.name > b.name ? 1 : -1)
    },
    // Group subtasks by column for the summary pills
    subtasksByColumn() {
      return this.childrenChats.reduce((acc, c) => {
        const col = c.column || 'Unknown'
        acc[col] = (acc[col] || 0) + 1
        return acc
      }, {})
    },
    parentChat() { return this.$chats.chats[this.theChat?.parent_id] },
    images() {
      return (this.workingChat.messages || [])
        .map(m => m.images || []).reduce((a, b) => a.concat(b), [])
        .map(i => { try { return i ? JSON.parse(i) : null } catch {} return null })
        .filter(i => !!i)
    },
    workingChat() {
      return this.$chats.chats[this.showChildChat?.id] || this.theChat
    },
    computedChatName() { return this.theChat.name || 'New Task' },
    computedChatDescription() {
      if (this.theChat.message_id) {
        const message = this.$storex.projects.allChats
          .find(c => c.id === this.theChat.parent_id)
          ?.messages.find(m => m.doc_id === this.theChat.message_id)
        return message?.content || '-- no description yet --'
      }
      return this.theChat.description
    }
  },
  watch: {
    chat(newVal, oldVal) {
      if (oldVal && newVal && oldVal.project_id !== newVal.project_id) this.init()
      this.showChildChat = null
    }
  },
  methods: {
    async init() {
      await this.$service.chat.findChat(this.chat || this.params?.params.chat)
      if (!this.theChat) throw new Error(`Chat not loaded`)
      this.setTaskProject()
      this.setProjectContext()
      await Promise.all(this.childrenChats.map(chat => this.$chats.loadChat(chat)))
      this.chatProfiles = await this.$storex.api.project(this.ownerProject)
        .then(p => p.profiles.list())
        .then(profiles => profiles.filter(p => this.theChat.profiles.includes(p.name)))
      if (this.isPRView) await this.$projects.loadBranches()
      this.showDescription = this.isThread
    },
    setTaskProject() {
      this.ownerProject = this.$projects.allProjectsById[this.theChat.owner_project_id]
      this.targetProject = this.$projects.allProjectsById[this.theChat.project_id] || this.$project
      this.subtaskProject = this.targetProject
    },
    async setProjectContext() {
      this.projectContext = await this.$service.project.loadProjectContext(this.$project)
    },
    async reloadChat() { this.$chats.reloadChat(this.workingChat) },
    async setChatProject(project) {
      this.targetProject = project
      this.workingChat.project_id = project.project_id
      await this.saveChat(this.workingChat)
    },
    async saveChat(chat) {
      this.editName = false
      return this.$chats.saveChat(chat || this.workingChat)
    },
    saveChatInfo(chat) { this.editName = false; this.$chats.saveChatInfo(chat) },
    async confirmDeleteChat() {
      this.confirmDelete = false
      await this.$chats.deleteChat(this.theChat)
      if (this.parentChat) this.$chats.setActiveChat(this.parentChat)
      else this.navigateToChats()
    },
    resetConfirmDelete() { this.confirmDelete = false },
    async removeFileFromContext() {
      this.theChat.profiles = this.theChat.profiles?.filter(f => f !== this.showFile)
      this.onRemoveFile(this.showFile)
      await this.reloadChat(this.theChat)
      this.showFile = null
    },
    async addFileToContext() {
      this.onAddFile(this.addFile)
      await this.saveChat(this.theChat)
      await this.reloadChat(this.theChat)
      this.showFile = null
      this.addFile = null
    },
    async onAddFile(file) {
      if (this.theChat.file_list?.includes(file)) return
      this.theChat.file_list = [...(this.theChat.file_list || []), file]
      this.addNewFile = null
      await this.saveChat(this.theChat)
    },
    async onRemoveFile(file) {
      this.workingChat.file_list = (this.workingChat.file_list || []).filter(f => f !== file)
      this.addNewFile = null
      await this.saveChat(this.theChat)
    },
    navigateToChats() {
      if (this.$ui.activeTab !== 'tasks') this.$ui.setActiveTab('tasks')
      this.$emit('chats', this.kanban?.title || this.theChat.board)
    },
    newSubChat(message) {
      this.subtaskParentId = this.theChat.id
      this.subtaskMessageId = message?.doc_id
      this.subtaskName = null
      this.subtaskDescription = null
      this.subtaskFiles = []
      this.subtaskProfiles = []
      this.subtaskMode = this.theChat.mode
      this.subtaskColumn = this.theChat.column
      this.subtaskProject = this.targetProject
      this.showSubtaskModal = true
    },
    async onNewMessageSubtask({ chat, mode, message: { column, files, profiles, doc_id: subtaskMessageId } }) {
      const findChild = () => this.$projects.allChats.find(c => c.message_id === subtaskMessageId)
      if (!findChild()) {
        await this.createSubTask({
          parent: chat, name: `${subtaskMessageId} - thread`,
          project_id: chat.project_id, parent_id: chat.parent_id,
          message_id: subtaskMessageId, file_list: files, profiles,
          mode, board: chat.board, column, activateChat: true,
          child_index: this.childrenChats?.length
        })
      }
      this.$chats.setActiveChat(findChild())
    },
    getSubTaskParentSummary() {
      let { messages } = this
      if (!messages.length) return ""
      if (this.theChat.mode === 'task') {
        messages = messages.reverse()
        const lastAI = messages.find(m => m.role === 'assistant')
        if (lastAI) return lastAI.content
      }
      return messages.reduce((acc, m) => acc + "\n" + m.content, "")
    },
    async onCreateSubtask() {
      if (!this.subtaskName.trim()) return
      if (this.subtaskDescription) {
        const parentContent = this.getSubTaskParentSummary()
        this.subtaskDescription = `${parentContent}\n\n${this.subtaskDescription}`
      }
      await this.createSubTask({
        parent: this.theChat, name: this.subtaskName, description: this.subtaskDescription,
        project_id: this.subtaskProject?.project_id || this.targetProject?.project_id,
        parent_id: this.subtaskParentId, message_id: this.subtaskMessageId,
        file_list: this.subtaskFiles, profiles: this.subtaskProfiles,
        mode: this.subtaskMode, board: this.theChat.board,
        column: this.subtaskColumn, activateChat: true, child_index: this.childrenChats?.length
      })
      this.resetSubtaskModal()
    },
    cancelSubtask() { this.resetSubtaskModal() },
    resetSubtaskModal() {
      this.showSubtaskModal = false
      this.subtaskName = ''
      this.subtaskDescription = ''
      this.subtaskMode = 'chat'
      this.subtaskFiles = []
      this.subtaskProfiles = []
      this.subtaskColumn = ''
    },
    addNewTag() {
      this.theChat.tags = [...new Set([...this.theChat.tags || [], this.newTag])]
      this.newTag = null
      this.saveChat()
    },
    setChatMode(mode) { this.workingChat.mode = mode; this.saveChat() },
    navigateToParent(parentChat) {
      if (parentChat) this.$emit('chat', parentChat)
      else this.navigateToChats()
    },
    async onAddProfile() { this.showAddProfile = true },
    toggleChatPinned() { this.theChat.pinned = !this.theChat.pinned; this.saveChat() },
    selectChildChat(childChat) {
      this.showChildChat = childChat
      if (childChat && !childChat.messages?.length) this.$chats.reloadChat(childChat)
    },
    async createSubTask({ parent, name, mode, description, project_id, parent_id, message_id, file_list, activateChat, child_index, column, profiles }) {
      const chat = await this.$chats.createNewChat({
        id: uuidv4(), board: parent.board, name, mode, profiles,
        column: column || parent.column, parent_id: parent_id || parent.id,
        message_id, owner_project_id: parent.owner_project_id || parent.project_id,
        project_id: project_id || parent.project_id,
        messages: description ? [{ role: 'user', content: description }] : [],
        file_list, child_index
      })
      await this.$chats.saveChat(chat)
      if (description) this.$storex.projects.chatWihProject(chat)
      if (activateChat) await this.$chats.setActiveChat(chat)
    },
    async createSubTasks() {
      if (this.showSubtasksModal) {
        this.$projects.createSubtasks({ chat: this.theChat, instructions: this.createTasksInstructions })
        this.showSubtasksModal = false
      } else {
        this.showSubtasksModal = true
        this.createTasksInstructions = ""
      }
    }
  }
}
</script>