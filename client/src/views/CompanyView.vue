<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { API } from '@/api/api'
import { $storex } from '@/store'

import CompanyOverviewPanel from '@/components/company/CompanyOverviewPanel.vue'
import CompanyOrganizationPanel from '@/components/company/CompanyOrganizationPanel.vue'
import CompanyTeamsPanel from '@/components/company/CompanyTeamsPanel.vue'
import CompanyProjectsPanel from '@/components/company/CompanyProjectsPanel.vue'
import CompanyMissionsPanel from '@/components/company/CompanyMissionsPanel.vue'
import CompanyActivityPanel from '@/components/company/CompanyActivityPanel.vue'
import { COMPANY_TEMPLATES } from '@/components/company/companyMeta'

const route = useRoute()
const router = useRouter()
const api = API.companies

const TABS = [
  { id: 'overview', label: 'Overview', icon: 'fa-solid fa-heart-pulse' },
  { id: 'organization', label: 'Organization', icon: 'fa-solid fa-sitemap' },
  { id: 'teams', label: 'Teams', icon: 'fa-solid fa-people-group' },
  { id: 'projects', label: 'Projects', icon: 'fa-solid fa-cubes' },
  { id: 'missions', label: 'Missions', icon: 'fa-solid fa-flag' },
  { id: 'activity', label: 'Activity', icon: 'fa-solid fa-clock-rotate-left' }
]

const STORAGE_KEY = 'codx.company.id'

const loading = ref(true)
const busy = ref(false)
const companies = ref([])
const activeId = ref('')
const snapshot = ref(null)
const references = ref({ projects: [], users: [], profiles: [], templates: [] })
const tab = ref('overview')
const focusMissionId = ref('')
const createOpen = ref(false)
const editOpen = ref(false)
const deleteConfirm = ref(false)

const createForm = reactive({
  name: '',
  description: '',
  mission: '',
  vision: '',
  template: 'blank',
  project_ids: []
})

const editForm = reactive({
  name: '',
  description: '',
  mission: '',
  vision: '',
  values: '',
  website: '',
  status: 'active',
  owner: ''
})

const company = computed(() => snapshot.value?.company || null)
const counts = computed(() => snapshot.value?.counts || {})
const tabs = computed(() =>
  TABS.map(item => ({
    ...item,
    badge:
      item.id === 'missions' ? counts.value.open_missions || 0 :
      item.id === 'teams' ? counts.value.teams || 0 :
      item.id === 'projects' ? counts.value.projects || 0 :
      item.id === 'organization' ? counts.value.org_units || 0 : 0
  }))
)

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
    // References are pickers only; the dashboard still works without them.
    notifyError(error)
  }
}

async function refreshSnapshot() {
  if (!activeId.value) return
  snapshot.value = await api.snapshot(activeId.value)
  fillEditForm()
}

async function selectCompany(companyId, { skipList = false } = {}) {
  if (!companyId) return
  activeId.value = companyId
  localStorage.setItem(STORAGE_KEY, companyId)
  busy.value = true
  try {
    if (!skipList) companies.value = await api.list()
    snapshot.value = await api.snapshot(companyId)
    fillEditForm()
  } catch (error) {
    notifyError(error)
  } finally {
    busy.value = false
  }
}

function fillEditForm() {
  const current = company.value
  if (!current) return
  Object.assign(editForm, {
    name: current.name || '',
    description: current.description || '',
    mission: current.mission || '',
    vision: current.vision || '',
    values: (current.values || []).join(', '),
    website: current.website || '',
    status: current.status || 'active',
    owner: current.owner || ''
  })
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
  }
})

// ── Generic action runner ───────────────────────────────────────────────────

async function perform(label, operation, { refresh = true, notifySuccess = true } = {}) {
  if (busy.value) return null
  busy.value = true
  try {
    const result = await operation()
    if (refresh) await refreshSnapshot()
    if (notifySuccess && label) notify(`${label} ✓`, 'success')
    return result
  } catch (error) {
    notifyError(error)
    return null
  } finally {
    busy.value = false
  }
}

// ── Company dialogs ─────────────────────────────────────────────────────────

function openCreate() {
  Object.assign(createForm, {
    name: '',
    description: '',
    mission: '',
    vision: '',
    template: 'blank',
    project_ids: []
  })
  createOpen.value = true
}

function toggleCreateProject(projectId) {
  const index = createForm.project_ids.indexOf(projectId)
  if (index === -1) createForm.project_ids.push(projectId)
  else createForm.project_ids.splice(index, 1)
}

async function submitCreate() {
  if (!createForm.name.trim()) {
    notify('Company name is required', 'error')
    return
  }
  busy.value = true
  try {
    const created = await api.create({
      name: createForm.name.trim(),
      description: createForm.description,
      mission: createForm.mission,
      vision: createForm.vision,
      template: createForm.template,
      project_ids: createForm.project_ids
    })
    createOpen.value = false
    companies.value = await api.list()
    await selectCompany(created.id, { skipList: true })
    tab.value = 'overview'
    notify(`Company "${created.name}" created ✓`, 'success')
  } catch (error) {
    notifyError(error)
  } finally {
    busy.value = false
  }
}

function openEdit() {
  fillEditForm()
  deleteConfirm.value = false
  editOpen.value = true
}

async function submitEdit() {
  if (!editForm.name.trim()) {
    notify('Company name is required', 'error')
    return
  }
  await perform('Company saved', () =>
    api.update(activeId.value, {
      name: editForm.name.trim(),
      description: editForm.description,
      mission: editForm.mission,
      vision: editForm.vision,
      values: editForm.values.split(',').map(value => value.trim()).filter(Boolean),
      website: editForm.website,
      status: editForm.status,
      owner: editForm.owner
    })
  )
  companies.value = await api.list()
  editOpen.value = false
}

async function removeCompany() {
  if (!deleteConfirm.value) {
    deleteConfirm.value = true
    return
  }
  busy.value = true
  try {
    await api.remove(activeId.value)
    editOpen.value = false
    deleteConfirm.value = false
    await loadCompanies()
    notify('Company deleted', 'info')
  } catch (error) {
    notifyError(error)
  } finally {
    busy.value = false
  }
}

// ── Organization ────────────────────────────────────────────────────────────

function saveOrgUnit({ id, payload }) {
  return perform(id ? 'Org unit saved' : 'Org unit created', () =>
    id
      ? api.updateOrgUnit(activeId.value, id, payload)
      : api.addOrgUnit(activeId.value, payload)
  )
}

function deleteOrgUnit(unitId) {
  return perform('Org unit deleted', () => api.deleteOrgUnit(activeId.value, unitId))
}

// ── Teams ───────────────────────────────────────────────────────────────────

function saveTeam({ id, payload }) {
  return perform(id ? 'Team saved' : 'Team created', () =>
    id
      ? api.updateTeam(activeId.value, id, payload)
      : api.addTeam(activeId.value, payload)
  )
}

async function deleteTeam(teamId) {
  const result = await perform('Team deleted', () => api.deleteTeam(activeId.value, teamId))
  if (!result) return
  return result
}

function removeTeamMember({ teamId, member }) {
  return perform('Member removed', () =>
    api.removeTeamMembers(activeId.value, teamId, [member])
  )
}

// ── Projects ────────────────────────────────────────────────────────────────

function saveProject({ project_id, payload }) {
  return perform('Project linked', () => api.linkProject(activeId.value, payload))
}

async function unlinkProject(projectId) {
  busy.value = true
  try {
    try {
      await api.unlinkProject(activeId.value, projectId)
    } catch (error) {
      if (error?.response?.status === 409) {
        const force = window.confirm(
          `${errorMessage(error)}\n\nForce the unlink and detach the open missions?`
        )
        if (!force) return
        await api.unlinkProject(activeId.value, projectId, { force: true })
      } else {
        throw error
      }
    }
    await refreshSnapshot()
    notify('Project unlinked ✓', 'success')
  } catch (error) {
    notifyError(error)
  } finally {
    busy.value = false
  }
}

function openProject(projectName) {
  if (!projectName) return
  router.push({ name: 'home', params: { projectName } })
}

// ── Missions ────────────────────────────────────────────────────────────────

function saveMission({ id, payload }) {
  return perform(id ? 'Mission saved' : 'Mission created', () =>
    id
      ? api.updateMission(activeId.value, id, payload)
      : api.addMission(activeId.value, payload)
  )
}

function deleteMission(missionId) {
  return perform('Mission deleted', () => api.deleteMission(activeId.value, missionId))
}

function dispatchMission(missionId) {
  return perform('Mission dispatched', () => api.dispatchMission(activeId.value, missionId))
}

function acceptMission({ id, result }) {
  return perform('Mission accepted', () => api.acceptMission(activeId.value, id, result))
}

function rejectMission({ id, reason }) {
  return perform('Mission returned to ready', () => api.rejectMission(activeId.value, id, reason))
}

function transitionMission({ id, status }) {
  return perform(`Mission moved to ${status}`, () =>
    api.transitionMission(activeId.value, id, status)
  )
}

function syncMissions() {
  return perform('Runs synced', () => api.syncMissions(activeId.value))
}

// ── Autonomy ────────────────────────────────────────────────────────────────

function updateAutonomy(patch) {
  return perform('', () => api.updateAutonomy(activeId.value, patch), {
    notifySuccess: false
  })
}

async function runCycle() {
  busy.value = true
  try {
    const result = await api.runCycle(activeId.value, { force: true })
    await refreshSnapshot()
    if (result?.status === 'ran') {
      const dispatched = result.dispatched?.length || 0
      const failed = result.failed?.length || 0
      notify(`Cycle ran · ${dispatched} dispatched · ${failed} failed`, failed ? 'warning' : 'success')
    } else {
      notify(result?.message || `Cycle: ${result?.status || 'done'}`, 'info')
    }
  } catch (error) {
    notifyError(error)
  } finally {
    busy.value = false
  }
}

// ── Navigation helpers ──────────────────────────────────────────────────────

function selectTab(next) {
  tab.value = next
}

function openMission(mission) {
  if (!mission) return
  focusMissionId.value = mission.id
  tab.value = 'missions'
}
</script>

<template>
  <div class="h-full w-full flex flex-col bg-base-100 overflow-hidden">
    <!-- Header -->
    <header class="shrink-0 border-b border-base-content/10 bg-base-100/80 backdrop-blur px-3 md:px-5 py-2.5">
      <div class="flex items-center gap-2 flex-wrap">
        <div class="w-9 h-9 rounded-xl grid place-items-center text-white shrink-0"
             :style="{ backgroundColor: company?.color || '#6366f1' }">
          <span class="text-sm font-black">{{ (company?.name || 'C').slice(0, 1).toUpperCase() }}</span>
        </div>
        <div class="min-w-0">
          <h1 class="text-base md:text-lg font-black leading-tight truncate">
            {{ company?.name || 'Companies' }}
          </h1>
          <p class="text-[10px] md:text-xs text-base-content/50 truncate">
            <template v-if="company">
              {{ counts.humans || 0 }} human · {{ counts.ai || 0 }} AI · {{ counts.teams || 0 }} teams ·
              {{ counts.projects || 0 }} projects
              <span v-if="snapshot?.autonomy?.enabled" class="text-success">· autopilot on</span>
            </template>
            <template v-else>Run a company where humans and AI work together</template>
          </p>
        </div>

        <div class="ml-auto flex items-center gap-1.5 flex-wrap">
          <select
            v-if="companies.length"
            class="select select-sm select-bordered max-w-48"
            :value="activeId"
            aria-label="Select company"
            @change="selectCompany($event.target.value)"
          >
            <option v-for="item in companies" :key="item.id" :value="item.id">{{ item.name }}</option>
          </select>
          <button class="btn btn-sm btn-ghost gap-1" :disabled="busy" title="Reload" @click="selectCompany(activeId)">
            <i class="fa-solid fa-rotate" :class="busy ? 'animate-spin' : ''"></i>
          </button>
          <button v-if="company" class="btn btn-sm btn-ghost gap-1" title="Edit company" @click="openEdit">
            <i class="fa-solid fa-pen"></i>
            <span class="hidden md:inline">Edit</span>
          </button>
          <button class="btn btn-sm btn-primary gap-1" title="Create company" @click="openCreate">
            <i class="fa-solid fa-plus"></i>
            <span class="hidden md:inline">New company</span>
          </button>
        </div>
      </div>
    </header>

    <!-- Tabs -->
    <nav v-if="company" class="shrink-0 px-2 md:px-4 pt-2 overflow-x-auto">
      <div role="tablist" class="tabs tabs-boxed w-max bg-base-200/60 p-1">
        <button
          v-for="item in tabs"
          :key="item.id"
          role="tab"
          class="tab gap-1.5"
          :class="tab === item.id ? 'tab-active' : ''"
          @click="selectTab(item.id)"
        >
          <i :class="item.icon" class="text-[11px]"></i>
          {{ item.label }}
          <span v-if="item.badge" class="badge badge-xs badge-ghost">{{ item.badge }}</span>
        </button>
      </div>
    </nav>

    <!-- Content -->
    <main class="flex-1 min-h-0 overflow-y-auto p-3 md:p-5">
      <div v-if="loading" class="h-full grid place-items-center">
        <div class="text-center text-base-content/50">
          <span class="loading loading-spinner loading-lg text-primary"></span>
          <p class="text-sm mt-2">Loading the company...</p>
        </div>
      </div>

      <div v-else-if="!companies.length" class="h-full grid place-items-center">
        <div class="max-w-lg text-center">
          <div class="w-16 h-16 rounded-3xl grid place-items-center bg-primary/10 text-primary mx-auto mb-4">
            <i class="fa-solid fa-building-columns text-2xl"></i>
          </div>
          <h2 class="text-xl font-black">Run your company on codx-junior</h2>
          <p class="text-sm text-base-content/60 mt-2">
            A company is the top-level entity above projects. Define its organization, build hybrid
            teams of humans and AI profiles, link the projects they work on and assign missions.
          </p>
          <p class="text-xs text-base-content/40 mt-2">
            Start with the SaaS template to get the codx-junior cloud structure in one click.
          </p>
          <button class="btn btn-primary mt-4" @click="openCreate">
            <i class="fa-solid fa-plus"></i> Create a company
          </button>
        </div>
      </div>

      <div v-else-if="company" class="max-w-[1600px] mx-auto">
        <CompanyOverviewPanel
          v-if="tab === 'overview'"
          :snapshot="snapshot"
          :busy="busy"
          @run-cycle="runCycle"
          @update-autonomy="updateAutonomy"
          @select-tab="selectTab"
          @open-mission="openMission"
        />
        <CompanyOrganizationPanel
          v-else-if="tab === 'organization'"
          :snapshot="snapshot"
          :references="references"
          :busy="busy"
          @save="saveOrgUnit"
          @delete="deleteOrgUnit"
        />
        <CompanyTeamsPanel
          v-else-if="tab === 'teams'"
          :snapshot="snapshot"
          :references="references"
          :busy="busy"
          @save="saveTeam"
          @delete="deleteTeam"
        />
        <CompanyProjectsPanel
          v-else-if="tab === 'projects'"
          :snapshot="snapshot"
          :references="references"
          :busy="busy"
          @save="saveProject"
          @delete="unlinkProject"
          @open-project="openProject"
        />
        <CompanyMissionsPanel
          v-else-if="tab === 'missions'"
          :snapshot="snapshot"
          :references="references"
          :busy="busy"
          :focus-mission-id="focusMissionId"
          @save="saveMission"
          @delete="deleteMission"
          @dispatch="dispatchMission"
          @accept="acceptMission"
          @reject="rejectMission"
          @transition="transitionMission"
          @sync="syncMissions"
          @open-project="openProject"
        />
        <CompanyActivityPanel
          v-else-if="tab === 'activity'"
          :snapshot="snapshot"
          :busy="busy"
          @refresh="selectCompany(activeId)"
        />
      </div>
    </main>

    <!-- Create company -->
    <div v-if="createOpen" class="modal modal-open" role="dialog" aria-modal="true">
      <div class="modal-box max-w-2xl max-h-[90vh] overflow-y-auto">
        <div class="flex items-center justify-between mb-3">
          <div>
            <h3 class="font-bold text-lg">New company</h3>
            <p class="text-xs text-base-content/50">The top-level container for teams, projects and missions.</p>
          </div>
          <button class="btn btn-ghost btn-sm btn-square" aria-label="Close" @click="createOpen = false">
            <i class="fa-solid fa-xmark"></i>
          </button>
        </div>

        <div class="grid gap-3 md:grid-cols-2">
          <label class="form-control md:col-span-2">
            <span class="label-text text-xs">Name</span>
            <input v-model="createForm.name" class="input input-sm input-bordered" placeholder="codx-junior cloud" @keyup.enter="submitCreate" />
          </label>
          <label class="form-control md:col-span-2">
            <span class="label-text text-xs">Description</span>
            <input v-model="createForm.description" class="input input-sm input-bordered" placeholder="A SaaS platform that offers codx-junior as a service" />
          </label>
          <label class="form-control md:col-span-2">
            <span class="label-text text-xs">Mission</span>
            <textarea v-model="createForm.mission" class="textarea textarea-sm textarea-bordered" rows="2"
                      placeholder="Why does this company exist?"></textarea>
          </label>
          <label class="form-control md:col-span-2">
            <span class="label-text text-xs">Vision</span>
            <textarea v-model="createForm.vision" class="textarea textarea-sm textarea-bordered" rows="2"
                      placeholder="Where is it going?"></textarea>
          </label>
        </div>

        <div class="mt-4">
          <div class="text-xs font-bold uppercase tracking-wide text-base-content/50 mb-1">Starter template</div>
          <div class="grid gap-2 md:grid-cols-2">
            <label
              v-for="template in COMPANY_TEMPLATES"
              :key="template.id"
              class="rounded-xl border p-2.5 cursor-pointer transition-colors"
              :class="createForm.template === template.id ? 'border-primary bg-primary/5' : 'border-base-content/10 hover:border-primary/30'"
            >
              <input v-model="createForm.template" type="radio" class="radio radio-xs radio-primary" :value="template.id" />
              <span class="ml-1.5 text-sm font-semibold">{{ template.label }}</span>
              <p class="text-[10px] text-base-content/50 mt-1">{{ template.hint }}</p>
            </label>
          </div>
        </div>

        <div class="mt-4">
          <div class="text-xs font-bold uppercase tracking-wide text-base-content/50 mb-1">Projects to link</div>
          <div class="flex flex-wrap gap-2">
            <label
              v-for="project in (references.projects || [])"
              :key="project.project_id"
              class="flex items-center gap-1.5 rounded-lg border border-base-content/10 px-2 py-1 text-xs cursor-pointer hover:border-primary/40"
            >
              <input
                type="checkbox"
                class="checkbox checkbox-xs checkbox-primary"
                :checked="createForm.project_ids.includes(project.project_id)"
                @change="toggleCreateProject(project.project_id)"
              />
              <span class="truncate max-w-44">{{ project.project_name }}</span>
            </label>
            <span v-if="!(references.projects || []).length" class="text-xs text-base-content/40">
              No discovered projects. You can link them later.
            </span>
          </div>
        </div>

        <div class="modal-action">
          <button class="btn btn-sm btn-ghost" @click="createOpen = false">Cancel</button>
          <button class="btn btn-sm btn-primary" :disabled="busy" @click="submitCreate">
            <i class="fa-solid fa-plus"></i> Create company
          </button>
        </div>
      </div>
      <div class="modal-backdrop" @click="createOpen = false"></div>
    </div>

    <!-- Edit company -->
    <div v-if="editOpen" class="modal modal-open" role="dialog" aria-modal="true">
      <div class="modal-box max-w-xl max-h-[90vh] overflow-y-auto">
        <div class="flex items-center justify-between mb-3">
          <h3 class="font-bold text-lg">Edit company</h3>
          <button class="btn btn-ghost btn-sm btn-square" aria-label="Close" @click="editOpen = false">
            <i class="fa-solid fa-xmark"></i>
          </button>
        </div>

        <div class="grid gap-3 md:grid-cols-2">
          <label class="form-control md:col-span-2">
            <span class="label-text text-xs">Name</span>
            <input v-model="editForm.name" class="input input-sm input-bordered" />
          </label>
          <label class="form-control md:col-span-2">
            <span class="label-text text-xs">Description</span>
            <input v-model="editForm.description" class="input input-sm input-bordered" />
          </label>
          <label class="form-control md:col-span-2">
            <span class="label-text text-xs">Mission</span>
            <textarea v-model="editForm.mission" class="textarea textarea-sm textarea-bordered" rows="2"></textarea>
          </label>
          <label class="form-control md:col-span-2">
            <span class="label-text text-xs">Vision</span>
            <textarea v-model="editForm.vision" class="textarea textarea-sm textarea-bordered" rows="2"></textarea>
          </label>
          <label class="form-control md:col-span-2">
            <span class="label-text text-xs">Values (comma separated)</span>
            <input v-model="editForm.values" class="input input-sm input-bordered" />
          </label>
          <label class="form-control">
            <span class="label-text text-xs">Website</span>
            <input v-model="editForm.website" class="input input-sm input-bordered" />
          </label>
          <label class="form-control">
            <span class="label-text text-xs">Status</span>
            <select v-model="editForm.status" class="select select-sm select-bordered">
              <option value="active">Active</option>
              <option value="paused">Paused</option>
              <option value="archived">Archived</option>
            </select>
          </label>
          <label class="form-control">
            <span class="label-text text-xs">Owner</span>
            <input v-model="editForm.owner" class="input input-sm input-bordered" />
          </label>
        </div>

        <div class="mt-4 rounded-xl border border-error/20 bg-error/5 p-3">
          <div class="text-xs font-bold text-error">Danger zone</div>
          <p class="text-[10px] text-base-content/50 mt-1">
            Deleting the company removes its org chart, teams, missions and journal. The linked codx-junior projects are untouched.
          </p>
          <button class="btn btn-xs btn-error mt-2" :disabled="busy" @click="removeCompany">
            {{ deleteConfirm ? 'Confirm delete company' : 'Delete company' }}
          </button>
        </div>

        <div class="modal-action">
          <button class="btn btn-sm btn-ghost" @click="editOpen = false">Cancel</button>
          <button class="btn btn-sm btn-primary" :disabled="busy" @click="submitEdit">Save</button>
        </div>
      </div>
      <div class="modal-backdrop" @click="editOpen = false"></div>
    </div>
  </div>
</template>

<!-- Made with ❤️ by codx-junior -->
