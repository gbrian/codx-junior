<script setup>
import moment from 'moment'
import ChatIcon from '../chat/ChatIcon.vue'
</script>
<template>
  <div :class="['p-2 shadow-lg rounded-lg flex flex-col gap-2', parentChat ? 'bg-base-100' : 'bg-base-300']">
    <div v-if="image" :style="`background-image: url(${image.src})`" class="bg-contain bg-no-repeat bg-center h-28 bg-base-300"></div>
    <div class="flex flex-col gap-2">
      <div>
        <div v-if="parentChat" class="text-xs text-primary/40 hover:text-primary text-nowrap overflow-hidden" @click.stop="$projects.setActiveChat(parentChat)">
          {{ parentChat.name }}
        </div>
        <div class="flex justify-between">
          <div class="font-semibold tracking-wide text-sm flex gap-2">
            <div class="rounded-full">
              <ChatIcon :mode="task.mode" />
            </div>
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
          <input type="text" class="input input-bordered w-full" v-model="modalData.name">
        </label>
        <label class="block mt-4">
          <span>Board</span>
          <input type="text" class="input input-bordered w-full" v-model="modalData.board">
        </label>
        <label class="block mt-4">
          <span>Column</span>
          <input type="text" class="input input-bordered w-full" v-model="modalData.column">
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
    <progress class="progress w-full" v-if="updating"></progress>
  </div>
</template>
<script>
export default {
  props: ['task'],
  data() {
    return {
      isSettingsModalOpen: false,
      modalData: {
        name: this.task.name,
        board: '',
        column: ''
      },
      badgeColor: {
        task: "primary",
        chat: "accent"
      }
    }
  },
  computed: {
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
      console.log('Task Saved:', this.modalData)
      this.closeSettingsModal()
    },
    deleteTask() {
      this.closeSettingsModal()
      this.$projects.deleteChat(this.task)
    }
  }
}
</script>