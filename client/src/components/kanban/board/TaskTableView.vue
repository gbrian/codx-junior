<script setup>
import ChatIcon from '@/components/chat/ChatIcon.vue'
</script>

<template>
  <div class="task-table-view flex flex-col h-full min-h-0 bg-base-100 overflow-hidden">

    <!-- ── Toolbar: search · time · advanced filters ── -->
    <div class="shrink-0 flex flex-col gap-2 px-4 py-3 border-b border-base-100 bg-base-200">

      <div class="flex flex-wrap items-center gap-2">
        <div class="flex flex-col min-w-0 mr-auto">
          <div class="flex items-center gap-2">
            <h2 class="font-semibold text-sm text-base-content">Tasks</h2>
            <span class="badge badge-sm badge-ghost font-normal text-base-content/50">
              {{ filteredTasks.length }} / {{ allTasks.length }}
            </span>
          </div>
          <span class="text-xs text-base-content/40">{{ scopeLabel }} · click a header to sort</span>
        </div>

        <!-- Text search -->
        <label class="input input-sm input-bordered flex items-center gap-2 w-52">
          <i class="fa-solid fa-magnifying-glass text-xs text-base-content/40"></i>
          <input
            v-model="searchQuery"
            type="text"
            placeholder="Search tasks…"
            class="grow bg-transparent outline-none text-xs min-w-0"
            aria-label="Search tasks"
          />
          <button
            v-if="searchQuery"
            class="btn btn-ghost btn-xs btn-circle"
            aria-label="Clear search"
            @click="searchQuery = ''"
          >
            <i class="fa-solid fa-xmark text-xs"></i>
          </button>
        </label>

        <!-- Quick time filter over the last update timestamp -->
        <div class="join" role="group" aria-label="Time filter" title="Filter by when the task was last updated">
          <button
            v-for="option in timeOptions"
            :key="option.value"
            class="btn btn-xs join-item gap-1.5"
            :class="timeRange === option.value ? 'btn-primary' : 'btn-ghost text-base-content/50'"
            :aria-pressed="timeRange === option.value"
            :title="option.title"
            @click="setTimeRange(option.value)"
          >
            <i :class="option.icon" class="text-[10px]"></i>
            <span class="text-xs">{{ option.label }}</span>
          </button>
        </div>

        <!-- Advanced filters -->
        <button
          class="btn btn-sm gap-1.5"
          :class="showFilters ? 'btn-primary' : 'btn-ghost border border-base-100 text-base-content/60'"
          :aria-expanded="showFilters"
          aria-controls="task-table-filters"
          @click="showFilters = !showFilters"
        >
          <i class="fa-solid fa-filter text-xs"></i>
          <span class="text-xs font-medium">Filters</span>
          <span
            v-if="activeFilterCount"
            class="badge badge-xs"
            :class="showFilters ? 'badge-neutral' : 'badge-primary'"
          >{{ activeFilterCount }}</span>
        </button>

        <button
          v-if="hasActiveFilters"
          class="btn btn-ghost btn-sm gap-1.5 text-base-content/50 hover:text-error"
          title="Clear every filter"
          @click="resetFilters"
        >
          <i class="fa-solid fa-rotate-left text-xs"></i>
          <span class="text-xs">Reset</span>
        </button>
      </div>

      <!-- Custom time range (only when the "Custom" quick range is selected) -->
      <div v-if="timeRange === 'custom'" class="flex flex-wrap items-center gap-2">
        <label class="flex items-center gap-1.5">
          <span class="text-[10px] uppercase tracking-wider text-base-content/40">From</span>
          <input
            v-model="customFrom"
            type="date"
            class="input input-xs input-bordered text-xs"
            aria-label="From date"
          />
        </label>
        <label class="flex items-center gap-1.5">
          <span class="text-[10px] uppercase tracking-wider text-base-content/40">To</span>
          <input
            v-model="customTo"
            type="date"
            class="input input-xs input-bordered text-xs"
            aria-label="To date"
          />
        </label>
        <button
          class="btn btn-ghost btn-xs gap-1.5 text-base-content/40 hover:text-error"
          title="Clear the custom range"
          @click="clearCustomRange"
        >
          <i class="fa-solid fa-xmark text-xs"></i>
          <span class="text-xs">Clear</span>
        </button>
        <span class="text-[11px] text-base-content/30">inclusive · last update</span>
      </div>

      <!-- Filter fields -->
      <div v-if="showFilters" id="task-table-filters" class="flex flex-col gap-2">
        <div class="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-4 gap-2">

          <!-- Board filter: only offered when the table is NOT rendered inside a
               Board/Sprint view (there the surrounding view fixes the board). -->
          <label v-if="showBoardFilter" class="flex flex-col gap-1">
            <span class="text-[10px] uppercase tracking-wider text-base-content/40">Board</span>
            <select v-model="boardFilter" class="select select-sm select-bordered text-xs">
              <option value="all">All boards</option>
              <option v-for="title in boardOptions" :key="title" :value="title">{{ title }}</option>
            </select>
          </label>

          <label class="flex flex-col gap-1">
            <span class="text-[10px] uppercase tracking-wider text-base-content/40">Column</span>
            <select v-model="columnFilter" class="select select-sm select-bordered text-xs">
              <option value="all">All columns</option>
              <option v-for="col in columnOptions" :key="col" :value="col">{{ columnLabel(col) }}</option>
            </select>
          </label>

          <label class="flex flex-col gap-1">
            <span class="text-[10px] uppercase tracking-wider text-base-content/40">Status</span>
            <select v-model="statusFilter" class="select select-sm select-bordered text-xs">
              <option value="all">All statuses</option>
              <option v-for="status in statusOptions" :key="status" :value="status">{{ statusLabel(status) }}</option>
            </select>
          </label>

          <label class="flex flex-col gap-1">
            <span class="text-[10px] uppercase tracking-wider text-base-content/40">Priority</span>
            <select v-model="priorityFilter" class="select select-sm select-bordered text-xs">
              <option value="all">All priorities</option>
              <option v-for="(meta, value) in priorities" :key="value" :value="value">{{ meta.label }}</option>
            </select>
          </label>

          <label class="flex flex-col gap-1">
            <span class="text-[10px] uppercase tracking-wider text-base-content/40">Due</span>
            <select v-model="dueFilter" class="select select-sm select-bordered text-xs">
              <option v-for="(label, value) in dueOptions" :key="value" :value="value">{{ label }}</option>
            </select>
          </label>

          <label class="flex flex-col gap-1">
            <span class="text-[10px] uppercase tracking-wider text-base-content/40">Profile</span>
            <select v-model="profileFilter" class="select select-sm select-bordered text-xs">
              <option value="all">All profiles</option>
              <option v-for="profile in profileOptions" :key="profile" :value="profile">{{ profile }}</option>
            </select>
          </label>

          <label class="flex flex-col gap-1">
            <span class="text-[10px] uppercase tracking-wider text-base-content/40">Assignee</span>
            <select v-model="assigneeFilter" class="select select-sm select-bordered text-xs">
              <option value="all">All assignees</option>
              <option v-for="user in assigneeOptions" :key="user" :value="user">{{ user }}</option>
            </select>
          </label>

          <label class="flex flex-col gap-1">
            <span class="text-[10px] uppercase tracking-wider text-base-content/40">Type</span>
            <select v-model="modeFilter" class="select select-sm select-bordered text-xs">
              <option value="all">All types</option>
              <option v-for="mode in modeOptions" :key="mode" :value="mode">{{ modeLabel(mode) }}</option>
            </select>
          </label>

          <label class="flex flex-col gap-1">
            <span class="text-[10px] uppercase tracking-wider text-base-content/40">Sort</span>
            <select v-model="sortBy" class="select select-sm select-bordered text-xs">
              <option value="updated_at">Last update</option>
              <option value="created_at">Created</option>
              <option value="name">Name</option>
              <option value="board">Board</option>
              <option value="column">Column</option>
              <option value="status">Status</option>
              <option value="priority">Priority</option>
              <option value="project">Project</option>
              <option value="due_date">Due date</option>
            </select>
          </label>
        </div>

        <div class="flex flex-wrap items-center gap-x-4 gap-y-1">
          <label class="label cursor-pointer gap-2 p-0">
            <input v-model="mineOnly" type="checkbox" class="checkbox checkbox-xs checkbox-primary" />
            <span class="label-text text-xs">Assigned to me</span>
          </label>
          <label class="label cursor-pointer gap-2 p-0">
            <input v-model="pinnedOnly" type="checkbox" class="checkbox checkbox-xs checkbox-primary" />
            <span class="label-text text-xs">Pinned only</span>
          </label>
          <label class="label cursor-pointer gap-2 p-0">
            <input v-model="hideSubtasks" type="checkbox" class="checkbox checkbox-xs checkbox-primary" />
            <span class="label-text text-xs">Hide subtasks</span>
          </label>
        </div>
      </div>
    </div>

    <!-- ── Table ── -->
    <!-- The container scrolls horizontally, so the identity columns (Profiles,
         Project, Last update) are ALWAYS rendered instead of being hidden behind
         a wide breakpoint: they are the ones that tell the tasks apart. -->
    <div class="flex-1 min-h-0 overflow-auto">
      <table class="table table-sm table-pin-rows min-w-full">
        <thead class="text-xs">
          <tr class="text-base-content/50">
            <th
              v-for="head in headers"
              :key="head.key"
              :class="[head.class, 'cursor-pointer select-none whitespace-nowrap hover:text-base-content']"
              :aria-sort="sortBy === head.key ? (sortDir === 'asc' ? 'ascending' : 'descending') : 'none'"
              :title="head.hint || `Sort by ${head.label}`"
              @click="toggleSort(head.key)"
            >
              <span class="inline-flex items-center gap-1.5">
                <i v-if="head.icon" :class="head.icon" class="text-[10px] text-base-content/40"></i>
                {{ head.label }}
                <i
                  class="text-[10px]"
                  :class="[sortIcon(head.key), sortBy === head.key ? 'text-primary' : 'text-base-content/20']"
                ></i>
              </span>
            </th>
          </tr>
        </thead>

        <tbody>
          <tr
            v-for="task in pageTasks"
            :key="task.id"
            class="cursor-pointer transition-colors duration-150 outline-none focus-visible:ring-2 focus-visible:ring-primary/50"
            :class="selectedTaskId === task.id
              ? 'bg-primary/10'
              : 'hover:bg-base-200 focus-visible:bg-base-200'"
            tabindex="0"
            :aria-label="`Open task ${task.name || 'untitled'}`"
            @click="$emit('open-task', task)"
            @keydown.enter.prevent="$emit('open-task', task)"
          >
            <!-- Task: name + last message excerpt (sender avatar + text) + meta -->
            <td class="max-w-[26rem]">
              <div class="flex items-start gap-2 min-w-0">
                <ChatIcon :mode="task.mode" class="text-xs shrink-0 mt-1" />
                <div class="min-w-0">
                  <div class="text-sm font-medium truncate" :title="task.name">
                    {{ task.name || 'Untitled task' }}
                  </div>

                  <!-- Last message excerpt: sender avatar + up to 200 chars (2 lines) -->
                  <div v-if="lastMessagePreview(task)" class="flex items-start gap-1.5 mt-1 min-w-0">
                    <span
                      class="w-4 h-4 rounded-full shrink-0 flex items-center justify-center text-[9px] font-semibold leading-none"
                      :class="lastMessageAvatar(task).class"
                      :title="lastMessageAvatar(task).label"
                      role="img"
                      :aria-label="lastMessageAvatar(task).label"
                    >
                      <i
                        v-if="lastMessageAvatar(task).icon"
                        :class="lastMessageAvatar(task).icon"
                        aria-hidden="true"
                      ></i>
                      <template v-else>{{ lastMessageAvatar(task).initial }}</template>
                    </span>
                    <p
                      class="text-[11px] leading-snug text-base-content/75 line-clamp-2 min-w-0"
                      :title="lastMessagePreview(task)"
                    >
                      {{ lastMessagePreview(task) }}
                    </p>
                  </div>
                  <p v-else class="text-[11px] italic leading-snug text-base-content/40 mt-1">
                    No messages yet
                  </p>

                  <!-- Compact meta (the columns stay visible now, this only adds
                       the board/column context on very narrow viewports) -->
                  <div class="text-[11px] text-base-content/40 truncate sm:hidden mt-0.5">
                    {{ task.board || 'no board' }} · {{ columnLabel(taskColumn(task)) }}
                  </div>
                </div>
                <span v-if="task.parent_id" class="badge badge-xs badge-ghost shrink-0 mt-1">sub</span>
                <i
                  v-if="task.pinned"
                  class="fa-solid fa-thumbtack text-[10px] text-warning shrink-0 mt-1.5"
                  title="Pinned"
                ></i>
              </div>
            </td>

            <!-- Board -->
            <td class="hidden sm:table-cell">
              <span class="text-xs text-base-content/60 truncate">{{ task.board || '—' }}</span>
            </td>

            <!-- Column -->
            <td class="hidden lg:table-cell">
              <span class="text-xs text-base-content/60 truncate">{{ columnLabel(taskColumn(task)) }}</span>
            </td>

            <!-- Status -->
            <td>
              <span class="inline-flex items-center gap-1.5 text-xs font-medium whitespace-nowrap" :class="statusMeta(taskStatus(task)).textColor">
                <i :class="statusMeta(taskStatus(task)).icon" class="text-[10px]"></i>
                {{ statusMeta(taskStatus(task)).label }}
              </span>
            </td>

            <!-- Priority -->
            <td>
              <span
                class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded border text-[11px] font-medium whitespace-nowrap"
                :class="priorityMeta(taskPriority(task)).badge"
              >
                <i :class="priorityMeta(taskPriority(task)).icon" class="text-[9px]"></i>
                {{ priorityMeta(taskPriority(task)).label }}
              </span>
            </td>

            <!-- Profiles (always visible: who the task is answered by) -->
            <td class="whitespace-nowrap">
              <div class="flex items-center gap-1 flex-wrap max-w-[12rem]">
                <span
                  v-for="profile in (task.profiles || [])"
                  :key="profile"
                  class="badge badge-xs badge-outline gap-1 border-base-content/25 text-base-content/70 max-w-[9rem] truncate"
                  :title="`Profile: ${profile}`"
                >
                  <i class="fa-solid fa-user-gear text-[8px]" aria-hidden="true"></i>
                  <span class="truncate">{{ profile }}</span>
                </span>
                <span v-if="!(task.profiles || []).length" class="text-xs text-base-content/25">—</span>
              </div>
            </td>

            <!-- Assignees -->
            <td class="hidden lg:table-cell">
              <div class="flex items-center gap-1 flex-wrap">
                <span
                  v-for="user in taskUsers(task).slice(0, 2)"
                  :key="user"
                  class="inline-flex items-center gap-1"
                  :title="user"
                >
                  <span class="w-4 h-4 rounded-full bg-primary/20 text-primary text-[9px] font-semibold flex items-center justify-center">
                    {{ initial(user) }}
                  </span>
                  <span class="text-[11px] text-base-content/60 max-w-[6rem] truncate">{{ user }}</span>
                </span>
                <span v-if="taskUsers(task).length > 2" class="text-[10px] text-base-content/40">
                  +{{ taskUsers(task).length - 2 }}
                </span>
                <span v-if="!taskUsers(task).length" class="text-xs text-base-content/25">unassigned</span>
              </div>
            </td>

            <!-- Target project — the project the task WORKS with, set at chat
                 level (`chat.project_id`). The owner project is printed below it
                 only when the task belongs to a different project. -->
            <td class="whitespace-nowrap">
              <div class="flex flex-col leading-tight min-w-0" :title="taskProject(task).title">
                <span
                  v-if="taskProject(task).label"
                  class="flex items-center gap-1 text-xs text-base-content/70 max-w-[12rem]"
                >
                  <img
                    v-if="taskProject(task).icon"
                    :src="taskProject(task).icon"
                    alt=""
                    class="w-3.5 h-3.5 rounded-full object-cover shrink-0"
                    aria-hidden="true"
                  />
                  <i v-else class="fa-solid fa-folder-open text-[10px] text-base-content/40" aria-hidden="true"></i>
                  <span class="truncate">{{ taskProject(task).label }}</span>
                </span>
                <span v-else class="text-xs text-base-content/25">—</span>
                <span
                  v-if="taskProject(task).owner"
                  class="flex items-center gap-1 text-[10px] text-base-content/45 max-w-[12rem]"
                >
                  <i class="fa-solid fa-user-shield text-[9px]" aria-hidden="true"></i>
                  <span class="truncate">{{ taskProject(task).owner }}</span>
                </span>
              </div>
            </td>

            <!-- Due -->
            <td class="hidden lg:table-cell">
              <span class="text-xs whitespace-nowrap" :class="dueState(task).class">
                <i :class="dueState(task).icon" class="text-[10px] mr-1"></i>{{ dueState(task).label }}
              </span>
            </td>

            <!-- Last update — "from now" age first, exact date/time below it.
                 Always visible so the latest changes are readable at a glance. -->
            <td class="whitespace-nowrap">
              <div
                class="flex flex-col leading-tight"
                :title="`Last update ${formatDate(taskTimestamp(task))} · Created ${formatDate(task.created_at)}`"
              >
                <span class="text-xs text-base-content/70 whitespace-nowrap">
                  <i class="fa-regular fa-clock text-[10px] mr-1 text-base-content/30"></i>{{ relativeTime(taskTimestamp(task)) }}
                </span>
                <span class="text-[10px] text-base-content/35 whitespace-nowrap tabular-nums">
                  {{ formatDate(taskTimestamp(task)) }}
                </span>
              </div>
            </td>
          </tr>
        </tbody>
      </table>

      <!-- Empty state -->
      <div
        v-if="!pageTasks.length"
        class="flex flex-col items-center gap-2 py-16 text-base-content/30"
      >
        <i class="fa-solid fa-inbox text-3xl"></i>
        <span class="text-sm">
          {{ hasActiveFilters ? 'No tasks match your filters' : 'No tasks on this board yet' }}
        </span>
        <button
          v-if="hasActiveFilters"
          class="btn btn-ghost btn-xs gap-1.5 text-primary"
          @click="resetFilters"
        >
          <i class="fa-solid fa-rotate-left text-xs"></i> Clear filters
        </button>
      </div>
    </div>

    <!-- ── Pagination ── -->
    <div class="shrink-0 flex items-center justify-between gap-2 px-4 py-2 border-t border-base-100 bg-base-200">
      <span class="text-xs text-base-content/40">{{ rangeLabel }}</span>

      <div class="flex items-center gap-1">
        <button
          class="btn btn-ghost btn-xs"
          :disabled="currentPage <= 1"
          aria-label="Previous page"
          @click="page = currentPage - 1"
        >
          <i class="fa-solid fa-chevron-left text-xs"></i>
        </button>
        <span class="text-xs text-base-content/50 tabular-nums px-1">
          Page {{ currentPage }} / {{ pageCount }}
        </span>
        <button
          class="btn btn-ghost btn-xs"
          :disabled="currentPage >= pageCount"
          aria-label="Next page"
          @click="page = currentPage + 1"
        >
          <i class="fa-solid fa-chevron-right text-xs"></i>
        </button>
      </div>
    </div>
  </div>
</template>

<script>
// Rows rendered per page
const PAGE_SIZE = 50

// Longest excerpt of the last message rendered under the task name
const LAST_MESSAGE_PREVIEW_LENGTH = 200

// Same priority vocabulary the planning views use
const PRIORITIES = {
  high: { value: 'high', label: 'High', icon: 'fa-solid fa-flag', badge: 'border-error/30 bg-error/10 text-error' },
  medium: { value: 'medium', label: 'Medium', icon: 'fa-solid fa-flag', badge: 'border-warning/30 bg-warning/10 text-warning' },
  low: { value: 'low', label: 'Low', icon: 'fa-solid fa-flag', badge: 'border-success/30 bg-success/10 text-success' }
}
const PRIORITY_WEIGHT = { high: 0, medium: 1, low: 2 }
const DEFAULT_PRIORITY = 'low'

// Placeholder column shared with the kanban store (see NO_COLUMN_ID)
const NO_COLUMN = '--none--'

const DUE_FILTERS = {
  all: 'Any due date',
  overdue: 'Overdue',
  today: 'Due today',
  week: 'Due in 7 days',
  none: 'No due date'
}

// Quick time ranges over the last update timestamp. `custom` reveals the date
// pickers; the range itself is resolved in `matchesTimeRange`.
const TIME_FILTERS = [
  { value: 'all', label: 'All', icon: 'fa-regular fa-clock', title: 'Any time' },
  { value: '1h', label: '1h', icon: 'fa-solid fa-bolt', title: 'Updated in the last hour' },
  { value: 'today', label: 'Today', icon: 'fa-regular fa-calendar-check', title: 'Updated today' },
  { value: 'week', label: 'This week', icon: 'fa-regular fa-calendar-days', title: 'Updated this week (since Monday)' },
  { value: 'custom', label: 'Custom', icon: 'fa-regular fa-calendar', title: 'Custom date range' }
]

// Table headers.
//
// Profiles, Project and Last update carry the identity of a task (who answers
// it, where it runs, when it changed) so they are ALWAYS rendered — the table
// container scrolls horizontally instead of hiding them behind a breakpoint.
// Only the secondary context columns (Board, Column, Assignees, Due) collapse on
// narrow viewports.
const HEADERS = [
  { key: 'name', label: 'Task', class: 'min-w-[18rem]' },
  { key: 'board', label: 'Board', class: 'hidden sm:table-cell' },
  { key: 'column', label: 'Column', class: 'hidden lg:table-cell' },
  { key: 'status', label: 'Status' },
  { key: 'priority', label: 'Priority' },
  { key: 'profiles', label: 'Profiles', icon: 'fa-solid fa-user-gear', hint: 'Profiles (answerers) of the chat · click to sort' },
  { key: 'users', label: 'Assignees', class: 'hidden lg:table-cell' },
  { key: 'project', label: 'Project', icon: 'fa-solid fa-folder-tree', hint: 'Target project the task works with (chat level) · click to sort' },
  { key: 'due_date', label: 'Due', class: 'hidden lg:table-cell' },
  { key: 'updated_at', label: 'Last update', icon: 'fa-regular fa-clock', hint: 'Last update (from now) · click to sort' }
]

const TEXT_SORT_KEYS = ['name', 'board', 'column', 'status', 'profiles', 'users', 'project']

export default {
  name: 'TaskTableView',
  props: {
    // Board whose tasks are listed. Ignored when the table is not embedded in a
    // board view (the board filter of the extended filters picks it instead).
    boardId: { type: String, default: null },
    // Task highlighted by the parent (inline detail pane selection)
    selectedTaskId: { type: String, default: null },
    // Whether the table is rendered INSIDE a Board/Sprint view. There the board
    // is already fixed by the surrounding view, so the board filter is not
    // offered: it only makes sense for a standalone (project level) table,
    // where it lives with the rest of the extended filters.
    inBoardView: { type: Boolean, default: false }
  },
  emits: ['open-task'],
  data() {
    return {
      searchQuery: '',
      // Board picked in the extended filters ('all' | board title). Only used by
      // a standalone table (see `showBoardFilter`).
      boardFilter: 'all',
      showFilters: false,
      columnFilter: 'all',
      statusFilter: 'all',
      priorityFilter: 'all',
      profileFilter: 'all',
      assigneeFilter: 'all',
      modeFilter: 'all',
      dueFilter: 'all',
      // Quick time range: 'all' | '1h' | 'today' | 'week' | 'custom'
      timeRange: 'all',
      // Custom range bounds (YYYY-MM-DD, inclusive)
      customFrom: '',
      customTo: '',
      mineOnly: false,
      pinnedOnly: false,
      hideSubtasks: false,
      sortBy: 'updated_at',
      sortDir: 'desc',
      page: 1,
      headers: HEADERS,
      priorities: PRIORITIES,
      dueOptions: DUE_FILTERS,
      timeOptions: TIME_FILTERS
    }
  },
  computed: {
    // The board filter lives with the extended filters and is only offered when
    // the table is not owned by a Board/Sprint view.
    showBoardFilter() {
      return !this.inBoardView
    },
    // Board the table is scoped to: the surrounding Board/Sprint view wins, then
    // the board picked in the extended filters. `null` means the whole project.
    targetBoardId() {
      if (this.inBoardView) return this.boardId
      return this.boardFilter !== 'all' ? this.boardFilter : null
    },
    board() {
      return this.$storex.kanban.boardById(this.targetBoardId)
    },
    boardTitle() {
      return this.board?.title || null
    },
    boardType() {
      return this.board?.type || 'kanban'
    },
    // Board titles offered by the board filter (every board of the project)
    boardOptions() {
      return (this.$storex.kanban.allBoards || []).map(board => board.title)
    },
    // Sprint boards group their tasks by the chat `status` (each column maps one
    // status to a UI title), so a sprint task's "column" is the title of the
    // column that groups its status. Kanban boards store it on `chat.column` and
    // get `null` here.
    sprintColumnByStatus() {
      if (this.boardType !== 'sprint' || !this.targetBoardId) return null
      const byStatus = {}
      ;(this.$storex.kanban.sprintColumns(this.targetBoardId) || []).forEach(column => {
        // Statuses compare ignoring case and are grouped by their status value
        const key = `${column.status ?? column.title ?? ''}`.trim().toLowerCase()
        if (key && !byStatus[key]) byStatus[key] = column.title
      })
      return byStatus
    },
    scopeLabel() {
      if (this.boardTitle) return `Board · ${this.boardTitle}`
      if (this.showBoardFilter) return 'All boards of this project'
      return 'No board selected'
    },
    // Every task the table may show, as stored (no clones: the cards keep the
    // identity the store relies on)
    allTasks() {
      const boardTasks = this.targetBoardId
        ? (this.boardType === 'sprint'
            ? this.$storex.kanban.sprintBoardChats(this.targetBoardId)
            : this.$storex.kanban.boardChats(this.targetBoardId))
        : null
      const tasks = boardTasks || Object.values(this.$storex.chats.chats || {}).filter(c =>
        c?.id &&
        !c.is_template &&
        c.mode !== 'channel' &&
        (c.board || c.column || c.mode === 'task')
      )
      return (tasks || []).filter(c => !c.is_template && c.mode !== 'channel')
    },

    // ── Filter options (derived from the visible dataset) ──
    columnOptions() {
      return this.uniqueValues(this.allTasks.map(task => this.taskColumn(task)))
    },
    statusOptions() {
      const known = (this.$storex.chats.statusList || []).map(status => status.value)
      const found = this.allTasks.map(task => this.taskStatus(task))
      return [...new Set([...known, ...found])]
    },
    profileOptions() {
      return this.uniqueValues(this.allTasks.flatMap(task => task.profiles || []))
    },
    assigneeOptions() {
      return this.uniqueValues(this.allTasks.flatMap(task => this.taskUsers(task)))
    },
    modeOptions() {
      return this.uniqueValues(this.allTasks.map(task => task.mode || 'chat'))
    },

    // ── Filtering ──
    filteredTasks() {
      const query = (this.searchQuery || '').trim().toLowerCase()
      const today = this.today()

      return this.allTasks.filter(task => {
        if (this.hideSubtasks && task.parent_id) return false
        if (this.pinnedOnly && !task.pinned) return false
        if (this.columnFilter !== 'all' && this.taskColumn(task) !== this.columnFilter) return false
        if (this.statusFilter !== 'all' && this.taskStatus(task) !== this.statusFilter) return false
        if (this.priorityFilter !== 'all' && this.taskPriority(task) !== this.priorityFilter) return false
        if (this.profileFilter !== 'all' && !(task.profiles || []).includes(this.profileFilter)) return false
        if (this.assigneeFilter !== 'all' && !this.taskUsers(task).includes(this.assigneeFilter)) return false
        if (this.modeFilter !== 'all' && (task.mode || 'chat') !== this.modeFilter) return false
        if (this.mineOnly && !this.taskUsers(task).includes(this.$user?.username)) return false
        if (this.dueFilter !== 'all' && !this.matchesDue(task, today)) return false
        if (!this.matchesTimeRange(task)) return false
        if (query && !this.matchesQuery(task, query)) return false
        return true
      })
    },
    activeFilterCount() {
      const active = [
        // The board filter only counts while it is offered
        this.showBoardFilter && this.boardFilter !== 'all',
        this.columnFilter !== 'all',
        this.statusFilter !== 'all',
        this.priorityFilter !== 'all',
        this.profileFilter !== 'all',
        this.assigneeFilter !== 'all',
        this.modeFilter !== 'all',
        this.dueFilter !== 'all',
        this.mineOnly,
        this.pinnedOnly,
        this.hideSubtasks
      ]
      return active.filter(Boolean).length
    },
    // The one-line hint shown under the table title: which time window is applied
    timeRangeLabel() {
      const option = TIME_FILTERS.find(o => o.value === this.timeRange)
      if (this.timeRange === 'custom') {
        if (this.customFrom && this.customTo) return `${this.customFrom} → ${this.customTo}`
        if (this.customFrom) return `since ${this.customFrom}`
        if (this.customTo) return `until ${this.customTo}`
        return 'Custom range'
      }
      return option?.title || 'Any time'
    },
    hasActiveFilters() {
      return this.activeFilterCount > 0 || this.timeRange !== 'all' || !!this.searchQuery?.trim()
    },
    // Resets the page whenever the filtered/sorted dataset changes
    filterSignature() {
      return [
        this.searchQuery, this.targetBoardId, this.columnFilter, this.statusFilter,
        this.priorityFilter, this.profileFilter, this.assigneeFilter,
        this.modeFilter, this.dueFilter, this.timeRange, this.customFrom,
        this.customTo, this.mineOnly, this.pinnedOnly,
        this.hideSubtasks, this.sortBy, this.sortDir
      ].join('|')
    },

    // ── Sorting ──
    sortedTasks() {
      const direction = this.sortDir === 'asc' ? 1 : -1
      const valueOf = task => {
        switch (this.sortBy) {
          case 'name': return (task.name || '').toLowerCase()
          case 'board': return (task.board || '').toLowerCase()
          case 'column': return this.columnLabel(this.taskColumn(task)).toLowerCase()
          case 'status': return this.taskStatus(task).toLowerCase()
          case 'priority': return PRIORITY_WEIGHT[this.taskPriority(task)]
          case 'project': return (this.taskProject(task).label || '').toLowerCase()
          case 'due_date': return task.due_date || '9999-12-31'
          case 'created_at': return task.created_at || this.taskTimestamp(task) || ''
          case 'profiles': return (task.profiles || []).join(',').toLowerCase()
          case 'users': return this.taskUsers(task).join(',').toLowerCase()
          default: return this.taskTimestamp(task) || ''
        }
      }
      return [...this.filteredTasks].sort((a, b) => {
        const left = valueOf(a)
        const right = valueOf(b)
        if (left === right) return 0
        return (left > right ? 1 : -1) * direction
      })
    },

    // ── Pagination ──
    pageCount() {
      return Math.max(1, Math.ceil(this.sortedTasks.length / PAGE_SIZE))
    },
    currentPage() {
      return Math.min(this.page, this.pageCount)
    },
    pageTasks() {
      const start = (this.currentPage - 1) * PAGE_SIZE
      return this.sortedTasks.slice(start, start + PAGE_SIZE)
    },
    rangeLabel() {
      const total = this.sortedTasks.length
      if (!total) return 'No tasks'
      const start = (this.currentPage - 1) * PAGE_SIZE + 1
      const end = Math.min(total, start + PAGE_SIZE - 1)
      return `Showing ${start}–${end} of ${total}`
    }
  },
  watch: {
    filterSignature() {
      this.page = 1
    },
    // Another board brings other columns/statuses: drop the board-bound filters
    boardId() {
      this.page = 1
      this.columnFilter = 'all'
      this.statusFilter = 'all'
    }
  },
  methods: {
    // ── Task normalisation ──
    // The column a task belongs to. Kanban tasks store it on `chat.column`;
    // sprint tasks are grouped by their status (see `sprintColumnByStatus`), so
    // the title of the column grouping that status is used instead — the stored
    // `column` of a sprint task is only the board column it was created in.
    taskColumn(task) {
      if (this.sprintColumnByStatus) {
        // A task without a status lands in the virtual "Unassigned" column,
        // whose status value is the NO_STATUS_ID placeholder.
        const key = `${task.status || '--no-status--'}`.trim().toLowerCase()
        return this.sprintColumnByStatus[key] || task.column || NO_COLUMN
      }
      return task.column || NO_COLUMN
    },
    columnLabel(value) {
      return !value || value === NO_COLUMN ? 'No column' : value
    },
    taskStatus(task) {
      return task.status || 'todo'
    },
    taskPriority(task) {
      const value = `${task.priority || ''}`.trim().toLowerCase()
      return PRIORITIES[value] ? value : DEFAULT_PRIORITY
    },
    // Assignees are stored as `assignees` (planning) and/or `users` (board stats)
    taskUsers(task) {
      return this.uniqueValues([...(task.users || []), ...(task.assignees || [])])
    },
    uniqueValues(values) {
      return [...new Set((values || []).filter(Boolean))].sort((a, b) => `${a}`.localeCompare(`${b}`))
    },
    today() {
      return new Date().toISOString().slice(0, 10)
    },
    matchesDue(task, today) {
      const due = task.due_date
      switch (this.dueFilter) {
        case 'overdue':
          return !!due && due < today && this.taskStatus(task) !== 'done'
        case 'today':
          return due === today
        case 'week': {
          const limit = new Date()
          limit.setDate(limit.getDate() + 7)
          const until = limit.toISOString().slice(0, 10)
          return !!due && due >= today && due <= until
        }
        case 'none':
          return !due
        default:
          return true
      }
    },
    // ── Projects (working / target) ──
    // `project_id` is the TARGET project the task works with — set at CHAT level
    // (the column or the parent may have provided it). `owner_project_id` is the
    // project the task BELONGS to (it owns the chat). Both ids are resolved
    // against the loaded projects so the table shows names/icons, not ids.
    projectById(projectId) {
      if (!projectId) return null
      return this.$storex.projects.allProjectsById?.[projectId]
        || (this.$storex.projects.allProjects || []).find(p => p.project_id === projectId)
        || null
    },
    projectName(projectId) {
      if (!projectId) return null
      const project = this.projectById(projectId)
      return project?.project_name || projectId
    },
    taskProject(task) {
      const workingId = task.project_id || null
      const ownerId = task.owner_project_id || null
      const workingProject = this.projectById(workingId)
      const working = workingProject?.project_name || (workingId ? workingId : null)
      const owner = this.projectName(ownerId)
      const different = !!working && !!owner && workingId !== ownerId
      return {
        // Main label: the target (working) project, falling back to its owner
        label: working || owner || null,
        // Its icon, so two projects with similar names stay distinguishable
        icon: workingProject?.project_icon || null,
        // Owner project, only rendered when it is a different project
        owner: different ? owner : null,
        title: `Target project: ${working || '—'} · Owner project: ${owner || '—'}`
      }
    },
    // ── Last update / last message ──
    // The chat's LAST UPDATE: the most recent of its document timestamp and the
    // last message activity the chats store maintains (`lastMessageAt`).
    // Whichever the backend refreshes, the column never shows a stale value —
    // and the time filter/sorting read the very same value.
    taskTimestamp(task) {
      return this.newestDate([task.updated_at, task.lastMessageAt, task.created_at])
    },
    // Latest of a list of ISO timestamps (invalid/empty values are ignored)
    newestDate(values) {
      const dated = (values || [])
        .filter(Boolean)
        .map(value => ({ value, time: new Date(value).getTime() }))
        .filter(({ time }) => !Number.isNaN(time))
      if (!dated.length) return null
      return dated.reduce((latest, item) => (item.time > latest.time ? item : latest)).value
    },
    // The most recent message. `list()`/`search()` only return a summary chat
    // carrying its last message, and a fully loaded chat ends with the newest
    // one, so the tail of `messages` is always the last message.
    lastMessage(task) {
      const messages = task?.messages
      if (Array.isArray(messages) && messages.length) return messages[messages.length - 1]
      return task?.last_message || null
    },
    // One-line excerpt of the last message, capped at 200 chars. Markdown noise
    // (code fences, link targets, emphasis markers) is stripped so the excerpt
    // reads as plain prose instead of raw markup.
    lastMessagePreview(task) {
      const message = this.lastMessage(task)
      const raw = message?.content ?? message?.think
      if (!raw) return ''

      const text = `${raw}`
        // Code blocks are useless in a one-line excerpt
        .replace(/```[\s\S]*?```/g, ' ')
        // Links / images → their label
        .replace(/!?\[([^\]]*)\]\([^)]*\)/g, '$1')
        // Headings, quotes, emphasis and inline code markers
        .replace(/[#>*_`~]+/g, ' ')
        .replace(/\s+/g, ' ')
        .trim()

      if (!text) return ''
      return text.length > LAST_MESSAGE_PREVIEW_LENGTH
        ? `${text.slice(0, LAST_MESSAGE_PREVIEW_LENGTH).trim()}…`
        : text
    },
    // Avatar of the last message sender: the author's initial for a user, a robot
    // glyph (or the answering profile initial) for the assistant. Rendered BEFORE
    // the excerpt so a row reads as a conversation, not as bare text.
    lastMessageAvatar(task) {
      const message = this.lastMessage(task)
      const role = message?.role

      if (role === 'assistant') {
        const profile = message?.profile || message?.profile_name || null
        return {
          // A named profile shows its own initial, the generic assistant a robot
          icon: profile ? null : 'fa-solid fa-robot',
          initial: profile ? this.initial(profile) : null,
          class: 'bg-secondary/25 text-secondary',
          label: profile || 'Assistant'
        }
      }
      if (role === 'system' || role === 'tool') {
        return {
          icon: 'fa-solid fa-gear',
          initial: null,
          class: 'bg-base-content/10 text-base-content/70',
          label: role === 'system' ? 'System' : 'Tool'
        }
      }

      const name = message?.user || message?.username || message?.author || this.$user?.username || ''
      return {
        icon: null,
        initial: this.initial(name),
        class: 'bg-primary/25 text-primary',
        label: name || 'User'
      }
    },
    matchesTimeRange(task) {
      if (this.timeRange === 'all') return true

      const value = this.taskTimestamp(task)
      if (!value) return false
      const date = new Date(value)
      if (Number.isNaN(date.getTime())) return false

      const now = new Date()
      switch (this.timeRange) {
        case '1h':
          // Rolling window, not a calendar boundary
          return date.getTime() >= now.getTime() - 60 * 60 * 1000
        case 'today':
          // Local calendar day (midnight → now), so "today" means the user's day
          return date >= new Date(now.getFullYear(), now.getMonth(), now.getDate())
        case 'week': {
          // Current week, starting on Monday (local time)
          const start = new Date(now.getFullYear(), now.getMonth(), now.getDate())
          const offset = (start.getDay() + 6) % 7
          start.setDate(start.getDate() - offset)
          return date >= start
        }
        default: {
          // Custom range: both bounds are inclusive, "to" covers the whole day
          const from = this.customFrom ? new Date(`${this.customFrom}T00:00:00`) : null
          const to = this.customTo ? new Date(`${this.customTo}T23:59:59.999`) : null
          if (from && date < from) return false
          if (to && date > to) return false
          return true
        }
      }
    },
    // Quick ranges behave like toggles: clicking the active one clears it
    setTimeRange(value) {
      this.timeRange = this.timeRange === value && value !== 'custom' ? 'all' : value
      // Seed the custom range so the pickers never open empty
      if (this.timeRange === 'custom' && !this.customFrom && !this.customTo) {
        const today = this.today()
        this.customFrom = today
        this.customTo = today
      }
      this.page = 1
    },
    clearCustomRange() {
      this.customFrom = ''
      this.customTo = ''
      this.page = 1
    },
    // Free-text search over the fields a user would look for, including the last
    // message excerpt shown in the row (the only message guaranteed to be loaded
    // for every task: the list endpoints return it as a summary).
    matchesQuery(task, query) {
      const haystack = [
        task.name,
        task.description,
        task.board,
        // The resolved column (a sprint task's column comes from its status)
        this.taskColumn(task),
        task.status,
        task.mode,
        // Target / owner project names shown in the Project column
        this.taskProject(task).label,
        this.taskProject(task).owner,
        this.lastMessagePreview(task),
        ...(task.profiles || []),
        ...this.taskUsers(task),
        ...(task.file_list || []).map(file => `${file}`.split('/').reverse()[0])
      ]
        .filter(Boolean)
        .join(' ')
        .toLowerCase()
      return haystack.includes(query)
    },

    // ── Presentation helpers ──
    priorityMeta(priority) {
      return PRIORITIES[priority] || PRIORITIES[DEFAULT_PRIORITY]
    },
    statusMeta(status) {
      const config = this.$storex.chats.statusConfig(status)
      // Unknown status values keep their own label instead of the fallback one
      return config.value === status ? config : { ...config, value: status, label: status }
    },
    statusLabel(status) {
      return this.statusMeta(status).label
    },
    modeLabel(mode) {
      return this.$storex.chats.chatModeLabel(mode)
    },
    initial(name) {
      return `${name || '?'}`.trim().charAt(0).toUpperCase() || '?'
    },
    formatDate(value) {
      if (!value) return '—'
      const date = new Date(value)
      if (Number.isNaN(date.getTime())) return '—'
      return `${date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}, ${date.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })}`
    },
    // Age of a timestamp in the densest readable form ("just now", "12m ago",
    // "3h ago", "5d ago"), then the calendar date for anything older than a week.
    relativeTime(value) {
      if (!value) return '—'
      const date = new Date(value)
      if (Number.isNaN(date.getTime())) return '—'

      const minutes = Math.floor((Date.now() - date.getTime()) / 60000)
      if (minutes < 1) return 'just now'
      if (minutes < 60) return `${minutes}m ago`
      const hours = Math.floor(minutes / 60)
      if (hours < 24) return `${hours}h ago`
      const days = Math.floor(hours / 24)
      if (days < 7) return `${days}d ago`
      return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
    },
    // Due badge: colour + icon + label (never colour alone)
    dueState(task) {
      const due = task.due_date
      if (!due) {
        return { label: '—', class: 'text-base-content/25', icon: 'fa-regular fa-calendar' }
      }
      const label = new Date(due).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
      const today = this.today()
      if (this.taskStatus(task) === 'done') {
        return { label, class: 'text-success', icon: 'fa-solid fa-circle-check' }
      }
      if (due < today) {
        return { label: `Overdue · ${label}`, class: 'text-error', icon: 'fa-regular fa-clock' }
      }
      if (due === today) {
        return { label: 'Due today', class: 'text-warning', icon: 'fa-regular fa-clock' }
      }
      return { label, class: 'text-base-content/50', icon: 'fa-regular fa-calendar' }
    },

    // ── Interactions ──
    toggleSort(key) {
      if (this.sortBy === key) {
        this.sortDir = this.sortDir === 'asc' ? 'desc' : 'asc'
        return
      }
      this.sortBy = key
      // Text columns read better ascending, dates/weights descending
      this.sortDir = TEXT_SORT_KEYS.includes(key) ? 'asc' : key === 'name' ? 'asc' : 'desc'
      this.page = 1
    },
    sortIcon(key) {
      if (this.sortBy !== key) return 'fa-solid fa-sort'
      return this.sortDir === 'asc' ? 'fa-solid fa-sort-up' : 'fa-solid fa-sort-down'
    },
    resetFilters() {
      this.searchQuery = ''
      this.boardFilter = 'all'
      this.columnFilter = 'all'
      this.statusFilter = 'all'
      this.priorityFilter = 'all'
      this.profileFilter = 'all'
      this.assigneeFilter = 'all'
      this.modeFilter = 'all'
      this.dueFilter = 'all'
      this.timeRange = 'all'
      this.customFrom = ''
      this.customTo = ''
      this.mineOnly = false
      this.pinnedOnly = false
      this.hideSubtasks = false
      this.page = 1
    }
  }
}
</script>
