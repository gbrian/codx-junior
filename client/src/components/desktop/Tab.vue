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
    // Read the app from the live store (not the static panel snapshot) so
    // runtime app-info updates — such as the active board name — are reflected
    // in the tab without recreating the panel.
    app() {
      const app = this.params?.params?.app
      return (app?.tabId && this.$storex.ui.openApps[app.tabId]) || app
    },
    // Workspace panels carry the raw workspace (name, path, …) in params under
    // the `workspace` key; fall back to the legacy `app` slot for old payloads.
    workspace() {
      return this.params?.params?.workspace || this.app
    },
    // Name of the board the panel is currently showing. The board view
    // publishes it into the app params when the active board changes.
    boardName() {
      return this.app?.params?.boardName || null
    },
    tabName() {
      // Precedence matters: chats and boards keep their name first, then the
      // workspace object, then the app name/title. Adding `app?.name` lets a
      // workspace opened with a name-only payload (no `workspace` in params)
      // still surface the workspace `name` instead of the generic title.
      return this.chat?.name ||
        this.boardName ||
        this.workspace?.name ||
        this.workspace?.title ||
        this.app?.name ||
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