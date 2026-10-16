<script setup>
import PlanningRangeFilter from './PlanningRangeFilter.vue'
</script>

<template>
  <div class="planning-view flex h-full bg-base-100 overflow-hidden">

    <!-- ── Left: prioritized task list ── -->
    <section class="flex-1 min-w-0 flex flex-col overflow-hidden">
      <!-- Toolbar -->
      <div class="shrink-0 flex flex-wrap items-center gap-2 px-4 py-3 border-b border-base-100 bg-base-200">
        <div class="flex flex-col mr-auto min-w-0">
          <div class="flex items-center gap-2">
            <h1 class="font-semibold text-sm">Planning</h1>
            <span
              v-if="totalCount"
              class="badge badge-sm badge-ghost text-base-content/50 font-normal"
            >
              Showing {{ loadedCount }} of {{ totalCount }}
            </span>
          </div>
          <span class="text-xs text-base-content/40">Drag to reorder · priority drives the order</span>
        </div>

        <label class="input input-sm input-bordered flex items-center gap-2 w-44">
          <i class="fa-solid fa-magnifying-glass text-xs text-base-content/40"></i>
          <input
            type="text"
            :value="filter"
            @input="$storex.planning.setFilter($event.target.value)"
            placeholder="Search tasks…"
            class="grow bg-transparent outline-none text-xs min-w-0"
          />
        </label>

        <select
          class="select select-sm select-bordered text-xs"
          :value="boardFilter"
          @change="$storex.planning.setBoardFilter($event.target.value)"
        >
          <option value="all">All boards</option>
          <option v-for="board in boards" :key="board" :value="board">{{ board }}</option>
        </select>

        <PlanningRangeFilter />
      </div>

      <div v-if="error" class="shrink-0 px-4 py-2 text-xs text-error bg-error/5 border-b border-error/20">
        <i class="fa-solid fa-circle-exclamation mr-1"></i>{{ error }}
      </div>

      <!-- Prioritized groups -->
      <div ref="listEl" class="flex-1 overflow-y-auto p-4" @scroll="onScroll">
        <template v-for="priority in priorityOrder" :key="priority">
          <div class="mb-5" v-if="priorityGroups[priority].length">
            <div class="flex items-center gap-2 px-1 mb-2">
              <i :class="`${priorityMeta(priority).icon} text-xs ${priorityMeta(priority).dot.replace('bg-', 'text-')}`"></i>
              <span class="text-xs font-bold text-base-content/60 uppercase tracking-widest">
                {{ priorityMeta(priority).label }}
              </span>
              <span class="badge badge-xs badge-outline">{{ priorityGroups[priority].length }}</span>
            </div>

            <div class="space-y-1.5">
              <div
                v-for="task in priorityGroups[priority]"
                :key="task.id"
                draggable="true"
                @dragstart="onDragStart(task)"
                @dragover.prevent="onDragOver(task)"
                @drop.prevent="onDrop(task)"
                @dragend="onDragEnd"
                @click="selectTask(task)"
                class="flex items-center gap-3 p-2.5 rounded-lg border cursor-pointer transition-colors duration-150"
                :class="[
                  selectedTaskId === task.id
                    ? 'bg-primary/10 border-primary/30'
                    : 'bg-base-200 border-transparent hover:bg-base-300/60',
                  draggingId === task.id ? 'opacity-40' : '',
                  dragOverId === task.id ? 'border-primary/50' : ''
                ]"
              >
                <i class="fa-solid fa-grip-vertical text-xs text-base-content/20 cursor-grab active:cursor-grabbing shrink-0"></i>

                <span class="badge badge-sm gap-1 border shrink-0" :class="priorityMeta(task.priority).badge">
                  <i :class="`${priorityMeta(task.priority).icon} text-[10px]`"></i>
                  {{ priorityMeta(task.priority).label }}
                </span>

                <div class="flex-1 min-w-0">
                  <div class="text-sm font-medium truncate">{{ task.name }}</div>
                  <div class="flex items-center gap-3 text-xs text-base-content/50 mt-1">
                    <span class="truncate">
                      <i class="fa-solid fa-layer-group mr-1 text-[10px]"></i>{{ task.board }} · {{ task.column }}
                    </span>
                    <span class="flex items-center gap-1 shrink-0" :class="dueState(task).class">
                      <i :class="dueState(task).icon"></i>{{ dueState(task).label }}
                    </span>
                  </div>
                  <progress
                    v-if="task.progress > 0"
                    class="progress h-1 w-28 mt-2"
                    :class="task.status === 'done' ? 'progress-success' : 'progress-primary'"
                    :value="task.progress"
                    max="100"
                  ></progress>
                </div>

                <!-- Assignees -->
                <div class="flex items-center shrink-0" v-if="task.assignees?.length">
                  <div class="avatar-group -space-x-2">
                    <div v-for="user in task.assignees.slice(0, 2)" :key="user" class="avatar">
                      <div class="w-5 h-5 rounded-full bg-primary/20 text-primary text-[10px] font-semibold flex items-center justify-center">
                        {{ initials(user) }}
                      </div>
                    </div>
                  </div>
                  <span v-if="task.assignees.length > 2" class="text-[10px] text-base-content/40 ml-1">
                    +{{ task.assignees.length - 2 }}
                  </span>
                </div>

                <span class="badge badge-sm badge-ghost shrink-0" v-if="!task.assignees?.length">unassigned</span>
              </div>
            </div>
          </div>
        </template>

        <div v-if="!totalFiltered && !loading" class="flex flex-col items-center gap-2 py-16 text-base-content/30">
          <i class="fa-solid fa-inbox text-3xl"></i>
          <span class="text-sm">No tasks match your filters</span>
        </div>

        <!-- Pagination footer -->
        <div class="flex items-center justify-center gap-2 py-4 text-xs text-base-content/40">
          <template v-if="loadingMore">
            <span class="loading loading-spinner loading-xs text-primary"></span>
            <span>Loading more…</span>
          </template>
          <template v-else-if="loadedCount && !hasMore">
            <span class="text-base-content/30">End of list</span>
          </template>
        </div>
      </div>
    </section>

    <!-- ── Right: task detail panel ── -->
    <aside
      v-if="selectedTask"
      class="w-80 shrink-0 border-l border-base-300 bg-base-200 hidden lg:flex flex-col"
    >
      <div class="flex items-center justify-between px-4 py-3 border-b border-base-100">
        <span class="text-xs font-bold text-base-content/40 uppercase tracking-widest">Task detail</span>
        <button class="btn btn-ghost btn-xs btn-circle" @click="$storex.planning.clearSelection()">
          <i class="fa-solid fa-xmark text-xs"></i>
        </button>
      </div>

      <div class="flex-1 overflow-y-auto p-4 flex flex-col gap-4">
        <div>
          <h2 class="font-semibold text-base">{{ selectedTask.name }}</h2>
          <p class="text-xs text-base-content/50 mt-1">{{ selectedTask.board }} · {{ selectedTask.column }}</p>
        </div>

        <div class="form-control">
          <label class="label py-1"><span class="label-text text-xs text-base-content/50">Priority</span></label>
          <select
            class="select select-sm select-bordered text-sm"
            :value="selectedTask.priority"
            @change="$storex.planning.updatePriority({ taskId: selectedTask.id, priority: $event.target.value })"
          >
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
        </div>

        <div class="form-control">
          <label class="label py-1"><span class="label-text text-xs text-base-content/50">Due date</span></label>
          <input
            type="date"
            class="input input-sm input-bordered text-sm"
            :value="selectedTask.dueDate || ''"
            @change="$storex.planning.updateDueDate({ taskId: selectedTask.id, dueDate: $event.target.value || null })"
          />
        </div>

        <div class="form-control">
          <label class="label py-1"><span class="label-text text-xs text-base-content/50">Status</span></label>
          <select
            class="select select-sm select-bordered text-sm"
            :value="selectedTask.status"
            @change="$storex.planning.updateStatus({ taskId: selectedTask.id, status: $event.target.value })"
          >
            <option v-for="s in statuses" :key="s.value" :value="s.value">{{ s.label }}</option>
          </select>
        </div>

        <div class="form-control">
          <label class="label py-1"><span class="label-text text-xs text-base-content/50">Progress</span></label>
          <input
            type="range"
            min="0"
            max="100"
            step="5"
            class="range range-primary range-xs"
            :value="selectedTask.progress"
            @input="$storex.planning.updateProgress({ taskId: selectedTask.id, progress: $event.target.value })"
          />
          <span class="label-text-alt text-base-content/40">{{ selectedTask.progress }}%</span>
        </div>

        <div class="form-control">
          <label class="label py-1"><span class="label-text text-xs text-base-content/50">Assignees</span></label>
          <div class="flex flex-wrap gap-1.5">
            <button
              v-for="user in assignees"
              :key="user"
              @click="$storex.planning.toggleAssignee({ taskId: selectedTask.id, username: user })"
              class="btn btn-xs rounded-full gap-1"
              :class="selectedTask.assignees?.includes(user)
                ? 'btn-primary'
                : 'btn-ghost border border-base-100 text-base-content/50'"
            >
              <i :class="selectedTask.assignees?.includes(user) ? 'fa-solid fa-circle-check' : 'fa-regular fa-circle'" class="text-[10px]"></i>
              {{ user }}
            </button>
          </div>
        </div>
      </div>
    </aside>
  </div>
</template>

<script>
// Distance (px) from the bottom that triggers loading the next page
const SCROLL_THRESHOLD = 120

export default {
  name: 'PlanningView',
  data() {
    return {
      priorityOrder: ['high', 'medium', 'low'],
      draggingId: null,
      dragOverId: null,
      draggingTask: null
    }
  },
  created() {
    this.$storex.planning.ensureLoaded()
  },
  computed: {
    filter() {
      return this.$storex.planning.filter
    },
    boardFilter() {
      return this.$storex.planning.boardFilter
    },
    boards() {
      return this.$storex.planning.boards
    },
    assignees() {
      return this.$storex.planning.assignees
    },
    error() {
      return this.$storex.planning.error
    },
    priorityGroups() {
      return this.$storex.planning.priorityGroups
    },
    selectedTaskId() {
      return this.$storex.planning.selectedTaskId
    },
    selectedTask() {
      return this.$storex.planning.selectedTask
    },
    statuses() {
      return this.$storex.planning.statusList
    },
    totalFiltered() {
      return this.$storex.planning.filteredTasks.length
    },
    loading() {
      return this.$storex.planning.loading
    },
    // ─── Pagination counters ───
    loadedCount() {
      return this.$storex.planning.loadedCount
    },
    totalCount() {
      return this.$storex.planning.totalCount
    },
    hasMore() {
      return this.$storex.planning.hasMore
    },
    loadingMore() {
      return this.$storex.planning.loadingMore
    }
  },
  methods: {
    // Infinite scroll: load the next page when close to the bottom.
    // The store ignores calls while a page is already loading, so firing on
    // every scroll event is safe.
    onScroll(event) {
      const el = event.target
      if (!el) return
      const distanceToBottom = el.scrollHeight - el.scrollTop - el.clientHeight
      if (distanceToBottom <= SCROLL_THRESHOLD) {
        this.$storex.planning.loadNextPage()
      }
    },
    priorityMeta(priority) {
      return this.$storex.planning.priorityConfig(priority)
    },
    statusMeta(status) {
      return this.$storex.planning.statusConfig(status)
    },
    initials(name) {
      return (name || '').slice(0, 1).toUpperCase()
    },
    dueState(task) {
      if (!task.dueDate) {
        return { label: 'no due date', class: 'text-base-content/30', icon: 'fa-regular fa-calendar' }
      }
      const today = new Date().toISOString().slice(0, 10)
      if (task.status === 'done') {
        return { label: this.formatDueDate(task.dueDate), class: 'text-success', icon: 'fa-solid fa-circle-check' }
      }
      if (task.dueDate < today) {
        return { label: `Overdue · ${this.formatDueDate(task.dueDate)}`, class: 'text-error', icon: 'fa-regular fa-clock' }
      }
      if (task.dueDate === today) {
        return { label: 'Due today', class: 'text-warning', icon: 'fa-regular fa-clock' }
      }
      return { label: this.formatDueDate(task.dueDate), class: 'text-base-content/50', icon: 'fa-regular fa-calendar' }
    },
    formatDueDate(dateStr) {
      const d = new Date(dateStr)
      return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
    },
    selectTask(task) {
      this.$storex.planning.selectTask(task.id)
    },
    onDragStart(task) {
      this.draggingTask = task
      this.draggingId = task.id
    },
    onDragOver(task) {
      this.dragOverId = task.id
    },
    onDrop(targetTask) {
      if (!this.draggingTask || this.draggingTask.priority !== targetTask.priority) {
        this.onDragEnd()
        return
      }

      const priority = this.draggingTask.priority
      const group = [...this.priorityGroups[priority]]
      const from = group.findIndex(t => t.id === this.draggingTask.id)
      const to = group.findIndex(t => t.id === targetTask.id)
      if (from === -1 || to === -1) {
        this.onDragEnd()
        return
      }

      const [moved] = group.splice(from, 1)
      group.splice(to, 0, moved)

      const order = this.priorityOrder
      const groups = { ...this.priorityGroups, [priority]: group }
      const orderedIds = order.flatMap(p => (groups[p] || []).map(t => t.id))

      this.$storex.planning.reorderTasks(orderedIds)
      this.onDragEnd()
    },
    onDragEnd() {
      this.draggingTask = null
      this.draggingId = null
      this.dragOverId = null
    }
  }
}
</script>