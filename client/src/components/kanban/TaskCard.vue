<script setup>
import moment from 'moment'
import ProfileAvatar from '../profile/ProfileAvatar.vue'
import TaskSettings from './TaskSettings.vue'
import ChatIcon from '../chat/ChatIcon.vue'
</script>

<template>
  <div class="rounded-2xl bg-base-100/80 backdrop-blur border border-white/10 shadow hover:shadow-lg transition-all duration-200 group">

    <!-- Cover image with gradient overlay -->
    <div v-if="image" class="relative h-28 rounded-t-2xl overflow-hidden">
      <div :style="`background-image: url(${image.src})`" class="bg-cover bg-center absolute inset-0"></div>
      <div class="absolute inset-0 bg-gradient-to-t from-base-100 to-transparent"></div>
    </div>

    <div class="p-3 flex flex-col gap-2">

      <!-- Title row -->
      <div class="flex items-start justify-between gap-2">
        <div class="flex items-center gap-2 min-w-0 flex-1">
          <ProfileAvatar :profile="profile" v-if="profile" @click.stop="" class="shrink-0" />
          <div class="min-w-0">
            <!-- Parent breadcrumb -->
            <div v-if="parentChat"
              class="text-xs text-primary/40 hover:text-primary cursor-pointer truncate"
              @click.stop="$chats.setActiveChat(parentChat)">
              {{ parentChat.name }} /
            </div>
            <div class="font-bold text-sm truncate leading-tight" :title="task.name">
              {{ task.name }}
            </div>
          </div>
        </div>

        <!-- Actions: always visible on mobile, group-hover on desktop -->
        <div class="flex gap-1 shrink-0 opacity-40 group-hover:opacity-100 transition-opacity">
          <ChatIcon :mode="task.mode" />
          <button class="btn btn-ghost btn-xs btn-circle" @click.stop="openSettingsModal">
            <i class="fas fa-cog text-xs"></i>
          </button>
        </div>
      </div>

      <!-- Cross-project label -->
      <div v-if="chatProject?.project_id !== $project.project_id"
        class="flex items-center gap-1">
        <div class="avatar">
          <div class="w-4 h-4 rounded-full ring ring-primary/20">
            <img :src="chatProject?.project_icon" />
          </div>
        </div>
        <span class="text-xs text-primary/60 font-medium">{{ chatProject?.project_name }}</span>
      </div>

      <!-- Description with expand toggle -->
      <div v-if="task.description" class="text-xs text-base-content/60 leading-relaxed">
        <span :class="expandDescription ? '' : 'line-clamp-3'">{{ task.description }}</span>
        <button class="ml-1 text-info hover:underline text-xs" @click.stop="expandDescription = !expandDescription">
          {{ expandDescription ? '▲ less' : '▼ more' }}
        </button>
      </div>

      <!-- Tags row -->
      <div class="flex flex-wrap gap-1" v-if="task.tags?.length">
        <span v-for="tag in task.tags" :key="tag"
          class="px-2 py-0.5 rounded-full bg-info/10 text-info text-xs font-medium">
          #{{ tag }}
        </span>
      </div>

      <!-- Files -->
      <div class="flex flex-col gap-0.5" v-if="task.file_list?.length">
        <div v-for="file in task.file_list" :key="file"
          class="flex items-center gap-1 text-xs text-base-content/50 hover:text-base-content/80 transition-colors group/file">
          <i class="fa-solid fa-paperclip"></i>
          <span class="truncate flex-1 tooltip" :data-tip="file">{{ file.split('/').pop() }}</span>
          <i class="fa-solid fa-copy cursor-pointer opacity-0 group-hover/file:opacity-100 transition-opacity"
            @click.stop="$ui.copyTextToClipboard(file)"></i>
        </div>
      </div>

      <!-- Footer -->
      <div class="flex items-center justify-between mt-1">
        <div class="flex items-center gap-1.5">
          <!-- Subtasks pill -->
          <div v-if="subTasks.length"
            class="flex items-center gap-1 px-2 py-0.5 rounded-full bg-warning/20 text-warning text-xs font-bold tooltip"
            :data-tip="`${subTasks.length} sub tasks`">
            <i class="fa-regular fa-file-lines"></i>
            {{ subTasks.length }}
          </div>
          <!-- Updating indicator -->
          <span v-if="updating" class="loading loading-dots loading-xs text-primary"></span>
        </div>
        <span :class="['text-xs', isToday ? 'text-success font-semibold' : 'text-base-content/30']">
          {{ formattedDate }}
        </span>
      </div>

    </div>

    <!-- Settings Modal -->
    <modal v-if="isSettingsModalOpen" @click.stop>
      <TaskSettings :taskData="taskData" @close="discardChanges" />
    </modal>
  </div>
</template>

<script>
export default {
  props: ['task'],
  data() {
    return {
      isSettingsModalOpen: false,
      taskData: {},
      expandDescription: false
    }
  },
  computed: {
    image() {
      const image = this.task.messages?.find(m => m.images?.length)?.images[0]
      return image ? JSON.parse(image) : null
    },
    isToday() {
      return moment(0, "HH").diff(this.task.updated_at, "days") === 0
    },
    formattedDate() {
      return this.isToday
        ? moment(this.task.updated_at).format('HH:mm')
        : moment(this.task.updated_at).format('MMM DD, YYYY')
    },
    subTasks() {
      return this.$storex.projects.allChats
        .filter(c => c.parent_id === this.task.id)
        .sort((a, b) => (a.updated_at || a.created_at) > (b.updated_at || b.created_at) ? -1 : 1)
    },
    chatProject() {
      return this.$projects.allProjects.find(p => p.project_id === this.task.project_id)
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
    }
  },
  methods: {
    openSettingsModal() {
      this.isSettingsModalOpen = true
      this.taskData = { ...this.task }
    },
    discardChanges() {
      this.isSettingsModalOpen = false
    },
    saveTask() {
      this.$projects.saveChatInfo(this.task)
    }
  }
}
</script>