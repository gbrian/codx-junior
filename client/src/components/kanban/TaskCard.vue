<script setup>
import moment from 'moment'
import ProfileAvatar from '../profile/ProfileAvatar.vue'
import UserAvatar from '../user/UserAvatar.vue'
import TaskSettings from './TaskSettings.vue';
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
            <div class="avatar" :title="taskProject.project_name" v-if="taskProject !== $project">
              <div class="w-6 h-6 rounded-full">
                <img :src="taskProject.project_icon"/>
              </div>
            </div>
            <UserAvatar :width="7" :user="user" v-for="user in taskUsers" :key="user.username">
              <li @click="removeUser(user)" ><a>Remove</a></li>
            </UserAvatar>  
                    
            <ProfileAvatar :profile="profile" v-if="profile" @click.stop="" />
            <div class="overflow-hidden h-10 overflow-auto" :title="task.name">{{ task.name }}</div>
          </div>
          <div class="flex gap-2 items-center">
            <div :class="`badge badge-outline badge-${badgeColor[task.mode]}`">{{ task.mode }}</div>
          </div>
        </div>
      </div>
      <div class="text-xs overflow-auto"
        :class="expandDescription ? '' : 'max-h-10'"
      >
        {{ task.description }}
      </div>
      <div class="text-xs text-info hover:underline click" 
        v-if="task.description" 
        @click.stop="expandDescription = !expandDescription">
        {{ expandDescription ? 'less' : 'more' }}
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
      <TaskSettings :taskData="taskData" @close="discardChanges" />
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
      badgeColor: {
        task: "primary",
        chat: "accent"
      },
      taskData: {},
      expandDescription: true
    }
  },
  computed: {
    taskUsers() {
      return this.$storex.api.userNetwork.filter(({ username }) => this.task.users?.includes(username))
    },
    image() {
      let image = this.task.messages?.find(m => m.images?.length)?.images[0]
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
      const { chat, message } = this.$session.lastEvent || {}
      return message && chat?.id === this.task.id
    },
    profile() {
      return this.$projects.profiles.find(p => p.name === this.task.profiles[0])
    },
    taskProject() {
      return this.$projects.allProjects.find(p => p.project_id === this.task.project_id) ||
                this.$project
    }
  },
  methods: {
    openSettingsModal() {
      this.isSettingsModalOpen = true
      this.taskData = { ...this.task }
    },
    closeSettingsModal() {
      this.isSettingsModalOpen = false
    },
    discardChanges() {
      this.closeSettingsModal()
    }
  }
}
</script>