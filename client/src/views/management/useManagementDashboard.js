/**
 * ============================================================================
 * Management dashboard — view state, filters and derived aggregations.
 * ----------------------------------------------------------------------------
 * One reactive object (`d`) is shared by the shell and by every section
 * component, so the sections stay presentational and there is a single source
 * of truth for the time range, the filters and the loaded payloads.
 *
 * WHY `reactive({...})` AND NOT `{ ...computedRefs }`
 * ------------------------------------------------
 * `reactive()` unwraps the refs/computeds it contains, so a template can write
 * `d.metrics.blocked` instead of `d.metrics.value.blocked` — and the value stays
 * reactive. Passing one object down also keeps the child props to a single
 * `d`, which is what makes the six sections independent of each other.
 *
 * LOADING MODEL
 * -------------
 * Sections load lazily and independently: opening "Cost" never waits for
 * "Team". Changing the time range invalidates every section EXCEPT the one on
 * screen, so the operator sees the new numbers immediately and the rest reload
 * when they are visited (no stale window ever rendered).
 *
 * COST & AI
 * ---------
 * The cost/AI SCREEN is the product's analytics dashboard
 * (`components/analytics/MetricsDashboard.vue`), so this module no longer
 * derives charts or breakdowns for it. What stays here is the `cost` loader and
 * `data.cost`, because the Pulse KPIs ("AI spend", "AI spend trend") and the
 * assistant read them.
 *
 * PROJECT SCOPE
 * -------------
 * The dashboard is the welcome screen of "/" and "/:projectName", and it can be
 * scoped to any SET of projects (the header filter). The scope is:
 *   • initialised from the route — visiting "/<project_name>" starts with that
 *     project selected (and re-initialises when the route project changes),
 *   • sent to the backend (`project_ids`, plus the legacy `project_id` when a
 *     single project is selected) so aggregates are computed for the scope,
 *   • re-applied client side to every LIST payload (attention, activity, boards,
 *     forecast, tasks, team) so a scoped view stays truthful even before the
 *     server understands `project_ids`.
 * ============================================================================
 */
import { computed, reactive } from 'vue'
import { $storex } from '@/store'
import { API } from '@/api/api'
import { managementModule, NO_PROJECT } from '@/api/modules/management'

/* ── Constants ────────────────────────────────────────────────────────────── */

/** Time windows of the header. `days` drives every request. */
export const RANGES = [
  { id: 'today', label: 'Today', days: 0 },
  { id: 'week', label: '7d', days: 7 },
  { id: 'month', label: '30d', days: 30 },
  { id: 'quarter', label: '90d', days: 90 }
]

/** Left rail entries: one section = one question management asks. */
export const SECTIONS = [
  { id: 'pulse', label: 'Pulse', icon: 'fa-solid fa-heart-pulse', title: 'Pulse', subtitle: 'What needs you now, across every project' },
  { id: 'work', label: 'Work', icon: 'fa-solid fa-list-check', title: 'Work', subtitle: 'Every task, filtered and drillable' },
  { id: 'blockers', label: 'Blockers', icon: 'fa-solid fa-circle-exclamation', title: 'Blockers', subtitle: 'Stoppers, overdue work and unowned tasks' },
  { id: 'delivery', label: 'Delivery', icon: 'fa-solid fa-rocket', title: 'Delivery', subtitle: 'Forecast, velocity and demo dates' },
  { id: 'team', label: 'Team', icon: 'fa-solid fa-people-group', title: 'Team', subtitle: 'Capacity, workload and AI agents' },
  { id: 'cost', label: 'Cost & AI', icon: 'fa-solid fa-coins', title: 'Cost & AI', subtitle: 'Spend, tokens, models and budget' }
]

export const STATUS_META = {
  todo: { label: 'To Do', badge: 'badge-ghost' },
  doing: { label: 'In Progress', badge: 'badge-info' },
  onhold: { label: 'On Hold', badge: 'badge-warning' },
  done: { label: 'Done', badge: 'badge-success' }
}

export const PRIORITY_META = {
  high: { label: 'High', badge: 'badge-error' },
  medium: { label: 'Medium', badge: 'badge-warning' },
  low: { label: 'Low', badge: 'badge-success' }
}

export const REASON_META = {
  blocked: { label: 'Blocked', badge: 'badge-error' },
  overdue: { label: 'Overdue', badge: 'badge-error' },
  due_today: { label: 'Due today', badge: 'badge-warning' },
  unassigned_high: { label: 'Unassigned', badge: 'badge-warning' },
  stalled: { label: 'Stalled', badge: 'badge-ghost' }
}

/** Default filters of every section (also used by "clear"). */
export function defaultFilters() {
  return {
    work: { project_id: '', board_id: '', status: '', priority: '', assignee: '', search: '', sort: 'priority', dir: 'asc', page: 1, page_size: 12 },
    blockers: { reason: 'all', project_id: '' },
    delivery: { board_id: '' },
    team: { type: 'all', project_id: '', onlyHot: false },
    cost: { project_id: '', model: '', series: { cost: true, tokens: false, calls: true } }
  }
}

const STORE_KEY = 'codx.management.dashboard'

/* ── Date helpers ─────────────────────────────────────────────────────────── */

export function todayISO() {
  return new Date().toISOString().slice(0, 10)
}

export function dayOffset(days) {
  const date = new Date()
  date.setDate(date.getDate() + days)
  return date.toISOString().slice(0, 10)
}

/* ── Module client ────────────────────────────────────────────────────────── */

let client = null

function api() {
  if (!client) client = managementModule(API)
  return client
}

/* ── Small pure helpers used by the templates ─────────────────────────────── */

export function fmtNum(value) {
  const number = Number(value) || 0
  if (Math.abs(number) >= 1000000) return `${(number / 1000000).toFixed(1)}M`
  if (Math.abs(number) >= 1000) return `${(number / 1000).toFixed(1)}K`
  return String(Math.round(number * 10) / 10)
}

export function fmtCoins(value) {
  if (value === null || value === undefined) return '—'
  const number = Number(value) || 0
  if (Math.abs(number) >= 1000000) return `${(number / 1000000).toFixed(2)}M cx`
  if (Math.abs(number) >= 1000) return `${(number / 1000).toFixed(1)}K cx`
  return `${Math.round(number * 10) / 10} cx`
}

export function fmtDate(value) {
  if (!value) return '—'
  const date = new Date(`${String(value).slice(0, 10)}T12:00:00`)
  if (Number.isNaN(date.getTime())) return '—'
  return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}

export function relTime(value) {
  if (!value) return '—'
  const minutes = Math.round((Date.now() - new Date(value).getTime()) / 60000)
  if (minutes < 2) return 'now'
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.round(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.round(hours / 24)
  if (days < 30) return `${days}d ago`
  return `${Math.round(days / 30)}mo ago`
}

export function initials(name) {
  return String(name || '?')
    .split(/[\s-]+/)
    .map(word => word.charAt(0))
    .slice(0, 2)
    .join('')
    .toUpperCase()
}

/** Stable colour per person id (avatars without images). */
export function personColor(id) {
  const palette = ['#e2419f', '#38bdf8', '#22c55e', '#f59e0b', '#a855f7', '#14b8a6', '#f05252', '#6366f1']
  let sum = 0
  String(id || '').split('').forEach(char => { sum += char.charCodeAt(0) })
  return palette[sum % palette.length]
}

/** Due date → `{ text, tone }` (`tone` maps to a daisyUI text class). */
export function dueLabel(task) {
  if (!task) return { text: '—', tone: '' }
  const left = task.days_until_due
  if (left === null || left === undefined) return { text: fmtDate(task.due_date), tone: '' }
  if (left < 0) return { text: `${Math.abs(left)}d late`, tone: 'text-error' }
  if (left === 0) return { text: 'due today', tone: 'text-warning' }
  if (left === 1) return { text: 'due tomorrow', tone: 'text-warning' }
  return { text: fmtDate(task.due_date), tone: 'opacity-60' }
}

/** Route params are percent-encoded; decode defensively. */
function safeDecode(value) {
  try {
    return decodeURIComponent(value)
  } catch (error) {
    return value
  }
}

/**
 * Builds a polyline `d` attribute for an inline SVG chart.
 * Coordinates are computed here (not in the template) so the sections only
 * render strings.
 */
export function seriesPath(values, { width = 720, height = 180, pad = 10, max: forcedMax } = {}) {
  const numbers = (values || []).map(value => Number(value) || 0)
  if (!numbers.length) return ''
  const max = forcedMax || Math.max(1, ...numbers)
  const stepX = numbers.length > 1 ? (width - pad * 2) / (numbers.length - 1) : 0
  return numbers
    .map((value, index) => {
      const x = pad + stepX * index
      const y = pad + (height - pad * 2) * (1 - value / max)
      return `${index === 0 ? 'M' : 'L'}${x.toFixed(1)} ${y.toFixed(1)}`
    })
    .join(' ')
}

/* ── Composable ───────────────────────────────────────────────────────────── */

export function useManagementDashboard() {
  const stored = readStoredPreferences()

  const state = reactive({
    section: stored.section || 'pulse',
    range: stored.range || 'week',
    railOpen: false,
    loading: {},
    error: {},
    lastUpdated: null,
    filters: Object.assign(defaultFilters(), stored.filters || {}),
    // Project scope (multi-select). NEVER restored from storage: it is derived
    // from the route the dashboard was opened on (see initProjectFilter).
    projectIds: [],
    projectsInitialized: false,
    selectedTaskId: null,
    selectedMemberId: null,
    assistant: { open: false, thinking: false, messages: [] }
  })

  const data = reactive({
    projects: [],
    people: [],
    boards: [],
    dashboard: null,
    tasks: null,
    forecast: [],
    teamLoad: [],
    teamTasks: [],
    cost: null,
    burndown: null
  })

  /* ── Range / filters ─────────────────────────────────────────────────── */

  const bounds = computed(() => {
    const range = RANGES.find(entry => entry.id === state.range) || RANGES[1]
    return { from: dayOffset(-range.days), to: todayISO() }
  })

  const rangeLabel = computed(() => {
    const range = RANGES.find(entry => entry.id === state.range) || RANGES[1]
    return range.id === 'today' ? 'today' : `last ${range.days} days`
  })

  function setRange(id) {
    if (!RANGES.some(entry => entry.id === id) || state.range === id) return
    state.range = id
    // The window changed: every other section is stale. They reload on visit.
    Object.keys(data).forEach((key) => {
      if (key === 'projects' || key === 'people' || key === 'boards') return
      if (key !== sectionDataKey(state.section)) data[key] = Array.isArray(data[key]) ? [] : null
    })
    persist()
    load(state.section)
  }

  function setSection(id) {
    if (!SECTIONS.some(section => section.id === id)) return
    state.section = id
    state.railOpen = false
    persist()
    load(id)
  }

  /** Patch one section filter; resets its pagination (Work) when relevant. */
  function setFilter(scope, patch) {
    const target = state.filters[scope]
    if (!target) return
    Object.assign(target, patch)
    if ('page' in target && !('page' in patch)) target.page = 1
    persist()
  }

  function clearFilters(scope) {
    state.filters[scope] = defaultFilters()[scope]
    persist()
    load(state.section)
  }

  function sectionDataKey(section) {
    return {
      pulse: 'dashboard',
      work: 'tasks',
      blockers: 'dashboard',
      delivery: 'forecast',
      team: 'teamLoad',
      cost: 'cost'
    }[section] || 'dashboard'
  }

  /* ── Project scope (multi-select) ────────────────────────────────────── */

  /** Raw route project segment, e.g. "my.project" (still percent-encoded). */
  function routeProjectName() {
    const current = $storex?.$router?.currentRoute?.value
    return current?.params?.projectName || null
  }

  /** Normalise a project coming from the API into { id, name, color, icon }. */
  function decorateProject(project) {
    const id = project.id || project.project_id
    const name = project.name || project.project_name
    const all = $storex?.projects?.allProjects || []
    const live = (id ? $storex?.projects?.allProjectsById?.[id] : null) ||
      all.find(entry => entry.project_id === id || entry.project_name === name)
    return {
      id,
      name,
      color: project.color || project.project_color || live?.project_color || null,
      icon: project.icon || project.project_icon || null
    }
  }

  /** Every project known to the dashboard (the filter options). */
  const projects = computed(() => (data.projects || []).map(decorateProject))

  const selectedProjectIds = computed(() => state.projectIds)

  const allProjectsSelected = computed(() => {
    const all = projects.value
    if (!all.length) return true
    return all.every(project => state.projectIds.includes(project.id))
  })

  const hasProjectFilter = computed(() => !allProjectsSelected.value)

  const projectScopeLabel = computed(() => {
    const all = projects.value
    if (!all.length) return 'no projects'
    if (allProjectsSelected.value) return 'all projects'
    if (!state.projectIds.length) return 'no project selected'
    if (state.projectIds.length === 1) {
      const only = projects.value.find(project => project.id === state.projectIds[0])
      return only ? only.name : '1 project'
    }
    return `${state.projectIds.length} of ${all.length} projects`
  })

  /**
   * Ids the view is restricted to, or `null` when every project is visible
   * (no restriction at all — the cross-project default).
   */
  function selectedIds() {
    if (!projects.value.length) return null
    if (allProjectsSelected.value) return null
    return state.projectIds
  }

  /** Query fragment carrying the scope to the backend. */
  function projectQuery() {
    const ids = selectedIds()
    if (!ids) return {}
    const list = ids.length ? ids.join(',') : NO_PROJECT
    // A single project still sends the legacy parameter so an older server
    // (which only knows `project_id`) scopes correctly.
    return ids.length === 1
      ? { project_id: ids[0], project_ids: list }
      : { project_ids: list }
  }

  /** Does a row belonging to `projectId`/`projectName` pass the scope? */
  function projectMatches(projectId, projectName) {
    const ids = selectedIds()
    if (!ids) return true
    if (projectId && ids.includes(projectId)) return true
    if (projectName) {
      const found = projects.value.find(project => project.name === projectName)
      if (found && ids.includes(found.id)) return true
    }
    return false
  }

  /** Filter a list payload client side by the current scope. */
  function filterRows(rows, projectIdsOf) {
    const ids = selectedIds()
    if (!ids) return rows || []
    return (rows || []).filter((row) => {
      const values = [].concat(projectIdsOf(row) || []).filter(Boolean)
      return values.some(value => ids.includes(value))
    })
  }

  /** Project object(s) a team member belongs to. */
  function projectsByIds(ids) {
    return (ids || [])
      .map(id => projects.value.find(project => project.id === id))
      .filter(Boolean)
  }

  function memberProjects(person) {
    return projectsByIds(person?.project_ids)
  }

  /**
   * Compact "which projects" rendering for a team member:
   * `{ visible, extra }` so the template can show 2 tags and a "+N".
   */
  function memberProjectTags(person, max = 2) {
    const all = memberProjects(person)
    return { visible: all.slice(0, max), extra: Math.max(0, all.length - max) }
  }

  /** The project the route points at, resolved against the loaded projects. */
  function resolveRouteProject() {
    const raw = routeProjectName()
    if (!raw) return null
    const name = safeDecode(raw)
    return projects.value.find(project => project.name === name || project.name === raw || project.id === raw) || null
  }

  /** The active project (store), resolved against the loaded projects. */
  function resolveActiveProject() {
    const active = $storex?.projects?.activeProject
    if (!active) return null
    return projects.value.find(project =>
      project.id === active.project_id || project.name === active.project_name) || null
  }

  /**
   * First-run initialisation: "/<project_name>" starts focused on that project,
   * "/" (no route project) falls back to the active project and finally to
   * every project. Returns true when the selection changed.
   */
  function initProjectFilter() {
    if (state.projectsInitialized) return false
    const all = projects.value
    if (!all.length) return false
    const target = resolveRouteProject() || resolveActiveProject()
    state.projectIds = target ? [target.id] : all.map(project => project.id)
    state.projectsInitialized = true
    return true
  }

  /**
   * Re-initialise the scope when the URL project changes
   * (e.g. navigating from "/alpha" to "/beta").
   */
  function syncProjectFilterWithRoute() {
    const target = resolveRouteProject()
    if (!target) return
    state.projectsInitialized = true
    if (state.projectIds.length === 1 && state.projectIds[0] === target.id) return
    state.projectIds = [target.id]
    load(state.section)
  }

  function toggleProject(id) {
    if (!id) return
    state.projectsInitialized = true
    state.projectIds = state.projectIds.includes(id)
      ? state.projectIds.filter(entry => entry !== id)
      : [...state.projectIds, id]
    // Lists react instantly (client-side filter); the aggregates come back a
    // moment later, coalesced so ticking several projects is one round trip.
    reloadSoon()
  }

  function selectAllProjects() {
    state.projectsInitialized = true
    state.projectIds = projects.value.map(project => project.id)
    reloadSoon(0)
  }

  function clearProjectSelection() {
    state.projectsInitialized = true
    state.projectIds = []
    reloadSoon(0)
  }

  let reloadTimer = null

  function reloadSoon(delay = 250) {
    if (reloadTimer) clearTimeout(reloadTimer)
    reloadTimer = setTimeout(() => {
      reloadTimer = null
      load(state.section)
    }, delay)
  }

  /* ── Loading ─────────────────────────────────────────────────────────── */

  const requestKey = { current: 0 }

  async function load(section = state.section) {
    const loader = LOADERS[section]
    if (!loader) return
    const token = ++requestKey.current
    state.loading[section] = true
    state.error[section] = null

    try {
      await loader()
      if (token !== requestKey.current) return
      // The project list arrives with the first payload: resolve the initial
      // scope from the route and re-read once so the aggregates match it.
      if (initProjectFilter()) {
        await loader()
        if (token !== requestKey.current) return
      }
      state.lastUpdated = new Date()
    } catch (error) {
      if (token !== requestKey.current) return
      state.error[section] = error?.message || String(error)
    } finally {
      if (token === requestKey.current) state.loading[section] = false
    }
  }

  const LOADERS = {
    async pulse() {
      const payload = await api().overview({ ...bounds.value, ...projectQuery() })
      data.projects = payload.projects
      data.dashboard = payload.dashboard
      data.forecast = payload.forecast
      data.teamLoad = payload.teamLoad
      data.cost = payload.cost
      data.boards = payload.dashboard.board_progress
    },
    async work() {
      const filters = state.filters.work
      const scope = projectQuery()
      const payload = await api().tasks({
        ...bounds.value,
        project_ids: scope.project_ids,
        project_id: filters.project_id || scope.project_id || undefined,
        board_id: filters.board_id || undefined,
        statuses: filters.status ? [filters.status] : [],
        priorities: filters.priority ? [filters.priority] : [],
        assignees: filters.assignee ? [filters.assignee] : [],
        search: filters.search || undefined,
        sort: { field: filters.sort, dir: filters.dir },
        page: filters.page,
        page_size: filters.page_size
      })
      data.tasks = payload
      data.boards = payload.boards
      data.projects = payload.projects
      data.people = payload.people
    },
    async blockers() {
      const scope = projectQuery()
      const payload = await api().blockers({
        ...bounds.value,
        project_ids: scope.project_ids,
        project_id: state.filters.blockers.project_id || scope.project_id || undefined
      })
      data.dashboard = payload.dashboard
      data.projects = payload.projects
      if (!state.filters.delivery.board_id) {
        data.boards = payload.dashboard.board_progress
      }
    },
    async delivery() {
      const payload = await api().delivery({
        ...bounds.value,
        ...projectQuery(),
        board_id: state.filters.delivery.board_id || undefined
      })
      data.forecast = payload.forecast
      data.burndown = payload.burndown
      data.projects = payload.projects
      if (!state.filters.delivery.board_id && payload.burndown) {
        state.filters.delivery.board_id = payload.burndown.board_id
      }
    },
    async team() {
      const payload = await api().team({ ...bounds.value, ...projectQuery() })
      data.teamLoad = payload.teamLoad
      data.teamTasks = payload.tasks
      data.projects = payload.projects
    },
    async cost() {
      const scope = projectQuery()
      const payload = await api().cost({
        ...bounds.value,
        project_ids: scope.project_ids,
        project_id: state.filters.cost.project_id || scope.project_id || undefined,
        model: state.filters.cost.model || undefined
      })
      data.cost = payload
      data.projects = payload.projects
      data.people = payload.people
    }
  }

  function refresh() {
    return load(state.section)
  }

  /** People list for the "reassign" dialog (loaded on demand). */
  async function ensurePeople() {
    if (data.people.length) return data.people
    try {
      const payload = await api().tasks({ ...bounds.value, ...projectQuery(), page_size: 1 })
      data.people = payload.people
      data.projects = data.projects.length ? data.projects : payload.projects
    } catch (error) {
      data.people = []
    }
    return data.people
  }

  /* ── Mutations ───────────────────────────────────────────────────────── */

  async function patchTask(id, patch, message) {
    try {
      const updated = await api().updateTask(id, patch)
      // Re-read the section so every aggregate that depends on the task (KPIs,
      // attention queue, forecast) is consistent with the write.
      await load(state.section)
      if (message) notify(message)
      return updated
    } catch (error) {
      notify(`Update failed: ${error?.message || error}`, 'error')
      return null
    }
  }

  const notices = reactive({ items: [] })

  function notify(text, tone = 'success') {
    const id = `${Date.now()}-${Math.random().toString(16).slice(2)}`
    notices.items.push({ id, text, tone })
    setTimeout(() => {
      const index = notices.items.findIndex(item => item.id === id)
      if (index >= 0) notices.items.splice(index, 1)
    }, 3000)
  }

  function openTask(id) {
    state.selectedTaskId = id
  }

  function closeOverlays() {
    state.selectedTaskId = null
    state.selectedMemberId = null
  }

  function openMember(id) {
    state.selectedMemberId = id
  }

  async function resetMock() {
    api().reset()
    Object.keys(data).forEach((key) => { data[key] = Array.isArray(data[key]) ? [] : null })
    await load(state.section)
    notify('Mock data regenerated')
  }

  /* ── Assistant ───────────────────────────────────────────────────────── */

  const SUGGESTIONS = [
    'What is blocking the delivery?',
    'Where did the AI budget go?',
    'Who is overloaded?',
    'What ships next week?',
    'What did we finish this week?'
  ]

  function toggleAssistant(open) {
    state.assistant.open = open === undefined ? !state.assistant.open : !!open
  }

  async function ask(question) {
    const text = String(question || '').trim()
    if (!text) return
    state.assistant.open = true
    state.assistant.thinking = true
    state.assistant.messages.push({ role: 'user', text })

    try {
      const answer = await api().ask({ question: text, ...bounds.value, ...projectQuery() })
      state.assistant.messages.push({ role: 'bot', text: answer.answer, sources: answer.sources || [] })
    } catch (error) {
      state.assistant.messages.push({ role: 'bot', text: `I could not answer: ${error?.message || error}` })
    } finally {
      state.assistant.thinking = false
      state.assistant.messages = state.assistant.messages.slice(-20)
    }
  }

  /* ── Derived: shared ─────────────────────────────────────────────────── */

  const metrics = computed(() => data.dashboard?.metrics || {
    total: 0, done: 0, active: 0, on_hold: 0, overdue: 0, due_today: 0,
    unassigned: 0, blocked: 0, completion: 0, by_status: {}, by_priority: {}
  })

  // ── Scope-aware lists ──
  // Every list payload is re-filtered here, so the tables/lists/cards never
  // show a row from a project the operator has filtered out (even if the
  // server has not learned `project_ids` yet).
  const attention = computed(() => filterRows(
    data.dashboard?.attention,
    item => item.task?.project_id || item.project_id
  ))

  const activity = computed(() => {
    const ids = selectedIds()
    if (!ids) return data.dashboard?.activity || []
    return (data.dashboard?.activity || []).filter((entry) => {
      const projectId = entry.project_id || entry.task?.project_id
      const projectName = entry.project_name || entry.task?.project_name
      // An entry without any project metadata cannot be attributed; keep it.
      if (!projectId && !projectName) return true
      return projectMatches(projectId, projectName)
    })
  })

  const boardProgress = computed(() => filterRows(
    data.dashboard?.board_progress,
    board => board.project_id || board.id
  ))

  const forecast = computed(() => (data.forecast || []).filter(board =>
    projectMatches(board.project_id, board.project_name)))

  const nextDemo = computed(() => {
    return forecast.value
      .filter(board => board.demo_date)
      .sort((a, b) => (a.demo_date < b.demo_date ? -1 : 1))[0] || null
  })

  const atRiskBoards = computed(() => forecast.value.filter(board => board.status !== 'on_track'))

  const attentionByProject = computed(() => {
    const map = new Map()
    attention.value.forEach((item) => {
      const key = item.task.project_name
      map.set(key, (map.get(key) || 0) + 1)
    })
    return [...map.entries()].map(([name, total]) => ({ name, total })).sort((a, b) => b.total - a.total)
  })

  const oldestBlocker = computed(() => {
    const blocked = attention.value.filter(item => item.reason === 'blocked')
    if (!blocked.length) return 0
    return Math.max(...blocked.map(item => (
      Math.abs(Math.round((Date.now() - new Date(item.task.blocked_since || item.task.updated_at).getTime()) / 86400000))
    )))
  })

  /* ── Derived: blockers ───────────────────────────────────────────────── */

  const filteredAttention = computed(() => {
    const filters = state.filters.blockers
    return attention.value.filter((item) => {
      if (filters.reason !== 'all' && item.reason !== filters.reason) return false
      if (filters.project_id && item.task.project_id !== filters.project_id) return false
      return true
    })
  })

  const attentionCounts = computed(() => {
    const counts = {}
    attention.value.forEach((item) => { counts[item.reason] = (counts[item.reason] || 0) + 1 })
    return counts
  })

  /* ── Derived: delivery ───────────────────────────────────────────────── */

  const burndownChart = computed(() => {
    const points = data.burndown?.points || []
    const width = 720
    const height = 170
    const max = Math.max(1, ...points.map(point => Math.max(point.ideal, point.actual)))
    return {
      width,
      height,
      ideal: seriesPath(points.map(point => point.ideal), { width, height, max }),
      actual: seriesPath(points.map(point => point.actual), { width, height, max }),
      labels: points.filter((_, index) => index % 3 === 0 || index === points.length - 1),
      points
    }
  })

  const milestones = computed(() => {
    return forecast.value
      .filter(board => board.demo_date)
      .sort((a, b) => (a.demo_date < b.demo_date ? -1 : 1))
  })

  /* ── Derived: team ───────────────────────────────────────────────────── */

  /** People belonging to the selected projects (before the team filters). */
  const teamRoster = computed(() => {
    const ids = selectedIds()
    const all = data.teamLoad || []
    if (!ids) return all
    return all.filter(person => (person.project_ids || []).some(id => ids.includes(id)))
  })

  const teamMembers = computed(() => {
    const filters = state.filters.team
    return (teamRoster.value || [])
      .filter((person) => {
        if (filters.type !== 'all' && person.type !== filters.type) return false
        if (filters.project_id && !person.project_ids.includes(filters.project_id)) return false
        if (filters.onlyHot && person.load_pct < 85) return false
        return true
      })
      .slice()
      .sort((a, b) => b.load_pct - a.load_pct)
  })

  const teamSummary = computed(() => {
    const all = teamRoster.value || []
    const humans = all.filter(person => person.type === 'human')
    return {
      humans: humans.length,
      agents: all.filter(person => person.type === 'agent').length,
      averageLoad: humans.length
        ? Math.round(humans.reduce((sum, person) => sum + person.load_pct, 0) / humans.length)
        : 0,
      overloaded: humans.filter(person => person.load_pct >= 85).length,
      cost: all.reduce((sum, person) => sum + person.cost_cxjcoins, 0)
    }
  })

  const selectedMember = computed(() => {
    if (!state.selectedMemberId) return null
    return (data.teamLoad || []).find(person => person.id === state.selectedMemberId) || null
  })

  const selectedMemberTasks = computed(() => {
    if (!selectedMember.value) return []
    const pool = data.teamTasks.length ? data.teamTasks : (data.tasks?.tasks || [])
    return pool.filter(task => task.assignees.includes(selectedMember.value.id))
  })

  /* ── Derived: work ───────────────────────────────────────────────────── */

  const workTasks = computed(() => (data.tasks?.tasks || []).filter(task =>
    projectMatches(task.project_id, task.project_name)))

  const workPager = computed(() => {
    const payload = data.tasks || { total: 0, page: 1, page_size: 12, total_pages: 1 }
    const start = payload.total ? (payload.page - 1) * payload.page_size + 1 : 0
    const end = Math.min(payload.total, payload.page * payload.page_size)
    const pages = []
    for (let page = 1; page <= payload.total_pages; page += 1) {
      const far = payload.total_pages > 7 && page > 2 && page < payload.total_pages - 1 && Math.abs(page - payload.page) > 1
      if (far && pages[pages.length - 1] !== '…') {
        pages.push('…')
        continue
      }
      if (!far) pages.push(page)
    }
    return { start, end, pages, total: payload.total, page: payload.page, hasPrev: payload.has_prev, hasNext: payload.has_next }
  })

  const selectedTask = computed(() => {
    if (!state.selectedTaskId) return null
    const pools = [
      workTasks.value,
      attention.value.map(item => item.task),
      (data.teamTasks || [])
    ]
    for (const pool of pools) {
      const found = pool.find(task => task.id === state.selectedTaskId)
      if (found) return found
    }
    return null
  })

  /* ── Persistence (best effort: a strict browser may block storage) ───── */

  // NOTE: the project scope is deliberately NOT persisted — it is re-derived
  // from the route on every mount (see initProjectFilterSync below).
  function persist() {
    try {
      window.localStorage.setItem(STORE_KEY, JSON.stringify({
        section: state.section,
        range: state.range,
        filters: state.filters
      }))
    } catch (error) {
      /* storage disabled: preferences live only for this session */
    }
  }

  function readStoredPreferences() {
    try {
      const raw = window.localStorage.getItem(STORE_KEY)
      if (!raw) return {}
      const parsed = JSON.parse(raw)
      const filters = defaultFilters()
      Object.keys(filters).forEach((scope) => {
        if (parsed.filters?.[scope]) filters[scope] = Object.assign(filters[scope], parsed.filters[scope])
      })
      return { section: parsed.section, range: parsed.range, filters }
    } catch (error) {
      return {}
    }
  }

  /* ── Public object (one reactive bag for every section) ──────────────── */

  return reactive({
    // configuration
    RANGES,
    SECTIONS,
    STATUS_META,
    PRIORITY_META,
    REASON_META,
    SUGGESTIONS,
    // state
    state,
    data,
    notices,
    bounds,
    rangeLabel,
    // derived — project scope
    projects,
    selectedProjectIds,
    hasProjectFilter,
    allProjectsSelected,
    projectScopeLabel,
    // derived — shared
    metrics,
    attention,
    activity,
    boardProgress,
    forecast,
    nextDemo,
    atRiskBoards,
    attentionByProject,
    oldestBlocker,
    // derived — blockers
    filteredAttention,
    attentionCounts,
    // derived — delivery
    burndownChart,
    milestones,
    // derived — team
    teamMembers,
    teamRoster,
    teamSummary,
    selectedMember,
    selectedMemberTasks,
    // derived — work
    workTasks,
    workPager,
    selectedTask,
    // navigation / filters
    setRange,
    setSection,
    setFilter,
    clearFilters,
    // project scope actions
    toggleProject,
    selectAllProjects,
    clearProjectSelection,
    syncProjectFilterWithRoute,
    // loading
    load,
    refresh,
    ensurePeople,
    // mutation
    patchTask,
    notify,
    resetMock,
    // overlays
    openTask,
    openMember,
    closeOverlays,
    // assistant
    toggleAssistant,
    ask,
    // helpers for templates
    fmtNum,
    fmtCoins,
    fmtDate,
    relTime,
    initials,
    personColor,
    dueLabel,
    projectMatches,
    memberProjects,
    memberProjectTags
  })
}

export default useManagementDashboard
