<script setup>
import AppIcon from '../apps/AppIcon.vue'
</script>
<template>
  <div class="flex gap-1 items-center justify-between px-3 py-1 bg-base-100 hover:bg-base-300 rounded-xl w-40 text-md">
    <div class="w-4/5 flex gap-1 items-center truncate overflow-hidden">
      <!-- Pass loading state to AppIcon so it shows the ring inside the icon area -->
      <AppIcon :app="app" :loading="isUpdating" />
      <div class="grow truncate overflow-hidden">{{ tabName }}</div>
    </div>
    <div class="click hover:text-warning shrink-0" @click="onClose">
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
    app() {
      return this.params.params.app
    },
    tabName() {
      return this.chat?.name || 
        this.app?.title ||
        this.params.params.tabName
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
      return this.params.params.project_id
    },
    isUpdating() {
        return this.chat?.id && this.$storex.chats.isChatUpdating(this.chat.id)
    }
  },
  methods: {
    onClose() {
      this.containerApi.removePanel(this.panel)
    }
  }
}
</script>