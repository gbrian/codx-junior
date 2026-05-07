<script setup>
import ProjectDetailt from '../ProjectDetailt.vue';
import AppIcon from '../apps/AppIcon.vue';
</script>
<template>
  <div class="flex gap-1 items-center pt-1">
    <ProjectDetailt iconify 
        :iconSize="5" 
        v-model="project" 
        @click.stop=""
        v-if="projectId"
    />
    <AppIcon :app="app" v-if="app"/>
    {{ tabName }}
    <span class="click hover:text-warning" @click="onClose">
      <i class="fa-solid fa-xmark"></i>
    </span>
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