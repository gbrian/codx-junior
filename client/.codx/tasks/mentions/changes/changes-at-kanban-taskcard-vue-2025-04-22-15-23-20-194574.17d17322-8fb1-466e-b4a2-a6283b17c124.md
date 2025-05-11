# [[{"id": "17d17322-8fb1-466e-b4a2-a6283b17c124", "doc_id": null, "project_id": null, "parent_id": null, "status": "", "tags": ["skip_knowledge"], "file_list": [], "profiles": [], "users": [], "name": "changes-at-kanban-taskcard-vue-2025-04-22-15-23-20-194574", "created_at": "2025-04-22 15:16:31.874631", "updated_at": "2025-04-22T15:23:35.423954", "mode": "chat", "kanban_id": "", "column_id": "", "board": "mentions", "column": "changes", "chat_index": 0, "url": "", "branch": "", "file_path": "", "model": "", "visibility": ""}]]
## [[{"doc_id": "2db5fff3-fe3b-4649-8a87-6270aa65c13d", "role": "user", "task_item": "", "hide": false, "improvement": false, "created_at": "2025-04-22 15:16:31.873061", "updated_at": "2025-04-22 15:16:31.873087", "images": [], "files": [], "meta_data": {}, "profiles": [], "user": null}]]

                      ```
                      <script setup>
import moment from 'moment'
import ProfileSelector from '@/components/profile/ProfileSelector.vue'
import ProfileAvatar from '../profile/ProfileAvatar.vue';
import UserAvatar from '../user/UserAvatar.vue';
</script>
<template>
  <div :class="['p-2 shadow-lg rounded-lg', parentChat ? 'bg-base-100' : 'bg-base-300']">
    <div v-if="image" :style="`background-image: url(${image.src})`" class="bg-contain bg-no-repeat bg-center h-28 bg-base-300"></div>
    <div class="h-full flex flex-col justify-between gap-2">
      <div>
        <div v-if="parentChat" class="text-xs text-primary/40 hover:text-primary text-nowrap overflow-hidden" @click.stop="$projects.setActiveChat(parentChat)">
          {{ parentChat.name }}
        </div>
        <div class="flex justify-between">
          <div class="font-semibold tracking-wide text-sm flex gap-2 mt-1">
            <UserAvatar :width="7" :user="user" v-for="user in taskUsers" :key="user.username">
              <li @click="removeUser(user)" ><a>Remove</a></li>
            </UserAvatar>  
                    
            <ProfileAvatar :profile="profile" v-if="profile" @click.stop="" />
            <div class="overflow-hidden">{{ task.name }}</div>
          </div>
          <div class="flex gap-2 items-center">
            <div :class="`badge badge-outline badge-${badgeColor[task.mode]}`">{{ task.mode }}</div>
          </div>
        </div>
      </div>
      <div class="flex justify-between items-center">
        <span :class="['text-xs', isToday ? 'font-bold' : 'text-gray-600']">{{ formattedDate }}</span>
        <div class="flex gap-1 justify-end">
          <div v-for="tag in task.tags" :key="tag" class="font-bold text-xs text-info flex gap-2">
            #{{ tag }}
          </div>
          <span class="text-xs tooltip"
            :data-tip="`${task.file_list?.length} files`"
            v-if="task.file_list?.length">
            <i class="fa-solid fa-paperclip"></i>
          </span>
        </div>
      </div>
      <div class="grow"></div>
      <div class="flex justify-between items-center">
        <div class="flex justify-end">
          <button class="btn btn-circle btn-sm" @click.stop="openSettingsModal">
            <i class="fas fa-cog"></i>
          </button>
        </div>
        <div class="flex justify-between items-center badge badge-warning" v-if="subTasks.length">
          <div class="text-xs font-bold tooltip tooltip-left" :data-tip="`${subTasks.length} sub tasks`">
            {{ subTasks.length }}
            <i class="fa-regular fa-file-lines"></i>
          </div>
          <div v-if="chatProject" class="badge badge-sm badge-warning">
            {{ chatProject.project_name }}
          </div>
        </div>
      </div>
    </div>
    <modal v-if="isSettingsModalOpen" @click.stop>
      <h3 class="font-bold text-lg">Task Settings</h3>
      <div class="py-4">
        <label class="block">
          <span>Task Name</span>
          <input type="text" class="input input-bordered w-full" v-model="taskData.name">
        </label>
        <label class="block mt-4">
          <span>Board</span>
          @codx-ok, please-wait...: add a select with boards and store the selected board id at taskBoardId
        </label>
        <label class="block mt-4">
          <span>Column</span>
          <input type="text" class="input input-bordered w-full" v-model="taskData.column">
        </label>
        <label class="block mt-4">
          <span>Profiles</span>
          <button class="btn btn-sm" @click="showProfileSelector = true">
            <i class="fa-solid fa-plus"></i>
          </button>
          <div class="flex gap-2">
            <div class="badge badge-sm badge-primary" v-for="profile in taskData.profiles" :key="profile">
              {{ profile }}
            </div>
          </div>
        </label>
      </div>
      <div class="modal-action">
        <button class="btn btn-ghost" @click="discardChanges">Discard</button>
        <button class="btn btn-primary" @click="saveChanges">Save</button>
      </div>
      <div tabindex="0" class="collapse">
        <input type="checkbox" />
        <div class="collapse-title font-semibold text-error">Delete</div>
        <div class="collapse-content text-sm">
          <button class="mt-2 btn btn-error btn-wide" @click.stop="deleteTask">Confirm delete</button>
        </div>
      </div>
    </modal>
    <modal close="true" @close="showProfileSelector = false" v-if="showProfileSelector">
      <ProfileSelector @select="addProfile($event)" :project="$project" />
    </modal>
    <progress class="progress w-full" v-if="updating"></progress>
  </div>
</template>
<script>
export default {
  props: ['task'],
  data() {
    return {
      showProfileSelector: false,
      isSettingsModalOpen: false,
      taskData: {
        name: this.task.name,
        board: '',
        column: '',
        profiles: []
      },
      badgeColor: {
        task: "primary",
        chat: "accent"
      }
    }
  },
  computed: {
    taskUsers() {
      return this.$storex.api.users.filter(({ username }) => this.task.users.includes(username))
    },
    image() {
      let image = this.task.messages?.find(m => m.images.length)?.images[0]
      return image ? JSON.parse(image) : null
    },
    isToday() {
      const updatedAt = this.task.updated_at
      return moment(0, "HH").diff(updatedAt, "days") === 0
    },
    formattedDate() {
      const updatedAt = this.task.updated_at
      return this.isToday ? moment(updatedAt).format('HH:mm:ss') : moment(updatedAt).format('YYYY-MM-DD hh:mm:ss')
    },
    subTasks() {
      return this.$storex.projects.allChats.filter(c => c.parent_id === this.task.id)
        .sort((a, b) => (a.updated_at || a.created_at) > (b.updated_at || b.created_at) ? -1 : 1)
    },
    chatProject() {
      return this.$projects.allProjects.find(p => p.project_id === this.task.project_id && p.project_id !== this.$project.project_id)
    },
    parentChat() {
      return this.$projects.chats[this.task.parent_id]
    },
    updating() {
      const { messages } = this.task
      if (!messages?.length) {
        return false
      }
      return moment().diff(
        moment(messages[messages.length - 1].updated_at)
      , 'seconds') < 10
    },
    profile() {
      return this.$projects.profiles.find(p => p.name === this.task.profiles[0])
    },
    boards() {
      return this.$projects.kanban.boards
    }
  },
  methods: {
    openSettingsModal() {
      this.isSettingsModalOpen = true
    },
    closeSettingsModal() {
      this.isSettingsModalOpen = false
    },
    discardChanges() {
      this.closeSettingsModal()
    },
    saveChanges() {
      this.$projects.saveChatInfo(this.taskData)
      this.closeSettingsModal()
    },
    deleteTask() {
      this.closeSettingsModal()
      this.$projects.deleteChat(this.task)
    },
    addProfile(profile) {
      if (!this.taskData.profiles.includes(profile.name)) {
        this.taskData.profiles.push(profile.name)
      }
      this.showProfileSelector = false
    }
  }
}
</script>
                      ```
                      
                      User commented in line 68: add a select with boards and store the selected board id at taskBoardId
                      
## [[{"doc_id": "e679a1d6-822a-4e72-aea7-49755e791974", "role": "user", "task_item": "", "hide": false, "improvement": false, "created_at": "2025-04-22 15:16:31.873061", "updated_at": "2025-04-22 15:16:31.873087", "images": [], "files": [], "meta_data": {}, "profiles": ["daisyui_components", "Vue files"], "user": null}]]
Best practices for this file:
                  Project uses DaisyUI for components, use them instead basic HTML elements
# Vue vuejs coding best pratices
Vue files must always follow this structure in this order.
No other elements are valid:
```example vue file
<script setup>
import Component from './component.vue'
import markdown from 'mardown'
</script>
<template>
<div class="w.full h-full flex gap-2">
</div>
</template>
<script>
export default {
props: [].
data (){
 return { myVariable: null }
},
computed: {},
watch: {},
methods: {}
}
</sctipt>
```
* export default component object
* Use component "data" method to return an object variables
* Use component "computed" to define computed properties
" Use component "methods" to define component methods 
* "script setup" section contains ONLY imports, no variables, properties bnor methods
* Use TailwindCSS classes for styling, always consider mobile styles
* Vue component definition will be exporting a default object like, without ref, nor computed imports
* Don't use ";" in the javascript or typescript code
* Avoid long functions
* Add short and concise comments for complex functions
* Don't use <style> elements, use TailWindCSS classes
                  
## [[{"doc_id": "88b57b87-ccdb-4a02-bc83-52028207d96a", "role": "user", "task_item": "", "hide": false, "improvement": false, "created_at": "2025-04-22 15:16:31.873061", "updated_at": "2025-04-22 15:16:31.873087", "images": [], "files": [], "meta_data": {}, "profiles": [], "user": null}]]

              Rewrite full file content replacing codx instructions with the minimum changes as possible.
              Return only the file content without any further decoration or comments.
              Do not surround response with '```' marks, just content.
              
## [[{"doc_id": "6b752698-9cd7-4763-87ee-1d6687ff090a", "role": "assistant", "task_item": "", "hide": false, "improvement": false, "created_at": "2025-04-22 15:16:31.873061", "updated_at": "2025-04-22 15:16:31.873087", "images": [], "files": [], "meta_data": {"time_taken": 15.22887134552002, "first_chunk_time_taken": 4.1367175579071045, "model": "gpt-4o"}, "profiles": [], "user": null}]]
<script setup>
import moment from 'moment'
import ProfileSelector from '@/components/profile/ProfileSelector.vue'
import ProfileAvatar from '../profile/ProfileAvatar.vue'
import UserAvatar from '../user/UserAvatar.vue'
</script>

<template>
  <div :class="['p-2 shadow-lg rounded-lg', parentChat ? 'bg-base-100' : 'bg-base-300']">
    <div v-if="image" :style="`background-image: url(${image.src})`" class="bg-contain bg-no-repeat bg-center h-28 bg-base-300"></div>
    <div class="h-full flex flex-col justify-between gap-2">
      <div>
        <div v-if="parentChat" class="text-xs text-primary/40 hover:text-primary text-nowrap overflow-hidden" @click.stop="$projects.setActiveChat(parentChat)">
          {{ parentChat.name }}
        </div>
        <div class="flex justify-between">
          <div class="font-semibold tracking-wide text-sm flex gap-2 mt-1">
            <UserAvatar :width="7" :user="user" v-for="user in taskUsers" :key="user.username">
              <li @click="removeUser(user)" ><a>Remove</a></li>
            </UserAvatar>  
                    
            <ProfileAvatar :profile="profile" v-if="profile" @click.stop="" />
            <div class="overflow-hidden">{{ task.name }}</div>
          </div>
          <div class="flex gap-2 items-center">
            <div :class="`badge badge-outline badge-${badgeColor[task.mode]}`">{{ task.mode }}</div>
          </div>
        </div>
      </div>
      <div class="flex justify-between items-center">
        <span :class="['text-xs', isToday ? 'font-bold' : 'text-gray-600']">{{ formattedDate }}</span>
        <div class="flex gap-1 justify-end">
          <div v-for="tag in task.tags" :key="tag" class="font-bold text-xs text-info flex gap-2">
            #{{ tag }}
          </div>
          <span class="text-xs tooltip"
            :data-tip="`${task.file_list?.length} files`"
            v-if="task.file_list?.length">
            <i class="fa-solid fa-paperclip"></i>
          </span>
        </div>
      </div>
      <div class="grow"></div>
      <div class="flex justify-between items-center">
        <div class="flex justify-end">
          <button class="btn btn-circle btn-sm" @click.stop="openSettingsModal">
            <i class="fas fa-cog"></i>
          </button>
        </div>
        <div class="flex justify-between items-center badge badge-warning" v-if="subTasks.length">
          <div class="text-xs font-bold tooltip tooltip-left" :data-tip="`${subTasks.length} sub tasks`">
            {{ subTasks.length }}
            <i class="fa-regular fa-file-lines"></i>
          </div>
          <div v-if="chatProject" class="badge badge-sm badge-warning">
            {{ chatProject.project_name }}
          </div>
        </div>
      </div>
    </div>
    <modal v-if="isSettingsModalOpen" @click.stop>
      <h3 class="font-bold text-lg">Task Settings</h3>
      <div class="py-4">
        <label class="block">
          <span>Task Name</span>
          <input type="text" class="input input-bordered w-full" v-model="taskData.name">
        </label>
        <label class="block mt-4">
          <span>Board</span>
          <select class="input input-bordered w-full" v-model="taskBoardId">
            <option v-for="board in boards" :key="board.id" :value="board.id">{{ board.name }}</option>
          </select>
        </label>
        <label class="block mt-4">
          <span>Column</span>
          <input type="text" class="input input-bordered w-full" v-model="taskData.column">
        </label>
        <label class="block mt-4">
          <span>Profiles</span>
          <button class="btn btn-sm" @click="showProfileSelector = true">
            <i class="fa-solid fa-plus"></i>
          </button>
          <div class="flex gap-2">
            <div class="badge badge-sm badge-primary" v-for="profile in taskData.profiles" :key="profile">
              {{ profile }}
            </div>
          </div>
        </label>
      </div>
      <div class="modal-action">
        <button class="btn btn-ghost" @click="discardChanges">Discard</button>
        <button class="btn btn-primary" @click="saveChanges">Save</button>
      </div>
      <div tabindex="0" class="collapse">
        <input type="checkbox" />
        <div class="collapse-title font-semibold text-error">Delete</div>
        <div class="collapse-content text-sm">
          <button class="mt-2 btn btn-error btn-wide" @click.stop="deleteTask">Confirm delete</button>
        </div>
      </div>
    </modal>
    <modal close="true" @close="showProfileSelector = false" v-if="showProfileSelector">
      <ProfileSelector @select="addProfile($event)" :project="$project" />
    </modal>
    <progress class="progress w-full" v-if="updating"></progress>
  </div>
</template>

<script>
export default {
  props: ['task'],
  data() {
    return {
      showProfileSelector: false,
      isSettingsModalOpen: false,
      taskData: {
        name: this.task.name,
        board: '',
        column: '',
        profiles: []
      },
      badgeColor: {
        task: "primary",
        chat: "accent"
      },
      taskBoardId: ''
    }
  },
  computed: {
    taskUsers() {
      return this.$storex.api.users.filter(({ username }) => this.task.users.includes(username))
    },
    image() {
      let image = this.task.messages?.find(m => m.images.length)?.images[0]
      return image ? JSON.parse(image) : null
    },
    isToday() {
      const updatedAt = this.task.updated_at
      return moment(0, "HH").diff(updatedAt, "days") === 0
    },
    formattedDate() {
      const updatedAt = this.task.updated_at
      return this.isToday ? moment(updatedAt).format('HH:mm:ss') : moment(updatedAt).format('YYYY-MM-DD hh:mm:ss')
    },
    subTasks() {
      return this.$storex.projects.allChats.filter(c => c.parent_id === this.task.id)
        .sort((a, b) => (a.updated_at || a.created_at) > (b.updated_at || b.created_at) ? -1 : 1)
    },
    chatProject() {
      return this.$projects.allProjects.find(p => p.project_id === this.task.project_id && p.project_id !== this.$project.project_id)
    },
    parentChat() {
      return this.$projects.chats[this.task.parent_id]
    },
    updating() {
      const { messages } = this.task
      if (!messages?.length) {
        return false
      }
      return moment().diff(
        moment(messages[messages.length - 1].updated_at)
      , 'seconds') < 10
    },
    profile() {
      return this.$projects.profiles.find(p => p.name === this.task.profiles[0])
    },
    boards() {
      return this.$projects.kanban.boards
    }
  },
  methods: {
    openSettingsModal() {
      this.isSettingsModalOpen = true
    },
    closeSettingsModal() {
      this.isSettingsModalOpen = false
    },
    discardChanges() {
      this.closeSettingsModal()
    },
    saveChanges() {
      this.$projects.saveChatInfo(this.taskData)
      this.closeSettingsModal()
    },
    deleteTask() {
      this.closeSettingsModal()
      this.$projects.deleteChat(this.task)
    },
    addProfile(profile) {
      if (!this.taskData.profiles.includes(profile.name)) {
        this.taskData.profiles.push(profile.name)
      }
      this.showProfileSelector = false
    }
  }
}
</script>