// ─────────────────────────────────────────────────────────────────────────────
// Solopreneur mode — shared, singleton state + actions.
//
// The dashboard sections (summary / account / wallet / updates / messages)
// still own a self-contained reactive data layer that reproduces the approved
// mockup, while integrating with the real app where it matters:
//
//   • identity   → the current user (`$storex.api.user`) and the active
//                  project name are overlaid on the seeded profile.
//   • logout     → real `$storex.users.logout()`.
//   • new project→ REAL creation (`$storex.projects.createNewProject`).
//   • toasts     → real `$storex.ui.addNotification`.
//   • navigation → real router (`$storex.$router`) via `goModule()`, but ONLY
//                  when the screen is hosted by its route (see below).
//
// The Projects and Sprints sections do NOT use this file's data: they read the
// real stores through `useSolopreneurProjects.js`.
//
// Only ONE SolopreneurView is mounted at a time, so a module-scoped singleton
// keeps every child component in sync without prop-drilling.
// ─────────────────────────────────────────────────────────────────────────────
import { reactive } from 'vue'
import { $storex } from '@/store'
import { translate, LANG_LOCALE } from './i18n'

export const MODULES = ['summary', 'account', 'projects', 'sprints', 'wallet', 'updates', 'messages']

export const PLANS = [
  { id: 'basic', name: 'Basic', price: 8.99, note: 'One project · monthly billing' },
  { id: 'pro', name: 'Pro', price: 24.0, note: 'Unlimited projects · priority expert review' }
]

export const CREDIT_PACKS = [
  { id: 'p500', credits: 500, price: 5 },
  { id: 'p2000', credits: 2000, price: 18 },
  { id: 'p5000', credits: 5000, price: 40 }
]

// ── layout tiers ────────────────────────────────────────────────────────────
// The screen is hosted either full width (single / mobile mode → the
// "/solopreneur" route) or inside a dockview PANEL (desktop mode), whose width
// is unrelated to the window's. Breakpoints therefore CANNOT be used here:
// media queries would measure the window, and container queries proved
// unreliable in this build (the rail kept `w-full` while the row layout was
// already active, collapsing the content column to 0px).
//
// Instead the view MEASURES the width it is actually given and publishes it
// here (`setViewportWidth`), so every component reads one source of truth.
const COMPACT_WIDTH = 640 // phone / narrow panel: one-row summaries, tighter paddings
const WIDE_WIDTH = 1024 // rail beside the content instead of above it
const XL_WIDTH = 1280   // room for the calendar side column

function tiers(width) {
  const w = Math.max(0, Math.round(Number(width) || 0))
  return {
    width: w,
    isCompact: w < COMPACT_WIDTH,
    isWide: w >= WIDE_WIDTH,
    isXl: w >= XL_WIDTH
  }
}

function initialViewport() {
  // First paint happens before the ResizeObserver fires: start from the window
  // width so the desktop layout does not flash as a stacked (mobile) one.
  return tiers(typeof window === 'undefined' ? 0 : window.innerWidth)
}

// ── date helpers ────────────────────────────────────────────────────────────
function pad(n) { return String(n).padStart(2, '0') }
function isoDate(d) { return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}` }
function daysAgo(n) { const d = new Date(); d.setDate(d.getDate() - n); return isoDate(d) }
function monthFirst(offset = 0) {
  const now = new Date()
  return new Date(now.getFullYear(), now.getMonth() + offset, 1)
}

function initialsFrom(name) {
  const parts = String(name || '').trim().split(/\s+/).filter(Boolean)
  if (!parts.length) return 'BB'
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase()
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
}

function capitalize(value) {
  const s = String(value || '')
  return s.charAt(0).toUpperCase() + s.slice(1)
}

// ── seed data (approved mockup) ─────────────────────────────────────────────
// Only dashboard copy: the project list, the boards and the tickets come from
// the real stores (see useSolopreneurProjects.js).
function seed() {
  return {
    user: {
      name: 'Sarah Denner', first: 'Sarah', initials: 'BB', avatar: '',
      email: 'sarah@bellaboutique.com', business: 'Bella Boutique', owner: 'Sarah Denner',
      country: 'Spain', plan: 'Basic', signIn: 'Google', notifications: true
    },
    wallet: {
      credits: 500, plan: 'Basic', billing: 'Monthly', invoice: 8.99, due: isoDate(monthFirst(1))
    },
    stats: { uptime: '99.98%', hours: '38 h', tasks: 18 },
    tasks: [
      { id: 't_1', title: 'Fix the checkout button on mobile', time: '10:00', context: 'Online store', status: 'in_progress' },
      { id: 't_2', title: 'Approve the new payment provider', time: '12:30', context: 'Waiting for your OK', status: 'in_progress' },
      { id: 't_3', title: 'Write the docs for the booking flow', time: '16:00', context: 'Booking system', status: 'done' }
    ],
    updates: [
      { id: 'u_1', title: 'Backup completed', badge: 'All good', tone: 'green', kind: 'system', text: 'Your website and database were backed up overnight. Nothing to do.', when: '2 h ago', read: false },
      { id: 'u_2', title: 'Security scan passed', badge: 'All good', tone: 'green', kind: 'system', text: 'No issues found. We also updated 6 packages for you.', when: 'Yesterday', read: false },
      { id: 'u_3', title: 'New version published', badge: 'Published', tone: 'pink', kind: 'release', text: 'Your booking form now loads 40% faster. Tested and live.', when: '2 days ago', read: false }
    ],
    events: [
      { id: 'e_1', group: 'TODAY', time: '10:00', title: 'Weekly check-in', meta: 'Your hybrid team' },
      { id: 'e_2', group: 'TODAY', time: '13:30', title: 'Design review', meta: 'Online store' },
      { id: 'e_3', group: 'TOMORROW', time: '09:00', title: 'Deployment window', meta: 'Company website' },
      { id: 'e_4', group: 'IN 3 DAYS', time: '11:00', title: 'Security report', meta: 'Monthly summary' },
      { id: 'e_5', group: 'IN 3 DAYS', time: '16:00', title: 'Backup check', meta: 'Automatic' }
    ],
    messages: [
      { id: 'm_1', from: 'ai', text: 'Morning! I noticed your traffic doubled last week. Want me to check whether you need a bigger plan?', time: '09:12' },
      { id: 'm_2', from: 'me', text: 'Yes please — and can we add an online payment button to the shop?', time: '09:15' },
      { id: 'm_3', from: 'ai', text: 'On it. I will draft the change and a human expert will review it today.', time: '09:16' }
    ],
    invoices: [
      { id: 'i_3', date: isoDate(monthFirst(0)), desc: 'Basic plan · Monthly', amount: 8.99, status: 'Paid' },
      { id: 'i_2', date: isoDate(monthFirst(-1)), desc: 'Basic plan · Monthly', amount: 8.99, status: 'Paid' },
      { id: 'i_1', date: isoDate(monthFirst(-2)), desc: '500 cxj credits', amount: 5, status: 'Paid' }
    ]
  }
}

function freshUi() {
  return {
    modal: null,
    errors: {},
    typing: false,
    query: '',
    updatesFilter: 'all'
  }
}

// `module` is the ACTIVE SECTION of the screen, kept here (and not only in the
// route) because the view has two hosts — see `goModule()` below.
// `viewport` is the width the view is actually GIVEN (see `setViewportWidth`).
export const state = reactive({
  ...seed(),
  module: 'summary',
  lang: 'EN',
  viewport: initialViewport(),
  ui: freshUi()
})

// ── viewport ────────────────────────────────────────────────────────────────
function setViewportWidth(width) {
  const next = tiers(width)
  if (next.width === state.viewport.width) {
    state.viewport.isCompact = next.isCompact
    state.viewport.isWide = next.isWide
    state.viewport.isXl = next.isXl
    return
  }
  state.viewport.width = next.width
  state.viewport.isCompact = next.isCompact
  state.viewport.isWide = next.isWide
  state.viewport.isXl = next.isXl
}

// ── formatters ──────────────────────────────────────────────────────────────
function t(key) { return translate(state.lang, key) }
function money(n) { return '€' + Number(n).toFixed(2) }

function shortDate(iso) {
  if (!iso) return ''
  const d = new Date(iso + 'T00:00:00')
  return new Intl.DateTimeFormat(LANG_LOCALE[state.lang] || 'en-GB',
    { day: 'numeric', month: 'short', year: 'numeric' }).format(d)
}

function dateLine() {
  const fmt = new Intl.DateTimeFormat(LANG_LOCALE[state.lang] || 'en-GB',
    { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })
  let text = fmt.format(new Date())
  if (!text.includes(',')) text = text.replace(/^(\S+)\s/, '$1, ')
  return t('todayIs') + ' ' + text
}

function nowTime() {
  const d = new Date()
  return pad(d.getHours()) + ':' + pad(d.getMinutes())
}

// ── identity overlay (real user + active project) ───────────────────────────
function syncIdentity() {
  const apiUser = ($storex.api && $storex.api.user) || {}
  const project = ($storex.projects && $storex.projects.activeProject) || {}

  if (apiUser.username) {
    const name = apiUser.username
    state.user.name = name
    state.user.first = name.split(/[\s._-]/)[0]
    state.user.initials = initialsFrom(name)
    state.user.owner = name
  }
  if (apiUser.email) state.user.email = apiUser.email
  if (apiUser.avatar) state.user.avatar = apiUser.avatar
  if (apiUser.oauth_provider) state.user.signIn = capitalize(apiUser.oauth_provider)
  if (project.project_name) state.user.business = project.project_name
}

// ── navigation ──────────────────────────────────────────────────────────────
// The screen is hosted in one of two ways (see router/index.ts + config/apps.js):
//
//   • single / mobile mode → the ROUTE renders it ("/solopreneur/:module?")
//   • desktop mode        → a DOCKVIEW PANEL renders it, while the route stays
//                           on ".../desktop"
//
// In the panel the route must NOT change: pushing "/solopreneur/..." swaps
// <RouterView> away from Desktop.vue and tears the whole dockview (and its
// saved layout) down. So the module lives in `state.module` and only the route
// host mirrors it into the URL.
function isPanelHosted() {
  return !!$storex.ui?.isDesktopMode
}

function setModule(id) {
  state.module = MODULES.includes(id) ? id : 'summary'
}

function goModule(id) {
  setModule(id)
  if (isPanelHosted()) return
  const router = $storex.$router
  if (!router) return
  const target = state.module === 'summary'
    ? { name: 'solopreneur' }
    : { name: 'solopreneur', params: { module: state.module } }
  router.push(target).catch(() => {})
}

// ── modal helpers ───────────────────────────────────────────────────────────
function openModal(type, id = null) { state.ui.modal = { type, id } }
function closeModal() { state.ui.modal = null; state.ui.errors = {} }

// ── toasts (real app notifications) ─────────────────────────────────────────
function toast(text, type = 'success') {
  $storex.ui && $storex.ui.addNotification && $storex.ui.addNotification({ text, type })
}

// ── actions ─────────────────────────────────────────────────────────────────
// Real project creation. The store reloads the project list and activates the
// new project, so the Projects section shows it straight away.
async function createProject({ name, repo }) {
  const value = String(name || '').trim()
  if (!value) {
    state.ui.errors = { name: t('common.required') }
    return false
  }
  state.ui.errors = {}
  try {
    await $storex.projects.createNewProject({
      project_name: value,
      git_path: String(repo || '').trim() || null
    })
    closeModal()
    toast(t('toast.created'))
    return true
  } catch (err) {
    toast(t('pp.createError'), 'error')
    return false
  }
}

function saveAccount(data) {
  const errors = {}
  if (!String(data.business || '').trim()) errors.business = t('common.required')
  if (!String(data.owner || '').trim()) errors.owner = t('common.required')
  if (!/^[^@\s]+@[^@\s]+\.[a-z]{2,}$/i.test(String(data.email || ''))) {
    errors.email = t('common.emailInvalid')
  }
  state.ui.errors = errors
  if (Object.keys(errors).length) {
    toast(t('common.fixErrors'), 'error')
    return false
  }
  state.user.business = data.business
  state.user.owner = data.owner
  state.user.email = data.email
  state.user.country = data.country
  toast(t('toast.saved'))
  return true
}

function addCredits(packId) {
  const pack = CREDIT_PACKS.find(p => p.id === packId) || CREDIT_PACKS[0]
  state.wallet.credits += pack.credits
  state.invoices.unshift({
    id: 'i_' + Date.now(),
    date: isoDate(new Date()),
    desc: pack.credits + ' cxj credits',
    amount: pack.price,
    status: 'Paid'
  })
  closeModal()
  toast(t('toast.credits'))
}

function changePlan(planId) {
  const plan = PLANS.find(p => p.id === planId) || PLANS[0]
  state.wallet.plan = plan.name
  state.wallet.invoice = plan.price
  state.user.plan = plan.name
  closeModal()
  toast(t('toast.plan'))
}

function markAllRead() {
  state.updates.forEach(u => { u.read = true })
  toast(t('toast.markedRead'))
}

function pickReply(text) {
  const s = String(text || '').toLowerCase()
  if (/(pay|checkout|shop|store|button)/.test(s)) {
    return 'On it. I will draft the change and a human expert will review it today.'
  }
  if (/(plan|credit|billing|invoice)/.test(s)) {
    return 'You have ' + state.wallet.credits + ' credits on the ' + state.wallet.plan +
      ' plan. Want me to prepare the switch to Pro?'
  }
  if (/(backup|security|update)/.test(s)) {
    return 'Backups run every night and the security scan is clean. I will flag anything that changes.'
  }
  return 'Got it. I have queued that up and will report back in your Updates feed.'
}

function sendMessage(text) {
  const value = String(text || '').trim()
  if (!value) return
  state.messages.push({ id: 'm_' + Date.now(), from: 'me', text: value, time: nowTime() })
  state.ui.typing = true
  setTimeout(() => {
    state.messages.push({ id: 'm_' + (Date.now() + 1), from: 'ai', text: pickReply(value), time: nowTime() })
    state.ui.typing = false
  }, 1100)
}

function toggleTask(id) {
  const task = state.tasks.find(x => x.id === id)
  if (!task) return
  const wasDone = task.status === 'done'
  task.status = wasDone ? 'in_progress' : 'done'
  state.stats.tasks = Math.max(0, state.stats.tasks + (wasDone ? -1 : 1))
  closeModal()
  toast(wasDone ? t('toast.taskReopened') : t('toast.taskDone'))
}

function toggleNotifications() {
  state.user.notifications = !state.user.notifications
  toast(t('toast.saved'))
}

async function logout() {
  closeModal()
  await $storex.users.logout()
}

function setLang(code) {
  state.lang = code
  toast(t('toast.lang'))
}

// Search runs over the REAL projects plus the dashboard copy.
function searchResults(query) {
  const q = String(query || '').trim().toLowerCase()
  if (!q) return []
  const out = []

  ;($storex.projects.allProjects || []).forEach(p => {
    if (String(p.project_name || '').toLowerCase().includes(q)) {
      out.push({ label: p.project_name, meta: 'Project', module: 'projects' })
    }
  })

  state.tasks.forEach(x => {
    if (x.title.toLowerCase().includes(q)) out.push({ label: x.title, meta: 'Task', module: 'summary' })
  })
  state.updates.forEach(u => {
    if ((u.title + ' ' + u.text).toLowerCase().includes(q)) out.push({ label: u.title, meta: 'Update', module: 'updates' })
  })
  state.events.forEach(e => {
    if (e.title.toLowerCase().includes(q)) out.push({ label: e.title, meta: 'Calendar', module: 'summary' })
  })
  return out.slice(0, 6)
}

export function useSolopreneur() {
  return {
    state,
    MODULES,
    PLANS,
    CREDIT_PACKS,
    t,
    money,
    shortDate,
    dateLine,
    nowTime,
    goModule,
    setModule,
    setViewportWidth,
    openModal,
    closeModal,
    createProject,
    saveAccount,
    addCredits,
    changePlan,
    markAllRead,
    sendMessage,
    toggleTask,
    toggleNotifications,
    logout,
    setLang,
    searchResults,
    syncIdentity
  }
}