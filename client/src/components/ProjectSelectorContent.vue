<script setup>
import NewProject from './project/NewProject.vue'
import ProjectList from './ProjectList.vue'
</script>

<template>
  <div class="flex flex-col gap-4 flex-1 h-full overflow-hidden">
    <div class="flex-1 overflow-hidden" v-if="!showNewProject">
      <ProjectList
        class="h-full"
        :current-project="currentProject"
        @select-project="$emit('select-project', $event)"
        @open-new-project="$emit('open-new-project')"
      />
    </div>

    <div v-else class="flex-1 overflow-y-auto overflow-x-hidden">
      <NewProject @close="$emit('close-new-project')" />
    </div>
  </div>
</template>

<script>
export default {
  props: {
    currentProject: Object,
    showNewProject: Boolean
  },
  emits: ['select-project', 'open-new-project', 'close-new-project']
}
</script>