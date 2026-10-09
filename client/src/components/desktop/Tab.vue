<script setup>
import AppIcon from '../apps/AppIcon.vue'
</script>
<template>
  <div
    class="codx-tab flex gap-1 items-center justify-between px-1 py-0.5 border rounded-xl w-40 text-md"
    :draggable="!!chat"
    :class="{ 'cursor-grab active:cursor-grabbing': !!chat }"
    @dragstart="onDragStart"
  >
    <div class="w-4/5 flex gap-1 items-center truncate overflow-hidden">
      <!-- Pass loading state to AppIcon so it shows the ring inside the icon area -->
      <AppIcon :app="app || workspace" :loading="isUpdating" />
      <div class="grow truncate overflow-hidden">{{ tabName }}</div>
    </div>
    <div class="click hover:text-warning shrink-0 mr-2" @click="onClose">
      <i class="fa-solid fa-xmark fa-sm"></i>
    </div>
  </div>
</template>
<script>

export default {
  props: ['params'],
  data() {
    return {
      project: null,
    }
  },
  async created() {
    this.project = this.$projects.allProjectsById[this.projectId]
  },
  computed: {
    chat() {
      const chatId = this.params?.params?.chat?.id
      return this.$storex.chats.chats[chatId]
    },
    // Workspace panels carry the raw workspace (name, path, …) in params under
    // the `workspace` key; fall back to the legacy `app` slot for old payloads.
    workspace() {
      return this.params?.params?.workspace || this.params?.params?.app
    },
    app() {
      return this.params?.params?.app
    },
    tabName() {
      return this.chat?.name ||
        this.workspace?.name ||
        this.workspace?.title ||
        this.app?.title ||
        this.params?.params?.tabName
    },
    api() {
      return this.params.api
    },
    containerApi() {
      return this.params.containerApi
    },
    panel() {
      return this.api.panel
    },
    projectId() {
      return this.params?.params?.project_id
    },
    isUpdating() {
      return this.$storex.chats.isChatUpdating(this.chat?.id)
    }
  },
  methods: {
    onDragStart(event) {
      // Only register a sprint task id when the tab is backed by a chat
      if (!this.chat) return
      event.dataTransfer.setData('sprintTaskId', this.chat.id)
      event.dataTransfer.effectAllowed = 'move'
    },
    onClose() {
      this.containerApi.removePanel(this.panel)
    }
  }
}
</script>