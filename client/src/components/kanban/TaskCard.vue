<script setup>
import moment from 'moment'
import ProfileAvatar from '../profile/ProfileAvatar.vue'
import TaskSettings from './TaskSettings.vue'
import CheckLists from '../chat/CheckLists.vue'
import ChatIcon from '../chat/ChatIcon.vue'
</script>

<template>
  <div class="rounded-xl border border-base-300 bg-base-100 shadow-sm hover:shadow-md transition-shadow duration-200 overflow-hidden">
    <!-- Top color accent bar -->
    <div :class="['h-1 w-full', task.pinned ? 'bg-warning' : 'bg-primary/30']"></div>

    <!-- Cover image -->
    <div v-if="image" :style="`background-image: url(${image.src})`"
      class="bg-cover bg-center h-24 w-full">
    </div>

    <!-- Header Row -->
    <div class="flex items-center gap-2 px-3 pt-3 pb-1">
      <ProfileAvatar :profile="profile" v-if="profile" class="shrink-0" @click.stop="" />
      <ChatIcon :mode="task.mode" class="shrink-0" />
      <div class="flex-1 min-w-0">
        <div v-if="parentChat" class="text-xs text-primary/50 hover:text-primary truncate cursor-pointer"
          @click.stop="$chats.setActiveChat(parentChat)">
          ↳ {{ parentChat.name }}
        </div>
        <div class="font-semibold text-sm truncate" :title="task.name">{{ task.name }}</div>
      </div>
      <button class="btn btn-ghost btn-xs btn-circle shrink-0" @click.stop="openSettingsModal">
        <i class="fas fa-ellipsis-v"></i>
      </button>
    </div>

    <!-- Project badge (cross-project) -->
    <div class="px-3 pb-1" v-if="chatProject?.project_id !== $project.project_id">
      <div class="flex items-center gap-1 text-xs text-base-content/50">
        <div class="avatar">
          <div class="w-3 h-3 rounded-full">
            <img :src="chatProject?.project_icon" />
          </div>
        </div>
        {{ chatProject?.project_name }}
      </div>
    </div>

    <!-- Description -->
    <div class="px-3 pb-2" v-if="task.description">
      <p :class="['text-xs text-base-content/70 leading-relaxed', expandDescription ? '' : 'line-clamp-2']">
        {{ task.description }}
      </p>
      <span class="text-xs text-info cursor-pointer hover:underline"
        @click.stop="expandDescription = !expandDescription">
        {{ expandDescription ? 'less' : 'more' }}
      </span>
    </div>

    <!-- Tags -->
    <div class="px-3 pb-2 flex flex-wrap gap-1" v-if="task.tags?.length">
      <span v-for="tag in task.tags" :key="tag"
        class="badge badge-outline badge-xs text-info border-info/40">
        #{{ tag }}
      </span>
    </div>

    <!-- Files -->
    <div class="px-3 pb-2 flex flex-col gap-1" v-if="task.file_list?.length">
      <span v-for="file in task.file_list" :key="file"
        class="text-xs text-base-content/60 flex items-center gap-1 tooltip" :data-tip="file">
        <i class="fa-solid fa-paperclip text-xs"></i>
        <span class="truncate max-w-full">{{ file.split('/').pop() }}</span>
        <i class="fa-solid fa-copy cursor-pointer hover:text-info" @click.stop="$ui.copyTextToClipboard(file)"></i>
      </span>
    </div>

    <!-- Footer -->
    <div class="flex items-center justify-between px-3 py-2 border-t border-base-300/50 bg-base-200/30">
      <span :class="['text-xs', isToday ? 'text-success font-bold' : 'text-base-content/40']">
        <i class="fa-regular fa-clock mr-1"></i>{{ formattedDate }}
      </span>
      <div class="flex items-center gap-2">
        <div v-if="subTasks.length" class="badge badge-warning badge-sm gap-1">
          <i class="fa-regular fa-file-lines text-xs"></i>
          {{ subTasks.length }}
        </div>
        <progress v-if="updating" class="progress progress-primary w-12 h-1"></progress>
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
      let image = this.task.messages?.find(m => m.images?.length)?.images[0]
      return image ? JSON.parse(image) : null
    },
    isToday() {
      return moment(0, "HH").diff(this.task.updated_at, "days") === 0
    },
    formattedDate() {
      return this.isToday
        ? moment(this.task.updated_at).format('HH:mm')
        : moment(this.task.updated_at).format('MMM DD')
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