import { getterTree, mutationTree, actionTree } from 'typed-vuex'
import { $storex } from '.'
import { ChatSearchRequest } from '@/api/model/ChatSearchRequest'

export const namespaced = true

// ─── Config ──────────────────────────────────────────────────────────────────

export const PRIORITIES = {
  high: {
    value: 'high',
    label: 'High',
    icon: 'fa-solid fa-flag',
    badge: 'border-error/30 bg-error/10 text-error',
    dot: 'bg-error'
  },
  medium: {
    value: 'medium',
    label: 'Medium',
    icon: 'fa-solid fa-flag',
    badge: 'border-warning/30 bg-warning/10 text-warning',
    dot: 'bg-warning'
  },
  low: {
    value: 'low',
    label: 'Low',
    icon: 'fa-solid fa-flag',
    badge: 'border-success/30 bg-success/10 text-success',
    dot: 'bg-success'
  }
}

export const TASK_STATUS = {
  todo:   { value: 'todo',   label: 'To Do',       icon: 'fa-regular fa-circle',       color: 'text-base-content/40' },
  doing:  { value: 'doing',  label: 'In Progress', icon: 'fa-solid fa-circle-play',    color: 'text-primary' },
  onhold: { value: 'onhold', label: 'On Hold',     icon: 'fa-solid fa-circle-pause',   color: 'text-warning' },
  done:   { value: 'done',   label: 'Done',        icon: 'fa-solid fa-circle-check',   color: 'text-success' }
}

const PRIORITY_WEIGHT = { high: 0, medium: 1, low: 2 }
const DEFAULT_PRIORITY = 'low'
const DEFAULT_RANGE = 'month'
const RANGE_VALUES = { today: true, week: true, month: true, custom: true }

// The /api/chats/search endpoint caps page_size at 100.
// We no longer fetch every page up-front: pages are loaded on demand when the
// user scrolls to the bottom of the list (see loadNextPage / fetchPage).
const PAGE_SIZE = 100
const MAX_PAGES = 50 // safety cap (100 * 50 = 5000 tasks)

// Fields scanned by the planning/follow-up dataset search.
// We skip heavy message/history scans: only board/column/status/mode matter.
function planningSearchFilters() {
  return {
    search_name: true,
    search_description: true,
    search_messages: false,
    search_message_metadata: false,
    search_history: false,
    search_files: false,
    search_model: false,
    search_status: true,
    search_mode: true
  }
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

function today() {
  return new Date().toISOString().slice(0, 10)
}

function daysAgo(days) {
  const date = new Date()
  date.setDate(date.getDate() - days)
  return date.toISOString().slice(0, 10)
}

function normalizePriority(priority) {
  return Object.prototype.hasOwnProperty.call(PRIORITIES, priority)
    ? priority
    : DEFAULT_PRIORITY
}

function relativeTime(value) {
  if (!value) return ''
  const then = new Date(value).getTime()
  if (Number.isNaN(then)) return ''
  const minutes = Math.round((Date.now() - then) / 60000)
  if (minutes < 1) return 'just now'
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.round(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.round(hours / 24)
  if (days < 30) return `${days}d ago`
  return `${Math.round(days / 30)}mo ago`
}

// A search result is either the chat itself or a wrapper { chat, ... }
function resultToChat(result) {
  return result?.chat || result
}

function dateRangeForFilter(state) {
  const now = today()

  if (state.rangeFilter === 'today') {
    return { from_date: now, to_date: now }
  }

  if (state.rangeFilter === 'week') {
    return { from_date: daysAgo(7), to_date: now }
  }

  if (state.rangeFilter === 'custom') {
    return {
      from_date: state.customFromDate || daysAgo(30),
      to_date: state.customToDate || now
    }
  }

  // Default: last 30 days
  return { from_date: daysAgo(30), to_date: now }
}

// Map a backend Chat into the task shape consumed by the planning views
function chatToTask(chat) {
  return {
    id: chat.id,
    name: chat.name,
    board: chat.board,
    column: chat.column,
    status: chat.status || 'todo',
    priority: normalizePriority(chat.priority),
    dueDate: chat.due_date || null,
    progress: Number(chat.progress) || 0,
    assignees: chat.assignees || [],
    sort_order: chat.sort_index ?? null,
    updatedAt: chat.updated_at || chat.created_at || null,
    users: chat.users || []
  }
}

// Derive an activity entry from a task's real current state
function taskToActivity(task) {
  const actor = task.users?.[0] || 'unknown'
  const name = task.name || task.column || task.board || task.id
  let text = `updated "${name}"`
  let tone = 'primary'

  if (task.status === 'done') {
    text = `completed "${name}"`
    tone = 'success'
  } else if (task.status === 'doing') {
    text = `moved "${name}" to ${task.column || 'In Progress'}`
    tone = 'info'
  } else if (task.status === 'onhold') {
    text = `put "${name}" on hold`
    tone = 'warning'
  }

  return {
    id: `${task.id}-${task.updatedAt}`,
    actor,
    text,
    target: task.id,
    timeLabel: relativeTime(task.updatedAt),
    time: task.updatedAt,
    tone
  }
}

function byPriorityAndDue(a, b) {
  const pa = PRIORITY_WEIGHT[a.priority] ?? 2
  const pb = PRIORITY_WEIGHT[b.priority] ?? 2
  if (pa !== pb) return pa - pb

  const aDue = a.dueDate || '9999-12-31'
  const bDue = b.dueDate || '9999-12-31'
  if (aDue !== bDue) return aDue < bDue ? -1 : 1
  return (a.name || '').localeCompare(b.name || '')
}

function applyTaskUpdates(task, updates) {
  const next = {}

  if ('priority' in updates) next.priority = normalizePriority(updates.priority)
  if ('due_date' in updates) next.dueDate = updates.due_date || null
  if ('status' in updates) next.status = updates.status
  if ('progress' in updates) {
    next.progress = Math.max(0, Math.min(100, Number(updates.progress) || 0))
  }
  if ('assignees' in updates) next.assignees = updates.assignees || []
  if ('sort_index' in updates) next.sort_order = updates.sort_index ?? null

  next.updatedAt = new Date().toISOString()

  return next
}

// ─── State ────────────────────────────────────────────────────────────────────
// Tasks are loaded incrementally from the /api/chats/search endpoint, scoped to
// a date range (default: last 30 days). Only the first page is fetched when the
// dataset filter changes; subsequent pages load as the user scrolls to the
// bottom of the list.

export const state = () => ({
  selectedTaskId: null,
  filter: '',
  boardFilter: 'all',
  assigneeFilter: 'all',
  rangeFilter: DEFAULT_RANGE,
  customFromDate: null,
  customToDate: null,
  tasks: [],
  rawChatsById: {},
  loading: false,
  loadingMore: false,
  loaded: false,
  error: null,

  // ── Pagination (incremental loading) ──
  currentPage: 0,   // last successfully loaded page
  hasMore: true,    // backend reports another page
  totalCount: 0,    // total matches reported by the backend ("Y")
  loadToken: 0      // guards against stale responses after a filter reset
})

// ─── Getters ──────────────────────────────────────────────────────────────────

export const getters = getterTree(state, {
  allTasks: state => state.tasks || [],

  selectedTask: (state, getters) => getters.allTasks.find(t => t.id === state.selectedTaskId) || null,

  boards: (state, getters) => [...new Set(getters.allTasks.map(t => t.board).filter(Boolean))].sort(),

  assignees: (state, getters) => [...new Set(getters.allTasks.flatMap(t => t.assignees || []))].sort(),

  priorityConfig: () => priority => PRIORITIES[priority] || PRIORITIES[DEFAULT_PRIORITY],

  statusConfig: () => status => TASK_STATUS[status] || TASK_STATUS.todo,

  statusList: () => Object.values(TASK_STATUS),

  dateRange: state => dateRangeForFilter(state),

  // ─── Pagination counters ("Showing X of Y") ───────────────────────────────
  loadedCount: state => state.tasks?.length || 0,
  totalCount: state => state.totalCount || 0,
  remainingCount: (state, getters) => Math.max(0, getters.totalCount - getters.loadedCount),
  hasMore: state => state.hasMore,
  loadingMore: state => state.loadingMore,

  filteredTasks: (state, getters) => {
    return getters.allTasks.filter(task => {
      if (state.boardFilter !== 'all' && task.board !== state.boardFilter) return false
      if (state.assigneeFilter !== 'all' && !(task.assignees || []).includes(state.assigneeFilter)) return false
      if (state.filter) {
        const q = state.filter.toLowerCase()
        const hay = `${task.name || ''} ${task.board || ''} ${task.column || ''}`.toLowerCase()
        if (!hay.includes(q)) return false
      }
      return true
    })
  },

  priorityGroups: (state, getters) => {
    const groups = { high: [], medium: [], low: [] }
    getters.filteredTasks.forEach(task => {
      (groups[task.priority] || groups.low).push(task)
    })

    for (const key of Object.keys(groups)) {
      groups[key].sort((a, b) => {
        const ao = a.sort_order ?? Number.MAX_SAFE_INTEGER
        const bo = b.sort_order ?? Number.MAX_SAFE_INTEGER
        if (ao !== bo) return ao - bo
        return byPriorityAndDue(a, b)
      })
    }
    return groups
  },

  metrics: (state, getters) => {
    const tasks = getters.filteredTasks
    const now = today()
    const total = tasks.length
    const done = tasks.filter(t => t.status === 'done').length
    const active = tasks.filter(t => t.status === 'doing' || t.status === 'todo').length
    const onHold = tasks.filter(t => t.status === 'onhold').length
    const overdue = tasks.filter(t => t.dueDate && t.dueDate < now && t.status !== 'done').length
    const dueToday = tasks.filter(t => t.dueDate === now && t.status !== 'done').length
    const completion = total ? Math.round((done / total) * 100) : 0

    return { total, done, active, onHold, overdue, dueToday, completion }
  },

  needsAttention: (state, getters) => {
    const now = today()
    return getters.filteredTasks
      .filter(t => t.status !== 'done')
      .filter(t => {
        const overdue = t.dueDate && t.dueDate < now
        const dueToday = t.dueDate === now
        const unassignedHigh = t.priority === 'high' && !(t.assignees || []).length
        return overdue || dueToday || unassignedHigh
      })
      .sort(byPriorityAndDue)
  },

  boardProgress: (state, getters) => {
    const map = {}
    getters.filteredTasks.forEach(task => {
      const board = task.board || '--none--'
      if (!map[board]) map[board] = { board, total: 0, done: 0 }
      map[board].total += 1
      if (task.status === 'done') map[board].done += 1
    })

    return Object.values(map)
      .map(b => ({ ...b, percentage: b.total ? Math.round((b.done / b.total) * 100) : 0 }))
      .sort((a, b) => a.board.localeCompare(b.board))
  },

  // Derived from the loaded tasks: most recently updated tasks first
  activityFeed: (state, getters) => {
    return getters.filteredTasks
      .filter(t => t.updatedAt)
      .sort((a, b) => (a.updatedAt < b.updatedAt ? 1 : -1))
      .slice(0, 30)
      .map(taskToActivity)
  }
})

// ─── Mutations ────────────────────────────────────────────────────────────────

export const mutations = mutationTree(state, {
  setSelectedTaskId(state, taskId) {
    state.selectedTaskId = taskId || null
  },

  setFilter(state, filter) {
    state.filter = filter || ''
  },

  setBoardFilter(state, board) {
    state.boardFilter = board || 'all'
  },

  setAssigneeFilter(state, assignee) {
    state.assigneeFilter = assignee || 'all'
  },

  setRangeFilter(state, range) {
    state.rangeFilter = range || DEFAULT_RANGE
  },

  setCustomFromDate(state, date) {
    state.customFromDate = date || null
  },

  setCustomToDate(state, date) {
    state.customToDate = date || null
  },

  setTasks(state, tasks) {
    state.tasks = tasks || []
  },

  appendTasks(state, tasks) {
    const existing = new Set(state.tasks.map(t => t.id))
    const additions = (tasks || []).filter(t => t.id && !existing.has(t.id))
    state.tasks = [...state.tasks, ...additions]
  },

  setRawChatsById(state, rawChatsById) {
    state.rawChatsById = rawChatsById || {}
  },

  appendRawChatsById(state, chatsById) {
    state.rawChatsById = { ...state.rawChatsById, ...(chatsById || {}) }
  },

  setLoading(state, loading) {
    state.loading = !!loading
  },

  setLoadingMore(state, loading) {
    state.loadingMore = !!loading
  },

  setLoaded(state, loaded) {
    state.loaded = !!loaded
  },

  setError(state, error) {
    state.error = error || null
  },

  setCurrentPage(state, page) {
    state.currentPage = Number(page) || 0
  },

  setHasMore(state, hasMore) {
    state.hasMore = !!hasMore
  },

  setTotalCount(state, total) {
    state.totalCount = Number(total) || 0
  },

  setLoadToken(state, token) {
    state.loadToken = Number(token) || 0
  },

  patchTask(state, { taskId, updates }) {
    const index = state.tasks.findIndex(t => t.id === taskId)
    if (index === -1) return
    const task = state.tasks[index]
    state.tasks.splice(index, 1, { ...task, ...applyTaskUpdates(task, updates) })
  }
})

// ─── Persistence helper ───────────────────────────────────────────────────────
// Writes task attributes through the chats store → /api/chats/metadata,
// which merges them into the persisted Chat without touching messages.

function persistTask(state, chatId, updates) {
  const chat = state.rawChatsById[chatId] || $storex.chats.chats?.[chatId]
  if (!chat) return Promise.resolve(null)
  return $storex.chats.updateChatInfo({ chat, updates })
}

// ─── Actions ──────────────────────────────────────────────────────────────────

export const actions = actionTree(
  { state, getters, mutations },
  {
    async init() {
      // Tasks are loaded lazily by the planning/follow-up views via ensureLoaded().
    },

    async ensureLoaded({ state }) {
      if (!state.loaded && !state.loading && !state.loadingMore) {
        await $storex.planning.loadTasks()
      }
    },

    // (Re)load the dataset from page 1. Called whenever the dataset filter
    // (date range) changes — this RESTARTS the pagination counters.
    async loadTasks({ state }) {
      const token = (state.loadToken || 0) + 1
      mutations.setLoadToken(state, token)

      // Restart counters
      mutations.setTasks(state, [])
      mutations.setRawChatsById(state, {})
      mutations.setCurrentPage(state, 0)
      mutations.setHasMore(state, true)
      mutations.setTotalCount(state, 0)
      mutations.setError(state, null)
      mutations.setLoaded(state, false)

      await $storex.planning.fetchPage({ page: 1, token })
    },

    // Load the next page. Safe to call repeatedly (e.g. on every scroll event):
    // in-flight loads are ignored and stale responses are discarded.
    async loadNextPage({ state }) {
      if (state.loading || state.loadingMore || !state.hasMore) return
      const nextPage = (state.currentPage || 0) + 1
      await $storex.planning.fetchPage({ page: nextPage, token: state.loadToken })
    },

    // Fetch a single page and merge (or replace, when it is page 1).
    async fetchPage({ state }, { page, token }) {
      const isFirst = page === 1
      mutations.setLoading(state, isFirst)
      mutations.setLoadingMore(state, !isFirst)

      const { from_date, to_date } = dateRangeForFilter(state)
      const searchRequest = new ChatSearchRequest({
        query: '',
        from_date,
        to_date,
        page,
        page_size: PAGE_SIZE,
        filters: planningSearchFilters()
      })

      try {
        const response = await $storex.chats.searchChats(searchRequest)

        // A newer load started while this one was in flight: discard.
        if (token !== state.loadToken) return

        if (!response) return

        if (response.error) {
          mutations.setError(state, response.error)
          if (isFirst) {
            mutations.setTasks(state, [])
            mutations.setRawChatsById(state, {})
          }
          return
        }

        const chatsById = {}
        ;(response.results || [])
          .map(resultToChat)
          .filter(c => c?.id)
          .forEach(chat => { chatsById[chat.id] = chat })

        const newTasks = Object.values(chatsById)
          .filter(c => !c.is_template && (c.board || c.column || c.mode === 'task'))
          .map(chatToTask)

        if (isFirst) {
          mutations.setTasks(state, newTasks)
          mutations.setRawChatsById(state, chatsById)
        } else {
          mutations.appendTasks(state, newTasks)
          mutations.appendRawChatsById(state, chatsById)
        }

        mutations.setCurrentPage(state, page)
        mutations.setTotalCount(state, response.total || 0)

        // Stop when the backend reports no next page, or a page came back empty
        // (guards against a mis-reported has_next).
        const pageCount = (response.results || []).length
        // FIX: `state` MUST be the first argument — omitting it makes the boolean
        // the `state` parameter and throws "Cannot create property ... on boolean".
        mutations.setHasMore(state, !!response.has_next && pageCount > 0 && page < MAX_PAGES)
        mutations.setLoaded(state, true)
      } catch (error) {
        console.error('[planning store] Failed to load planning tasks:', error)
        if (token === state.loadToken) {
          mutations.setError(state, error.message || 'Failed to load planning tasks')
          if (isFirst) mutations.setTasks(state, [])
        }
      } finally {
        // Only the current load token is allowed to clear the loading flags.
        if (token === state.loadToken) {
          mutations.setLoading(state, false)
          mutations.setLoadingMore(state, false)
        }
      }
    },

    reset({ state }) {
      mutations.setLoadToken(state, (state.loadToken || 0) + 1)
      mutations.setTasks(state, [])
      mutations.setRawChatsById(state, {})
      mutations.setLoaded(state, false)
      mutations.setSelectedTaskId(state, null)
      mutations.setError(state, null)
      mutations.setLoading(state, false)
      mutations.setLoadingMore(state, false)
      mutations.setCurrentPage(state, 0)
      mutations.setHasMore(state, true)
      mutations.setTotalCount(state, 0)
    },

    selectTask({ state }, taskId) {
      mutations.setSelectedTaskId(state, taskId)
    },

    clearSelection({ state }) {
      mutations.setSelectedTaskId(state, null)
    },

    setFilter({ state }, filter) {
      mutations.setFilter(state, filter)
    },

    setBoardFilter({ state }, board) {
      mutations.setBoardFilter(state, board)
    },

    setAssigneeFilter({ state }, assignee) {
      mutations.setAssigneeFilter(state, assignee)
    },

    async setRangeFilter({ state }, range) {
      const normalized = Object.prototype.hasOwnProperty.call(RANGE_VALUES, range)
        ? range
        : DEFAULT_RANGE

      mutations.setRangeFilter(state, normalized)

      if (normalized === 'custom' && (!state.customFromDate || !state.customToDate)) {
        mutations.setCustomFromDate(state, daysAgo(30))
        mutations.setCustomToDate(state, today())
      }

      // Dataset filter changed → restart counters & load page 1
      await $storex.planning.loadTasks()
    },

    async setCustomRange({ state }, { fromDate, toDate }) {
      if (fromDate) mutations.setCustomFromDate(state, fromDate)
      if (toDate) mutations.setCustomToDate(state, toDate)
      mutations.setRangeFilter(state, 'custom')

      // Dataset filter changed → restart counters & load page 1
      await $storex.planning.loadTasks()
    },

    async updatePriority({ state }, { taskId, priority }) {
      const normalized = normalizePriority(priority)
      await persistTask(state, taskId, { priority: normalized })
      mutations.patchTask(state, { taskId, updates: { priority: normalized } })
    },

    async updateDueDate({ state }, { taskId, dueDate }) {
      await persistTask(state, taskId, { due_date: dueDate || null })
      mutations.patchTask(state, { taskId, updates: { due_date: dueDate || null } })
    },

    async updateStatus({ state }, { taskId, status }) {
      await persistTask(state, taskId, { status })
      mutations.patchTask(state, { taskId, updates: { status } })
    },

    async updateProgress({ state }, { taskId, progress }) {
      const normalized = Math.max(0, Math.min(100, Number(progress) || 0))
      await persistTask(state, taskId, { progress: normalized })
      mutations.patchTask(state, { taskId, updates: { progress: normalized } })
    },

    async toggleAssignee({ state }, { taskId, username }) {
      const task = state.tasks.find(t => t.id === taskId)
      if (!task) return

      const assignees = task.assignees || []
      const next = assignees.includes(username)
        ? assignees.filter(u => u !== username)
        : [...assignees, username]

      await persistTask(state, taskId, { assignees: next })
      mutations.patchTask(state, { taskId, updates: { assignees: next } })
    },

    async reorderTasks({ state }, orderedIds) {
      await Promise.all(
        orderedIds.map((id, index) => persistTask(state, id, { sort_index: index }))
      )

      orderedIds.forEach((id, index) => {
        mutations.patchTask(state, { taskId: id, updates: { sort_index: index } })
      })
    }
  }
)