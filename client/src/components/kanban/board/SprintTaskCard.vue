<script setup>
</script>

<template>
  <article
    class="group/card rounded-xl bg-base-200 border p-2.5 cursor-pointer transition-all duration-150"
    :class="selected ? 'border-primary/50 bg-primary/5' : 'border-base-100 hover:border-primary/40'"
    @click="$emit('open')"
  >
    <!-- Title row -->
    <div class="flex items-start gap-2">
      <i :class="[modeIcon, 'text-xs text-base-content/40 mt-0.5 w-3 text-center shrink-0']"></i>
      <span
        class="flex-1 text-sm font-medium leading-tight"
        :class="task.status === 'done' ? 'line-through opacity-60' : ''"
      >{{ task.name || 'Untitled' }}</span>
      <span
        v-if="priority"
        class="badge badge-xs badge-outline shrink-0"
        :class="priority.badge"
      >{{ priority.label }}</span>
    </div>

    <!-- Sprint membership chips -->
    <div v-if="sprintChips.length" class="flex items-center gap-1 mt-2 flex-wrap">
      <span
        v-for="chip in sprintChips"
        :key="chip.id"
        class="badge badge-xs badge-ghost gap-1"
        :title="chip.title"
      >
        <i class="fa-solid fa-layer-group text-[8px]"></i>{{ chip.short }}
      </span>
    </div>

    <!-- Parent breadcrumb for subtasks -->
    <div
      v-if="parentChat"
      class="text-[10px] text-primary/50 hover:text-primary truncate mt-1"
      @click.stop="$chats.setActiveChat(parentChat)"
    >
      {{ parentChat.name }}
    </div>

    <!-- Footer -->
    <div class="flex items-center justify-between mt-2 gap-1">
      <div class="flex items-center gap-1.5 min-w-0">
        <!-- Card accumulated cost -->
        <span
          v-if="task.cost > 0"
          class="text-[10px] px-1.5 py-0.5 rounded-full bg-amber-400/10 text-amber-400 flex items-center gap-1 tabular-nums font-semibold shrink-0"
          :title="costTooltip"
        >
          <i class="fa-solid fa-coins text-[9px]"></i>{{ formatCoins(task.cost) }}
        </span>
        <span
          v-if="subTasks.length"
          class="text-[10px] px-1.5 py-0.5 rounded-full bg-warning/15 text-warning flex items-center gap-1 shrink-0"
          :title="`${subTasks.length} subtasks`"
        >
          <i class="fa-regular fa-file-lines"></i>{{ subTasks.length }}
        </span>
        <span v-else class="text-[10px] text-base-content/25 shrink-0">no subtasks</span>
      </div>

      <!-- Card actions (revealed on hover / focus-within) -->
      <div class="flex items-center gap-0.5 opacity-0 group-hover/card:opacity-100 focus-within:opacity-100 transition-opacity shrink-0">
        <button
          class="btn btn-ghost btn-xs rounded-md h-5 min-h-0 px-1 text-primary"
          title="Create subtask"
          aria-label="Create subtask"
          @click.stop="$emit('add-subtask')"
        >
          <i class="fa-solid fa-plus text-xs"></i>
        </button>
        <button
          class="btn btn-ghost btn-xs rounded-md h-5 min-h-0 px-1 text-base-content/30 hover:text-error"
          title="Remove from sprint"
          aria-label="Remove from sprint"
          @click.stop="$emit('remove')"
        >
          <i class="fa-solid fa-xmark text-xs"></i>
        </button>
      </div>
    </div>
  </article>
</template>

<script>
export default {
  name: 'SprintTaskCard',
  props: {
    task: { type: Object, required: true },
    selected: { type: Boolean, default: false }
  },
  emits: ['open', 'add-subtask', 'remove'],
  computed: {
    modeIcon() {
      return this.$storex.chats.chatModeIcon(this.task.mode) || 'fa-solid fa-message'
    },
    priority() {
      const value = this.task.priority
      return value ? this.$storex.planning.priorityConfig(value) : null
    },
    subTasks() {
      return this.$storex.chats.chatChildren(this.task.id) || []
    },
    parentChat() {
      return this.task.parent_id ? this.$storex.chats.chats?.[this.task.parent_id] : null
    },
    sprintChips() {
      const boards = this.$storex.kanban.allBoards
      return (this.task.sprints || []).map(id => {
        const board = boards.find(b => b.id === id)
        const title = board?.title || id
        return { id, title, short: title.split('·')[0].trim() }
      })
    },
    costTooltip() {
      const spent = this.formatCoins(this.task?.cost || 0)
      if (this.task?.estimation_cost) {
        return `Cost: ${spent} of ${this.formatCoins(this.task.estimation_cost)} cxjcoins`
      }
      return `Cost: ${spent} cxjcoins`
    }
  },
  methods: {
    formatCoins(val) {
      if (val == null) return '-'
      if (val >= 1_000_000) return (val / 1_000_000).toFixed(2) + 'M'
      if (val >= 1_000) return (val / 1_000).toFixed(2) + 'K'
      return Number(val).toFixed(2)
    }
  }
}
</script>