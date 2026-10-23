// ─────────────────────────────────────────────────────────────────────────────
// Solopreneur mode — REAL data bridge for the Projects and Sprints sections.
//
// This module holds no seed data: everything it exposes comes from the stores
// that already own the information.
//
//   projects.allProjects      → the project list (name, icon, folder, boards…)
//   project.$state.kanban     → boards of a project (the `kanban` store getters)
//   chats.chats               → the TICKETS: a sprint/kanban card IS a chat
//
// A ticket is a chat:
//   • sprint boards → the card's column is `chat.status` (todo/doing/onhold/done)
//   • kanban boards → the card's column is `chat.column`
// `$storex.kanban.sprintColumns(boardId)` already groups the chats by status,
// so the board is rendered straight from that getter — never from a local copy.
//
// The chats store is scoped to the ACTIVE project, so ticket-level information
// only exists for it. Picking another project activates it through the real
// `projects.activeProjectChanged()` action, which loads its boards and chats.
// That is why every project action funnels through `activate()`.
//
// Plain-language translation of the real states:
//   todo   → "To do"       doing → "In progress"
//   onhold → "On hold"     (this is the real "waiting for you" state)
//   done   → "Done"
// ─────────────────────────────────────────────────────────────────────────────
import { computed, reactive } from 'vue'
import moment from 'moment'
import { $storex } from '@/store'
import { useSolopreneur } from './useSolopreneur'

const { t, toast, goModule } = useSolopreneur()

// Projects rendered before the first "Load more" click, and added per click.
// Shared with the Summary card so both pages grow at the same rhythm.
export const PROJECTS_PAGE_SIZE = 4

// ── shared UI state ─────────────────────────────────────────────────────────
// Only ONE SolopreneurView is mounted at a time, so a module-scoped object
// keeps the Projects/Sprints sections in sync without prop drilling.
export const ui = reactive({
  projectId: null,   // null → the projects list is shown instead of a detail
  tab: 'overview',   // overview | sprints | settings
  sprintId: null,
  ticketId: null,
  filter: 'all',     // 'all' | a chat status value
  query: '',
  // How many projects the list currently shows. Accounts can own dozens of
  // them, so the list is paged instead of rendered in one very long column.
  projectLimit: PROJECTS_PAGE_SIZE,
  busy: false,
  errors: {}
})

// ── helpers ─────────────────────────────────────────────────────────────────
export function relative(value) {
  if (!value) return ''
  const m = moment(value)
  return m.isValid() ? m.fromNow() : ''
}

// Boards of a project, shaped like the `kanban.allBoards` getter: the board key
// doubles as `id`/`title` (boards are keyed by title in the kanban document).
function boardList(project) {
  const boards = project?.$state?.kanban?.boards
  if (!boards) return []
  return Object.keys(boards)
    .filter(title => boards[title])
    .map(title => ({
      ...boards[title],
      id: title,
      title,
      type: boards[title]?.type || 'kanban'
    }))
}

// A chat is a task when it is neither a template, a channel nor a thread.
function isTicket(chat) {
  return !!chat?.id && !chat.is_template && chat.mode !== 'channel' && !chat.message_id
}

const projectChats = computed(() => ($storex.chats.allChats || []).filter(isTicket))

function countByStatus(chats) {
  return chats.reduce((acc, chat) => {
    const status = chat.status || 'todo'
    acc[status] = (acc[status] || 0) + 1
    return acc
  }, {})
}

// Status copy in plain words, falling back to the app's own status label.
export function statusLabel(value) {
  const key = 'sp.' + value
  const translated = t(key)
  return translated === key ? $storex.chats.statusLabel(value) : translated
}

// ── projects ────────────────────────────────────────────────────────────────
export const projects = computed(() => {
  const activeId = $storex.projects.activeProject?.project_id
  const chats = projectChats.value

  return ($storex.projects.allProjects || []).map(project => {
    const boards = boardList(project)
    const active = !!activeId && project.project_id === activeId
    // Ticket data only exists for the active project (chats store is scoped).
    const own = active ? chats : []
    const done = own.filter(c => (c.status || 'todo') === 'done').length
    const onhold = own.filter(c => (c.status || 'todo') === 'onhold').length
    const lastBoardUpdate = boards.reduce(
      (latest, b) => (b.last_update && b.last_update > (latest || '') ? b.last_update : latest),
      null
    )

    return {
      id: project.project_id,
      name: project.project_name,
      icon: project.project_icon,
      path: project.abs_project_path || project.codx_path || '',
      project,
      active,
      boards,
      sprintBoards: boards.filter(b => b.type === 'sprint'),
      kanbanBoards: boards.filter(b => b.type !== 'sprint'),
      tasks: own.length,
      done,
      onhold,
      progress: own.length ? Math.round((done / own.length) * 100) : null,
      updated: project._metrics?.last_update || lastBoardUpdate
    }
  })
})

export const filterCounts = computed(() => ({
  all: projects.value.length,
  active: projects.value.filter(p => p.active).length,
  sprints: projects.value.filter(p => !!p.sprintBoards.length).length
}))

export const filteredProjects = computed(() => {
  const q = ui.query.trim().toLowerCase()
  return projects.value.filter(p => {
    if (ui.filter === 'active' && !p.active) return false
    if (ui.filter === 'sprints' && !p.sprintBoards.length) return false
    if (q && !p.name.toLowerCase().includes(q)) return false
    return true
  })
})

// ── projects list paging ────────────────────────────────────────────────────
// The list renders one page at a time (`PROJECTS_PAGE_SIZE` cards) and grows on
// demand, so an account with 40 projects still opens on a short, scannable page.
export const visibleProjects = computed(
  () => filteredProjects.value.slice(0, ui.projectLimit)
)

export const hiddenProjects = computed(
  () => Math.max(0, filteredProjects.value.length - visibleProjects.value.length)
)

export const hasMoreProjects = computed(() => hiddenProjects.value > 0)

// The free-text search is only worth its space when the list does not fit in
// one page — small accounts keep the clean two-row layout.
export const searchableProjects = computed(
  () => projects.value.length > PROJECTS_PAGE_SIZE
)

export function loadMoreProjects() {
  ui.projectLimit += PROJECTS_PAGE_SIZE
}

export function resetProjectsPage() {
  ui.projectLimit = PROJECTS_PAGE_SIZE
}

export const selectedProject = computed(
  () => projects.value.find(p => p.id === ui.projectId) || null
)

// "Tasks by status" of the open project (real chat statuses).
export const statusRows = computed(() => {
  const project = selectedProject.value
  if (!project?.active) return []
  const chats = projectChats.value
  const counts = countByStatus(chats)
  const total = chats.length || 1
  return $storex.chats.statusList
    .filter(status => counts[status.value])
    .map(status => ({
      value: status.value,
      label: statusLabel(status.value),
      count: counts[status.value],
      pct: Math.round((counts[status.value] / total) * 100)
    }))
})

// Newest tasks of the open project — the real activity feed of the project.
export const recentChats = computed(() => {
  const project = selectedProject.value
  if (!project?.active) return []
  return projectChats.value
    .slice()
    .sort((a, b) => ((a.updated_at || '') < (b.updated_at || '') ? 1 : -1))
    .slice(0, 5)
})

// Tasks of one sprint board (used by the projects detail, before opening it).
export function countSprintTasks(boardId) {
  if (!boardId) return 0
  return projectChats.value.filter(c => (c.sprints || []).includes(boardId)).length
}

export function countSprintDone(boardId) {
  if (!boardId) return 0
  return projectChats.value.filter(
    c => (c.sprints || []).includes(boardId) && (c.status || 'todo') === 'done'
  ).length
}

// ── sprints ─────────────────────────────────────────────────────────────────
export const sprintBoards = computed(() =>
  boardList($storex.projects.activeProject).filter(b => b.type === 'sprint')
)

export const selectedSprint = computed(() => {
  const list = sprintBoards.value
  if (!list.length) return null
  return list.find(b => b.id === ui.sprintId) || list[0]
})

export const selectedSprintId = computed(() => selectedSprint.value?.id || null)

// Columns (title + tasks) straight from the kanban store: each column groups
// the chats whose `status` matches the column's status.
export const sprintColumns = computed(() => {
  const id = selectedSprintId.value
  return id ? ($storex.kanban.sprintColumns(id) || []) : []
})

// Columns filtered by the active chip / search query.
export const visibleColumns = computed(() => {
  const q = ui.query.trim().toLowerCase()
  return sprintColumns.value.map(column => ({
    ...column,
    tasks: (column.tasks || []).filter(task => {
      if (q && !String(task.name || '').toLowerCase().includes(q)) return false
      return true
    })
  }))
})

// Chips: "All" + one per column, with their real counts.
export const statusFilters = computed(() => [
  { value: 'all', label: t('sp.all'), count: sprintColumns.value.reduce((n, c) => n + (c.tasks || []).length, 0) },
  ...sprintColumns.value.map(column => ({
    value: column.status,
    label: column.title,
    count: (column.tasks || []).length
  }))
])

export const sprintStats = computed(() => {
  const tickets = sprintColumns.value.flatMap(column => column.tasks || [])
  const by = countByStatus(tickets)
  const total = tickets.length
  const done = by.done || 0
  return {
    total,
    todo: by.todo || 0,
    doing: by.doing || 0,
    onhold: by.onhold || 0,
    rejected: by.rejected || 0,
    done,
    progress: total ? Math.round((done / total) * 100) : 0
  }
})

// ── open ticket (drawer) ────────────────────────────────────────────────────
export const openTicket = computed(
  () => (ui.ticketId ? $storex.chats.chats?.[ui.ticketId] || null : null)
)

export const ticketMessages = computed(() =>
  (openTicket.value?.messages || []).filter(m => !m.hide)
)

// ── actions: loading ────────────────────────────────────────────────────────
// The kanban document of the active project is required by every board view.
export async function ensureReady() {
  const project = $storex.projects.activeProject
  if (!project?.$api) return
  if (project.$state?.kanban) return
  try {
    await $storex.projects.loadKanban(project)
  } catch (err) {
    // A project without boards is still valid — the views show their empty state.
  }
}

async function activate(project) {
  if (!project) return
  ui.busy = true
  try {
    if ($storex.projects.activeProject?.project_id !== project.project_id) {
      await $storex.projects.activeProjectChanged(project)
    }
    await ensureReady()
  } catch (err) {
    toast(t('pp.openError'), 'error')
  } finally {
    ui.busy = false
  }
}

// ── actions: projects ───────────────────────────────────────────────────────
export async function selectProject(id) {
  const target = projects.value.find(p => p.id === id)
  if (!target) return null
  ui.projectId = id
  ui.tab = 'overview'
  ui.sprintId = null
  ui.ticketId = null
  ui.filter = 'all'
  ui.query = ''
  await activate(target.project)
  return target
}

export async function selectProjectByName(name) {
  const match = projects.value.find(p => p.name === name)
  return match ? selectProject(match.id) : null
}

export function backToList() {
  ui.projectId = null
  ui.ticketId = null
  ui.tab = 'overview'
}

export function setTab(tab) {
  ui.tab = ['overview', 'sprints', 'settings'].includes(tab) ? tab : 'overview'
}

// A new filter or query is a NEW result set: go back to the first page.
export function setFilter(value) {
  ui.filter = value || 'all'
  resetProjectsPage()
}

export function setQuery(value) {
  ui.query = value || ''
  resetProjectsPage()
}

export async function workOnProject() {
  await activate($storex.projects.activeProject)
}

export function openFullSettings() {
  const project = $storex.projects.activeProject
  const router = $storex.$router
  if (!project?.project_name || !router) return
  router.push({ name: 'settings', params: { projectName: project.project_name } }).catch(() => {})
}

export async function createProject({ name, repo }) {
  const value = String(name || '').trim()
  if (!value) {
    ui.errors = { name: t('pp.nameRequired') }
    return null
  }
  ui.errors = {}
  ui.busy = true
  try {
    // Real project creation: the store reloads the list and activates it.
    await $storex.projects.createNewProject({
      project_name: value,
      git_path: String(repo || '').trim() || null
    })
    toast(t('pp.created'))
    return value
  } catch (err) {
    toast(t('pp.createError'), 'error')
    return null
  } finally {
    ui.busy = false
  }
}

// ── actions: sprints ────────────────────────────────────────────────────────
export function setSprint(id) {
  ui.sprintId = id || null
  ui.ticketId = null
  ui.filter = 'all'
}

export function focusSprint(id) {
  setSprint(id)
}

export function openSprintBoard(boardId) {
  const target = boardId || selectedProject.value?.sprintBoards?.[0]?.id
  if (target) focusSprint(target)
  goModule('sprints')
}

// "Needs you" is the real `onhold` status: the task is blocked waiting on you.
export function showTicketsOnHold() {
  ui.filter = 'onhold'
  ui.ticketId = null
  goModule('sprints')
}

export async function createSprint({ name, description }) {
  const title = String(name || '').trim()
  if (!title) {
    ui.errors = { sprint: t('sp.nameRequired') }
    return null
  }
  ui.errors = {}
  try {
    const board = await $storex.kanban.createSprintBoard({
      title,
      description: String(description || '').trim()
    })
    if (board) setSprint(board.title || title)
    toast(t('sp.sprintCreated'))
    return board
  } catch (err) {
    toast(t('sp.sprintError'), 'error')
    return null
  }
}

// ── actions: tickets ────────────────────────────────────────────────────────
export async function openTicketById(id) {
  ui.ticketId = id
  const chat = $storex.chats.chats?.[id]
  if (!chat) return
  try {
    // Cards come from the chat list (summary + last message): load the full
    // history so the drawer can show the description and the conversation.
    await $storex.chats.loadUninitialized(chat)
  } catch (err) {
    // Showing the summary is still useful when the fetch fails.
  }
}

export function closeTicket() {
  ui.ticketId = null
}

async function moveTicket(chat, status) {
  if (!chat?.id || !status) return false
  if ((chat.status || 'todo') === status) return false
  try {
    await $storex.kanban.moveSprintStatus({ taskId: chat.id, status })
    toast(t('sp.moved'))
    return true
  } catch (err) {
    toast(t('sp.moveError'), 'error')
    return false
  }
}

export async function setTicketStatus(status) {
  const chat = openTicket.value
  return chat ? moveTicket(chat, status) : false
}

// Resume an "on hold" task: move it to the first column that is neither
// "done" nor its current status (usually "In progress").
export async function resumeTicket(id) {
  const chat = $storex.chats.chats?.[id]
  if (!chat) return false
  const current = chat.status || 'todo'
  const target = sprintColumns.value.find(c => c.status !== 'done' && c.status !== current)
  return target ? moveTicket(chat, target.status) : false
}

export async function sendTicketMessage(text) {
  const chat = openTicket.value
  const content = String(text || '').trim()
  if (!chat || !content) return false
  try {
    await $storex.chats.addMessage({
      chat,
      message: { role: 'user', content, done: true, user: $storex.api?.user?.username }
    })
    toast(t('sp.messageSent'))
    return true
  } catch (err) {
    toast(t('sp.messageError'), 'error')
    return false
  }
}

export async function createTicket({ name, details }) {
  const sprint = selectedSprint.value
  const title = String(name || '').trim()
  if (!sprint || !title) {
    ui.errors = { name: t('sp.nameRequired') }
    return null
  }
  ui.errors = {}
  try {
    // `newSprintTask` creates the chat with `sprints: [sprintId]` and the status
    // of the sprint's first column, so it lands in the board immediately.
    const chat = await $storex.kanban.newSprintTask({
      name: title,
      status: sprintColumns.value[0]?.status || 'todo',
      sprintId: sprint.id
    })
    const note = String(details || '').trim()
    if (chat?.id && note) {
      try {
        await $storex.chats.addMessage({
          chat,
          message: { role: 'user', content: note, done: true }
        })
      } catch (err) {
        // The task exists; the extra note is optional.
      }
    }
    toast(t('sp.ticketCreated'))
    return chat
  } catch (err) {
    toast(t('sp.ticketError'), 'error')
    return null
  }
}

export function useSolopreneurProjects() {
  return {
    // state
    ui,
    // projects
    projects,
    filteredProjects,
    visibleProjects,
    hiddenProjects,
    hasMoreProjects,
    searchableProjects,
    loadMoreProjects,
    resetProjectsPage,
    filterCounts,
    selectedProject,
    statusRows,
    recentChats,
    statusLabel,
    countSprintTasks,
    countSprintDone,
    // sprints
    sprintBoards,
    selectedSprint,
    selectedSprintId,
    sprintColumns,
    visibleColumns,
    statusFilters,
    sprintStats,
    // ticket drawer
    openTicket,
    ticketMessages,
    // helpers + actions
    relative,
    ensureReady,
    selectProject,
    selectProjectByName,
    backToList,
    setTab,
    setFilter,
    setQuery,
    workOnProject,
    openFullSettings,
    createProject,
    setSprint,
    focusSprint,
    openSprintBoard,
    showTicketsOnHold,
    createSprint,
    openTicketById,
    closeTicket,
    setTicketStatus,
    resumeTicket,
    sendTicketMessage,
    createTicket
  }
}