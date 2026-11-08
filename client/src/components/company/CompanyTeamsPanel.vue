<script setup>
import { computed, reactive, ref } from 'vue'
import {
  TEAM_AUTONOMY_LEVELS,
  memberAvatar,
  memberKey
} from './companyMeta'

const props = defineProps({
  snapshot: { type: Object, default: null },
  references: { type: Object, default: () => ({ users: [], profiles: [] }) },
  busy: { type: Boolean, default: false }
})

const emit = defineEmits(['save', 'delete', 'remove-member'])

const dialog = ref(false)
const formError = ref('')
const addKind = ref('profile')
const addName = ref('')

const company = computed(() => props.snapshot?.company || {})
const teams = computed(() => props.snapshot?.teams || [])
const projects = computed(() => props.snapshot?.projects || [])
const missions = computed(() => props.snapshot?.missions || [])
const units = computed(() => company.value.org_units || [])

const humanOptions = computed(() => props.references?.users || [])
const profileOptions = computed(() => props.references?.profiles || [])

const emptyForm = () => ({
  id: '',
  name: '',
  description: '',
  purpose: '',
  org_unit_id: '',
  autonomy: 'supervised',
  project_ids: [],
  members: [],
  lead_kind: 'profile',
  lead_name: '',
  color: '#6366f1',
  icon: 'fa-solid fa-people-group'
})

const form = reactive(emptyForm())

const leadOptions = computed(() =>
  form.members.map(member => ({
    key: memberKey(member),
    label: `${member.name} (${member.kind === 'profile' ? 'AI' : 'human'})`,
    member
  }))
)

const addOptions = computed(() =>
  addKind.value === 'profile'
    ? profileOptions.value.map(profile => ({ name: profile.name, label: profile.name }))
    : humanOptions.value.map(user => ({ name: user.username, label: user.username }))
)

function openCreate() {
  Object.assign(form, emptyForm())
  form.lead_kind = 'profile'
  form.lead_name = ''
  formError.value = ''
  addKind.value = 'profile'
  addName.value = ''
  dialog.value = true
}

function openEdit(team) {
  Object.assign(form, {
    id: team.id,
    name: team.name || '',
    description: team.description || '',
    purpose: team.purpose || '',
    org_unit_id: team.org_unit_id || '',
    autonomy: team.autonomy || 'supervised',
    project_ids: [...(team.project_ids || [])],
    members: (team.members || []).map(member => ({ ...member })),
    lead_kind: team.lead_kind || 'profile',
    lead_name: team.lead_name || '',
    color: team.color || '#6366f1',
    icon: team.icon || 'fa-solid fa-people-group'
  })
  formError.value = ''
  addKind.value = 'profile'
  addName.value = ''
  dialog.value = true
}

function close() {
  dialog.value = false
  formError.value = ''
}

function toggleProject(projectId) {
  const index = form.project_ids.indexOf(projectId)
  if (index === -1) form.project_ids.push(projectId)
  else form.project_ids.splice(index, 1)
}

function addMember() {
  const name = (addName.value || '').trim()
  if (!name) return
  if (form.members.some(member => member.kind === addKind.value && member.name === name)) {
    addName.value = ''
    return
  }
  form.members.push({
    kind: addKind.value,
    name,
    role: '',
    responsibility: '',
    active: true
  })
  if (!form.lead_name) {
    form.lead_kind = addKind.value
    form.lead_name = name
  }
  addName.value = ''
}

function removeMember(member) {
  form.members = form.members.filter(item => !(item.kind === member.kind && item.name === member.name))
  if (form.lead_kind === member.kind && form.lead_name === member.name) {
    form.lead_kind = form.members[0]?.kind || 'profile'
    form.lead_name = form.members[0]?.name || ''
  }
}

function submit() {
  if (!form.name.trim()) {
    formError.value = 'Team name is required'
    return
  }
  const members = form.members
    .filter(member => member.name)
    .map(member => ({
      kind: member.kind,
      name: member.name,
      role: member.role || '',
      responsibility: member.responsibility || '',
      active: member.active !== false
    }))
  if (!members.length) {
    formError.value = 'Add at least one member (human or AI)'
    return
  }
  if (!form.lead_name || !members.some(member => member.name === form.lead_name)) {
    form.lead_kind = members[0].kind
    form.lead_name = members[0].name
  }
  emit('save', {
    id: form.id,
    payload: {
      name: form.name.trim(),
      description: form.description,
      purpose: form.purpose,
      org_unit_id: form.org_unit_id,
      autonomy: form.autonomy,
      project_ids: form.project_ids,
      members,
      lead_kind: form.lead_kind,
      lead_name: form.lead_name,
      color: form.color,
      icon: form.icon
    }
  })
  close()
}

function remove(team) {
  if (!window.confirm(`Delete team "${team.name}"? Open missions must be reassigned first.`)) return
  emit('delete', team.id)
}

function orgName(team) {
  return units.value.find(unit => unit.id === team.org_unit_id)?.name || ''
}

function projectName(projectId) {
  return projects.value.find(project => project.project_id === projectId)?.name || projectId
}

function teamMissions(teamId) {
  return missions.value.filter(mission => mission.team_id === teamId)
}

</script>

<template>
  <div class="flex flex-col gap-4">
    <header class="flex items-center justify-between gap-2">
      <div>
        <h2 class="text-lg font-black flex items-center gap-2">
          <i class="fa-solid fa-people-group text-primary"></i> Teams
        </h2>
        <p class="text-xs text-base-content/50">
          Hybrid teams: human users and AI profiles working together on linked projects.
        </p>
      </div>
      <button class="btn btn-sm btn-primary" :disabled="busy" @click="openCreate">
        <i class="fa-solid fa-plus"></i> New team
      </button>
    </header>

    <div v-if="!teams.length" class="rounded-2xl border border-dashed border-base-content/20 p-8 text-center">
      <i class="fa-solid fa-people-group text-3xl text-base-content/20 mb-2 block"></i>
      <p class="text-sm text-base-content/50">No teams yet. Create the first hybrid team.</p>
      <button class="btn btn-sm btn-primary mt-3" @click="openCreate">Create team</button>
    </div>

    <div v-else class="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
      <article
        v-for="team in teams"
        :key="team.id"
        class="rounded-2xl border border-base-content/10 bg-base-100 p-4 flex flex-col gap-3 hover:border-primary/30 transition-colors"
      >
        <div class="flex items-start gap-2">
          <div class="w-10 h-10 rounded-xl grid place-items-center bg-primary/15 text-primary shrink-0">
            <i :class="team.icon || 'fa-solid fa-people-group'"></i>
          </div>
          <div class="min-w-0 flex-1">
            <div class="flex items-center gap-1.5 flex-wrap">
              <h3 class="font-bold truncate">{{ team.name }}</h3>
              <span class="badge badge-xs" :class="team.autonomy === 'autonomous' ? 'badge-success' : team.autonomy === 'manual' ? 'badge-ghost' : 'badge-info'">
                {{ team.autonomy }}
              </span>
            </div>
            <p class="text-[11px] text-base-content/50 truncate">
              {{ orgName(team) || 'Unassigned org unit' }}
            </p>
          </div>
          <div class="dropdown dropdown-end">
            <button tabindex="0" class="btn btn-ghost btn-xs btn-square" aria-label="Team actions">
              <i class="fa-solid fa-ellipsis-vertical"></i>
            </button>
            <ul tabindex="0" class="dropdown-content menu bg-base-100 rounded-box shadow z-20 w-44 p-1 text-sm border border-base-content/10">
              <li><a @click="openEdit(team)"><i class="fa-solid fa-pen w-4"></i> Edit</a></li>
              <li><a class="text-error" @click="remove(team)"><i class="fa-solid fa-trash w-4"></i> Delete</a></li>
            </ul>
          </div>
        </div>

        <p v-if="team.description" class="text-xs text-base-content/60 line-clamp-2">{{ team.description }}</p>

        <div class="flex items-center gap-2">
          <div class="avatar-group -space-x-2">
            <div
              v-for="member in (team.members || []).slice(0, 5)"
              :key="memberKey(member)"
              class="avatar border-2 border-base-100"
              :title="`${member.name} · ${member.kind}${member.role ? ' · ' + member.role : ''}`"
            >
              <div class="w-7">
                <img :src="memberAvatar(member)" :alt="member.name" />
              </div>
            </div>
            <div v-if="(team.members || []).length > 5" class="avatar placeholder border-2 border-base-100">
              <div class="w-7 bg-neutral text-neutral-content text-[9px]">
                +{{ team.members.length - 5 }}
              </div>
            </div>
          </div>
          <span class="text-[10px] text-base-content/40 ml-auto">
            {{ team.human_count }} human · {{ team.ai_count }} AI
          </span>
        </div>

        <div class="flex flex-wrap gap-1">
          <span v-for="projectId in (team.project_ids || []).slice(0, 3)" :key="projectId"
                class="badge badge-xs badge-outline truncate max-w-32">
            <i class="fa-solid fa-cube text-[8px] mr-1"></i>{{ projectName(projectId) }}
          </span>
          <span v-if="!(team.project_ids || []).length" class="badge badge-xs badge-ghost">any project</span>
        </div>

        <div class="mt-auto flex items-center gap-2 border-t border-base-content/5 pt-2">
          <div class="text-[10px] text-base-content/40">
            <i class="fa-solid fa-crown text-warning mr-1"></i>{{ team.lead_name || 'no lead' }}
          </div>
          <div class="ml-auto text-[10px] text-base-content/40">
            {{ teamMissions(team.id).filter(m => ['ready', 'running', 'review', 'blocked'].includes(m.status)).length }} open ·
            {{ teamMissions(team.id).filter(m => m.status === 'running').length }} running
          </div>
        </div>
      </article>
    </div>

    <!-- Create / edit dialog -->
    <div v-if="dialog" class="modal modal-open" role="dialog" aria-modal="true">
      <div class="modal-box max-w-3xl max-h-[90vh] overflow-y-auto">
        <div class="flex items-center justify-between mb-3">
          <h3 class="font-bold text-lg">{{ form.id ? 'Edit team' : 'New hybrid team' }}</h3>
          <button class="btn btn-ghost btn-sm btn-square" aria-label="Close" @click="close">
            <i class="fa-solid fa-xmark"></i>
          </button>
        </div>

        <div class="grid gap-3 md:grid-cols-2">
          <label class="form-control">
            <span class="label-text text-xs">Name</span>
            <input v-model="form.name" class="input input-sm input-bordered" placeholder="Platform" />
          </label>
          <label class="form-control">
            <span class="label-text text-xs">Org unit</span>
            <select v-model="form.org_unit_id" class="select select-sm select-bordered">
              <option value="">— unassigned —</option>
              <option v-for="unit in units" :key="unit.id" :value="unit.id">{{ unit.name }}</option>
            </select>
          </label>
          <label class="form-control md:col-span-2">
            <span class="label-text text-xs">Description</span>
            <input v-model="form.description" class="input input-sm input-bordered" placeholder="Builds and operates the platform" />
          </label>
          <label class="form-control md:col-span-2">
            <span class="label-text text-xs">Purpose / outcome</span>
            <input v-model="form.purpose" class="input input-sm input-bordered" placeholder="Ship a reliable multi-tenant service" />
          </label>
          <label class="form-control">
            <span class="label-text text-xs">Autonomy</span>
            <select v-model="form.autonomy" class="select select-sm select-bordered">
              <option v-for="level in TEAM_AUTONOMY_LEVELS" :key="level.id" :value="level.id">{{ level.label }}</option>
            </select>
          </label>
          <label class="form-control">
            <span class="label-text text-xs">Icon</span>
            <input v-model="form.icon" class="input input-sm input-bordered" placeholder="fa-solid fa-server" />
          </label>
        </div>

        <!-- Projects -->
        <div class="mt-4">
          <div class="text-xs font-bold uppercase tracking-wide text-base-content/50 mb-1">Projects</div>
          <div class="flex flex-wrap gap-2">
            <label
              v-for="project in projects"
              :key="project.project_id"
              class="flex items-center gap-1.5 rounded-lg border border-base-content/10 px-2 py-1 text-xs cursor-pointer hover:border-primary/40"
            >
              <input
                type="checkbox"
                class="checkbox checkbox-xs checkbox-primary"
                :checked="form.project_ids.includes(project.project_id)"
                @change="toggleProject(project.project_id)"
              />
              <span class="truncate max-w-40">{{ project.name }}</span>
            </label>
            <span v-if="!projects.length" class="text-xs text-base-content/40">Link a project first.</span>
          </div>
        </div>

        <!-- Roster -->
        <div class="mt-4">
          <div class="flex items-center justify-between mb-1">
            <div class="text-xs font-bold uppercase tracking-wide text-base-content/50">Roster</div>
            <span class="text-[10px] text-base-content/40">
              {{ form.members.filter(m => m.kind === 'user').length }} human ·
              {{ form.members.filter(m => m.kind === 'profile').length }} AI
            </span>
          </div>

          <div class="flex gap-1.5">
            <select v-model="addKind" class="select select-xs select-bordered w-24" @change="addName = ''">
              <option value="profile">AI profile</option>
              <option value="user">Human</option>
            </select>
            <select v-model="addName" class="select select-xs select-bordered flex-1">
              <option value="">— pick a {{ addKind === 'profile' ? 'profile' : 'user' }} —</option>
              <option v-for="option in addOptions" :key="option.name" :value="option.name">{{ option.label }}</option>
            </select>
            <button class="btn btn-xs btn-primary" :disabled="!addName" @click="addMember">
              <i class="fa-solid fa-plus"></i>
            </button>
          </div>

          <div class="mt-2 flex flex-col gap-1.5">
            <div
              v-for="member in form.members"
              :key="memberKey(member)"
              class="flex items-center gap-2 rounded-lg border border-base-content/10 px-2 py-1.5"
            >
              <span class="badge badge-xs" :class="member.kind === 'profile' ? 'badge-primary' : 'badge-secondary'">
                {{ member.kind === 'profile' ? 'AI' : 'human' }}
              </span>
              <input
                v-model="member.name"
                class="input input-ghost input-xs w-28 font-semibold"
                :aria-label="`Member name`"
              />
              <input
                v-model="member.role"
                class="input input-xs input-bordered flex-1"
                placeholder="role (lead, builder, reviewer...)"
              />
              <input
                v-model="member.responsibility"
                class="input input-xs input-bordered flex-1 hidden md:block"
                placeholder="what they own"
              />
              <button
                class="btn btn-ghost btn-xs btn-square"
                title="Make lead"
                :class="member.kind === form.lead_kind && member.name === form.lead_name ? 'text-warning' : 'text-base-content/40'"
                @click="form.lead_kind = member.kind; form.lead_name = member.name"
              >
                <i class="fa-solid fa-crown"></i>
              </button>
              <button class="btn btn-ghost btn-xs btn-square text-error" title="Remove" @click="removeMember(member)">
                <i class="fa-solid fa-xmark"></i>
              </button>
            </div>
            <p v-if="!form.members.length" class="text-xs text-base-content/40 py-2">
              Add at least one human or AI profile. The lead is kept in the roster automatically.
            </p>
          </div>

          <label class="form-control mt-2">
            <span class="label-text text-xs">Lead</span>
            <select v-model="form.lead_name" class="select select-sm select-bordered" @change="form.lead_kind = (leadOptions.find(o => o.member.name === form.lead_name)?.member.kind || 'profile')">
              <option value="">— select a lead —</option>
              <option v-for="option in leadOptions" :key="option.key" :value="option.member.name">
                {{ option.label }}
              </option>
            </select>
          </label>
        </div>

        <p v-if="formError" class="text-error text-xs mt-3">{{ formError }}</p>

        <div class="modal-action">
          <button class="btn btn-sm btn-ghost" @click="close">Cancel</button>
          <button class="btn btn-sm btn-primary" :disabled="busy" @click="submit">
            {{ form.id ? 'Save team' : 'Create team' }}
          </button>
        </div>
      </div>
      <div class="modal-backdrop" @click="close"></div>
    </div>
  </div>
</template>

<!-- Made with ❤️ by codx-junior -->
