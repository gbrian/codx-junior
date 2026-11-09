<script setup>
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { API } from '@/api/api'
import { $storex } from '@/store'

import CompanySimpleHome from '@/components/company/CompanySimpleHome.vue'
import CompanyAssistant from '@/components/company/CompanyAssistant.vue'
import CompanyChatPanel from '@/components/company/CompanyChatPanel.vue'
import { COMPANY_TEMPLATES } from '@/components/company/companyMeta'

/**
 * Company shell — ONE simple screen plus the always-present codx-junior
 * assistant.
 *
 * The target user is a manager with no technical skills. They should never
 * need to learn a tab tree: the home screen shows what is happening and four
 * obvious actions, and everything else (teams, people, projects, missions,
 * settings) is done conversationally with the assistant.
 *
 * The old deep links (`?tab=teams`, `?tab=people`, …) still work: they are
 * translated into an assistant prompt instead of another screen.
 */
const route = useRoute()
const router = useRouter()
const api = API.companies

const STORAGE_KEY = 'codx.company.id'

const loading = ref(true)
const busy = ref(false)
const companies = ref([])
const activeId = ref('')
const snapshot = ref(null)
const references = ref({ projects: [], users: [], profiles: [], templates: [] })
const createOpen = ref(false)
const createAdvanced = ref(false)
const chatsOpen = ref(false)

const isMobile = computed(() => $storex.ui.isMobile)

const createForm = reactive({
  name: '',
  description: '',
  mission: '',
  template: 'blank',
  project_ids: []
})

const company = computed(() => snapshot.value?.company || null)
const counts = computed(() => snapshot.value?.counts || {})

// Company role (not global role) decides what the shell exposes.
const myCompanyRole = computed(() => {
  if ($storex.users.isAdmin) return 'admin'
  if (!company.value?.owner) return 'admin'
  if (company.value.owner === $storex.api.user?.username) return 'admin'
  return $storex.users.companyRole(activeId.value) || ''
})
const canAdmin = computed(() => myCompanyRole.value === 'admin')
const canManage = computed(() => ['admin', 'manager'].includes(myCompanyRole.value))

// The assistant is the product. No tabs, no settings screens — just prompts.
const ASSISTANT_INTENTS = {
  settings: 'Open company settings',
  'add-person': 'Add a person',
  people: 'Who is in the company?',
  'create-team': 'I need a team',
  teams: 'Show teams',
  'create-mission': 'Create a mission',
  missions: 'What needs my attention?',
  work: 'What needs my attention?',
  projects: 'Show projects',
  organization: 'Show the organization',
  activity: 'What happened recently?',
  open: ''
}

// ── Notifications ───────────────────────────────────────────────────────────

function notify(text, type = 'info') {
  try {
    $storex.ui.addNotification({ text, type })
  } catch {
    // Notifications are best effort (the view must keep working headless).
  }
}

function errorMessage(error) {
  return (
    error?.response?.data?.detail ||
    error?.response?.data?.message ||
    error?.message ||
    String(error)
  )
}

function notifyError(error) {
  notify(errorMessage(error), 'error')
}

// ── Loading ─────────────────────────────────────────────────────────────────

async function loadCompanies() {
  companies.value = await api.list()
  if (!companies.value.length) {
    activeId.value = ''
    snapshot.value = null
    return
  }
  const routeCompany = String(route.query.company || route.params.companyId || '')
  const stored = localStorage.getItem(STORAGE_KEY) || ''
  const candidate = companies.value.find(item => item.id === routeCompany) ||
    companies.value.find(item => item.id === stored) ||
    companies.value[0]
  await selectCompany(candidate.id, { skipList: true })
}

async function loadReferences() {
  try {
    references.value = await api.references()
  } catch (error) {
    // Reference catalogs are only used by the advanced create form.
    notifyError(error)
  }
}

async function refreshSnapshot() {
  if (!activeId.value) return
  try {
    snapshot.value = await api.snapshot(activeId.value)
  } catch (error) {
    notifyError(error)
  }
}

async function selectCompany(companyId, { skipList = false } = {}) {
  if (!companyId) return
  activeId.value = companyId
  localStorage.setItem(STORAGE_KEY, companyId)
  busy.value = true
  try {
    if (!skipList) companies.value = await api.list()
    snapshot.value = await api.snapshot(companyId)
  } catch (error) {
    notifyError(error)
  } finally {
    busy.value = false
  }
}

async function onCompanyDeleted() {
  snapshot.value = null
  activeId.value = ''
  notify('Company deleted', 'info')
  await loadCompanies()
}

onMounted(async () => {
  loading.value = true
  try {
    await loadReferences()
    await loadCompanies()
  } catch (error) {
    notifyError(error)
  } finally {
    loading.value = false
    const intent = route.query.assistant || legacyTabIntent(route.query.tab)
    if (handleAssistantIntent(intent)) {
      const rest = { ...route.query }
      delete rest.assistant
      delete rest.tab
      router.replace({ query: rest }).catch(() => {})
    }
  }
})

watch(() => route.query.tab, value => {
  const intent = legacyTabIntent(value)
  if (!intent) return
  if (handleAssistantIntent(intent)) {
    const rest = { ...route.query }
    delete rest.tab
    router.replace({ query: rest }).catch(() => {})
  }
})

watch(() => route.query.assistant, value => {
  if (handleAssistantIntent(value)) {
    const rest = { ...route.query }
    delete rest.assistant
    router.replace({ query: rest }).catch(() => {})
  }
})

// Old `/company` links used `?tab=…`. Keep them working by turning them into a
// prompt for the assistant instead of rendering another screen.
function legacyTabIntent(tab) {
  const map = {
    teams: 'teams',
    people: 'people',
    projects: 'projects',
    organization: 'organization',
    activity: 'activity',
    missions: 'missions',
    overview: 'open'
  }
  return map[String(tab || '')] || ''
}

function handleAssistantIntent(intent) {
  const key = String(intent || '').trim()
  if (!key) return false
  const prompt = ASSISTANT_INTENTS[key]
  if (prompt === undefined) return false
  nextTick(() => askAssistant(prompt))
  return true
}

// ── Assistant ───────────────────────────────────────────────────────────────

function askAssistant(prompt = '') {
  window.dispatchEvent(new CustomEvent('company-assistant:open', {
    detail: { prompt }
  }))
}

function openCompanySettings() {
  askAssistant('Open company settings')
}

// ── Company onboarding ──────────────────────────────────────────────────────

function openCreate() {
  Object.assign(createForm, {
    name: '',
    description: '',
    mission: '',
    template: 'blank',
    project_ids: []
  })
  createAdvanced.value = false
  createOpen.value = true
}

function toggleCreateProject(projectId) {
  const index = createForm.project_ids.indexOf(projectId)
  if (index === -1) createForm.project_ids.push(projectId)
  else createForm.project_ids.splice(index, 1)
}

async function submitCreate() {
  if (!createForm.name.trim()) {
    notify('Please give the company a name', 'error')
    return
  }
  busy.value = true
  try {
    const created = await api.create({
      name: createForm.name.trim(),
      description: createForm.description,
      mission: createForm.mission,
      template: createForm.template,
      project_ids: createForm.project_ids
    })
    createOpen.value = false
    companies.value = await api.list()
    await selectCompany(created.id, { skipList: true })
    notify(`Company "${created.name}" created ✓`, 'success')
    nextTick(() => askAssistant('What should we do first?'))
  } catch (error) {
    notifyError(error)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="h-full w-full flex bg-base-100 overflow-hidden">
    <!-- ── The one company screen ────────────────────────────────────────── -->
    <div class="flex-1 min-w-0 flex flex-col overflow-hidden">
      <header class="shrink-0 border-b border-base-content/10 bg-base-100/80 backdrop-blur px-3 md:px-5 py-2.5">
        <div class="flex items-center gap-2 flex-wrap">
          <div class="w-9 h-9 rounded-xl grid place-items-center text-white shrink-0"
               :style="{ backgroundColor: company?.color || '#6366f1' }">
            <span class="text-sm font-black">{{ (company?.name || 'C').slice(0, 1).toUpperCase() }}</span>
          </div>
          <div class="min-w-0">
            <h1 class="text-base md:text-lg font-black leading-tight truncate">
              {{ company?.name || 'Company' }}
            </h1>
            <p class="text-[10px] md:text-xs text-base-content/50 truncate">
              <template v-if="company">
                {{ (snapshot?.members || []).length }} people · {{ counts.teams || 0 }} teams ·
                {{ counts.open_missions || 0 }} open mission(s)
              </template>
              <template v-else>Run a company where humans and AI work together</template>
            </p>
          </div>

          <div class="ml-auto flex items-center gap-1.5 flex-wrap">
            <span class="badge badge-sm badge-primary gap-1" title="Manager workspace">
              <i class="fa-solid fa-building-columns text-[9px]"></i> Company
            </span>
            <select
              v-if="companies.length"
              class="select select-sm select-bordered max-w-48"
              :value="activeId"
              aria-label="Select company"
              @change="selectCompany($event.target.value)"
            >
              <option v-for="item in companies" :key="item.id" :value="item.id">{{ item.name }}</option>
            </select>
            <button class="btn btn-sm btn-ghost btn-square" :disabled="busy" title="Reload"
                    aria-label="Reload company" @click="selectCompany(activeId)">
              <i class="fa-solid fa-rotate" :class="busy ? 'animate-spin' : ''"></i>
            </button>
            <button v-if="company" class="btn btn-sm btn-ghost gap-1"
                    title="Company chats" @click="chatsOpen = true">
              <i class="fa-regular fa-comments"></i>
              <span class="hidden md:inline">Chats</span>
              <span v-if="counts.chats" class="badge badge-xs badge-ghost">{{ counts.chats }}</span>
            </button>
            <button v-if="company && canManage" class="btn btn-sm btn-ghost gap-1"
                    title="Change company details with the assistant" @click="openCompanySettings">
              <i class="fa-solid fa-wand-magic-sparkles"></i>
              <span class="hidden md:inline">Change details</span>
            </button>
            <button class="btn btn-sm btn-primary gap-1" title="Create company" @click="openCreate">
              <i class="fa-solid fa-plus"></i>
              <span class="hidden md:inline">New company</span>
            </button>
          </div>
        </div>
      </header>

      <main class="flex-1 min-h-0 overflow-y-auto p-3 md:p-5">
        <div v-if="loading" class="h-full grid place-items-center">
          <div class="text-center text-base-content/50">
            <span class="loading loading-spinner loading-lg text-primary"></span>
            <p class="text-sm mt-2">Getting your company ready…</p>
          </div>
        </div>

        <div v-else-if="!companies.length" class="h-full grid place-items-center">
          <div class="max-w-lg text-center">
            <div class="w-16 h-16 rounded-3xl grid place-items-center bg-primary/10 text-primary mx-auto mb-4">
              <i class="fa-solid fa-building-columns text-2xl"></i>
            </div>
            <h2 class="text-xl font-black">Let's set up your company</h2>
            <p class="text-sm text-base-content/60 mt-2">
              Give it a name. codx-junior will help you add people, create teams and start work —
              no technical knowledge needed.
            </p>
            <button class="btn btn-primary mt-4" @click="openCreate">
              <i class="fa-solid fa-plus"></i> Create my company
            </button>
          </div>
        </div>

        <CompanySimpleHome
          v-else-if="company"
          :snapshot="snapshot"
          :busy="busy"
          :can-manage="canManage"
          :can-admin="canAdmin"
          @assistant="askAssistant"
        />
      </main>
    </div>

    <!-- ── Always-present assistant ───────────────────────────────────────── -->
    <CompanyAssistant
      v-if="company"
      :company-id="activeId"
      :company-name="company.name"
      :view="'home'"
      :can-manage="canManage"
      :can-admin="canAdmin"
      :docked="!isMobile"
      @refresh="refreshSnapshot"
      @deleted="onCompanyDeleted"
    />

    <!-- ── Create company (only the minimum first; advanced details optional) ── -->
    <div v-if="createOpen" class="modal modal-open" role="dialog" aria-modal="true">
      <div class="modal-box max-w-lg">
        <div class="flex items-center justify-between mb-3">
          <div>
            <h3 class="font-bold text-lg">Create your company</h3>
            <p class="text-xs text-base-content/50">You can change everything later just by asking.</p>
          </div>
          <button class="btn btn-ghost btn-sm btn-square" aria-label="Close" @click="createOpen = false">
            <i class="fa-solid fa-xmark"></i>
          </button>
        </div>

        <label class="form-control">
          <span class="label-text text-xs font-semibold">Company name</span>
          <input v-model="createForm.name" class="input input-bordered" placeholder="For example: Acme" autofocus
                 @keyup.enter="submitCreate" />
        </label>

        <label class="form-control mt-3">
          <span class="label-text text-xs font-semibold">What does it do? <span class="font-normal text-base-content/40">(optional)</span></span>
          <textarea v-model="createForm.description" class="textarea textarea-bordered" rows="2"
                    placeholder="For example: We design and sell furniture online"></textarea>
        </label>

        <details class="mt-3" :open="createAdvanced" @toggle="createAdvanced = $event.target.open">
          <summary class="cursor-pointer text-xs font-semibold text-primary">More options (optional)</summary>
          <div class="mt-3 flex flex-col gap-3">
            <label class="form-control">
              <span class="label-text text-xs">Mission — why does it exist?</span>
              <textarea v-model="createForm.mission" class="textarea textarea-sm textarea-bordered" rows="2"></textarea>
            </label>
            <div>
              <div class="text-xs font-semibold mb-1">Start with a template</div>
              <div class="flex flex-col gap-1.5">
                <label v-for="template in COMPANY_TEMPLATES" :key="template.id"
                       class="flex items-start gap-2 rounded-lg border border-base-content/10 p-2 cursor-pointer"
                       :class="createForm.template === template.id ? 'border-primary bg-primary/5' : ''">
                  <input v-model="createForm.template" type="radio" class="radio radio-xs radio-primary mt-0.5" :value="template.id" />
                  <span>
                    <span class="block text-xs font-semibold">{{ template.label }}</span>
                    <span class="block text-[10px] text-base-content/50">{{ template.hint }}</span>
                  </span>
                </label>
              </div>
            </div>
            <div>
              <div class="text-xs font-semibold mb-1">Link projects</div>
              <div class="flex flex-wrap gap-2">
                <label v-for="project in (references.projects || [])" :key="project.project_id"
                       class="flex items-center gap-1.5 rounded-lg border border-base-content/10 px-2 py-1 text-xs cursor-pointer">
                  <input type="checkbox" class="checkbox checkbox-xs checkbox-primary"
                         :checked="createForm.project_ids.includes(project.project_id)"
                         @change="toggleCreateProject(project.project_id)" />
                  <span class="truncate max-w-40">{{ project.project_name }}</span>
                </label>
                <span v-if="!(references.projects || []).length" class="text-xs text-base-content/40">
                  No projects found — you can add them later.
                </span>
              </div>
            </div>
          </div>
        </details>

        <div class="modal-action">
          <button class="btn btn-ghost" @click="createOpen = false">Cancel</button>
          <button class="btn btn-primary" :disabled="busy || !createForm.name.trim()" @click="submitCreate">
            <i class="fa-solid fa-plus"></i> Create company
          </button>
        </div>
      </div>
      <div class="modal-backdrop" @click="createOpen = false"></div>
    </div>

    <CompanyChatPanel
      v-if="chatsOpen && company"
      :company-id="activeId"
      :snapshot="snapshot"
      :can-manage="canManage"
      @close="chatsOpen = false"
      @changed="selectCompany(activeId)"
    />
  </div>
</template>

<!-- Made with ❤️ by codx-junior -->
