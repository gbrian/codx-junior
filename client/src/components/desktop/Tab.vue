<script setup>
import ProjectDetailt from '../ProjectDetailt.vue';
</script>
<template>
  <div class="flex gap-1 items-center pt-1">
    <ProjectDetailt iconify 
        :iconSize="5" 
        v-model="project" 
        @click.stop=""
        v-if="projectId"
    />
    {{ tabName }}
    <span class="click hover:text-warning" @click="onClose">
      <i class="fa-solid fa-xmark"></i>
    </span>
  </div>
</template>
<script>
export default {
  props: ['params'],
  data () {
    return {
      project: null,
      chat: null
    }
  },
  created() {
    this.chat = this.$service.chat.findChat(this.params.params.chat)
    this.project = this.$projects.allProjectsById[this.projectId]
  },
  computed: {
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
  methods: {
    onClose() {
      this.containerApi.removePanel(this.panel)
    }
  }
}
</script>