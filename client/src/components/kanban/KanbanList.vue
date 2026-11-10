<script setup>
import moment from 'moment'
</script>

<template>
  <div class="kanban-list w-full h-full flex flex-col gap-3">

    <!-- ── Sticky header bar ── -->
    <div class="sticky top-0 z-10 flex flex-col gap-2 pb-2 pt-1">
      <div class="flex gap-2 items-center">
        <!-- Search input -->
        <div class="input input-sm input-bordered flex items-center gap-2 flex-1 min-w-0">
          <i class="fa-solid fa-magnifying-glass opacity-40 text-sm shrink-0"></i>
          <input
            type="text"
            v-model="boardFilter"
            class="grow bg-transparent outline-none text-sm"
            placeholder="Search boards..."
          />
          <button
            v-if="boardFilter"
            @click="boardFilter = ''"
            class="btn btn-ghost btn-xs btn-circle shrink-0"
          >
            <i class="fa-solid fa-times text-xs"></i>
          </button>
        </div>

        <!-- Project-wide task search (all boards) -->
        <button
          class="btn btn-sm btn-ghost shrink-0 gap-1.5 tooltip tooltip-bottom"
          title="Search every task in the project"
          aria-label="Search every task"
          @click="$emit('find-tasks')"
        >
          <i class="fa-solid fa-magnifying-glass-chart text-xs"></i>
          <span class="hidden sm:inline">Find</span>
        </button>

        <!-- Task filters: keep only the boards holding matching tasks -->
        <button
          class="btn btn-sm shrink-0 gap-1.5"
          :class="showTaskFilters ? 'btn-primary' : 'btn-ghost'"
          :aria-expanded="showTaskFilters"
          aria-controls="kanban-task-filters"
          title="Filter boards by their tasks"
          @click="showTaskFilters = !showTaskFilters"
        >
          <i class="fa-solid fa-filter text-xs"></i>
          <span class="hidden sm:inline">Filters</span>
          <span
            v-if="activeTaskFilterCount"
            class="badge badge-xs"
            :class="showTaskFilters ? 'badge-neutral' : 'badge-primary'"
          >{{ activeTaskFilterCount }}</span>
        </button>

        <!-- New board button -->
        <button class="btn btn-sm btn-warning btn-outline shrink-0" @click="$emit('new-board')">
          <i class="fa-solid fa-plus"></i>
          <span class="hidden sm:inline">Board</span>
        </button>

        <!-- History button -->
        <button class="btn btn-sm btn-ghost shrink-0" @click="$emit('toogle-history')">
          <i class="fa-solid fa-clock-rotate-left"></i>
          <span class="hidden sm:inline">History</span>
        </button>
      </div>

      <!-- Task filters panel -->
      <div
        v-if="showTaskFilters"
        id="kanban-task-filters"
        class="flex flex-col gap-2 p-2 rounded-lg bg-base-200 border border-base-100"
      >
        <div class="grid grid-cols-2 sm:grid-cols-3 gap-2">
          <!-- Board filter: makes sense here, the list spans every board -->
          <label class="flex flex-col gap-1">
            <span class="text-[10px] uppercase tracking-wider text-base-content/40">Board</span>
            <select v-model="taskFilters.board" class="select select-xs select-bordered text-xs">
              <option value="all">All boards</option>
              <option v-for="title in boardTitles" :key="title" :value="title">{{ title }}</option>
            </select>
          </label>

          <label class="flex flex-col gap-1">
            <span class="text-[10px] uppercase tracking-wider text-base-content/40">Status</span>
            <select v-model="taskFilters.status" class="select select-xs select-bordered text-xs">
              <option value="all">All statuses</option>
              <option v-for="status in statusOptions" :key="status.value" :value="status.value">{{ status.label }}</option>
            </select>
          </label>

          <label class="flex flex-col gap-1">
            <span class="text-[10px] uppercase tracking-wider text-base-content/40">Priority</span>
            <select v-model="taskFilters.priority" class="select select-xs select-bordered text-xs">
              <option value="all">All priorities</option>
              <option v-for="priority in priorityOptions" :key="priority.value" :value="priority.value">{{ priority.label }}</option>
            </select>
          </label>

          <label class="flex flex-col gap-1">
            <span class="text-[10px] uppercase tracking-wider text-base-content/40">Profile</span>
            <select v-model="taskFilters.profile" class="select select-xs select-bordered text-xs">
              <option value="all">All profiles</option>
              <option v-for="profile in profileOptions" :key="profile" :value="profile">{{ profile }}</option>
            </select>
          </label>

          <label class="flex flex-col gap-1">
            <span class="text-[10px] uppercase tracking-wider text-base-content/40">Assignee</span>
            <select v-model="taskFilters.assignee" class="select select-xs select-bordered text-xs">
              <option value="all">All assignees</option>
              <option v-for="user in assigneeOptions" :key="user" :value="user">{{ user }}</option>
            </select>
          </label>

          <label class="flex flex-col gap-1">
            <span class="text-[10px] uppercase tracking-wider text-base-content/40">Time</span>
            <select v-model="taskFilters.time" class="select select-xs select-bordered text-xs">
              <option v-for="option in timeOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
            </select>
          </label>
        </div>

        <div class="flex flex-wrap items-center gap-2">
          <template v-if="taskFilters.time === 'custom'">
            <input
              v-model="taskFilters.from"
              type="date"
              class="input input-xs input-bordered text-xs"
              aria-label="From date"
            />
            <input
              v-model="taskFilters.to"
              type="date"
              class="input input-xs input-bordered text-xs"
              aria-label="To date"
            />
          </template>
          <span class="text-[11px] text-base-content/30">a board is listed while it holds matching tasks</span>
          <button
            v-if="hasTaskFilters"
            class="btn btn-ghost btn-xs gap-1.5 text-base-content/50 hover:text-error ml-auto"
            title="Clear the task filters"
            @click="resetTaskFilters"
          >
            <i class="fa-solid fa-rotate-left text-xs"></i>
            <span class="text-xs">Reset</span>
          </button>
        </div>
      </div>

      <!-- No results hint -->
      <div v-if="boardFilter && filteredBoards.length === 0" class="text-sm text-base-content/40 px-1">
        No boards found for "<span class="font-medium">{{ boardFilter }}</span>"
      </div>
      <div v-if="hasTaskFilters && !bookmarks.length && !sortedBoards.length" class="text-sm text-base-content/40 px-1">
        <i class="fa-solid fa-filter text-xs mr-1"></i>
        No boards hold tasks matching the filters
      </div>
    </div>

    <!-- ── Bookmarked boards (horizontal scroll on mobile) ── -->
    <div v-if="bookmarks.length">
      <div class="text-xs font-semibold text-base-content/40 uppercase tracking-wide px-1 mb-2">
        <i class="fa-solid fa-bookmark text-warning mr-1"></i> Bookmarks
      </div>
      <div class="flex gap-3 overflow-x-auto pb-1 snap-x snap-mandatory">
        <div
          v-for="board in bookmarks"
          :key="board.title"
          @click="selectBoard(board)"
          class="border-secondary/30 hover:border-secondary border rounded-md snap-start shrink-0 w-48 h-28 p-3 card card-bordered shadow rounded-xl cursor-pointer border-warning relative overflow-hidden active:scale-95 transition-transform"
        >
          <div
            class="absolute inset-0 opacity-30 rounded-xl bg-cover bg-center"
            :style="`background-image: url(${board.background})`"
            v-if="board.background"
          ></div>
          <div class="relative flex flex-col h-full gap-1">
            <div class="flex items-center gap-1">
              <i
                class="fa-solid fa-bookmark text-warning cursor-pointer"
                @click.stop="toggleBookmark(board)"
              ></i>
              <span class="text-sm font-semibold truncate">{{ board.title }}</span>
            </div>
            <p class="text-xs text-base-content/50 line-clamp-2">{{ board.description }}</p>
          </div>
        </div>
      </div>
    </div>

    <!-- ── All boards grid ── -->
    <div v-if="sortedBoards.length">
      <div class="text-xs font-semibold text-base-content/40 uppercase tracking-wide px-1 mb-2">
        Boards
      </div>
      <!-- Single column on mobile, 2 on sm, 3 on xl -->
      <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
        <div
          v-for="board in sortedBoards"
          :key="board.title"
          @click="selectBoard(board)"
          class="border-primary/30 hover:border-primary card card-bordered border border-base-100/80 hover:border-base-100 shadow rounded-xl cursor-pointer relative overflow-hidden active:scale-[0.98] transition-transform min-h-36"
        >
          <!-- Background image -->
          <div
            class="absolute inset-0 opacity-20 bg-cover bg-center"
            :style="`background-image: url(${board.background})`"
            v-if="board.background"
          ></div>

          <div class="card-body p-3 flex flex-col gap-1 relative">
            <!-- Timestamp (last task activity) -->
            <span class="text-xs text-base-content/40" v-if="boardLastActivity(board)">
              {{ moment(boardLastActivity(board)).fromNow() }}
            </span>

            <!-- Parent label -->
            <span class="text-xs text-base-content/40" v-if="board.parent_id">
              <i class="fa-solid fa-sitemap text-xs"></i> {{ board.parent_id }}
            </span>

            <!-- Title row -->
            <div class="flex items-start gap-2">
              <!-- Virtual board: fixed inbox affordance instead of a bookmark toggle -->
              <i
                v-if="!board.virtual"
                class="fa-solid fa-bookmark mt-0.5 shrink-0 cursor-pointer"
                :class="board.bookmark ? 'text-warning' : 'text-base-content/20'"
                @click.stop="toggleBookmark(board)"
              ></i>
              <i
                v-else
                class="fa-solid fa-inbox mt-0.5 shrink-0 text-base-content/40"
                title="Virtual board"
              ></i>
              <h2 class="font-bold text-sm leading-tight truncate flex-1" :title="board.title">
                {{ board.title }}
              </h2>
              <span
                v-if="board.virtual"
                class="badge badge-xs badge-warning badge-outline gap-0.5 shrink-0 mt-0.5"
                title="Chats without a board"
              >
                <i class="fa-solid fa-inbox text-[8px]"></i> no board
              </span>
              <span
                v-else-if="board.type === 'sprint'"
                class="badge badge-xs badge-primary badge-outline gap-0.5 shrink-0 mt-0.5"
                title="Sprint board"
              >
                <i class="fa-solid fa-layer-group text-[8px]"></i> sprint
              </span>
              <span
                v-if="board.manager?.enabled"
                class="badge badge-xs badge-success badge-outline gap-0.5 shrink-0 mt-0.5"
                :title="`Board manager: ${board.manager.profile || board.assignee || 'ProjectManager'}`"
              >
                <i class="fa-solid fa-user-tie text-[8px]"></i> manager
              </span>
            </div>

            <!-- Description -->
            <p class="text-xs text-base-content/60 line-clamp-2" v-if="board.description">
              {{ board.description }}
            </p>

            <!-- Search match info -->
            <div
              v-if="boardFilter && getMatchingContent(board).columns.length > 0"
              class="text-xs p-1.5 bg-base-200 rounded-lg mt-1"
            >
              <div class="text-base-content/50 truncate">
                <i class="fa-solid fa-table-columns text-xs mr-1"></i>
                {{ getMatchingContent(board).columns.join(', ') }}
              </div>
              <div v-if="getMatchingContent(board).chatCount" class="text-base-content/50 mt-0.5">
                <i class="fa-solid fa-message text-xs mr-1"></i>
                {{ getMatchingContent(board).chatCount }} chats
              </div>
            </div>

            <!-- Task filter match info -->
            <div
              v-if="hasTaskFilters"
              class="text-xs p-1.5 bg-base-200 rounded-lg mt-1 text-base-content/50"
            >
              <i class="fa-solid fa-list-check text-xs mr-1"></i>
              {{ matchingTaskCount(board) }} / {{ boardTaskCount(board) }} tasks match
            </div>

            <div class="grow"></div>

            <!-- Footer stats -->
            <div class="flex items-center gap-3 text-base-content/40 text-xs mt-1">
              <span class="flex items-center gap-1">
                <i class="fas fa-columns"></i>
                {{ board.columns?.length || 0 }}
              </span>
              <span class="flex items-center gap-1">
                <i class="fa-brands fa-trello"></i>
                {{ boardTaskCount(board) }}
              </span>
              <!-- Remote URL -->
              <a
                v-if="board.remote_url"
                class="ml-auto text-xs underline text-primary truncate max-w-[120px]"
                :title="board.remote_url"
                @click.stop="openRemoteBoard(board)"
              >
                <i class="fa-solid fa-link text-xs mr-0.5"></i>
                {{ board.remote_url }}
              </a>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Empty state -->
    <div v-if="!bookmarks.length && !sortedBoards.length && !hasAnyFilter" class="flex flex-col items-center justify-center py-16 text-base-content/30 gap-3">
      <i class="fa-brands fa-trello text-5xl"></i>
      <span class="text-sm">No boards yet</span>
      <button class="btn btn-sm btn-warning btn-outline" @click="$emit('new-board')">
        <i class="fa-solid fa-plus"></i> Create a board
      </button>
    </div>
  </div>
</template>

<script>
// Task priorities, same vocabulary the task table (TaskTableView) uses
const PRIORITIES = [
  { value: 'high', label: 'High' },
  { value: 'medium', label: 'Medium' },
  { value: 'low', label: 'Low' }
]
const DEFAULT_PRIORITY = 'low'

// Quick time ranges over the task timestamp (last update)
const TIME_FILTERS = [
  { value: 'all', label: 'Any time' },
  { value: '1h', label: 'Last hour' },
  { value: 'today', label: 'Today' },
  { value: 'week', label: 'This week' },
  { value: 'custom', label: 'Custom range' }
]

// Board titles and statuses are free text, compared ignoring case everywhere
// else in the kanban store — the list must do the same.
function sameKey(a, b) {
  return `${a ?? ''}`.trim().toLowerCase() === `${b ?? ''}`.trim().toLowerCase()
}

// `chat.status` defaults to the first canonical status when it is not set
function taskStatusValue(chat) {
  return chat?.status || 'todo'
}

// Same normalization the task table applies: an undefined priority counts as low
function taskPriorityValue(chat) {
  const value = `${chat?.priority || ''}`.trim().toLowerCase()
  return PRIORITIES.some(p => p.value === value) ? value : DEFAULT_PRIORITY
}

// Assignees may live on `users` (board stats) and/or `assignees` (planning)
function taskUsersValue(chat) {
  return [...new Set([...(chat?.users || []), ...(chat?.assignees || [])].filter(Boolean))]
}

export default {
  props: {
    boards: {
      type: Array,
      default: null
    },
    project: {
      type: Object,
      default: null
    },
    options: {
      type: Object,
      default: () => ({})
    }
  },
  data() {
    return {
      boardFilter: '',
      // Whether the extended task filters panel is open
      showTaskFilters: false,
      // Task filters: a board is listed while it holds tasks matching them.
      // The board filter makes sense here because the list spans every board.
      taskFilters: {
        board: 'all',
        status: 'all',
        priority: 'all',
        profile: 'all',
        assignee: 'all',
        time: 'all',
        from: '',
        to: ''
      },
      priorityOptions: PRIORITIES,
      timeOptions: TIME_FILTERS
    }
  },
  computed: {
    allStoredBoards() {
      // Use storex.kanban as the source of truth (includes the virtual board)
      return this.$storex.kanban.allBoards || []
    },
    displayBoards() {
      if (this.boards && Array.isArray(this.boards) && this.boards.length > 0) {
        return this.boards
      }
      return this.allStoredBoards
    },
    // Boards offered by the board filter
    boardTitles() {
      return this.displayBoards.map(board => board.title)
    },
    statusOptions() {
      return this.$storex.chats.statusList || []
    },
    profileOptions() {
      return this.uniqueTaskValues(this.allChats.flatMap(chat => chat.profiles || []))
    },
    assigneeOptions() {
      return this.uniqueTaskValues(this.allChats.flatMap(chat => taskUsersValue(chat)))
    },
    allChats() {
      return Object.values(this.$storex.chats.chats || {})
    },
    // Chats with no board — sourced from the shared store getter
    noBoardChats() {
      return this.$storex.kanban.noBoardChats || []
    },
    // Latest activity across the virtual board's chats
    virtualLastActivity() {
      return this.noBoardChats.reduce((latest, c) => {
        const ts = c.updated_at || c.lastMessageAt || null
        return ts && ts > (latest || '') ? ts : latest
      }, null)
    },
    chatMap() {
      const map = {}
      this.allChats.forEach(chat => {
        map[chat.id] = chat
      })
      return map
    },
    // Map board title -> latest task updated_at (board for kanban, membership for sprint)
    boardActivityMap() {
      const map = {}
      this.allChats.forEach(chat => {
        const ts = chat.updated_at || chat.created_at || null
        if (!ts) return
        const keys = [chat.board, ...(chat.sprints || [])].filter(Boolean)
        keys.forEach(key => {
          if (!map[key] || ts > map[key]) map[key] = ts
        })
      })
      return map
    },
    // ── Task filters state ──
    hasTaskFilters() {
      const filters = this.taskFilters
      return filters.board !== 'all' ||
        filters.status !== 'all' ||
        filters.priority !== 'all' ||
        filters.profile !== 'all' ||
        filters.assignee !== 'all' ||
        filters.time !== 'all'
    },
    // Number of active task filters (badge on the "Filters" button)
    activeTaskFilterCount() {
      const filters = this.taskFilters
      return [
        filters.board !== 'all',
        filters.status !== 'all',
        filters.priority !== 'all',
        filters.profile !== 'all',
        filters.assignee !== 'all',
        filters.time !== 'all'
      ].filter(Boolean).length
    },
    // Whether anything (text search or task filters) narrows the list
    hasAnyFilter() {
      return !!this.boardFilter?.trim() || this.hasTaskFilters
    },
    bookmarks() {
      // The virtual board is never bookmarked
      return this.displayBoards.filter(b => b.bookmark && !b.virtual && this.matchesFilter(b))
    },
    rootBoards() {
      if (this.boards && Array.isArray(this.boards)) {
        return this.boards
      }
      const allBoardIds = this.allStoredBoards.map(b => b.id)
      return this.allStoredBoards.filter(b => !allBoardIds.includes(b.parent_id))
    },
    filteredBoards() {
      if (!this.hasAnyFilter) return this.rootBoards
      return this.rootBoards.filter(board => this.matchesFilter(board))
    },
    sortedBoards() {
      return this.filteredBoards
        .filter(b => !b.bookmark)
        .sort((a, b) => {
          // Sort by latest task activity first, fallback to board last_update
          const aTs = this.boardLastActivity(a) || ''
          const bTs = this.boardLastActivity(b) || ''
          return aTs > bTs ? -1 : aTs < bTs ? 1 : 0
        })
    }
  },
  methods: {
    boardLastActivity(board) {
      if (board.virtual) return this.virtualLastActivity || board.last_update || null
      return this.boardActivityMap[board.title] || board.last_update || null
    },
    // Tasks of a board: kanban tasks carry `chat.board`, sprint tasks carry the
    // board id in `sprints` and the virtual board groups every board-less chat.
    boardTasks(board) {
      if (board.virtual) return this.noBoardChats
      const isSprint = board?.type === 'sprint'
      return this.allChats.filter(chat => isSprint
        ? (chat.sprints || []).some(id => sameKey(id, board.title))
        : sameKey(chat.board, board.title))
    },
    boardTaskCount(board) {
      return this.boardTasks(board).length
    },
    uniqueTaskValues(values) {
      return [...new Set((values || []).filter(Boolean))].sort((a, b) => `${a}`.localeCompare(`${b}`))
    },
    // How many of the board's tasks match the extended task filters
    matchingTaskCount(board) {
      return this.boardTasks(board).filter(task => this.taskMatchesFilters(task)).length
    },
    // A single task against the extended task filters
    taskMatchesFilters(task) {
      const filters = this.taskFilters
      if (filters.status !== 'all' && taskStatusValue(task) !== filters.status) return false
      if (filters.priority !== 'all' && taskPriorityValue(task) !== filters.priority) return false
      if (filters.profile !== 'all' && !(task.profiles || []).includes(filters.profile)) return false
      if (filters.assignee !== 'all' && !taskUsersValue(task).includes(filters.assignee)) return false
      if (!this.matchesTimeRange(task)) return false
      return true
    },
    // Task timestamp: last message activity, then the document timestamps
    taskTimestamp(task) {
      return task?.lastMessageAt || task?.updated_at || task?.created_at || null
    },
    matchesTimeRange(task) {
      const range = this.taskFilters.time
      if (range === 'all') return true

      const value = this.taskTimestamp(task)
      if (!value) return false
      const date = new Date(value)
      if (Number.isNaN(date.getTime())) return false

      const now = new Date()
      if (range === '1h') {
        // Rolling window, not a calendar boundary
        return date.getTime() >= now.getTime() - 60 * 60 * 1000
      }
      if (range === 'today') {
        return date >= new Date(now.getFullYear(), now.getMonth(), now.getDate())
      }
      if (range === 'week') {
        // Current week, starting on Monday (local time)
        const start = new Date(now.getFullYear(), now.getMonth(), now.getDate())
        start.setDate(start.getDate() - ((start.getDay() + 6) % 7))
        return date >= start
      }
      // Custom range: both bounds inclusive, "to" covers the whole day
      const from = this.taskFilters.from ? new Date(`${this.taskFilters.from}T00:00:00`) : null
      const to = this.taskFilters.to ? new Date(`${this.taskFilters.to}T23:59:59.999`) : null
      if (from && date < from) return false
      if (to && date > to) return false
      return true
    },
    // A board is listed when it belongs to the selected board AND holds at least
    // one task matching the extended filters
    matchesTaskFilters(board) {
      if (this.taskFilters.board !== 'all' && !sameKey(this.taskFilters.board, board.title)) {
        return false
      }
      if (!this.hasTaskFilters) return true
      return this.boardTasks(board).some(task => this.taskMatchesFilters(task))
    },
    matchesFilter(board) {
      // Extended task filters first: they decide which boards are relevant
      if (!this.matchesTaskFilters(board)) return false

      const filterLower = (this.boardFilter || '').toLowerCase()
      if (!filterLower) return true

      // The virtual board matches on its own title or any of its chats
      if (board.virtual) {
        if (board.title.toLowerCase().includes(filterLower)) return true
        return this.noBoardChats.some(chat => this.chatMatches(chat, filterLower))
      }

      if (board.title && board.title.toLowerCase().includes(filterLower)) {
        return true
      }

      if (board.columns && Array.isArray(board.columns)) {
        if (board.columns.some(col =>
          col.title && col.title.toLowerCase().includes(filterLower)
        )) {
          return true
        }
      }

      if (board.columns && Array.isArray(board.columns)) {
        for (const column of board.columns) {
          if (column.chats && Array.isArray(column.chats)) {
            for (const chatId of column.chats) {
              const chat = this.chatMap[chatId]
              if (chat && this.chatMatches(chat, filterLower)) {
                return true
              }
            }
          }
        }
      }

      // Sprint boards: match tasks that belong to the sprint
      if (board.type === 'sprint') {
        const sprintChats = this.allChats.filter(c => (c.sprints || []).includes(board.title))
        if (sprintChats.some(chat => this.chatMatches(chat, filterLower))) {
          return true
        }
      }

      return false
    },
    chatMatches(chat, filterLower) {
      if (!chat) return false

      if (chat.name && chat.name.toLowerCase().includes(filterLower)) {
        return true
      }

      if (chat.file_list?.some(f => f.toLowerCase().includes(filterLower))) {
        return true
      }

      if (chat.messages && Array.isArray(chat.messages)) {
        return chat.messages.some(msg =>
          (msg.content && msg.content.toLowerCase().includes(filterLower)) ||
          (msg.think && msg.think.toLowerCase().includes(filterLower)) ||
          (msg.files && msg.files.some(f => f.toLowerCase().includes(filterLower)))
        )
      }

      return false
    },
    getMatchingContent(board) {
      const filterLower = this.boardFilter.toLowerCase()
      const matchingColumns = []
      let chatCount = 0

      // The virtual board has no columns — report matching chats instead
      if (board.virtual) {
        chatCount = this.noBoardChats.filter(chat => this.chatMatches(chat, filterLower)).length
        return { columns: [], chatCount }
      }

      if (board.columns && Array.isArray(board.columns)) {
        for (const column of board.columns) {
          let columnMatches = false

          if (column.title && column.title.toLowerCase().includes(filterLower)) {
            matchingColumns.push(column.title)
            columnMatches = true
          }

          if (column.chats && Array.isArray(column.chats)) {
            for (const chatId of column.chats) {
              const chat = this.chatMap[chatId]
              if (chat && this.chatMatches(chat, filterLower)) {
                chatCount++
                if (!columnMatches) {
                  matchingColumns.push(column.title)
                  columnMatches = true
                }
              }
            }
          }
        }
      }

      return {
        columns: [...new Set(matchingColumns)],
        chatCount
      }
    },
    // Clear every extended task filter (the text search is cleared separately)
    resetTaskFilters() {
      this.taskFilters = {
        board: 'all',
        status: 'all',
        priority: 'all',
        profile: 'all',
        assignee: 'all',
        time: 'all',
        from: '',
        to: ''
      }
    },
    selectBoard(board) {
      this.$emit('select', board.title)
    },
    openRemoteBoard(board) {
      window.open(board.remote_url, '_blank')
    },
    toggleBookmark(board) {
      this.$emit('bookmark', board)
    }
  }
}
</script>