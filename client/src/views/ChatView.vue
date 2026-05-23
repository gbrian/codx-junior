<script setup>
import moment from 'moment'
import { v4 as uuidv4 } from 'uuid'
import AddFileDialog from '../components/chat/AddFileDialog.vue'
import Chat from '@/components/chat/Chat.vue'
import UserSelector from '@/components/chat/UserSelector.vue'
import TaskSettings from '@/components/kanban/TaskSettings.vue'
import ChatIcon from '@/components/chat/ChatIcon.vue'
import ChatSelector from '@/components/chat/ChatSelector.vue'
import VerticalSplitter from '@/components/layout/VerticalSplitter.vue'
import ProjectDetailt from '@/components/ProjectDetailt.vue'
import ExportChat from '@/components/chat/ExportChat.vue'
import Markdown from '../components/Markdown.vue'
import ProjectIcon from '@/components/ProjectIcon.vue'
</script>

<template>
  <div class="p-2 flex flex-col h-full bg-base-300/80 p-1" v-if="workingChat">
    <div class="grow flex gap-2 h-full justify-between">
      <div class="grow flex flex-col w-full">
        <div class="flex gap-2 items-center" v-if="!chatMode">
          <div class="flex items-start gap-2 w-full">
            <div class="flex gap-2 items-start">
              <input type="text" class="input input-sm input-bordered"
                @keydown.enter.stop="saveChatInfo(theChat)" 
                @keydown.esc="editName = false" 
                v-model="theChat.name" 
                v-if="editName" />
              <div class="font-bold flex -space-y-2" 
                :class="[isVibe ? 'items-start gap-2 flex-row-reverse' : 'flex-col']"
                v-else>
                <div class="flex gap-2 mb-2 shrink-0">
                  <div class="my-2 hover:underline cursor-pointer font-bold text-primary" @click="navigateToParent()">
                    <i class="fa-brands fa-trello"></i>
                    {{ kanban?.title || theChat.board }}
                  </div>
                  <div class="my-2 hover:underline cursor-pointer font-bold text-secondary" @click="navigateToParent(parentChat)"
                    v-if="parentChat">
                    {{ parentChat.name }}
                  </div>
                </div>
                <div class="flex gap-2">
                  <div class="flex gap-1 relative">
                    <!-- targetProject: project that will be affected by the chat -->
                    <ProjectDetailt 
                      v-model="targetProject" 
                      :iconify="true"
                      :options="{ showFolders: false, showIcon: true, showSelector: true }"
                      @select="setChatProject"  
                    />
                    <UserSelector 
                      class="dropdown-bottom"
                      :allUsers="true"
                      @user-changed="onAddProfile($event)"
                    />
                  </div>

                  <div class="cursor-pointer text-xs @md:text-md @xl:text-xl flex flex-col">
                    <div class="flex gap-2 items-start">
                      <span class="click tooltip pt-1" @click.stop="toggleChatPinned"
                        data-tip="Bookmark"
                      >
                        <i class="text-warning fa-solid fa-bookmark" v-if="theChat.pinned" ></i>
                        <i class="fa-regular fa-bookmark" v-else></i>
                      </span>
                      
                      <div class="flex flex-col" :class="showChildChat && 'opacity-80'">
                        <div>
                          <span :class="showChildChat && 'opacity-70 hover:opacity-100'" 
                            @dblclick="onChatNameClick"
                            @click="showChildChat = null"
                          >
                            {{ computedChatName }}
                          </span>
                          <span v-if="showChildChat"> / {{ showChildChat.name }}</span>
                        </div>
                        <div class="flex gap-1 text-xs gap-2">
                          <!-- ownerProject: project where the chat was created -->
                          <span class="text-xs text-base-content/50" v-if="showTaskProjectName" :title="`Owner: ${ownerProject?.title}`">
                            <i class="fa-solid fa-house text-xs"></i> {{ ownerProject?.title }}
                          </span>
                          [{{ formattedChatUpdatedDate }}]
                          <span class="text-xs hover:underline"
                              :class="showDescription ? 'text-error/70': 'text-info'"
                            @click.stop="showDescription = !showDescription"
                            v-if="computedChatDescription"> [{{ showDescription ? 'close': 'description' }}]
                          </span>
                        </div>
                      </div> 
                    </div>
                    <div class="text-xs" v-if="showDescription">
                      <markdown class="prose-sm" :text="computedChatDescription || '-- no description yet --'" />
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <div class="grow"></div>
            <div class="flex flex-col">
              <div class="flex gap-1 items-center">
                <div class="flex gap-2 p-1 items-center -top-1">
                  <div class="flex input input-sm input-bordered w-40 items-center">
                    <input v-model="chatSearch" class="bg-transparant w-full" />
                    <span class="text-error" @click="chatSearch = null" v-if="chatSearch"><i class="fa-regular fa-circle-xmark"></i></span>
                    <span v-else><i class="fa-solid fa-magnifying-glass"></i></span>
                  </div>
                  <button class="btn btn-sm" v-if="childrenChats.length" 
                    @click="showChatMenu = !showChatMenu"
                    :class="showChatMenu && 'text-info'"
                    >
                    <i class="fa-solid fa-list"></i>
                  </button>
                  <button class="btn btn-sm" @click="showHidden = !showHidden">
                    <div class="flex items-center gap-2 tooltip"
                      data-tip="Archived messages" 
                      :class="showHidden ? 'text-warning':''">
                      <i class="mt-1 fa-regular fa-message"></i>
                      {{ messageCount - hiddenCount }}
                      <span v-if="hiddenCount">
                        <i class="mt-1 fa-regular fa-eye-slash"></i>
                        {{ hiddenCount }}
                      </span>
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
                      <li @click="setChatMode('word')">
                        <a><ChatIcon mode="word" /> Rich Editor</a>
                      </li>
                      <li @click="setChatMode('vibe')">
                        <a><ChatIcon mode="vibe" /> Vibe</a>
                      </li>
                      <li class="flex gap-2" @click="setChatMode('prview')">
                        <a><ChatIcon mode="prview" /> Changes review</a>
                      </li>
                      <li @click="setChatMode('browser')">
                        <a><ChatIcon mode="browser" /> Browser</a>
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
                      <li @click="newTag = true">
                        <a><i class="fa-solid fa-plus"></i> New #tag</a>
                      </li>
                      <hr>
                      <li @click="reloadChat(workingChat)">
                        <a><i class="fa-solid fa-recycle"></i> Load</a>
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
        <div class="flex gap-2 items-center">  
          <div class="text-xs font-bold" v-for="tag in theChat.tags" :key="tag">
            #{{ tag }}
          </div>
        </div>
        <div class="flex justify-between">
          <div class="flex gap-2 items-center">  
            <div class="avatar-group -space-x-6 relative" v-if="images.length">
              <div class="avatar" v-for="image, ix in images" :key="ix">
                <div class="w-8">
                  <img :src="image.src" />
                </div>
              </div>
            </div>
          </div>
        </div>
        <VerticalSplitter 
          class="mt-2"
          :panels="{
            left: { defaultSize: 20 },
            right: { defaultSize: 80 }
          }">
          <template v-slot:left v-if="showLeftMenu">
            <div class="flex justify-start">
              <button class="btn btn-xs btn-ghost" @click="showChatMenu = false">
                <i class="fa-solid fa-caret-left"></i>
              </button>
            </div>
            <ul class="flex flex-col overflow-auto h-full">
              <li class="p-2 hover:bg-base-100 rounded-lg click"
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
                <a class="group">
                  <div class="flex gap-2 items-start">
                    <ProjectIcon 
                      width="6"
                      icon-only="true"
                      :project="$projects.allProjectsById[childChat.project_id] || $project" />
                    <div class="flex flex-col gap-1"> 
                      {{ childChat.name }}
                      <div class="badge badge-outline badge-xs" v-if="childChat.column !== workingChat.column">
                        {{ childChat.column }}
                      </div>
                    </div>
                    <div class="grow hidden group-hover:flex text-xs justify-end" 
                      @click.stop="$chats.setActiveChat(childChat)">
                      <i class="fa-solid fa-up-right-from-square"></i>
                    </div>
                  </div>
                </a>
              </li>
            </ul>
          </template>
          <template v-slot:right>
            <Chat 
              :class="[showLeftMenu && 'ml-2']"
              :chat="workingChat"
              :showHidden="showHidden"
              :childrenChats="showChatMenu ? null : childrenChats"
              :filter="chatSearch"
              @refresh-chat="reloadChat(workingChat)"
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
            <div class="text-xl p-1">{{ theChat.name }}</div>
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
            
            <div class="form-control">
              <label class="label">
                <span class="label-text">Select Subtask Mode</span>
              </label>
              <select class="select select-bordered" v-model="subtaskMode">
                <option value="task" selected>Task</option>
                <option value="chat">Chat</option>
                <option value="topic">Topic</option>
                <option value="prview">PR View</option>
                <option value="browser">Browser</option>
                <option value="slides">Slides</option>
              </select>
            </div>

            <textarea v-model="subtaskDescription" class="textarea textarea-bordered" placeholder="Short Description (optional)" rows="3"></textarea>
            
            <!-- subtaskProject defaults to targetProject of parent chat -->
            <ProjectDetailt 
              v-model="subtaskProject" 
              :options="{ showFolders: false, showIcon: true, showSelector: true }"
            />
            <div class="flex" v-for="profile in subtaskProfiles" :key="profile.name">
              <div class="badge">{{ profile.name }}</div>
            </div>
            <div class="flex gap-2 justify-end">
              <button class="btn btn-error" @click="cancelSubtask">Cancel</button>
              <button class="btn btn-primary" @click="onCreateSubtask">Create</button>
            </div>
          </div>
        </modal>
        <modal class="w-2/3 h-2/3" v-if="showSubtasksModal">
          <div class="h-full flex flex-col gap-4 p-4">
            <h3 class="font-bold text-2xl">Split into tasks</h3>
            <div class="tex-xl">Instructions:</div>
            <textarea v-model="createTasksInstructions" class="grow textarea textarea-bordered" placeholder="Short Description (optional)" rows="3"></textarea>
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
  components: { Markdown },
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
      showChatMenu: false,
      showChildChat: null,
      showExportChat: false,
      dropOver: null,
      chatSearch: null,
      // ownerProject: project where the chat was originally created (chat.owner_project_id)
      ownerProject: null,
      // targetProject: project the chat work targets (chat.project_id)
      targetProject: null
    }
  },
  created() {
    this.init()
  },
  async mounted() {
  },
  computed: {
    theChat() {
      return this.$chats.chats[this.chat?.id || this.params?.params.chat?.id] 
    },
    isThread() {
      return !!this.theChat.message_id
    },
    isPRView() {
      return this.workingChat?.mode === 'prview'
    },
    isVibe() {
      return this.workingChat?.mode === 'vibe'
    },
    taskAIModel() {
      return this.aiModels.find(m => m.name === this.theChat.llm_model)
    },
    aiModels() {
      return this.$projects.ai.models
    },
    // Show owner label only when owner differs from current active project
    showTaskProjectName() {
      return this.ownerProject && this.ownerProject.project_id !== this.$project.project_id
    },
    chatUsers() {
      return this.$storex.api.userNetwork.filter(({ username }) => this.theChat.users?.includes(username))
    },
    chatModes() {
      return this.$projects.chatModes
    },
    hiddenCount() {
      return this.workingChat.messages?.filter(m => m.hide).length
    },
    messageCount() {
      return this.workingChat.messages?.length
    },
    messages() {
      return this.theChat.messages.filter(m => !m.hide || this.showHidden)
    },
    formattedChatUpdatedDate() {
      const updatedAt = this.theChat.updated_at
      return moment(updatedAt).isAfter(moment().subtract(7, 'days'))
        ? moment(updatedAt).fromNow()
        : moment(updatedAt).format('YYYY-MM-DD')
    },
    childrenChats() {
      return this.$chats.allChats
        .filter(c => c.parent_id === this.theChat.id && !c.message_id)
        .sort((a, b) => a.name > b.name ? 1 : -1)
    },
    chatProject() {
      return this.$projects.allProjectsById[this.theChat.project_id] || this.$project
    },
    parentChat() {
      return this.$chats.chats[this.theChat?.parent_id]
    },
    chatFiles() {
      return this.workingChat.file_list || []
    },
    images() {
      return (this.workingChat.messages || [])
        .map(m => m.images || [])
        .reduce((a, b) => a.concat(b), [])
        .map(i => {
          try { return i ? JSON.parse(i) : null } catch {}
          return null
        })
        .filter(i => !!i)
    },
    workingChat() {
      return this.$chats.chats[this.showChildChat?.id] || this.theChat
    },
    computedChatName() {
      return this.theChat.name
    },
    computedChatDescription() {
      if (this.theChat.message_id) {
        const message = this.$storex.projects.allChats
          .find(c => c.id === this.theChat.parent_id)
          ?.messages.find(m => m.doc_id === this.theChat.message_id)
        return message?.content || '-- no description yet --'
      }
      return this.theChat.description
    },
    showLeftMenu() {
      return this.childrenChats?.length && this.showChatMenu && !this.isPRView
    }
  },
  watch: {
    chat(newVal, oldVal) {
      if (oldVal && newVal && oldVal.project_id !== newVal.project_id) {
        this.init()
      }
      this.showChildChat = null
      this.showChatMenu = false
    }
  },
  methods: {
    async init() {
      const chat = await this.$service.chat.findChat(this.chat || this.params?.params.chat)
      if (!this.theChat) {
        throw new Error(`Chat not loaded: ${this.chat || this.params?.params.chat}`)
      }
      // Resolve projects before loading children and context
      this.setTaskProject()
      this.setProjectContext()
      await Promise.all(
        this.childrenChats.map(chat => this.$chats.loadChat(chat))
      )
      this.chatProfiles = await this.$storex.api.project(this.ownerProject)
        .then(p => p.profiles.list())
        .then(profiles => profiles.filter(p => this.theChat.profiles.includes(p.name)))
      if (this.isPRView) {
        await this.$projects.loadBranches()
      }
      this.showChatMenu = !this.$ui.isMobile && !this.isPRView
      this.showDescription = this.isThread
    },

    setTaskProject() {
      this.ownerProject = this.$projects.allProjectsById[this.theChat.owner_project_id]
      this.targetProject = this.$projects.allProjectsById[this.theChat.project_id] || this.$project
      // subtaskProject inherits targetProject by default
      this.subtaskProject = this.targetProject
    },

    async setProjectContext() {
      this.projectContext = await this.$service.project.loadProjectContext(this.$project)
    },

    async reloadChat() {
      this.$chats.reloadChat(this.workingChat)
    },

    async setChatProject(project) {
      // Update targetProject and persist
      this.targetProject = project
      this.workingChat.project_id = project.project_id
      await this.saveChat(this.workingChat)
    },

    async saveChat(chat) {
      this.editName = false
      return this.$chats.saveChat(chat || this.workingChat)
    },
    saveChatInfo(chat) {
      this.editName = false
      this.$chats.saveChatInfo(chat)
    },
    async confirmDeleteChat() {
      this.confirmDelete = false
      await this.$chats.deleteChat(this.theChat)
      const parentChat = this.parentChat
      if (parentChat) {
        this.$chats.setActiveChat(parentChat)
      } else {
        this.navigateToChats()
      }
    },

    resetConfirmDelete() {
      this.confirmDelete = false
    },

    async loadChat(chat) {
      await this.$chats.setActiveChat(chat)
      this.showChatsTree = false
    },

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

    async addProfile(profile) {
      if (!this.theChat.profiles?.includes(profile)) {
        this.theChat.profiles = [...this.theChat.profiles || [], profile]
        await this.saveChat(this.theChat)
      }
      this.showAddProfile = false
    },

    async addUserToChat(user) {
      if (!this.theChat.users?.includes(user.username)) {
        this.theChat.users = [...this.theChat.users || [], user.username]
        await this.saveChat(this.theChat)
      }
      this.showAddProfile = false
    },

    async removeUser(user) {
      if (this.theChat.users?.includes(user.username)) {
        this.theChat.users = this.theChat.users.filter(u => u !== user.username)
        await this.saveChat(this.theChat)
      }
    },

    removeProfile(profile) {
      if (this.theChat.profiles?.includes(profile.name)) {
        this.theChat.profiles = this.theChat.profiles.filter(p => p !== profile.name)
        this.saveChat(this.theChat)
      }
    },

    onRemoveMessage(message) {
      const ix = this.theChat.messages.findIndex(m => m.doc_id === message.doc_id)
      if (this.theChat.mode == 'task' && message.role === "assistant" && ix > 1) {
        this.theChat.messages[ix - 1].hide = false
      }
      this.theChat.messages = this.theChat.messages.filter((_, i) => i !== ix)
      this.saveChat()
    },

    navigateToChats() {
      if (this.$ui.activeTab !== 'tasks') {
        this.$ui.setActiveTab('tasks')
      }
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
      // Subtask targets same project as parent chat by default
      this.subtaskProject = this.targetProject
      this.showSubtaskModal = true
    },

    async onNewMessageSubtask({ chat, mode, message: { column, files, profiles, doc_id: subtaskMessageId }}) {
      const findChild = () => this.$projects.allChats.find(c => c.message_id === subtaskMessageId)
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

    onCreateSubtask() {
      if (!this.subtaskName.trim()) return
      if (this.subtaskDescription) {
        const parentContent = this.getSubTaskParentSummary()
        this.subtaskDescription = `${parentContent}\n\n${this.subtaskDescription}`
      }
      this.createSubTask({
        parent: this.theChat,
        name: this.subtaskName,
        description: this.subtaskDescription,
        // Use selected subtaskProject (defaults to targetProject)
        project_id: this.subtaskProject?.project_id || this.targetProject?.project_id,
        parent_id: this.subtaskParentId,
        message_id: this.subtaskMessageId,
        file_list: this.subtaskFiles,
        profiles: this.subtaskProfiles,
        mode: this.subtaskMode,
        board: this.theChat.board,
        column: this.subtaskColumn,
        activateChat: this.theChat.mode !== 'task',
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
      this.theChat.tags = [...new Set([...this.theChat.tags || [], this.newTag])]
      this.newTag = null
      this.saveChat()
    },

    removeTag(tag) {
      this.theChat.tags = this.theChat.tags.filter(t => t !== tag)
      this.saveChat()
    },

    setChatMode(mode) {
      this.workingChat.mode = mode
      this.saveChat()
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

    toggleChatPinned() {
      this.theChat.pinned = !this.theChat.pinned
      this.saveChat()
    },

    selectChildChat(childChat) {
      this.showChildChat = childChat
      if (childChat && !childChat.messages?.length) {
        this.$chats.reloadChat(childChat)
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
      $event.dataTransfer.setData("chatId", childChat.id)
    },

    onTaskDragover($event, childChat) {
      const id = $event.dataTransfer.getData("chatId")
      if (id === childChat.id) {
        this.dropOver = null
        return
      }
      this.dropOver = childChat
      $event.preventDefault()
      $event.target.scrollIntoView({ block: 'center', behavior: 'smooth' })
    },

    onTaskDropped($event, childChat) {
      const id = $event.dataTransfer.getData("chatId")
      if (id === childChat.id) return
      const dropChat = this.childrenChats.find(c => c.id === id)
      if (!dropChat) return
      dropChat.parent_id = childChat.id
      this.dropOver = null
      this.saveChat(dropChat)
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
        // Inherit owner from parent; target project is explicit project_id
        owner_project_id: parent.owner_project_id || parent.project_id,
        project_id: project_id || parent.project_id,
        messages: description ? [{ role: 'user', content: description }] : [],
        file_list,
        child_index
      })
      await this.$chats.saveChat(chat)
      if (description) this.$storex.projects.chatWihProject(chat)
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