<script setup>
import moment from 'moment'
import ProfileAvatar from '../profile/ProfileAvatar.vue'
import UserAvatar from '../user/UserAvatar.vue'
</script>

<template>
  <div :class="['p-2 shadow-lg rounded-lg', parentChat ? 'bg-base-100' : 'bg-base-300']">
    <div v-if="image" :style="`background-image: url(${image.src})`" class="bg-contain bg-no-repeat bg-center h-28 bg-base-300"></div>
    <div class="flex flex-col justify-between gap-2">
      <div>
        <div class="flex justify-between">
          <div class="tracking-wide text-sm flex gap-2">
            <div class="avatar" :title="taskProject.project_name" v-if="taskProject !== $project">
              <div class="w-6 h-6 rounded-full">
                <img :src="taskProject.project_icon"/>
              </div>
            </div>
            <UserAvatar :width="5" :user="user" v-for="user in taskUsers" :key="user.username">
            </UserAvatar>  
            <div>
              <div class="flex gap-2">
                <ProfileAvatar :profile="profile" v-if="profile" @click.stop="" />
                <div class="overflow-hidden overflow-auto font-bold" :title="task.name">
                  {{ task.name }}
                </div>
              </div>
              <span :class="['text-xs']">{{ formattedDate }}</span>
            </div>
          </div>
          <div class="flex gap-2 items-center">
            <div :class="`badge badge-sm badge-outline badge-${badgeColor[task.mode]}`">{{ task.mode }}</div>
          </div>
        </div>
      </div>
      <div class="text-xs overflow-auto h-16">
        {{ task.description }}
      </div>
      <div class="flex justify-between items-center">
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
    </div>
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
    }
  }
}
</script>