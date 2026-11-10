<script setup>
import moment from 'moment'
</script>

<template>
  <modal close @close="$emit('close')">
    <template #header>
      <div class="flex items-center gap-2 min-w-0 w-full">
        <i class="fa-solid fa-magnifying-glass text-sm text-primary shrink-0"></i>
        <input
          ref="queryInput"
          v-model="query"
          type="text"
          class="grow bg-transparent text-sm outline-none placeholder:text-base-content/35 min-w-0"
          placeholder="Search every task: name, description, profile, person…"
          aria-label="Search tasks"
          @keydown="onKeydown"
        />
        <span
          v-if="loading"
          class="loading loading-spinner loading-xs text-base-content/40 shrink-0"
        ></span>
        <span class="hidden sm:inline text-[10px] text-base-content/30 shrink-0 tabular-nums">
          {{ total }} result{{ total === 1 ? '' : 's' }}
        </span>
      </div>
    </template>

    <!-- Filters -->
    <div class="flex flex-wrap items-center gap-1.5 pb-3 border-b border-base-content/5">
      <select v-model="filters.board" class="select select-xs select-bordered max-w-[10rem]" aria-label="Board">
        <option value="">All boards</option>
        <option v-for="value in facets.boards" :key="value" :value="value">{{ value }}</option>
      </select>

      <select v-model="filters.status" class="select select-xs select-bordered max-w-[9rem]" aria-label="Status">
        <option value="">Any status</option>
        <option v-for="value in facets.statuses" :key="value" :value="value">{{ value }}</option>
      </select>

      <select v-model="filters.priority" class="select select-xs select-bordered max-w-[8rem]" aria-label="Priority">
        <option value="">Any priority</option>
        <option value="high">High</option>
        <option value="medium">Medium</option>
        <option value="low">Low</option>
      </select>

      <select v-model="filters.profile" class="select select-xs select-bordered max-w-[10rem]" aria-label="Profile">
        <option value="">Any profile</option>
        <option v-for="value in facets.profiles" :key="value" :value="value">{{ value }}</option>
      </select>

      <select v-model="filters.assignee" class="select select-xs select-bordered max-w-[10rem]" aria-label="Assignee">
        <option value="">Anyone</option>
        <option v-for="value in facets.assignees" :key="value" :value="value">{{ value }}</option>
      </select>

      <label class="flex items-center gap-1.5 text-[11px] text-base-content/60 cursor-pointer select-none">
        <input v-model="includeDone" type="checkbox" class="checkbox checkbox-xs" />
        Include done
      </label>

      <button
        v-if="hasFilters"
        type="button"
        class="btn btn-ghost btn-xs gap-1 text-base-content/50 hover:text-error ml-auto"
        @click="resetFilters"
      >
        <i class="fa-solid fa-rotate-left text-[10px]"></i>
        Reset
      </button>
    </div>

    <!-- Result list -->
    <div
      ref="resultsList"
      class="min-h-[18rem] max-h-[60vh] overflow-y-auto -mx-1 px-1"
      role="listbox"
      aria-label="Task search results"
    >
      <div v-if="error" class="py-10 text-center text-sm text-error">
        <i class="fa-solid fa-triangle-exclamation mr-1"></i> {{ error }}
      </div>

      <div
        v-else-if="!results.length && !loading"
        class="py-12 flex flex-col items-center gap-2 text-base-content/35"
      >
        <i class="fa-solid fa-magnifying-glass text-3xl"></i>
        <span class="text-sm">No tasks match this search</span>
        <span v-if="hasFilters" class="text-[11px]">Try removing a filter or a term</span>
      </div>

      <button
        v-for="(task, index) in results"
        :key="task.id"
        type="button"
        role="option"
        :aria-selected="index === selectedIndex"
        class="w-full text-left px-2 py-2 rounded-lg transition-colors flex items-start gap-2.5"
        :class="index === selectedIndex
          ? 'bg-primary/15 ring-1 ring-primary/30'
          : 'hover:bg-base-content/5'"
        @mouseenter="selectedIndex = index"
        @click="select(task)"
      >
        <span
          class="mt-0.5 w-6 h-6 rounded-md bg-base-content/10 grid place-items-center shrink-0"
          :class="task.status === 'done' ? 'text-success' : (task.run_status ? 'text-primary' : 'text-base-content/50')"
        >
          <i
            :class="task.run_status
              ? 'fa-solid fa-arrows-spin'
              : (task.status === 'done' ? 'fa-solid fa-circle-check' : 'fa-regular fa-square-check')"
            class="text-[10px]"
          ></i>
        </span>

        <span class="min-w-0 flex-1">
          <span class="flex items-baseline gap-2 min-w-0">
            <span class="font-medium text-sm truncate" :title="task.name">{{ task.name || 'Untitled task' }}</span>
            <span
              v-if="task.status"
              class="badge badge-xs shrink-0"
              :class="statusBadgeClass(task.status)"
            >{{ task.status }}</span>
            <span
              v-if="task.priority && task.priority !== 'low'"
              class="badge badge-xs shrink-0"
              :class="task.priority === 'high' ? 'badge-error badge-outline' : 'badge-warning badge-outline'"
            >{{ task.priority }}</span>
          </span>

          <span class="block text-[11px] text-base-content/45 truncate mt-0.5">
            <i class="fa-solid fa-table-columns text-[9px] mr-1"></i>
            {{ task.board || 'No board' }}
            <span v-if="task.column">· {{ task.column }}</span>
            <span v-if="task.profiles?.length">· <i class="fa-solid fa-user-gear text-[9px] mx-0.5"></i>{{ task.profiles.join(', ') }}</span>
            <span v-if="task.users?.length">· <i class="fa-solid fa-user text-[9px] mx-0.5"></i>{{ task.users.join(', ') }}</span>
          </span>

          <span v-if="task.snippet" class="block text-[11px] text-base-content/55 line-clamp-2 mt-1">
            {{ task.snippet }}
          </span>
        </span>

        <span class="hidden sm:block text-[10px] text-base-content/30 shrink-0 tabular-nums pt-0.5">
          {{ when(task.updated_at) }}
        </span>
      </button>
    </div>

    <!-- Footer -->
    <div class="pt-2 mt-1 border-t border-base-content/5 flex items-center gap-2">
      <span class="text-[10px] text-base-content/35 hidden sm:flex items-center gap-1">
        <kbd class="kbd kbd-xs">↑</kbd><kbd class="kbd kbd-xs">↓</kbd> move
        <kbd class="kbd kbd-xs ml-1">Enter</kbd> open
        <kbd class="kbd kbd-xs ml-1">Esc</kbd> close
      </span>
      <span class="grow"></span>
      <button
        v-if="results.length < total"
        type="button"
        class="btn btn-ghost btn-xs gap-1"
        :disabled="loading"
        @click="loadMore"
      >
        <i class="fa-solid fa-arrow-down text-[10px]"></i>
        Load more ({{ total - results.length }})
      </button>
    </div>
  </modal>
</template>

<script>
const PRIORITIES = ['high', 'medium', 'low']

export default {
  name: 'GlobalTaskSearch',
  props: {
    project: { type: Object, default: null },
    // Boards available in the current project (fallback when facets are empty)
    boards: { type: Array, default: () => [] }
  },
  emits: ['close', 'select'],
  data() {
    return {
      query: '',
      filters: {
        board: '',
        status: '',
        priority: '',
        profile: '',
        assignee: ''
      },
      includeDone: true,
      results: [],
      total: 0,
      facets: {
        boards: [],
        statuses: [],
        priorities: [],
        profiles: [],
        assignees: []
      },
      selectedIndex: 0,
      loading: false,
      error: '',
      limit: 40,
      // Debounce handle: one request per pause, not one per keystroke.
      debounceHandle: null,
      requestId: 0
    }
  },
  computed: {
    api() {
      return this.project?.$api || this.$project?.$api || null
    },
    hasFilters() {
      return !!(this.query?.trim() || Object.values(this.filters).some(Boolean) || !this.includeDone)
    },
    priorityOptions() {
      return PRIORITIES
    }
  },
  watch: {
    query() {
      this.scheduleSearch()
    },
    filters: {
      deep: true,
      handler() {
        this.scheduleSearch()
      }
    },
    includeDone() {
      this.scheduleSearch()
    }
  },
  mounted() {
    this.$nextTick(() => this.$refs.queryInput?.focus())
    this.search()
  },
  beforeUnmount() {
    clearTimeout(this.debounceHandle)
  },
  methods: {
    scheduleSearch() {
      clearTimeout(this.debounceHandle)
      this.debounceHandle = setTimeout(() => this.search(), 220)
    },
    params(offset = 0) {
      return {
        q: this.query?.trim() || '',
        board: this.filters.board || '',
        status: this.filters.status || '',
        priority: this.filters.priority || '',
        profile: this.filters.profile || '',
        assignee: this.filters.assignee || '',
        include_done: this.includeDone ? 'true' : 'false',
        limit: this.limit,
        offset
      }
    },
    async search(append = false) {
      if (!this.api?.kanban?.searchTasks) return
      const requestId = ++this.requestId
      this.loading = true
      this.error = ''
      try {
        const offset = append ? this.results.length : 0
        const response = await this.api.kanban.searchTasks(this.params(offset))
        // A slower response for an older query must never replace the latest.
        if (requestId !== this.requestId) return
        if (response?.error) {
          this.error = response.error
          this.results = []
          this.total = 0
          return
        }
        const items = response?.results || []
        this.results = append ? [...this.results, ...items] : items
        this.total = Number(response?.total || 0)
        this.selectedIndex = Math.min(this.selectedIndex, Math.max(0, this.results.length - 1))
        if (response?.facets) {
          this.facets = {
            boards: response.facets.boards || [],
            statuses: response.facets.statuses || [],
            priorities: response.facets.priorities || [],
            profiles: response.facets.profiles || [],
            assignees: response.facets.assignees || []
          }
        }
        // Keep the board filter useful even before the first response.
        if (!this.facets.boards.length && this.boards?.length) {
          this.facets.boards = this.boards.map(board => board.title).filter(Boolean)
        }
      } catch (ex) {
        if (requestId === this.requestId) {
          this.error = ex?.message || 'Task search failed'
          this.results = []
          this.total = 0
        }
      } finally {
        if (requestId === this.requestId) this.loading = false
      }
    },
    loadMore() {
      this.search(true)
    },
    resetFilters() {
      this.query = ''
      this.filters = { board: '', status: '', priority: '', profile: '', assignee: '' }
      this.includeDone = true
      this.search()
    },
    onKeydown(event) {
      if (event.key === 'ArrowDown') {
        event.preventDefault()
        this.moveSelection(1)
      } else if (event.key === 'ArrowUp') {
        event.preventDefault()
        this.moveSelection(-1)
      } else if (event.key === 'Enter') {
        event.preventDefault()
        const task = this.results[this.selectedIndex]
        if (task) this.select(task)
      }
    },
    moveSelection(delta) {
      if (!this.results.length) return
      this.selectedIndex = (this.selectedIndex + delta + this.results.length) % this.results.length
      this.$nextTick(() => {
        const list = this.$refs.resultsList
        const item = list?.children?.[this.selectedIndex]
        item?.scrollIntoView?.({ block: 'nearest' })
      })
    },
    select(task) {
      if (!task) return
      this.$emit('select', task)
    },
    when(value) {
      if (!value) return ''
      const date = moment(value)
      return date.isValid() ? date.fromNow() : ''
    },
    statusBadgeClass(status) {
      const value = String(status || '').toLowerCase()
      if (value === 'done') return 'badge-success badge-outline'
      if (value === 'doing') return 'badge-primary badge-outline'
      if (value === 'onhold') return 'badge-warning badge-outline'
      if (value === 'rejected') return 'badge-error badge-outline'
      return 'badge-ghost text-base-content/50'
    }
  }
}
</script>
