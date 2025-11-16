<script setup>
import moment from 'moment'
import AddFileDialog from '../components/chat/AddFileDialog.vue'
import Chat from '@/components/chat/Chat.vue'
import ProfileAvatar from '@/components/profile/ProfileAvatar.vue'
import UserSelector from '@/components/chat/UserSelector.vue'
import UserAvatar from '@/components/user/UserAvatar.vue'
import TaskSettings from '@/components/kanban/TaskSettings.vue'
import ChatIcon from '@/components/chat/ChatIcon.vue'
import ChatSelector from '@/components/chat/ChatSelector.vue'
import PRView from '@/components/repo/PRView.vue'
import VerticalSplitter from '@/components/layout/VerticalSplitter.vue'
import ProjectDetailt from '@/components/ProjectDetailt.vue'
import ExportChat from '@/components/chat/ExportChat.vue'
</script>

<template>
  <div class="flex flex-col h-full pb-1" v-if="chat">
    <div class="grow flex gap-2 h-full justify-between">
      <div class="grow flex flex-col w-full">
        <div class="flex gap-2 items-center" v-if="!chatMode">
          <div class="flex items-start gap-2 w-full">
            <div class="flex gap-2 items-start">
              <input v-if="editName" type="text" class="input input-bordered" @keydown.enter.stop="saveChat" @keydown.esc="editName = false" v-model="chat.name" />
              <div class="font-bold flex flex-col -space-y-2" v-else>
                <div class="flex gap-2 mb-2">
                  <div class="my-2 hover:underline cursor-pointer font-bold text-primary" @click="navigateToParent()">
                    <i class="fa-solid fa-caret-left"></i> {{ kanban?.title || chat.board }}
                  </div>
                  <div class="my-2 hover:underline cursor-pointer font-bold text-secondary" @click="navigateToParent(parentChat)" v-if="parentChat">
                    <i class="fa-brands fa-trello"></i>
                    {{ parentChat.name }}
                  </div>
                </div>
                <div class="flex gap-2">
                  <div class="flex gap-1">
                    <div class="avatar" :title="taskProject.project_name" v-if="taskProject.project_id !== $project.project_id">
                      <div class="w-7 h-7 rounded-full">
                        <img :src="taskProject.project_icon"/>
                      </div>
                    </div>
                    <UserAvatar :width="7" :user="user" v-for="user in chatUsers" :key="user.username">
                      <li @click="removeUser(user)"><a>Remove</a></li>
                    </UserAvatar>  
                    <ProfileAvatar :profile="profile"
                      :project="taskProject"
                      width="7"
                      v-for="profile in chatProfiles" :key="profile.name">
                        <div class="flex justify-end gap-2">
                          <div class="badge badge-xs badge-warning cursor-pointer" @click="removeProfile(profile)">
                            change
                          </div>
                        </div>
                    </ProfileAvatar>

                    <UserSelector 
                      class="dropdown-bottom"
                      :allUsers="true"
                      @user-changed="onAddProfile($event)"
                    />
                
                  </div>

                  <div class="cursor-pointer text-xs @md:text-md @xl:text-xl flex flex-col">
                    <div class="flex gap-1 items-end">
                      <span class="click tooltip" @click.stop="toggleChatPinned"
                        data-tip="Bookmark"
                      >
                        <i class="text-warning fa-solid fa-bookmark" v-if="chat.pinned" ></i>
                        <i class="fa-regular fa-bookmark" v-else></i>
                      </span>
                      
                      <div class="flex flex-col" :class="showChildChat && 'opacity-80'" @click="onChatNameClick">
                        <div class="text-xs">[{{ formattedChatUpdatedDate }}]</div>
                        <div>{{ chat.name }}</div>
                      </div> 
                      <span v-if="showChildChat"> / {{ showChildChat.name }}</span>
                      <span class="text-xs hover:underline"
                      :class="showDescription ? 'text-error/70': 'text-info'"
                        @click.stop="showDescription = !showDescription"
                        v-if="chat.description"> [{{ showDescription ? 'close': 'more' }}]
                      </span>
                      <span class="badge badge-md badge-outline" v-if="showTaskProjectName">
                        <img :src="taskProject.project_icon" class="w-3 rounded-full mr-1" />
                        {{ taskProject.project_name }}
                      </span>
                    </div>
                    <div class="text-xs" v-if="showDescription">
                      {{ workingChat.description || '-- no description yet --' }}
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <div class="grow"></div>
            <div class="flex flex-col">
              <div class="flex gap-1 items-center">
                <div class="flex gap-2 p-1 items-center -top-1">
                  <button class="btn btn-sm" v-if="childrenChats.length" 
                    @click="showChatMenu = !showChatMenu"
                    :class="showChatMenu && 'text-info'"
                    >
                    <i class="fa-solid fa-list"></i>
                  </button>
                  <button class="btn btn-sm" v-if="hiddenCount" @click="showHidden = !showHidden">
                    <div class="flex items-center gap-2 tooltip"
                      data-tip="Archived messages" 
                      :class="showHidden ? 'text-warning':''">
                      ({{ hiddenCount }}/{{ messageCount }})
                      <i class="fa-solid fa-box-archive"></i>
                    </div>
                  </button>
                  <div class="dropdown dropdown-end">
                    <div tabindex="0" role="button" class="btn  btn-sm m-1">
                      <ChatIcon :mode="workingChat.mode" />
                    </div>
                    <ul tabindex="0" class="dropdown-content menu bg-base-100 rounded-box z-[1] w-52 p-2 shadow">
                      <li @click="setChatMode('chat')">
                        <a><ChatIcon mode="chat" /> Conversation</a>
                      </li>
                      <li @click="setChatMode('task')">
                        <a><ChatIcon mode="task" /> Document</a>
                      </li>
                      <li @click="setChatMode('topic')">
                        <a><ChatIcon mode="topic" /> Discussion</a>
                      </li>
                      <li class="flex gap-2" @click="setChatMode('prview')">
                        <a><ChatIcon mode="prview" /> Changes review</a>
                      </li>
                      <li @click="openChatSearchModal">
                        <a><i class="fa-solid fa-link"></i> Link</a>
                      </li>
                    </ul>
                  </div>
                  <div class="grow"></div>
                  <div class="dropdown dropdown-end dropdown-bottom">
                    <div tabindex="0" class="btn btn-sm flex items-center indicator">
                      <i class="fa-solid fa-bars"></i>
                    </div>
                    <ul tabindex="0" class="dropdown-content menu bg-base-300 border rounded-box z-[1] p-2 w-96 shadow">
                      <li @click="newSubChat()">
                        <a><i class="fa-solid fa-plus"></i> New sub task</a>
                      </li>
                      <li @click="createSubTasks()">
                        <a><i class="fa-solid fa-wand-magic-sparkles"></i> Create sub tasks</a>
                      </li>
                      <li @click="showExportChat = true">
                        <a><i class="fa-solid fa-file-arrow-down"></i> Export</a>
                      </li>
                      <li @click="showChatSelector = true">
                        <a><i class="fa-solid fa-link"></i> Link chats</a>
                      </li>
                      <li @click="saveChat">
                        <a><i class="fa-solid fa-floppy-disk"></i> Save</a>
                      </li>
                      <div class="divider" v-if="childrenChats.length"></div>
                      <li @click="showTaskSettings = true">
                        <a><i class="fa-solid fa-gear"></i> Settings</a>
                      </li>
                    </ul>
                  </div>
                </div>
              </div>
              <div class="flex justify-end items-center">
              </div>
            </div>
          </div>
        </div>
        <div class="flex justify-between">
          <div class="flex gap-2 items-center">
            <div class="badge badge-sm badge-info flex gap-2" v-for="tag in chat.tags" :key="tag">
              {{ tag }}
              <button class="btn btn-ghost" @click="removeTag(tag)">
                x
              </button>
            </div>
            <button class="btn btn-xs" @click="newTag = ''">
              + Tag
            </button>
            
            <div class="avatar-group -space-x-6 relative" v-if="images.length">
              <div class="avatar" v-for="image, ix in images" :key="ix">
                <div class="w-8">
                  <img :src="image.src" />
                </div>
              </div>
            </div>
          </div>
          <div class="flex gap-1 justify-end items-center">
            <div class="badge badge-sm badge-warning badge-outline p-3 gap-2" v-if="taskAIModel">
              <i class="fa-solid fa-brain"></i> {{ taskAIModel.name }}
            </div>
          </div>
        </div>
        <PRView class="h-full overflow-auto" 
          :fromBranch="chat.pr_view?.from_branch"
          :toBranch="chat.pr_view?.to_branch"
          :extendedData="extendedData"
          :prChats="prChats"
          :chat="workingChat"
          @select="onPRViewBranchChanged"
          @comment="onPRFileComment"
          @change-column="$emit('change-column', $event)"
          @new-chat="onPRFileCreateChat"
          v-if="isPRView" />
          <VerticalSplitter v-else>
            <template v-slot:left v-if="childrenChats?.length && showChatMenu">
              <div class="flex justify-start">
                <button class="btn btn-xs btn-ghost" @click="showChatMenu = false">
                  <i class="fa-solid fa-caret-left"></i>
                </button>
              </div>
              <ul class="flex flex-col gap-2 overflow-auto h-full">
                <li class="p-2 hover:bg-base-100 rounded-lg"
                  @click="showChildChat = null"
                  :class="!showChildChat && 'text-warning'"
                >
                  <a class="flex gap-2 items-start">
                    <ChatIcon :mode="chat.mode" />{{ chat.name }}</a>
                </li>
                <li class="p-2 hover:bg-base-100 rounded-lg"
                  v-for="childChat in childrenChats" :key="childChat.id"
                  :class="[
                    (showChildChat?.name === childChat?.name) && 'text-warning',
                    (childChat === dropOver) && 'bg-white border border-red-300'
                  ]"
                  @click="selectChildChat(childChat)"
                  @dragstart="onChildMenuDragStart($event, childChat)"
                  @dragenter.prevent=""
                  @dragover.prevent="onTaskDragover($event, childChat)"
                  @dragleave="dropOver = false"
                  @drop.prevent="onTaskDropped($event, childChat)"
                  :draggable="true"
                >
                  <a class="flex gap-2 justify-between items-start group">
                    <ChatIcon :mode="childChat.mode" /> {{ childChat.name }}
                    <span class="hidden group-hover:flex text-xs" 
                      @click.stop="$projects.setActiveChat(childChat)">
                      <i class="fa-solid fa-up-right-from-square"></i>
                    </span>
                  </a>
                </li>
              </ul>
            </template>
            <template v-slot:right>
              <Chat class="h-full overflow-auto" 
              :chat="workingChat"
              :showHidden="showHidden"
              :childrenChats="showChatMenu ? null : childrenChats"
              @refresh-chat="loadChat(workingChat)"
              @remove-file="onRemoveFile" 
              @delete="confirmDelete = true"
              @subtask="onNewMessageSubtask"
            />
            </template>
          </VerticalSplitter>
        <modal v-if="confirmDelete">
          <div class="">
            <h3 class="font-bold text-lg">Confirm Delete</h3>
            <p class="text-error font-bold">Are you sure you want to delete this chat?</p>
            <div class="text-xl p-1">{{ chat.name }}</div>
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
              <button class="btn btn-error" @click="removeFileFromContext" v-if="showFile">
                Remove
              </button>
              <button class="btn btn-primary" @click="addFileToContext" v-else>
                Add
              </button>
              <button class="btn" @click="addFile = showFile = null">
                Close
              </button>
            </div>
          </div>
        </modal>
        <modal v-if="newTag !== null">
          <div class="flex flex-col gap-2">
            <div class="text-xl">New tag</div>
            <select class="select select-sm select-bordered" @change="newTag = $event.target.value">
              <option value="" selected>New</option>
              <option v-for="t in $projects.allTags" :key="t" :value="t">{{t}}</option>
            </select>
            <input type="text" class="input input-sm input-bordered" v-model="newTag" />
            <div class="flex gap-2 justify-end">
              <button class="btn btn-error" @click="newTag = null">
                Cancel
              </button>
              <button class="btn" @click="addNewTag" :disabled="newTag.length === 0">
                Add
              </button>
            </div>
          </div>
        </modal>
        <modal v-if="showSubtaskModal">
          <div class="flex flex-col gap-4 p-4">
            <h3 class="font-bold text-lg">Create New Subtask</h3>
            <input v-model="subtaskName" type="text" class="input input-bordered" placeholder="Subtask Name" />
            
            <!-- Dropdown for selecting subTaskMode -->
            <div class="form-control">
              <label class="label">
                <span class="label-text">Select Subtask Mode</span>
              </label>
              <select class="select select-bordered" v-model="subtaskMode">
                <option value="task" selected>Task</option>
                <option value="chat">Chat</option>
                <option value="topic">Topic</option>
                <option value="prview">PR View</option>
              </select>
            </div>

            <textarea v-model="subtaskDescription" class="textarea textarea-bordered" placeholder="Short Description (optional)" rows="3"></textarea>
            
            <ProjectDetailt 
              :project="$projects.allProjectsById[subtaskProject || chat.project_id || chatProject?.project_id]" 
              :options="{ showFolders: false, showIcon: true, showSelector: true }"
              @select="subtaskProject = $event.project_id"  
            />
            <div class="flex" v-for="profile in subtaskProfiles" :key="profile.name">
              <div class="badge">{{ profile.name }}</div>
            </div>
            <div class="flex gap-2 justify-end">
              <button class="btn btn-error" @click="cancelSubtask">Cancel</button>
              <button class="btn btn-primary" @click="createSubtask">Create</button>
            </div>
          </div>
        </modal>
        <modal v-if="showSubtasksModal">
          <div class="flex flex-col gap-4 p-4">
            <h3 class="font-bold text-2xl">Split into tasks</h3>
            <div class="tex-xl">Instructions:</div>
            <textarea v-model="createTasksInstructions" class="textarea textarea-bordered" placeholder="Short Description (optional)" rows="3"></textarea>
            <div class="flex gap-2 justify-end">
              <button class="btn btn-error" @click="showSubtasksModal = false">Cancel</button>
              <button class="btn btn-primary" @click="createSubTasks">Create</button>
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
  props: ['chatMode', 'chat', 'kanban'],
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
      subtaskMode: 'task', // Default mode
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
      extendedData: {},
      showChatMenu: false,
      showChildChat: null,
      showExportChat: false,
      dropOver: null
    }
  },
  created() {
    this.init()
  },
  async mounted() {
    this.showChatMenu = !this.$ui.isMobile
    this.chatProfiles = await this.$storex.api.project(this.taskProject)
      .then(p => p.profiles.list())
      .then(profiles => profiles.filter(p => this.chat.profiles.includes(p.name)))
    if (this.isPRView) {
      await this.$projects.loadBranches()
    }
  },
  computed: {
    branches() {
      return this.$projects.project_branches || []
    },
    isPRView() {
      return this.workingChat.mode === 'prview'
    },
    taskAIModel() {
      return this.aiModels.find(m => m.name === this.chat.llm_model)
    },
    aiModels() {
      return this.$projects.ai.models
    },
    showTaskProjectName() {
      return this.taskProject && this.taskProject.project_id != this.$project.project_id 
    },
    taskProject() {
      return this.$projects.allProjects.find(p => p.project_id === this.chat.project_id) ||
        this.$project
    },
    chatUsers() {
      return this.$storex.api.userNetwork.filter(({ username }) => this.chat.users?.includes(username))
    },
    chatModes() {
      return this.$projects.chatModes
    },
    subProjects() {
      return [
        this.$project,
        ...this.$projects.childProjects || [],
        ...this.$projects.projectDependencies || []
      ]
    },
    hiddenCount() {
      return this.workingChat.messages?.filter(m => m.hide).length
    },
    messageCount() {
      return this.workingChat.messages?.length
    },
    messages() {
      return this.chat.messages.filter(m => !m.hide || this.showHidden)
    },
    formattedChatUpdatedDate() {
      const updatedAt = this.chat.updated_at
      return moment(updatedAt).isAfter(moment().subtract(7, 'days'))
        ? moment(updatedAt).fromNow()
        : moment(updatedAt).format('YYYY-MM-DD')
    },
    chats() {
      return this.$projects.allChats
    },
    prChats() {
      return this.childrenChats.filter(c => c.file_list?.length === 1)
            .sort((a, b) => a.updated_at > b.updated_at ? 1 : -1)
            .reduce((acc, c) => ({ ...acc, [c.file_list[0]]: c }), {})
    },
    childrenChats() {
      return this.$storex.projects.allChats.filter(c => c.parent_id === this.chat.id)
        .sort((a, b) => a.child_index > b.child_index ? 1 : -1)
    },
    chatProject() {
      return this.$projects.allProjectsById[this.chat.project_id] ||
        this.$project
    },
    parentChat() {
      return this.$projects.allChats.find(c => c.id === this.chat?.parent_id)
    },
    chatFiles() {
      return this.workingChat.file_list || []
    },
    taskProjects() {
      return [this.$project, ...this.$projects.childProjects]
    },
    images() {
      return (this.workingChat.messages ||[]).map(m => m.images || [])
                .reduce((a, b) => a.concat(b), [])
                .map(i => {
                  try {
                    return i ? JSON.parse(i) : null
                  } catch {}
                  return null
                })
                .filter(i => !!i)
    },
    workingChat() {
      return this.$projects.chats[this.showChildChat?.id || this.chat.id]
    }
  },
  watch: {
    chat(newVal, oldVal) {
      if (oldVal && 
          newVal && 
          oldVal.project_id !== newVal.project_id) {
        this.init()
      }
    }
  },
  methods: {
    async init() {
      this.setProjectContext()
      await Promise.all(
        this.childrenChats.map(chat => this.$projects.loadChat(chat))
      )
    },
    async setProjectContext() {
      this.projectContext = await this.$service.project.loadProjectContext(this.$project)
    },
    async saveChat(chat) {
      this.editName = false
      await this.$projects.saveChat(chat || this.workingChat)
    },
    async confirmDeleteChat() {
      this.confirmDelete = false
      await this.$projects.deleteChat(this.chat)
      const parentChat = this.parentChat
      if (parentChat) {
        this.$projects.setActiveChat(parentChat)
      } else {
        this.navigateToChats()
      }
    },
    resetConfirmDelete() {
      this.confirmDelete = false
    },
    async loadChat(chat) {
      await this.$projects.setActiveChat(chat)
      this.showChatsTree = false
    },
    async removeFileFromContext() {
      this.chat.profiles = this.chat.profiles?.filter(f => f !== this.showFile)
      this.onRemoveFile(this.showFile)
      await this.loadChat(this.chat)
      this.showFile = null
    },
    async addFileToContext() {
      this.onAddFile(this.addFile)
      await this.saveChat()
      await this.loadChat(this.chat)
      this.showFile = null
      this.addFile = null
    },
    async onAddFile(file) {
      if (this.chat.file_list?.includes(file)) {
        return
      }
      this.chat.file_list = [...(this.chat.file_list || []), file]
      this.addNewFile = null
      await this.saveChat()
    },
    async onRemoveFile(file) {
      this.workingChat.file_list = (this.workingChat.file_list || []).filter(f => f !== file)
      this.addNewFile = null
      await this.saveChat()
    },
    async addProfile(profile) {
      if (!this.chat.profiles?.includes(profile)) {
        this.chat.profiles = [...this.chat.profiles || [], profile]
        await this.saveChat()
      }
      this.showAddProfile = false
    },
    async addUserToChat(user) {
      if (!this.chat.users?.includes(user.username)) {
        this.chat.users = [...this.chat.users || [], user.username]
        await this.saveChat()
      }
      this.showAddProfile = false
    },
    async removeUser(user) {
      if (this.chat.users?.includes(user.username)) {
        this.chat.users = this.chat.users.filter(u => u !== user.username)
        await this.saveChat()
      }
    },
    removeProfile(profile) {
      if (this.chat.profiles?.includes(profile.name)) {
        this.chat.profiles = this.chat.profiles.filter(p => p !== profile.name)
        this.saveChat()
      }
    },
    onRemoveMessage(message) {
      const ix = this.chat.messages.findIndex(m => m.doc_id === message.doc_id)
      if (this.chat.mode == 'task' && message.role === "assistant" && ix > 1) {
        this.chat.messages[ix - 1].hide = false
      }
      this.chat.messages = this.chat.messages.filter((_, i) => i !== ix)
      this.saveChat()
    },
    navigateToChats() {
      if (this.$ui.activeTab !== 'tasks') {
        this.$ui.setActiveTab('tasks')
      }
      this.$emit('chats', this.kanban?.title || this.chat.board)
    },
    newSubChat(message) {
      this.subtaskProject = this.chat.project_id
      this.subtaskParentId = null
      this.subtaskMessageId = null
      this.showSubtaskModal = true

      this.subtaskName = null
      this.subtaskDescription = null
      this.subtaskProject = null
      this.subtaskParentId = this.chat.id
      this.subtaskMessageId = message?.doc_id
      this.subtaskFiles = []
      this.subtaskProfiles = []
      this.subtaskMode = this.chat.mode
      this.subtaskColumn = this.chat.column
    },
    onNewMessageSubtask({ chat: { id: subtaskParentId }, message: { id: subtaskMessageId }}) {
      this.subtaskProject = this.$project.project_id
      this.subtaskParentId = subtaskParentId
      this.subtaskMessageId = subtaskMessageId
      this.showSubtaskModal = true

    },
    getSubTaskParentSummary() {
      let { messages } = this
      if (!messages.length) {
        return ""
      }
      if (this.chat.mode === 'task') {
        messages = messages.reverse()
        const lastAI = messages.find(m => m.role === 'assistant')
        if (lastAI) {
          return lastAI.content
        }
      }
      return messages.reduce((acc, m) => acc + "\n" + m.content, "")
    },
    createSubtask() {
      if (!this.subtaskName.trim()) {
        return
      }
      if (this.subtaskDescription) {
        const parentContent = this.getSubTaskParentSummary()
        this.subtaskDescription = `${parentContent}\n\n${this.subtaskDescription}`
      }
      this.$emit('sub-task', {
        parent: this.chat,
        name: this.subtaskName,
        description: this.subtaskDescription,
        project_id: this.subtaskProject,
        parent_id: this.subtaskParentId,
        message_id: this.subtaskMessageId,
        file_list: this.subtaskFiles,
        profiles: this.subtaskProfiles,
        mode: this.subtaskMode,
        column: this.subtaskColumn,
        activateChat: this.chat.mode !== 'task',
        child_index: this.childrenChats?.length
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
    },
    addNewTag() {
      this.chat.tags = [...new Set([...this.chat.tags || [], this.newTag])]
      this.newTag = null
      this.saveChat()
    },
    removeTag(tag) {
      this.chat.tags = this.chat.tags.filter(t => t !== tag)
      this.saveChat()
    },
    setChatMode(mode) {
      this.workingChat.mode = mode
      this.saveChat()
    },
    async createSubTasks() {
      if (this.showSubtasksModal) {
        this.$emit('sub-tasks', { chat: this.chat, instructions: this.createTasksInstructions })
        this.showSubtasksModal = false
      } else {
        this.showSubtasksModal = true
        this.createTasksInstructions = ""
      }
    },
    navigateToParent(parentChat) {
      if (parentChat) {
        this.$emit('chat', parentChat)
      } else {
        this.navigateToChats()
      }
    },
    async openChatSearchModal() {
      // Open a modal for linking chat
    },
    async onAddProfile() {
      this.showAddProfile = true
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
    toggleChatPinned() {
      this.chat.pinned = !this.chat.pinned
      this.saveChat()  
    },
    selectChildChat(childChat) {
      this.showChildChat = childChat
      if (!childChat.messages?.length) {
        this.$projects.loadChat(childChat)
      }
    },
    onChatNameClick() {
      if (this.showChildChat) {
        this.selectChildChat(null)
      } else {
        this.editName = true
      }
    },
    onChildMenuDragStart($event, childChat) {
      console.log("Menu drag start", $event)
      $event.dataTransfer.setData("chatId", childChat.id)
    },
    onTaskDragover($event, childChat) {
      const id = $event.dataTransfer.getData("chatId")
      if (id === childChat.id) {
        this.dropOver = null
        return
      }
      this.dropOver = childChat
      console.log("Menu drag over", this.dropOver.name)
      $event.preventDefault();
      $event.target.scrollIntoView({ block: 'center', behavior: 'smooth' })
    },
    onTaskDropped($event, childChat) {
      const id = $event.dataTransfer.getData("chatId")
      if (id === childChat.id) {
        return
      }
      return
      const dropChat = this.childrenChats.find(c => c.id === id)
      dropChat.parent_id = childChat.id
      this.dropOver = null
      this.saveChat(dropChat)
    }
  }
}
</script>