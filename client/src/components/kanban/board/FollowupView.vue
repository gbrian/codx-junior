<script setup>
import PlanningRangeFilter from './PlanningRangeFilter.vue'
</script>

<template>
  <div ref="scrollEl" class="followup-view h-full overflow-y-auto bg-base-100" @scroll="onScroll">
    <div class="p-4 lg:p-6 max-w-6xl mx-auto w-full">

      <!-- Header + filters -->
      <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-5">
        <div>
          <div class="flex items-center gap-2">
            <h1 class="font-semibold text-lg">Follow-up</h1>
            <span
              v-if="totalCount"
              class="badge badge-sm badge-ghost text-base-content/50 font-normal"
            >
              Showing {{ loadedCount }} of {{ totalCount }}
            </span>
          </div>
          <p class="text-xs text-base-content/50 mt-0.5">Sprint health & attention queue</p>
        </div>

        <div class="flex flex-wrap items-center gap-2">
          <PlanningRangeFilter />

          <select
            class="select select-sm select-bordered text-xs"
            :value="boardFilter"
            @change="$storex.planning.setBoardFilter($event.target.value)"
          >
            <option value="all">All boards</option>
            <option v-for="board in boards" :key="board" :value="board">{{ board }}</option>
          </select>

          <select
            class="select select-sm select-bordered text-xs"
            :value="assigneeFilter"
            @change="$storex.planning.setAssigneeFilter($event.target.value)"
          >
            <option value="all">All assignees</option>
            <option v-for="user in assignees" :key="user" :value="user">{{ user }}</option>
          </select>
        </div>
      </div>

      <p v-if="error" class="text-xs text-error mb-4">
        <i class="fa-solid fa-circle-exclamation mr-1"></i>{{ error }}
      </p>

      <!-- Metric cards -->
      <div class="grid grid-cols-2 lg:grid-cols-5 gap-3 mb-6">
        <div class="bg-base-200 border border-base-100 rounded-lg p-4">
          <div class="text-xs text-base-content/40 uppercase tracking-wide">Total</div>
          <div class="text-2xl font-bold mt-1">{{ metrics.total }}</div>
          <div class="text-xs text-base-content/50 mt-1"><i class="fa-solid fa-list-ul mr-1"></i>all boards</div>
        </div>

        <div class="bg-base-200 border border-base-100 rounded-lg p-4">
          <div class="text-xs text-base-content/40 uppercase tracking-wide">Active</div>
          <div class="text-2xl font-bold mt-1 text-info">{{ metrics.active }}</div>
          <div class="text-xs text-base-content/50 mt-1">in progress / todo</div>
        </div>

        <div class="bg-base-200 border border-base-100 rounded-lg p-4">
          <div class="text-xs text-base-content/40 uppercase tracking-wide">Done</div>
          <div class="text-2xl font-bold mt-1 text-success">{{ metrics.done }}</div>
          <div class="text-xs text-base-content/50 mt-1">{{ metrics.completion }}% completion</div>
        </div>

        <div class="bg-base-200 rounded-lg p-4" :class="metrics.overdue ? 'border border-error/30' : 'border border-base-100'">
          <div class="text-xs text-base-content/40 uppercase tracking-wide">Overdue</div>
          <div class="text-2xl font-bold mt-1 text-error">{{ metrics.overdue }}</div>
          <div class="text-xs mt-1" :class="metrics.overdue ? 'text-error/70' : 'text-base-content/50'">
            <i class="fa-solid fa-triangle-exclamation mr-1" v-if="metrics.overdue"></i>
            {{ metrics.overdue ? 'needs attention' : 'clear' }}
          </div>
        </div>

        <div class="bg-base-200 border border-base-100 rounded-lg p-4">
          <div class="text-xs text-base-content/40 uppercase tracking-wide">Due today</div>
          <div class="text-2xl font-bold mt-1 text-warning">{{ metrics.dueToday }}</div>
          <div class="text-xs text-base-content/50 mt-1">focus today</div>
        </div>
      </div>

      <!-- Lower grid -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <!-- Attention + board progress -->
        <section class="lg:col-span-2">
          <h2 class="text-sm font-semibold flex items-center gap-2 mb-3">
            <i class="fa-solid fa-triangle-exclamation text-warning"></i> Needs attention
          </h2>

          <div class="space-y-2">
            <div
              v-for="task in needsAttention"
              :key="task.id"
              class="flex items-center gap-3 p-3 rounded-lg bg-base-200 border border-base-100 transition-colors"
              :class="task.priority === 'high' ? 'hover:border-error/40' : 'hover:border-warning/40'"
            >
              <span class="badge badge-sm gap-1 border shrink-0" :class="priorityMeta(task.priority).badge">
                <i :class="`${priorityMeta(task.priority).icon} text-[10px]`"></i>
                {{ priorityMeta(task.priority).label }}
              </span>

              <div class="flex-1 min-w-0">
                <div class="text-sm font-medium truncate">{{ task.name }}</div>
                <div class="text-xs text-base-content/50">
                  {{ task.board }} ·
                  <span :class="dueState(task).class">{{ dueState(task).label }}</span>
                </div>
              </div>

              <span v-if="!task.assignees?.length" class="badge badge-sm badge-ghost shrink-0 text-base-content/40">unassigned</span>
            </div>

            <div v-if="!needsAttention.length" class="text-sm text-base-content/30 py-8 text-center">
              Nothing needs attention 🎉
            </div>
          </div>

          <!-- Board progress -->
          <h2 class="text-sm font-semibold flex items-center gap-2 mt-7 mb-3">
            <i class="fa-solid fa-bars-progress text-info"></i> Board progress
          </h2>
          <div class="space-y-3">
            <div v-for="board in boardProgress" :key="board.board">
              <div class="flex justify-between text-xs mb-1">
                <span class="text-base-content/60">{{ board.board }}</span>
                <span class="text-base-content/40">{{ board.done }}/{{ board.total }} · {{ board.percentage }}%</span>
              </div>
              <progress
                class="progress w-full h-2"
                :class="progressClass(board.percentage)"
                :value="board.percentage"
                max="100"
              ></progress>
            </div>

            <div v-if="!boardProgress.length" class="text-sm text-base-content/30 py-8 text-center">
              No board data
            </div>
          </div>
        </section>

        <!-- Activity feed -->
        <aside>
          <h2 class="text-sm font-semibold flex items-center gap-2 mb-3">
            <i class="fa-solid fa-satellite-dish text-base-content/50"></i> Activity
          </h2>
          <ol class="relative border-s border-base-300 ms-3 space-y-4">
            <li v-for="event in activityFeed" :key="event.id" class="ms-6">
              <span class="absolute -start-1.5 mt-1 h-3 w-3 rounded-full" :class="toneDot(event.tone)"></span>
              <p class="text-xs text-base-content/70">
                <span class="font-semibold">{{ event.actor }}</span> {{ event.text }}
              </p>
              <time class="text-xs text-base-content/40">{{ event.timeLabel }}</time>
            </li>
          </ol>
        </aside>
      </div>

      <!-- Pagination footer -->
      <div class="flex items-center justify-center gap-2 py-6 text-xs text-base-content/40">
        <template v-if="loadingMore">
          <span class="loading loading-spinner loading-xs text-primary"></span>
          <span>Loading more…</span>
        </template>
        <template v-else-if="loadedCount && !hasMore">
          <span class="text-base-content/30">End of list</span>
        </template>
      </div>
    </div>
  </div>
</template>

<script>
// Distance (px) from the bottom that triggers loading the next page
const SCROLL_THRESHOLD = 120

export default {
  name: 'FollowupView',
  created() {
    this.$storex.planning.ensureLoaded()
  },
  computed: {
    boardFilter() {
      return this.$storex.planning.boardFilter
    },
    assigneeFilter() {
      return this.$storex.planning.assigneeFilter
    },
    error() {
      return this.$storex.planning.error
    },
    boards() {
      return this.$storex.planning.boards
    },
    assignees() {
      return this.$storex.planning.assignees
    },
    metrics() {
      return this.$storex.planning.metrics
    },
    needsAttention() {
      return this.$storex.planning.needsAttention
    },
    boardProgress() {
      return this.$storex.planning.boardProgress
    },
    activityFeed() {
      return this.$storex.planning.activityFeed
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
    dueState(task) {
      if (!task.dueDate) return { label: 'no due date', class: 'text-base-content/40' }
      const today = new Date().toISOString().slice(0, 10)
      if (task.dueDate < today) return { label: `${this.daysLate(task.dueDate)} overdue`, class: 'text-error' }
      if (task.dueDate === today) return { label: 'due today', class: 'text-warning' }
      return { label: this.formatDueDate(task.dueDate), class: 'text-base-content/50' }
    },
    daysLate(dateStr) {
      const diff = Math.round((new Date(dateStr) - new Date(new Date().toISOString().slice(0, 10))) / 86400000)
      return Math.abs(diff) === 1 ? '1 day' : `${Math.abs(diff)} days`
    },
    formatDueDate(dateStr) {
      return new Date(dateStr).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
    },
    progressClass(percentage) {
      if (percentage >= 100) return 'progress-success'
      if (percentage >= 60) return 'progress-primary'
      if (percentage >= 30) return 'progress-info'
      return 'progress-warning'
    },
    toneDot(tone) {
      return {
        info: 'bg-info',
        success: 'bg-success',
        primary: 'bg-primary',
        warning: 'bg-warning',
        error: 'bg-error'
      }[tone] || 'bg-base-content/30'
    }
  }
}
</script>