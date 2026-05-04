<script setup>
import moment from 'moment'
import ProfileAvatar from '../profile/ProfileAvatar.vue'
import UserAvatar from '../user/UserAvatar.vue'
import TaskSettings from './TaskSettings.vue';
import CheckLists from '../chat/CheckLists.vue'
import ChatIcon from '../chat/ChatIcon.vue'
</script>

<template>
  <div :class="['p-2 shadow-lg rounded-lg', parentChat ? 'bg-base-100' : 'bg-base-300']">
    <div v-if="image" :style="`background-image: url(${image.src})`" class="bg-contain bg-no-repeat bg-center h-28 bg-base-300"></div>
    <div class="h-full flex flex-col justify-between gap-2">
      <div>
        <div v-if="parentChat" class="text-xs text-primary/40 hover:text-primary text-nowrap overflow-hidden" @click.stop="$chats.setActiveChat(parentChat)">
          {{ parentChat.name }}
        </div>
        <div class="flex justify-between">
          <div class="flex flex-col">
            <div class="font-semibold tracking-wide text-sm flex gap-2 mt-1">
              <ProfileAvatar :profile="profile" v-if="profile" @click.stop="" />
              <ChatIcon :mode="task.mode" />
              <span class="click tooltip" @click.stop="toggleChatPinned"
                data-tip="Bookmark"
              >
                <i class="text-warning fa-solid fa-bookmark" v-if="task.pinned" ></i>
                <i class="fa-regular fa-bookmark" v-else></i>
              </span>
              <div class="overflow-hidden h-10 overflow-auto" :title="task.name">
                {{ task.name }}
              </div>
            </div>
            <div class="text-xs flex" v-if="chatProject?.project_id !== $project.project_id">
            <div class="avatar mr-1">
              <div class="w-4 h-4 rounded-full">
                <img :src="chatProject?.project_icon"/>
              </div>
            </div>
            {{ chatProject?.project_name }}
          </div>
        </div>
         <div class="flex gap-2 items-center"> 
            <button class="btn btn-circle btn-sm" @click.stop="openSettingsModal">
              <i class="fas fa-cog"></i>
            </button>
          </div>
        </div>
      </div>
      <div class="text-xs overflow-auto max-h-20"
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
        </div>
      </div>
      <div class="flex flex-col gap-1">
          <span class="text-xs tooltip text-info"
            :data-tip="file"
            v-for="file in task.file_list" :key="file">
            <i class="fa-solid fa-paperclip"></i> {{ file.split('/').pop() }}
            <i class="click fa-solid fa-copy" @click.stop="$ui.copyTextToClipboard(file)"></i>
          </span>
      </div>
      <div class="grow"></div>
      <div class="flex justify-between items-center">
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
    <CheckLists class="mb-2" :chat="task" @change="saveTask" v-if="false" />
      
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
      return this.$chats.chats[this.task.parent_id]
    },
    updating() {
      const { chat, message } = this.$session.lastEvent || {}
      return message && chat?.id === this.task.id
    },
    profile() {
      return this.$projects.profiles?.find(p => p.name === this.task.profiles[0])
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
    },
    saveTask() {
      this.$projects.saveChatInfo(this.task)
    },
    toggleChatPinned() {
      this.task.pinned = !this.task.pinned
      this.saveTask()  
    }
  }
}
</script>