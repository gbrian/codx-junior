<script setup>
import { computed, reactive, ref } from 'vue'
import { priorityMeta } from './companyMeta'

const props = defineProps({
  snapshot: { type: Object, default: null },
  references: { type: Object, default: () => ({ projects: [] }) },
  busy: { type: Boolean, default: false }
})

const emit = defineEmits(['save', 'delete', 'open-project'])

const dialog = ref(false)
const formError = ref('')
const editing = ref(false)

const company = computed(() => props.snapshot?.company || {})
const projects = computed(() => props.snapshot?.projects || [])
const teams = computed(() => props.snapshot?.teams || [])
const missions = computed(() => props.snapshot?.missions || [])

const form = reactive({
  project_id: '',
  name: '',
  role: '',
  description: '',
  team_id: '',
  priority: 'medium',
  status: 'active',
  budget_cxjcoins: 0
})

const linkedIds = computed(() => new Set(projects.value.map(project => project.project_id)))
const availableProjects = computed(() =>
  (props.references?.projects || []).filter(project => !linkedIds.value.has(project.project_id))
)

function reset() {
  Object.assign(form, {
    project_id: '',
    name: '',
    role: '',
    description: '',
    team_id: '',
    priority: 'medium',
    status: 'active',
    budget_cxjcoins: 0
  })
  formError.value = ''
}

function openLink() {
  reset()
  editing.value = false
  dialog.value = true
}

function openEdit(project) {
  Object.assign(form, {
    project_id: project.project_id,
    name: project.name || '',
    role: project.role || '',
    description: project.description || '',
    team_id: project.team_id || '',
    priority: project.priority || 'medium',
    status: project.status || 'active',
    budget_cxjcoins: project.budget_cxjcoins || 0
  })
  formError.value = ''
  editing.value = true
  dialog.value = true
}

function close() {
  dialog.value = false
}

function pickProject(projectId) {
  form.project_id = projectId
  const found = availableProjects.value.find(project => project.project_id === projectId)
  if (found && !form.name) form.name = found.project_name
}

function submit() {
  if (!form.project_id) {
    formError.value = 'Pick a project to link'
    return
  }
  emit('save', {
    project_id: form.project_id,
    payload: {
      project_id: form.project_id,
      name: form.name,
      role: form.role,
      description: form.description,
      team_id: form.team_id,
      priority: form.priority,
      status: form.status,
      budget_cxjcoins: Number(form.budget_cxjcoins) || 0
    }
  })
  close()
}

function remove(project) {
  if (!window.confirm(`Unlink "${project.name || project.project_id}" from the company? The codx-junior project itself is untouched.`)) return
  emit('delete', project.project_id)
}

function teamName(teamId) {
  return teams.value.find(team => team.id === teamId)?.name || ''
}

function openMissions(projectId) {
  return missions.value.filter(mission => mission.project_id === projectId)
}
</script>

<template>
  <div class="flex flex-col gap-4">
    <header class="flex items-center justify-between gap-2">
      <div>
        <h2 class="text-lg font-black flex items-center gap-2">
          <i class="fa-solid fa-cubes text-primary"></i> Projects
        </h2>
        <p class="text-xs text-base-content/50">
          The codx-junior projects this company runs. Missions are dispatched into these projects.
        </p>
      </div>
      <button class="btn btn-sm btn-primary" :disabled="busy" @click="openLink">
        <i class="fa-solid fa-link"></i> Link project
      </button>
    </header>

    <div v-if="!projects.length" class="rounded-2xl border border-dashed border-base-content/20 p-8 text-center">
      <i class="fa-solid fa-cubes text-3xl text-base-content/20 mb-2 block"></i>
      <p class="text-sm text-base-content/50">No projects linked yet.</p>
      <button class="btn btn-sm btn-primary mt-3" @click="openLink">Link the first project</button>
    </div>

    <div v-else class="grid gap-3 md:grid-cols-2">
      <article
        v-for="project in projects"
        :key="project.project_id"
        class="rounded-2xl border border-base-content/10 bg-base-100 p-4 flex flex-col gap-2"
      >
        <div class="flex items-start gap-2">
          <div class="w-9 h-9 rounded-xl grid place-items-center bg-primary/10 text-primary shrink-0">
            <i class="fa-solid fa-cube"></i>
          </div>
          <div class="min-w-0 flex-1">
            <div class="flex items-center gap-1.5 flex-wrap">
              <h3 class="font-bold truncate">{{ project.name || project.project_id }}</h3>
              <span class="badge badge-xs" :class="project.available ? 'badge-success' : 'badge-error'">
                {{ project.available ? 'available' : 'missing' }}
              </span>
            </div>
            <p class="text-[10px] text-base-content/40 font-mono truncate">{{ project.project_id }}</p>
          </div>
          <div class="dropdown dropdown-end">
            <button tabindex="0" class="btn btn-ghost btn-xs btn-square" aria-label="Project actions">
              <i class="fa-solid fa-ellipsis-vertical"></i>
            </button>
            <ul tabindex="0" class="dropdown-content menu bg-base-100 rounded-box shadow z-20 w-44 p-1 text-sm border border-base-content/10">
              <li><a @click="openEdit(project)"><i class="fa-solid fa-pen w-4"></i> Edit</a></li>
              <li v-if="project.discovered_name">
                <a @click="emit('open-project', project.discovered_name)">
                  <i class="fa-solid fa-arrow-up-right-from-square w-4"></i> Open project
                </a>
              </li>
              <li><a class="text-error" @click="remove(project)"><i class="fa-solid fa-link-slash w-4"></i> Unlink</a></li>
            </ul>
          </div>
        </div>

        <p v-if="project.description" class="text-xs text-base-content/60 line-clamp-2">{{ project.description }}</p>
        <p v-else-if="project.discovered_path" class="text-[10px] text-base-content/40 font-mono truncate">{{ project.discovered_path }}</p>

        <div class="flex flex-wrap items-center gap-1.5 text-[10px]">
          <span v-if="project.role" class="badge badge-xs badge-outline">{{ project.role }}</span>
          <span class="badge badge-xs" :class="priorityMeta(project.priority).badge">{{ project.priority }}</span>
          <span class="badge badge-xs badge-ghost">{{ project.status }}</span>
          <span v-if="project.team_id" class="badge badge-xs badge-secondary">
            <i class="fa-solid fa-people-group text-[8px] mr-1"></i>{{ teamName(project.team_id) }}
          </span>
        </div>

        <div class="mt-auto flex items-center justify-between border-t border-base-content/5 pt-2 text-[10px] text-base-content/40">
          <span>{{ openMissions(project.project_id).filter(m => ['ready', 'running', 'review', 'blocked'].includes(m.status)).length }} open missions</span>
          <span v-if="project.budget_cxjcoins">{{ project.budget_cxjcoins }} cxj budget</span>
        </div>
      </article>
    </div>

    <!-- Link / edit -->
    <div v-if="dialog" class="modal modal-open" role="dialog" aria-modal="true">
      <div class="modal-box max-w-xl">
        <div class="flex items-center justify-between mb-3">
          <h3 class="font-bold text-lg">{{ editing ? 'Edit linked project' : 'Link a project' }}</h3>
          <button class="btn btn-ghost btn-sm btn-square" aria-label="Close" @click="close">
            <i class="fa-solid fa-xmark"></i>
          </button>
        </div>

        <div class="grid gap-3 md:grid-cols-2">
          <label v-if="!editing" class="form-control md:col-span-2">
            <span class="label-text text-xs">Discovered codx-junior project</span>
            <select class="select select-sm select-bordered" :value="form.project_id" @change="pickProject($event.target.value)">
              <option value="">— pick a project —</option>
              <option v-for="project in availableProjects" :key="project.project_id" :value="project.project_id">
                {{ project.project_name }} ({{ project.project_id }})
              </option>
            </select>
            <span v-if="!availableProjects.length" class="text-[10px] text-base-content/40 mt-1">
              Every discovered project is already linked.
            </span>
          </label>
          <label class="form-control">
            <span class="label-text text-xs">Display name</span>
            <input v-model="form.name" class="input input-sm input-bordered" placeholder="codx-junior cloud" />
          </label>
          <label class="form-control">
            <span class="label-text text-xs">Role in the company</span>
            <input v-model="form.role" class="input input-sm input-bordered" placeholder="platform, console, website..." />
          </label>
          <label class="form-control md:col-span-2">
            <span class="label-text text-xs">Description</span>
            <input v-model="form.description" class="input input-sm input-bordered" placeholder="Why this project exists" />
          </label>
          <label class="form-control">
            <span class="label-text text-xs">Owning team</span>
            <select v-model="form.team_id" class="select select-sm select-bordered">
              <option value="">— unassigned —</option>
              <option v-for="team in teams" :key="team.id" :value="team.id">{{ team.name }}</option>
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
            <span class="label-text text-xs">Status</span>
            <select v-model="form.status" class="select select-sm select-bordered">
              <option value="active">Active</option>
              <option value="paused">Paused</option>
              <option value="archived">Archived</option>
            </select>
          </label>
          <label class="form-control">
            <span class="label-text text-xs">Budget (cxjcoins)</span>
            <input v-model="form.budget_cxjcoins" type="number" min="0" class="input input-sm input-bordered" />
          </label>
        </div>

        <p v-if="formError" class="text-error text-xs mt-3">{{ formError }}</p>

        <div class="modal-action">
          <button class="btn btn-sm btn-ghost" @click="close">Cancel</button>
          <button class="btn btn-sm btn-primary" :disabled="busy" @click="submit">
            {{ editing ? 'Save' : 'Link project' }}
          </button>
        </div>
      </div>
      <div class="modal-backdrop" @click="close"></div>
    </div>
  </div>
</template>

<!-- Made with ❤️ by codx-junior -->
