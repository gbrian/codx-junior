<script setup>
import KanbanContainer from '@/components/kanban/KanbanContainer.vue'
</script>

<template>
  <div class="flex h-full w-full bg-[#111111] overflow-hidden text-white">
    <!-- Kanban Container with full responsive support -->
    <KanbanContainer class="flex-1 min-w-0 h-full" />
  </div>
</template>

<script>
export default {
  name: 'KanbanView',
  components: {
    KanbanContainer: () => import('@/components/kanban/KanbanContainer.vue')
  },
  data() {
    return {}
  },
  computed: {
    isMobile() {
      return this.$ui.isMobile
    }
  }
}
</script>

<style scoped>
/* Ensure proper layout for all screen sizes */
:deep(.kanban-container) {
  display: flex;
  flex-direction: column;
  height: 100%;
  width: 100%;
}

/* Mobile-specific adjustments */
@media (max-width: 1024px) {
  :deep(.kanban) {
    padding: 0.5rem;
  }
}
</style>