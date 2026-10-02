<script setup>
</script>

<template>
  <div
    class="group flex items-center gap-2 px-2 py-1.5 rounded-lg cursor-pointer transition-all duration-150 relative"
    :class="isSelected
      ? 'bg-primary/10 border border-primary/30'
      : 'hover:bg-base-content/5 border border-transparent'"
    @click="$emit('select')"
  >
    <!-- Status icon -->
    <i
      class="text-xs shrink-0 transition-colors"
      :class="statusIcon"
    ></i>

    <!-- Task name -->
    <span
      class="text-xs flex-1 truncate transition-colors"
      :class="[
        isSelected ? 'text-base-content/90 font-medium' : 'text-base-content/60',
        task.status === 'done' ? 'line-through opacity-60' : ''
      ]"
    >{{ task.name || 'Untitled' }}</span>

    <!-- Subtask count badge -->
    <span
      v-if="subtaskCount > 0"
      class="text-xs text-primary/70 bg-primary/10 border border-primary/20 rounded-full px-1.5 shrink-0"
    >{{ subtaskCount }}</span>

    <!-- Add subtask button (hover reveal) -->
    <button
      @click.stop="$emit('add-subtask')"
      class="btn btn-ghost btn-xs rounded-md h-5 min-h-0 px-1 text-base-content/30 hover:text-primary opacity-0 group-hover:opacity-100 transition-opacity shrink-0"
      title="Add subtask"
    >
      <i class="fa-solid fa-plus text-xs"></i>
    </button>
  </div>
</template>

<script>
const STATUS_ICONS = {
  todo:     'fa-regular fa-circle text-info/50',
  doing:    'fa-solid fa-circle-half-stroke text-primary/60',
  onhold:   'fa-solid fa-circle-pause text-warning/60',
  done:     'fa-solid fa-circle-check text-success/60',
  rejected: 'fa-solid fa-circle-xmark text-error/60',
}

export default {
  props: {
    task: { type: Object, required: true },
    isSelected: { type: Boolean, default: false },
    columnColor: { type: String, default: null }
  },
  emits: ['select', 'add-subtask'],
  computed: {
    statusIcon() {
      return STATUS_ICONS[this.task.status] || STATUS_ICONS.todo
    },
    subtaskCount() {
      return this.$chats.chatChildren(this.task.id)?.length || 0
    }
  }
}
</script>