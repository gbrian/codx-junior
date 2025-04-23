<script setup>
import moment from 'moment'
import AddFileDialog from '../components/chat/AddFileDialog.vue'
import Chat from '@/components/chat/Chat.vue'
import Kanban from '@/components/kanban/Kanban.vue'
import ProfileSelector from '@/components/profile/ProfileSelector.vue'
import ProfileAvatar from '@/components/profile/ProfileAvatar.vue'
import UserSelector from '@/components/user/UserSelector.vue'
import UserAvatar from '@/components/user/UserAvatar.vue'
import TaskSettings from '@/components/kanban/TaskSettings.vue'
</script>

<template>
  <div class="flex flex-col h-full pb-2" v-if="chat">
    <div class="grow flex gap-2 h-full justify-between">
      <div class="grow flex flex-col gap-2 w-full">
        <div class="flex gap-2 items-center" v-if="!chatMode">
          <div class="flex items-start gap-2 w-full">
            <div class="flex gap-2 items-start">
              <input v-if="editName" type="text" class="input input-xs input-bordered" @keydown.enter.stop="saveChat" @keydown.esc="editName = false" v-model="chat.name" />
              <div class="font-bold flex flex-col" v-else>
                <div class="flex gap-2">
                  <div class="my-2 text-xs hover:underline click font-bold text-primary" @click="naviageToParent()">
                    <i class="fa-solid fa-caret-left"></i> {{ kanban?.title }}
                  </div>
                  <div class="my-2 text-xs hover:underline click font-bold text-secondary" @click="naviageToParent(parentChat)" v-if="parentChat">
                    <i class="fa-brands fa-trello"></i>
                    {{ parentChat.name }}
                  </div>
                </div>
                <div class="flex items-center gap-2">
                  <div class="flex gap-1">
                    <div class="avatar" :title="taskProject.project_name" v-if="taskProject !== $project">
                      <div class="w-7 h-7 rounded-full">
                        <img :src="taskProject.project_icon"/>
                      </div>
                    </div>
                    <UserAvatar :width="7" :user="user" v-for="user in chatUsers" :key="user.username">
                      <li @click="removeUser(user)" ><a>Remove</a></li>
                    </UserAvatar>  
                    <ProfileAvatar :profile="chatProfiles[0]"
                      :project="taskProject"
                      width="7"
                      v-if="chatProfiles.length">
                        <div class="flex justify-end gap-2">
                          <div class="badge badge-xs badge-warning click" @click="removeProfile(chatProfiles[0])">
                            change
                          </div>
                        </div>
                    </ProfileAvatar>

                    <button class="btn btn-sm btn-circle tooltip" data-tip="Add profile"
                      @click="onAddProfile">
                      <i class="fa-solid fa-plus"></i>
                    </button>
                  </div>

                  <div class="click text-xs md:text-xl" @click="editName = true">
                    {{ chat.name }}
                  </div>
                </div>
              </div>
            </div>
            <div class="grow"></div>
            <div class="flex flex-col gap-2">
              <div class="flex gap-1 items-center">
                <div class="flex gap-2 p-1 items-center -top-1" v-if="toggleChatOptions">
                  <button class="btn btn-xs" v-if="hiddenCount" @click="showHidden = !showHidden">
                    <div class="flex items-center gap-2" v-if="!showHidden">
                      ({{ hiddenCount }})
                      <i class="fa-solid fa-eye-slash"></i>
                    </div>
                    <span class="text-warning" v-else>
                      <i class="fa-solid fa-eye"></i>
                    </span>
                  </button>
                  <div class="grow"></div>
                  <div class="dropdown dropdown-end dropdown-bottom">
                    <div tabindex="0" class="btn btn-sm flex items-center indicator">
                      <i class="fa-solid fa-bars"></i>
                    </div>
                    <ul tabindex="0" class="dropdown-content menu bg-base-300 rounded-box z-[1] p-2 w-96 shadow">
                      <li @click="newSubChat()">
                        <a><i class="fa-solid fa-plus"></i> New sub task</a>
                      </li>
                      <li @click="createSubTasks()">
                        <a><i class="fa-solid fa-wand-magic-sparkles"></i> Create sub tasks</a>
                      </li>
                      <li @click="onExport">
                        <a><i class="fa-solid fa-copy"></i> Export</a>
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
                <div class="md:hidden btn btn-sm" @click="toggleChatOptions = !toggleChatOptions">
                  <i class="fa-solid fa-bars"></i>
                </div>
              </div>
              <div class="flex justify-end items-center">
              </div>
            </div>
          </div>
        </div>
        <div class="flex justify-between">
          <div class="flex gap-2 items-center">
            <div class="text-xs">{{ formattedChatUpdatedDate }}</div>
            <div class="badge badge-sm badge-info flex gap-2" v-for="tag in chat.tags" :key="tag">
              {{ tag }}
              <button class="btn btn-xs btn-ghost" @click="removeTag(tag)">
                x
              </button>
            </div>
            <button class="btn btn-xs" @click="newTag = ''">
              + tag
            </button>
          </div>
          <div class="flex gap-1 justify-end items-center">
          </div>
        </div>
        <div class="w-full overflow-auto" v-if="chatFiles.length">
          <div class="my-2 text-xs">
            <span>
              <i class="fa-solid fa-paperclip"></i>
            </span>
            <a v-for="file in chatFiles" :key="file" :data-tip="file" class="group text-nowrap ml-2 hover:underline hover:bg-base-300 click text-accent" @click="$ui.openFile(file)">
              <span>{{ file.split('/').reverse()[0] }}</span>
              <span class="ml-2 click" @click.stop="onRemoveFile(file)">
                <i class="fa-regular fa-circle-xmark"></i>
              </span>
            </a>
          </div>
        </div>
        <Chat :chatId="chat.id"
          :showHidden="showHidden"
          :childrenChats="childrenChats"
          @refresh-chat="loadChat(chat)"
          @add-file="onAddFile"
          @remove-file="onRemoveFile" 
          @delete-message="onRemoveMessage"
          @delete="confirmDelete = true"
          @save="saveChat" 
          v-if="chat"/>
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
            <textarea v-model="subtaskDescription" class="textarea textarea-bordered" placeholder="Short Description (optional)" rows="3"></textarea>
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
          <TaskSettings :taskData="chat" @close="showTaskSettings = false" />
        </modal>
      </div>
      <add-file-dialog v-if="addNewFile" @open="onAddFile" @close="addNewFile = false" />
    </div>
    <modal class="max-w-full w-1/3" v-if="showAddProfile" :close="true" @close="showAddProfile = false">
      <UserSelector @select="addUserToChat($event)" />
      <ProfileSelector @select="addProfile($event.name)" :project="chatProject" />
    </modal>
  </div>
</template>

<script>
export default {
  props: ['chatMode', 'openChat', 'kanban'],
  data() {
    return {
      showFile: null,
      addFile: null,
      showChatsTree: false,
      editName: false,
      showSettings: false,
      addNewFile: null,
      showHidden: false,
      confirmDelete: false,
      newTag: null,
      toggleChatOptions: false,
      showSubtaskModal: false,
      showSubtasksModal: false,
      showTaskSettings: false,
      subtaskName: '',
      subtaskDescription: '',
      showAddProfile: false,
      createTasksInstructions: '',
      chatProfiles: []
    }
  },
  async mounted () {
    this.toggleChatOptions = !this.$ui.isMobile
    this.chatProfiles = await this.$storex.api.project(this.taskProject)
                                .then(p => p.profiles.list())
                                .then(profiles => profiles.filter(p => this.chat.profiles.includes(p.name)))
  },
  computed: {
    taskProject() {
      return this.$projects.allProjects.find(p => p.project_id === this.chat.project_id) ||
                this.$project
    },
    chatUsers() {
      return this.$storex.api.userNetwork.filter(({ username }) => this.chat.users?.includes(username))
    },
    chatModes () {
      return this.$projects.chatModes
    },
    subProjects () {
      return [
        this.$project,
        ...this.$projects.childProjects || [],
        ...this.$projects.projectDependencies || []
      ]
    },
    hiddenCount() {
      return this.chat.messages?.filter(m => m.hide).length
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
    chat() {
      return this.$projects.chats[this.openChat?.id || this.$projects.activeChat?.id]
    },
    childrenChats() {
      return this.$storex.projects.allChats.filter(c => c.parent_id === this.chat.id)
        .sort((a, b) => (a.updated_at || a.created_at) > (b.updated_at || b.created_at) ? -1 : 1)
    },
    chatProject() {
      return this.subProjects.find(p => p.project_id === this.chat.project_id) ||
              this.$project
    },
    parentChat () {
      return this.$projects.allChats.find(c => c.id === this.chat?.parent_id)
    },
    chatFiles() {
      return [...this.chat.file_list||[], ...this.parentChat?.file_list||[]]
    }
  },
  methods: {
    async saveChat() {
      this.editName = false
      await this.$projects.saveChat(this.chat)
    },
    async confirmDeleteChat() {
      this.confirmDelete = false
      const parent_id = this.chat.parent_id
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
      this.chat.file_list = (this.chat.file_list || []).filter(f => f !== file)
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
      this.$emit('chats')
    },
    async newSubChat() {
      this.showSubtaskModal = true
    },
    createSubtask() {
      if (this.subtaskName.trim()) {
        this.$emit('sub-task', {
          parent: this.chat,
          name: this.subtaskName,
          description: this.subtaskDescription
        })
        this.resetSubtaskModal()
      }
    },
    cancelSubtask() {
      this.resetSubtaskModal()
    },
    resetSubtaskModal() {
      this.showSubtaskModal = false
      this.subtaskName = ''
      this.subtaskDescription = ''
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
    setChatMode(mode, profile) {
      this.chat.mode = mode
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
    naviageToParent(parentChat) {
      if (parentChat) {
        this.$emit('chat', parentChat)
      } else {
        this.navigateToChats()
      }
    },
    onExport() {
      this.$ui.copyTextToClipboard(JSON.stringify(this.chat, null, 2))
    },
    async onAddProfile() {
      this.showAddProfile = true
    }
  }
}
</script>