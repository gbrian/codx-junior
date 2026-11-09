<script setup>
import { computed } from 'vue'
import { memberAvatar } from './companyMeta'

/**
 * People view of the company shell.
 *
 * Company admins can add users, but the form is NOT rendered here: it lives in
 * the always-present assistant window (see CompanyAssistant.vue). This panel
 * stays a simple, read-first roster with direct role/removal actions for admins.
 */
const props = defineProps({
  snapshot: { type: Object, default: null },
  busy: { type: Boolean, default: false },
  canAdmin: { type: Boolean, default: false },
  canManage: { type: Boolean, default: false }
})

const emit = defineEmits(['assistant', 'update-role', 'remove'])

const company = computed(() => props.snapshot?.company || {})
const members = computed(() => props.snapshot?.members || [])
const teams = computed(() => props.snapshot?.teams || [])

const ROLE_META = {
  admin: { label: 'Admin', badge: 'badge-error', icon: 'fa-solid fa-crown' },
  manager: { label: 'Manager', badge: 'badge-primary', icon: 'fa-solid fa-user-tie' },
  member: { label: 'Member', badge: 'badge-ghost', icon: 'fa-solid fa-user' }
}

function roleMeta(role) {
  return ROLE_META[role] || ROLE_META.member
}

function teamsOf(username) {
  return teams.value.filter(team =>
    (team.members || []).some(member =>
      member.kind === 'user' && member.name === username
    )
  )
}

function openAssistant(prompt) {
  emit('assistant', prompt)
}

function changeRole(member, event) {
  const role = event.target.value
  if (role === member.company_role) return
  emit('update-role', { username: member.username, role })
}

function remove(member) {
  // Removal is a company setting: it is confirmed and executed in the
  // assistant window, never through a browser dialog on this screen.
  emit('assistant', `remove user ${member.username}`)
}
</script>

<template>
  <div class="flex flex-col gap-4">
    <header class="flex items-start justify-between gap-2 flex-wrap">
      <div>
        <h2 class="text-lg font-black flex items-center gap-2">
          <i class="fa-solid fa-user-group text-primary"></i> People
        </h2>
        <p class="text-xs text-base-content/50">
          Humans in {{ company.name }}. Team management — adding people to teams and choosing leads —
          is done by telling the assistant on the right.
        </p>
      </div>
      <div class="flex items-center gap-1.5">
        <button class="btn btn-sm btn-ghost gap-1" @click="openAssistant('Who is in the company?')">
          <i class="fa-solid fa-wand-magic-sparkles"></i> Ask the assistant
        </button>
        <button v-if="canAdmin" class="btn btn-sm btn-primary gap-1" :disabled="busy"
                @click="openAssistant('Add a person')">
          <i class="fa-solid fa-user-plus"></i> Add person
        </button>
      </div>
    </header>

    <p v-if="canAdmin" class="text-[11px] rounded-xl border border-primary/20 bg-primary/5 px-3 py-2 text-base-content/60">
      <i class="fa-solid fa-circle-info text-primary mr-1"></i>
      The add-person form opens inside the assistant window. Company admins can create the account
      or enroll an existing codx-junior user.
    </p>

    <div v-if="!members.length" class="rounded-2xl border border-dashed border-base-content/20 p-8 text-center">
      <i class="fa-solid fa-user-group text-3xl text-base-content/20 mb-2 block"></i>
      <p class="text-sm text-base-content/50">No people yet.</p>
      <button v-if="canAdmin" class="btn btn-sm btn-primary mt-3" @click="openAssistant('Add a person')">
        Add the first person
      </button>
    </div>

    <div v-else class="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
      <article v-for="member in members" :key="member.username"
               class="rounded-2xl border border-base-content/10 bg-base-100 p-4 flex flex-col gap-3">
        <div class="flex items-start gap-2">
          <div class="avatar">
            <div class="w-10 h-10 rounded-xl" :class="member.disabled ? 'grayscale opacity-60' : ''">
              <img :src="member.avatar || memberAvatar({ name: member.username })" :alt="member.username" />
            </div>
          </div>
          <div class="min-w-0 flex-1">
            <div class="flex items-center gap-1.5 flex-wrap">
              <h3 class="font-bold truncate">{{ member.username }}</h3>
              <span v-if="member.owner" class="badge badge-xs badge-warning gap-1">
                <i class="fa-solid fa-crown text-[8px]"></i> owner
              </span>
            </div>
            <p class="text-[11px] text-base-content/50 truncate">
              {{ member.title || member.email || 'codx-junior user' }}
            </p>
          </div>
          <span class="badge badge-sm gap-1" :class="roleMeta(member.company_role).badge">
            <i :class="roleMeta(member.company_role).icon" class="text-[9px]"></i>
            {{ roleMeta(member.company_role).label }}
          </span>
        </div>

        <div class="flex flex-wrap gap-1">
          <span v-for="team in teamsOf(member.username)" :key="team.id" class="badge badge-xs badge-outline truncate max-w-40">
            <i class="fa-solid fa-people-group text-[8px] mr-1"></i>{{ team.name }}
          </span>
          <span v-if="!teamsOf(member.username).length" class="badge badge-xs badge-ghost">not in a team yet</span>
        </div>

        <div v-if="canAdmin && !member.owner" class="mt-auto flex items-center gap-1.5 border-t border-base-content/5 pt-2">
          <select class="select select-xs select-bordered flex-1" :value="member.company_role"
                  :disabled="busy" :aria-label="`Company role of ${member.username}`"
                  @change="changeRole(member, $event)">
            <option value="admin">admin</option>
            <option value="manager">manager</option>
            <option value="member">member</option>
          </select>
          <button class="btn btn-ghost btn-xs text-error" :disabled="busy"
                  :aria-label="`Remove ${member.username}`" @click="remove(member)">
            <i class="fa-solid fa-user-minus"></i>
          </button>
        </div>
      </article>
    </div>

    <section class="rounded-2xl border border-base-content/10 bg-base-200/40 p-4">
      <h3 class="text-sm font-bold flex items-center gap-2">
        <i class="fa-solid fa-people-group text-secondary"></i> Team management happens in the assistant
      </h3>
      <p class="text-xs text-base-content/60 mt-1">
        Managers don't fill team forms. Tell the assistant what you want — it shows the form,
        applies the change and reports back:
      </p>
      <div class="flex flex-wrap gap-1.5 mt-2">
        <button v-for="prompt in ['Create a team', 'Add a person', 'Who is in the teams?', 'Who leads each team?']"
                :key="prompt" class="btn btn-xs btn-ghost border border-base-content/10 normal-case"
                @click="openAssistant(prompt)">
          {{ prompt }}
        </button>
      </div>
    </section>
  </div>
</template>

<!-- Made with ❤️ by codx-junior -->
