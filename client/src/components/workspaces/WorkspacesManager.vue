<script setup>
import WorkspacesList from './WorkspacesList.vue'
import WorkspaceCreate from './WorkspaceCreate.vue'
</script>

<template>
  <div class="w-full h-full flex flex-col">
    <WorkspacesList 
      v-if="!isCreating"
      :project="project"
      @create="isCreating = true"
    />
    <WorkspaceCreate 
      v-else
      :project="project"
      @close="isCreating = false"
      @created="handleWorkspaceCreated"
    />
  </div>
</template>

<script>
export default {
  props: ['project'],
  data() {
    return {
      isCreating: false
    }
  },
  methods: {
    handleWorkspaceCreated(workspace) {
      this.isCreating = false
      // Refresh list or emit event to parent
      this.$emit('workspace-created', workspace)
    }
  }
}
</script>