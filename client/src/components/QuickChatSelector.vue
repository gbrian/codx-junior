<script setup>
import ProjectDetailt from './ProjectDetailt.vue'
</script>

<template>
  <div class="dropdown dropdown-end">
    <button 
      class="btn btn-sm btn-ghost gap-2 hover:bg-base-200"
      tabindex="0"
    >
      <i class="fa-solid fa-comments"></i>
    </button>
    <div 
      tabindex="0" 
      class="dropdown-content z-50 menu p-2 shadow bg-base-100 rounded-lg border border-white/40 w-56"
    >
      <ProjectDetailt 
        :model-value="null"
        @select="onProjectSelected"
        :options="{ showIcon: true, showFolders: false }"
        position="dropdown-end"
      />
    </div>
  </div>
</template>

<script>
export default {
  methods: {
    async onProjectSelected(project) {
      if (project) {
        await this.$service.chat.newQuickChat({ project })
      }
    }
  }
}
</script>