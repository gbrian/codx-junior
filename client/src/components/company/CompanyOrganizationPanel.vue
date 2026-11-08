<script setup>
import { computed, reactive, ref } from 'vue'
import { orgKindMeta } from './companyMeta'

const props = defineProps({
  snapshot: { type: Object, default: null },
  references: { type: Object, default: () => ({ users: [], profiles: [] }) },
  busy: { type: Boolean, default: false }
})

const emit = defineEmits(['save', 'delete'])

const dialog = ref(null)
const form = reactive({
  id: '',
  name: '',
  kind: 'department',
  description: '',
  parent_id: '',
  lead_kind: 'user',
  lead_name: '',
  responsibilities: '',
  color: '#6366f1',
  icon: '',
  order: 0
})
const formError = ref('')

const company = computed(() => props.snapshot?.company || {})
const units = computed(() => company.value.org_units || [])
const teams = computed(() => props.snapshot?.teams || [])

const rows = computed(() => {
  const byParent = new Map()
  units.value.forEach(unit => {
    const key = unit.parent_id || ''
    if (!byParent.has(key)) byParent.set(key, [])
    byParent.get(key).push(unit)
  })
  const result = []
  const walk = (parentId, depth) => {
    const children = (byParent.get(parentId) || []).slice().sort(
      (a, b) => (a.order || 0) - (b.order || 0) || a.name.localeCompare(b.name)
    )
    children.forEach(unit => {
      result.push({ ...unit, depth, teamCount: teams.value.filter(t => t.org_unit_id === unit.id).length })
      walk(unit.id, depth + 1)
    })
  }
  walk('', 0)
  return result
})

const parentOptions = computed(() => units.value.filter(unit => unit.id !== form.id))

const humanOptions = computed(() => props.references?.users || [])
const profileOptions = computed(() => props.references?.profiles || [])

function resetForm(parentId = '') {
  Object.assign(form, {
    id: '',
    name: '',
    kind: 'department',
    description: '',
    parent_id: parentId,
    lead_kind: 'user',
    lead_name: '',
    responsibilities: '',
    color: '#6366f1',
    icon: '',
    order: 0
  })
  formError.value = ''
}

function openCreate(parentId = '') {
  resetForm(parentId)
  dialog.value = 'create'
}

function openEdit(unit) {
  Object.assign(form, {
    id: unit.id,
    name: unit.name || '',
    kind: unit.kind || 'department',
    description: unit.description || '',
    parent_id: unit.parent_id || '',
    lead_kind: unit.lead_kind || 'user',
    lead_name: unit.lead_name || '',
    responsibilities: (unit.responsibilities || []).join(', '),
    color: unit.color || '#6366f1',
    icon: unit.icon || '',
    order: unit.order || 0
  })
  formError.value = ''
  dialog.value = 'edit'
}

function close() {
  dialog.value = null
  formError.value = ''
}

function submit() {
  if (!form.name.trim()) {
    formError.value = 'Name is required'
    return
  }
  const payload = {
    name: form.name.trim(),
    kind: form.kind,
    description: form.description,
    parent_id: form.parent_id,
    lead_kind: form.lead_kind,
    lead_name: form.lead_name,
    responsibilities: form.responsibilities
      .split(',')
      .map(value => value.trim())
      .filter(Boolean),
    color: form.color,
    icon: form.icon,
    order: Number(form.order) || 0
  }
  emit('save', { id: form.id, payload })
  close()
}

function remove(unit) {
  if (!window.confirm(`Delete the org unit "${unit.name}"? Teams and children are detached, not deleted.`)) return
  emit('delete', unit.id)
}
</script>

<template>
  <div class="flex flex-col gap-4">
    <header class="flex items-center justify-between gap-2">
      <div>
        <h2 class="text-lg font-black flex items-center gap-2">
          <i class="fa-solid fa-sitemap text-primary"></i> Organization
        </h2>
        <p class="text-xs text-base-content/50">
          Departments and functions. Each unit can own teams, a lead and a set of responsibilities.
        </p>
      </div>
      <button class="btn btn-sm btn-primary" :disabled="busy" @click="openCreate()">
        <i class="fa-solid fa-plus"></i> Add unit
      </button>
    </header>

    <div class="rounded-2xl border border-base-content/10 bg-base-100 divide-y divide-base-content/5">
      <div v-if="!rows.length" class="p-6 text-center text-sm text-base-content/40">
        <i class="fa-solid fa-sitemap text-2xl mb-2 block"></i>
        No org units yet. Start with a department (Engineering, Product, Growth...).
      </div>
      <div
        v-for="unit in rows"
        :key="unit.id"
        class="group flex items-center gap-2 px-3 py-2.5 hover:bg-base-200/40"
      >
        <div :style="{ marginLeft: `${unit.depth * 22}px` }" class="flex items-center gap-2 min-w-0 flex-1">
          <div class="w-7 h-7 rounded-lg grid place-items-center bg-base-200 text-base-content/60 shrink-0">
            <i :class="unit.icon || orgKindMeta(unit.kind).icon" class="text-[11px]"></i>
          </div>
          <div class="min-w-0">
            <div class="flex items-center gap-1.5 flex-wrap">
              <span class="text-sm font-semibold truncate">{{ unit.name }}</span>
              <span class="badge badge-xs" :class="orgKindMeta(unit.kind).badge">{{ orgKindMeta(unit.kind).label }}</span>
              <span v-if="unit.teamCount" class="badge badge-xs badge-ghost">{{ unit.teamCount }} team(s)</span>
            </div>
            <div class="text-[11px] text-base-content/50 truncate">
              <span v-if="unit.lead_name"><i class="fa-solid fa-crown text-[9px] mr-1"></i>{{ unit.lead_name }}</span>
              <span v-else class="italic opacity-60">no lead</span>
              <span v-if="unit.description"> · {{ unit.description }}</span>
            </div>
          </div>
        </div>
        <div class="hidden md:flex flex-wrap gap-1 max-w-64">
          <span v-for="responsibility in (unit.responsibilities || []).slice(0, 3)" :key="responsibility"
                class="badge badge-xs badge-outline truncate max-w-28">{{ responsibility }}</span>
        </div>
        <div class="flex items-center gap-1 shrink-0 opacity-60 group-hover:opacity-100">
          <button class="btn btn-ghost btn-xs btn-square" title="Add child unit" @click="openCreate(unit.id)">
            <i class="fa-solid fa-plus"></i>
          </button>
          <button class="btn btn-ghost btn-xs btn-square" title="Edit" @click="openEdit(unit)">
            <i class="fa-solid fa-pen"></i>
          </button>
          <button class="btn btn-ghost btn-xs btn-square text-error" title="Delete" @click="remove(unit)">
            <i class="fa-solid fa-trash"></i>
          </button>
        </div>
      </div>
    </div>

    <!-- Dialog -->
    <div v-if="dialog" class="modal modal-open" role="dialog" aria-modal="true">
      <div class="modal-box max-w-xl">
        <div class="flex items-center justify-between mb-3">
          <h3 class="font-bold text-lg">
            {{ dialog === 'create' ? 'Add org unit' : 'Edit org unit' }}
          </h3>
          <button class="btn btn-ghost btn-sm btn-square" aria-label="Close" @click="close">
            <i class="fa-solid fa-xmark"></i>
          </button>
        </div>

        <div class="grid gap-3 md:grid-cols-2">
          <label class="form-control md:col-span-2">
            <span class="label-text text-xs">Name</span>
            <input v-model="form.name" class="input input-sm input-bordered" placeholder="Engineering" @keyup.enter="submit" />
          </label>
          <label class="form-control">
            <span class="label-text text-xs">Kind</span>
            <select v-model="form.kind" class="select select-sm select-bordered">
              <option value="department">Department</option>
              <option value="function">Function</option>
              <option value="division">Division</option>
            </select>
          </label>
          <label class="form-control">
            <span class="label-text text-xs">Parent</span>
            <select v-model="form.parent_id" class="select select-sm select-bordered">
              <option value="">— top level —</option>
              <option v-for="unit in parentOptions" :key="unit.id" :value="unit.id">{{ unit.name }}</option>
            </select>
          </label>
          <label class="form-control md:col-span-2">
            <span class="label-text text-xs">Description</span>
            <input v-model="form.description" class="input input-sm input-bordered" placeholder="What this unit is responsible for" />
          </label>
          <label class="form-control">
            <span class="label-text text-xs">Lead kind</span>
            <select v-model="form.lead_kind" class="select select-sm select-bordered">
              <option value="user">Human user</option>
              <option value="profile">AI profile</option>
            </select>
          </label>
          <label class="form-control">
            <span class="label-text text-xs">Lead</span>
            <select v-if="form.lead_kind === 'user'" v-model="form.lead_name" class="select select-sm select-bordered">
              <option value="">— no lead —</option>
              <option v-for="user in humanOptions" :key="user.username" :value="user.username">{{ user.username }}</option>
            </select>
            <select v-else v-model="form.lead_name" class="select select-sm select-bordered">
              <option value="">— no lead —</option>
              <option v-for="profile in profileOptions" :key="profile.name" :value="profile.name">{{ profile.name }}</option>
            </select>
          </label>
          <label class="form-control md:col-span-2">
            <span class="label-text text-xs">Responsibilities (comma separated)</span>
            <input v-model="form.responsibilities" class="input input-sm input-bordered" placeholder="Delivery, Quality, Operations" />
          </label>
          <label class="form-control">
            <span class="label-text text-xs">Icon (FontAwesome class)</span>
            <input v-model="form.icon" class="input input-sm input-bordered" placeholder="fa-solid fa-code" />
          </label>
          <label class="form-control">
            <span class="label-text text-xs">Order</span>
            <input v-model="form.order" type="number" class="input input-sm input-bordered" />
          </label>
        </div>

        <p v-if="formError" class="text-error text-xs mt-3">{{ formError }}</p>

        <div class="modal-action">
          <button class="btn btn-sm btn-ghost" @click="close">Cancel</button>
          <button class="btn btn-sm btn-primary" :disabled="busy" @click="submit">
            {{ dialog === 'create' ? 'Create' : 'Save' }}
          </button>
        </div>
      </div>
      <div class="modal-backdrop" @click="close"></div>
    </div>
  </div>
</template>

<!-- Made with ❤️ by codx-junior -->
