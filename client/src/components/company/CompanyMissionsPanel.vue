<script setup>
import { computed, reactive, ref, watch } from 'vue'
import {
  MISSION_COLUMNS,
  MISSION_OTHER_STATUSES,
  formatDate,
  priorityMeta,
  statusMeta
} from './companyMeta'

const props = defineProps({
  snapshot: { type: Object, default: null },
  references: { type: Object, default: () => ({ projects: [] }) },
  busy: { type: Boolean, default: false },
  focusMissionId: { type: String, default: '' }
})

const emit = defineEmits([
  'save',
  'delete',
  'dispatch',
  'accept',
  'reject',
  'transition',
  'sync',
  'open-project'
])

const dialog = ref(false)
const detail = ref(null)
const formError = ref('')
const draggingId = ref('')

const company = computed(() => props.snapshot?.company || {})
const missions = computed(() => props.snapshot?.missions || [])
const teams = computed(() => props.snapshot?.teams || [])
const projects = computed(() => props.snapshot?.projects || [])

const form = reactive(emptyForm())

function emptyForm() {
  return {
    id: '',
    title: '',
    objective: '',
    acceptance: '',
    team_id: '',
    project_id: '',
    priority: 'medium',
    dispatch_mode: 'manual',
    budget_cxjcoins: 0,
    due_date: '',
    tags: ''
  }
}

const columns = computed(() =>
  MISSION_COLUMNS.map(column => ({
    ...column,
    missions: missions.value.filter(mission => mission.status === column.id)
  }))
)

const otherMissions = computed(() =>
  missions.value.filter(mission => MISSION_OTHER_STATUSES.includes(mission.status))
)

function openCreate() {
  Object.assign(form, emptyForm())
  form.team_id = teams.value[0]?.id || ''
  form.project_id = projects.value[0]?.project_id || ''
  formError.value = ''
  dialog.value = true
}

function openEdit(mission) {
  Object.assign(form, {
    id: mission.id,
    title: mission.title || '',
    objective: mission.objective || '',
    acceptance: mission.acceptance || '',
    team_id: mission.team_id || '',
    project_id: mission.project_id || '',
    priority: mission.priority || 'medium',
    dispatch_mode: mission.dispatch_mode || 'manual',
    budget_cxjcoins: mission.budget_cxjcoins || 0,
    due_date: mission.due_date || '',
    tags: (mission.tags || []).join(', ')
  })
  formError.value = ''
  dialog.value = true
}

function close() {
  dialog.value = false
  formError.value = ''
}

function submit() {
  if (!form.title.trim()) {
    formError.value = 'Title is required'
    return
  }
  emit('save', {
    id: form.id,
    payload: {
      title: form.title.trim(),
      objective: form.objective || form.title,
      acceptance: form.acceptance,
      team_id: form.team_id,
      project_id: form.project_id,
      priority: form.priority,
      dispatch_mode: form.dispatch_mode,
      budget_cxjcoins: Number(form.budget_cxjcoins) || 0,
      due_date: form.due_date,
      tags: form.tags.split(',').map(tag => tag.trim()).filter(Boolean)
    }
  })
  close()
}

function remove(mission) {
  if (!window.confirm(`Delete mission "${mission.title}"?`)) return
  emit('delete', mission.id)
}

function dispatch(mission) {
  emit('dispatch', mission.id)
}

function accept(mission) {
  const result = window.prompt('Outcome summary (optional):', mission.result || '') ?? ''
  emit('accept', { id: mission.id, result })
}

function reject(mission) {
  const reason = window.prompt('Why is this not acceptable?', mission.last_error || '') ?? ''
  emit('reject', { id: mission.id, reason })
}

function move(mission, status) {
  if (!mission || mission.status === status) return
  emit('transition', { id: mission.id, status })
}

function onDragStart(mission) {
  draggingId.value = mission.id
}

function onDrop(status) {
  const mission = missions.value.find(item => item.id === draggingId.value)
  draggingId.value = ''
  if (mission) move(mission, status)
}

function teamName(teamId) {
  return teams.value.find(team => team.id === teamId)?.name || ''
}

function projectName(projectId) {
  return projects.value.find(project => project.project_id === projectId)?.name || projectId
}

function projectRouteName(projectId) {
  const project = projects.value.find(item => item.project_id === projectId)
  return project?.discovered_name || project?.name || projectId
}

function canDispatch(mission) {
  return ['ready', 'blocked'].includes(mission.status)
}

// The overview can open a mission directly: focus it as soon as the board has
// the data (the panel may mount before the snapshot arrives).
watch(
  () => [props.focusMissionId, missions.value.length],
  () => {
    if (!props.focusMissionId) return
    const mission = missions.value.find(item => item.id === props.focusMissionId)
    if (mission) detail.value = mission
  },
  { immediate: true }
)
</script>

<template>
  <div class="flex flex-col gap-4">
    <header class="flex items-center justify-between gap-2">
      <div>
        <h2 class="text-lg font-black flex items-center gap-2">
          <i class="fa-solid fa-flag text-primary"></i> Missions
        </h2>
        <p class="text-xs text-base-content/50">
          Company objectives. Drag a card between columns or use the actions; dispatch starts a real orchestration run in its project.
        </p>
      </div>
      <div class="flex items-center gap-2">
        <button class="btn btn-sm btn-ghost" :disabled="busy" @click="emit('sync')">
          <i class="fa-solid fa-rotate"></i> Sync runs
        </button>
        <button class="btn btn-sm btn-primary" :disabled="busy" @click="openCreate">
          <i class="fa-solid fa-plus"></i> New mission
        </button>
      </div>
    </header>

    <!-- Board -->
    <div class="flex gap-3 overflow-x-auto pb-2">
      <section
        v-for="column in columns"
        :key="column.id"
        class="w-64 shrink-0 rounded-2xl border border-base-content/10 bg-base-200/30 flex flex-col"
        @dragover.prevent
        @drop="onDrop(column.id)"
      >
        <header class="flex items-center justify-between px-3 py-2 border-b border-base-content/10">
          <div class="flex items-center gap-1.5">
            <span class="badge badge-sm" :class="statusMeta(column.id).badge">{{ column.label }}</span>
            <span class="text-[10px] text-base-content/40">{{ column.missions.length }}</span>
          </div>
          <span class="text-[10px] text-base-content/30">{{ column.hint }}</span>
        </header>
        <div class="p-2 flex flex-col gap-2 min-h-32">
          <article
            v-for="mission in column.missions"
            :key="mission.id"
            draggable="true"
            class="rounded-xl border border-base-content/10 bg-base-100 p-2.5 cursor-grab active:cursor-grabbing hover:border-primary/40 transition-colors"
            @dragstart="onDragStart(mission)"
            @dragend="draggingId = ''"
            @click="detail = mission"
          >
            <div class="flex items-start gap-1.5">
              <span class="badge badge-xs" :class="priorityMeta(mission.priority).badge">{{ mission.priority }}</span>
              <span v-if="mission.dispatch_mode === 'auto'" class="badge badge-xs badge-outline" title="Autopilot may dispatch">auto</span>
              <span class="ml-auto text-[9px] text-base-content/30 font-mono">{{ mission.id.slice(-6) }}</span>
            </div>
            <h3 class="text-sm font-semibold leading-snug mt-1 line-clamp-2">{{ mission.title }}</h3>
            <div class="flex flex-wrap items-center gap-1 mt-1.5 text-[9px] text-base-content/50">
              <span v-if="mission.team_id" class="truncate max-w-24"><i class="fa-solid fa-people-group mr-0.5"></i>{{ teamName(mission.team_id) }}</span>
              <span v-if="mission.project_id" class="truncate max-w-24"><i class="fa-solid fa-cube mr-0.5"></i>{{ projectName(mission.project_id) }}</span>
            </div>
            <div v-if="mission.status === 'running'" class="mt-2">
              <div class="flex justify-between text-[9px] text-base-content/40 mb-0.5">
                <span>{{ mission.run_status || 'running' }}</span>
                <span>{{ mission.progress || 0 }}%</span>
              </div>
              <progress class="progress progress-primary w-full h-1" :value="mission.progress || 0" max="100"></progress>
            </div>
            <p v-if="mission.last_error" class="text-[9px] text-error/70 line-clamp-2 mt-1">{{ mission.last_error }}</p>
            <div class="flex items-center gap-1 mt-2" @click.stop>
              <button
                v-if="mission.status === 'draft'"
                class="btn btn-xs btn-info flex-1"
                :disabled="busy"
                @click="move(mission, 'ready')"
              >
                <i class="fa-solid fa-circle-play"></i> Mark ready
              </button>
              <button
                v-if="canDispatch(mission)"
                class="btn btn-xs btn-primary flex-1"
                :disabled="busy"
                @click="dispatch(mission)"
              >
                <i class="fa-solid fa-rocket"></i> Dispatch
              </button>
              <template v-else-if="mission.status === 'review'">
                <button class="btn btn-xs btn-success flex-1" :disabled="busy" @click="accept(mission)">
                  <i class="fa-solid fa-check"></i> Accept
                </button>
                <button class="btn btn-xs btn-ghost" :disabled="busy" @click="reject(mission)" title="Reject">
                  <i class="fa-solid fa-rotate-left"></i>
                </button>
              </template>
              <button class="btn btn-xs btn-ghost btn-square ml-auto" title="Edit" @click="openEdit(mission)">
                <i class="fa-solid fa-pen"></i>
              </button>
              <button class="btn btn-xs btn-ghost btn-square text-error" title="Delete" @click="remove(mission)">
                <i class="fa-solid fa-trash"></i>
              </button>
            </div>
          </article>
          <button
            v-if="!column.missions.length"
            class="rounded-lg border border-dashed border-base-content/15 py-4 text-[10px] text-base-content/30 hover:border-primary/30"
            @click="openCreate"
          >
            + add mission
          </button>
        </div>
      </section>
    </div>

    <!-- Other statuses (paused / blocked / cancelled) -->
    <section v-if="otherMissions.length" class="rounded-2xl border border-base-content/10 bg-base-100 p-3">
      <h3 class="text-xs font-bold uppercase tracking-wide text-base-content/50 mb-2">Needs attention</h3>
      <div class="grid gap-2 md:grid-cols-2 xl:grid-cols-3">
        <article
          v-for="mission in otherMissions"
          :key="mission.id"
          class="rounded-xl border border-base-content/10 p-2.5 hover:border-primary/30 cursor-pointer"
          @click="detail = mission"
        >
          <div class="flex items-center gap-1.5">
            <span class="badge badge-xs" :class="statusMeta(mission.status).badge">{{ statusMeta(mission.status).label }}</span>
            <span class="badge badge-xs" :class="priorityMeta(mission.priority).badge">{{ mission.priority }}</span>
            <span class="ml-auto text-[9px] text-base-content/30 font-mono">{{ mission.id.slice(-6) }}</span>
          </div>
          <h3 class="text-sm font-semibold mt-1 truncate">{{ mission.title }}</h3>
          <p v-if="mission.last_error" class="text-[10px] text-error/70 line-clamp-2">{{ mission.last_error }}</p>
          <div class="flex gap-1 mt-2" @click.stop>
            <button v-if="canDispatch(mission)" class="btn btn-xs btn-ghost" @click="dispatch(mission)">
              <i class="fa-solid fa-rocket"></i> Retry
            </button>
            <button class="btn btn-xs btn-ghost" @click="move(mission, 'ready')">Mark ready</button>
          </div>
        </article>
      </div>
    </section>

    <!-- Create / edit mission -->
    <div v-if="dialog" class="modal modal-open" role="dialog" aria-modal="true">
      <div class="modal-box max-w-2xl max-h-[90vh] overflow-y-auto">
        <div class="flex items-center justify-between mb-3">
          <h3 class="font-bold text-lg">{{ form.id ? 'Edit mission' : 'New mission' }}</h3>
          <button class="btn btn-ghost btn-sm btn-square" aria-label="Close" @click="close">
            <i class="fa-solid fa-xmark"></i>
          </button>
        </div>

        <div class="grid gap-3 md:grid-cols-2">
          <label class="form-control md:col-span-2">
            <span class="label-text text-xs">Title</span>
            <input v-model="form.title" class="input input-sm input-bordered" placeholder="Ship the hosted provisioning flow" @keyup.enter="submit" />
          </label>
          <label class="form-control md:col-span-2">
            <span class="label-text text-xs">Objective</span>
            <textarea v-model="form.objective" class="textarea textarea-sm textarea-bordered" rows="4"
                      placeholder="What must be achieved, in the company's voice"></textarea>
          </label>
          <label class="form-control md:col-span-2">
            <span class="label-text text-xs">Acceptance criteria</span>
            <textarea v-model="form.acceptance" class="textarea textarea-sm textarea-bordered" rows="2"
                      placeholder="How will we judge the outcome?"></textarea>
          </label>
          <label class="form-control">
            <span class="label-text text-xs">Team</span>
            <select v-model="form.team_id" class="select select-sm select-bordered">
              <option value="">— unassigned —</option>
              <option v-for="team in teams" :key="team.id" :value="team.id">{{ team.name }}</option>
            </select>
          </label>
          <label class="form-control">
            <span class="label-text text-xs">Project</span>
            <select v-model="form.project_id" class="select select-sm select-bordered">
              <option value="">— unassigned —</option>
              <option v-for="project in projects" :key="project.project_id" :value="project.project_id">
                {{ project.name }} ({{ project.project_id }})
              </option>
            </select>
          </label>
          <label class="form-control">
            <span class="label-text text-xs">Priority</span>
            <select v-model="form.priority" class="select select-sm select-bordered">
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
              <option value="critical">Critical</option>
            </select>
          </label>
          <label class="form-control">
            <span class="label-text text-xs">Dispatch mode</span>
            <select v-model="form.dispatch_mode" class="select select-sm select-bordered">
              <option value="manual">Manual — a human dispatches</option>
              <option value="auto">Auto — autopilot may dispatch</option>
            </select>
          </label>
          <label class="form-control">
            <span class="label-text text-xs">Budget (cxjcoins)</span>
            <input v-model="form.budget_cxjcoins" type="number" min="0" class="input input-sm input-bordered" />
          </label>
          <label class="form-control">
            <span class="label-text text-xs">Due date</span>
            <input v-model="form.due_date" type="date" class="input input-sm input-bordered" />
          </label>
          <label class="form-control md:col-span-2">
            <span class="label-text text-xs">Tags (comma separated)</span>
            <input v-model="form.tags" class="input input-sm input-bordered" placeholder="launch, pricing" />
          </label>
        </div>

        <p v-if="formError" class="text-error text-xs mt-3">{{ formError }}</p>

        <div class="modal-action">
          <button class="btn btn-sm btn-ghost" @click="close">Cancel</button>
          <button class="btn btn-sm btn-primary" :disabled="busy" @click="submit">
            {{ form.id ? 'Save mission' : 'Create mission' }}
          </button>
        </div>
      </div>
      <div class="modal-backdrop" @click="close"></div>
    </div>

    <!-- Mission detail -->
    <div v-if="detail" class="modal modal-open" role="dialog" aria-modal="true">
      <div class="modal-box max-w-2xl">
        <div class="flex items-start justify-between gap-2">
          <div>
            <div class="flex items-center gap-1.5 flex-wrap">
              <span class="badge badge-sm" :class="statusMeta(detail.status).badge">{{ statusMeta(detail.status).label }}</span>
              <span class="badge badge-sm" :class="priorityMeta(detail.priority).badge">{{ detail.priority }}</span>
              <span class="badge badge-sm badge-outline">{{ detail.dispatch_mode }}</span>
            </div>
            <h3 class="text-lg font-black mt-1">{{ detail.title }}</h3>
          </div>
          <button class="btn btn-ghost btn-sm btn-square" aria-label="Close" @click="detail = null">
            <i class="fa-solid fa-xmark"></i>
          </button>
        </div>

        <div class="grid gap-2 md:grid-cols-2 mt-3 text-xs">
          <div class="rounded-lg bg-base-200/50 p-2">
            <div class="text-[10px] uppercase text-base-content/40">Team</div>
            <div class="font-semibold">{{ teamName(detail.team_id) || 'Unassigned' }}</div>
          </div>
          <div class="rounded-lg bg-base-200/50 p-2">
            <div class="text-[10px] uppercase text-base-content/40">Project</div>
            <button class="font-semibold link link-hover text-left" @click="emit('open-project', projectRouteName(detail.project_id))">
              {{ projectName(detail.project_id) || 'Unassigned' }}
            </button>
          </div>
          <div class="rounded-lg bg-base-200/50 p-2">
            <div class="text-[10px] uppercase text-base-content/40">Run</div>
            <div class="font-mono text-[10px] truncate">{{ detail.run_id || 'not dispatched' }}</div>
            <div class="text-[10px] text-base-content/40">{{ detail.run_status || '-' }} · {{ detail.progress || 0 }}%</div>
          </div>
          <div class="rounded-lg bg-base-200/50 p-2">
            <div class="text-[10px] uppercase text-base-content/40">Due</div>
            <div class="font-semibold">{{ formatDate(detail.due_date) }}</div>
          </div>
        </div>

        <div class="mt-3">
          <div class="text-[10px] uppercase text-base-content/40">Objective</div>
          <p class="text-sm whitespace-pre-wrap">{{ detail.objective }}</p>
        </div>
        <div v-if="detail.acceptance" class="mt-3">
          <div class="text-[10px] uppercase text-base-content/40">Acceptance</div>
          <p class="text-sm whitespace-pre-wrap">{{ detail.acceptance }}</p>
        </div>
        <div v-if="detail.last_error" class="mt-3 rounded-lg bg-error/10 text-error p-2 text-xs">
          <i class="fa-solid fa-triangle-exclamation mr-1"></i>{{ detail.last_error }}
        </div>
        <div v-if="detail.result" class="mt-3 rounded-lg bg-success/10 text-success p-2 text-xs">
          <i class="fa-solid fa-circle-check mr-1"></i>{{ detail.result }}
        </div>

        <div class="modal-action">
          <button v-if="detail.status === 'draft'" class="btn btn-sm btn-info" :disabled="busy" @click="move(detail, 'ready'); detail = null">
            <i class="fa-solid fa-circle-play"></i> Mark ready
          </button>
          <button v-if="canDispatch(detail)" class="btn btn-sm btn-primary" :disabled="busy" @click="dispatch(detail); detail = null">
            <i class="fa-solid fa-rocket"></i> Dispatch
          </button>
          <template v-if="detail.status === 'review'">
            <button class="btn btn-sm btn-success" :disabled="busy" @click="accept(detail); detail = null">Accept</button>
            <button class="btn btn-sm btn-ghost" :disabled="busy" @click="reject(detail); detail = null">Reject</button>
          </template>
          <button class="btn btn-sm btn-ghost" @click="openEdit(detail); detail = null">Edit</button>
          <button class="btn btn-sm btn-ghost" @click="detail = null">Close</button>
        </div>
      </div>
      <div class="modal-backdrop" @click="detail = null"></div>
    </div>
  </div>
</template>

<!-- Made with ❤️ by codx-junior -->
