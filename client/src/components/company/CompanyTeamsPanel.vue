<script setup>
import { computed } from 'vue'
import { memberAvatar, memberKey } from './companyMeta'

/**
 * Teams view of the company shell.
 *
 * Team management is intentionally NOT a dialog in this panel: managers
 * instruct the always-present codx-junior assistant, which renders the roster
 * form in its own window and applies the change through the company API
 * (see CompanyAssistant.vue + company/assistant.py).
 */
const props = defineProps({
  snapshot: { type: Object, default: null },
  references: { type: Object, default: () => ({ users: [], profiles: [] }) },
  busy: { type: Boolean, default: false },
  canManage: { type: Boolean, default: false }
})

const emit = defineEmits(['assistant'])

const company = computed(() => props.snapshot?.company || {})
const teams = computed(() => props.snapshot?.teams || [])
const projects = computed(() => props.snapshot?.projects || [])
const missions = computed(() => props.snapshot?.missions || [])
const units = computed(() => company.value.org_units || [])

function orgName(team) {
  return units.value.find(unit => unit.id === team.org_unit_id)?.name || ''
}

function projectName(projectId) {
  const project = projects.value.find(item => item.project_id === projectId)
  return project?.name || project?.project_id || projectId
}

function teamMissions(teamId) {
  return missions.value.filter(mission => mission.team_id === teamId)
}

function ask(prompt) {
  emit('assistant', prompt)
}

function describeTeam(team) {
  ask(`Describe the team ${team.name}: who is in it and what is it working on?`)
}
</script>

<template>
  <div class="flex flex-col gap-4">
    <header class="flex items-start justify-between gap-2 flex-wrap">
      <div>
        <h2 class="text-lg font-black flex items-center gap-2">
          <i class="fa-solid fa-people-group text-primary"></i> Teams
        </h2>
        <p class="text-xs text-base-content/50">
          Hybrid teams of humans and AI profiles. Managers change them by telling the assistant.
        </p>
      </div>
      <div class="flex items-center gap-1.5">
        <button class="btn btn-sm btn-ghost gap-1" @click="ask('Who is in the teams?')">
          <i class="fa-solid fa-wand-magic-sparkles"></i> Ask the assistant
        </button>
        <button v-if="canManage" class="btn btn-sm btn-primary gap-1" :disabled="busy"
                @click="ask('Create a team')">
          <i class="fa-solid fa-plus"></i> New team
        </button>
      </div>
    </header>

    <p v-if="canManage" class="text-[11px] rounded-xl border border-primary/20 bg-primary/5 px-3 py-2 text-base-content/60">
      <i class="fa-solid fa-circle-info text-primary mr-1"></i>
      The team form opens inside the assistant window. Try “create a team”, “add alice to Platform”
      or “make bob lead of Platform”.
    </p>

    <div v-if="!teams.length" class="rounded-2xl border border-dashed border-base-content/20 p-8 text-center">
      <i class="fa-solid fa-people-group text-3xl text-base-content/20 mb-2 block"></i>
      <p class="text-sm text-base-content/50">No teams yet.</p>
      <button v-if="canManage" class="btn btn-sm btn-primary mt-3" @click="ask('Create a team')">
        Create the first hybrid team
      </button>
      <p v-else class="text-[11px] text-base-content/40 mt-2">
        Ask a manager or company admin to create the first team.
      </p>
    </div>

    <div v-else class="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
      <article v-for="team in teams" :key="team.id"
               class="rounded-2xl border border-base-content/10 bg-base-100 p-4 flex flex-col gap-3 hover:border-primary/30 transition-colors">
        <div class="flex items-start gap-2">
          <div class="w-10 h-10 rounded-xl grid place-items-center bg-primary/15 text-primary shrink-0">
            <i :class="team.icon || 'fa-solid fa-people-group'"></i>
          </div>
          <div class="min-w-0 flex-1">
            <div class="flex items-center gap-1.5 flex-wrap">
              <h3 class="font-bold truncate">{{ team.name }}</h3>
              <span class="badge badge-xs"
                    :class="team.autonomy === 'autonomous' ? 'badge-success' : team.autonomy === 'manual' ? 'badge-ghost' : 'badge-info'">
                {{ team.autonomy }}
              </span>
            </div>
            <p class="text-[11px] text-base-content/50 truncate">
              {{ orgName(team) || 'Unassigned org unit' }}
            </p>
          </div>
          <button class="btn btn-ghost btn-xs btn-square" title="Ask about this team"
                  :aria-label="`Ask about ${team.name}`" @click="describeTeam(team)">
            <i class="fa-solid fa-wand-magic-sparkles"></i>
          </button>
        </div>

        <p v-if="team.description" class="text-xs text-base-content/60 line-clamp-2">{{ team.description }}</p>

        <div class="flex items-center gap-2">
          <div class="avatar-group -space-x-2">
            <div v-for="member in (team.members || []).slice(0, 5)" :key="memberKey(member)"
                 class="avatar border-2 border-base-100"
                 :title="`${member.name} · ${member.kind}${member.role ? ' · ' + member.role : ''}`">
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
  </div>
</template>

<!-- Made with ❤️ by codx-junior -->
