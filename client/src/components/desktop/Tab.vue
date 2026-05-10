<script setup>
import AppIcon from '../apps/AppIcon.vue';
</script>
<template>
  <div class="flex gap-1 items-center justify-between px-3 py-1 bg-base-100 hover:bg-base-300 rounded-xl w-40 text-md">
    <div class="w-4/5 flex gap-1 items-center truncate overflow-hidden">
      <AppIcon :app="app" />
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
      chat: null
    }
  },
  async created() {
    console.log("Tab params", this.params)
    this.project = this.$projects.allProjectsById[this.projectId]
    if (this.params.params.chat)
        this.chat = await this.$service.chat.findChat(this.params.params.chat)
  },
  computed: {
    app() {
      return this.params.params.app
    },
    tabName() {
      return this.chat?.name || this.params.params.tabName
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
    }
  },
  watch: {
    chat(newVal, oldVal) {
        console.log("Chat has changed", this.chat)
    }
  },
  methods: {
    onClose() {
      this.containerApi.removePanel(this.panel)
    }
  }
}
</script>
<style lang="css">

.dv-tabs-and-actions-container {
    background-color: inherit;
    box-sizing: unset;
    height: inherit;
    font-size: inherit;
}

.dv-tabs-and-actions-container {
  height: fit-content;
}
.dv-tab {
  font-size: large;
}
.dv-groupview.dv-active-group > .dv-tabs-and-actions-container .dv-tabs-container > .dv-tab.dv-active-tab {
    background-color: inherit;
    color: inherit;
}
</style>