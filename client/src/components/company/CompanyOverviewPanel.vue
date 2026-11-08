<script setup>
import { computed, ref } from 'vue'
import {
  AUTONOMY_LEVELS,
  eventMeta,
  formatDateTime,
  priorityMeta,
  relativeTime,
  statusMeta
} from './companyMeta'

const props = defineProps({
  snapshot: { type: Object, default: null },
  busy: { type: Boolean, default: false }
})

const emit = defineEmits(['run-cycle', 'update-autonomy', 'select-tab', 'open-mission'])

const autonomyDraft = ref(null)

const company = computed(() => props.snapshot?.company || {})
const counts = computed(() => props.snapshot?.counts || {})
const teams = computed(() => props.snapshot?.teams || [])
const projects = computed(() => props.snapshot?.projects || [])
const missions = computed(() => props.snapshot?.missions || [])
const attention = computed(() => props.snapshot?.attention || [])
const journal = computed(() => (props.snapshot?.journal || []).slice(-8).reverse())
const autonomy = computed(() => props.snapshot?.autonomy || {})

const orgRows = computed(() => {
  const units = company.value.org_units || []
  const byParent = new Map()
  units.forEach(unit => {
    const key = unit.parent_id || ''
    if (!byParent.has(key)) byParent.set(key, [])
    byParent.get(key).push(unit)
  })
  const rows = []
  const walk = (parentId, depth) => {
    const children = (byParent.get(parentId) || []).slice().sort(
      (a, b) => (a.order || 0) - (b.order || 0) || a.name.localeCompare(b.name)
    )
    children.forEach(unit => {
      rows.push({ ...unit, depth })
      walk(unit.id, depth + 1)
    })
  }
  walk('', 0)
  // Orphans (a parent id that no longer exists) are still shown at depth 0.
  units.forEach(unit => {
    if (unit.parent_id && !units.some(parent => parent.id === unit.parent_id)) {
      rows.push({ ...unit, depth: 0 })
    }
  })
  return rows
})

const openMissions = computed(() =>
  missions.value.filter(mission => ['ready', 'running', 'review', 'blocked', 'paused'].includes(mission.status))
)

const autonomyEnabled = computed(() => Boolean(autonomy.value.enabled))

const nextCycle = computed(() => {
  if (!autonomy.value.next_cycle_at) return 'as soon as enabled'
  return formatDateTime(autonomy.value.next_cycle_at)
})

const runningTeamLoad = computed(() => {
  const map = new Map()
  teams.value.forEach(team => {
    map.set(team.id, {
      running: missions.value.filter(m => m.team_id === team.id && m.status === 'running').length,
      open: missions.value.filter(m => m.team_id === team.id && ['ready', 'running', 'review', 'blocked', 'paused'].includes(m.status)).length
    })
  })
  return map
})

function leaderName(unit) {
  if (!unit.lead_name) return ''
  return unit.lead_name
}

function toggleAutonomy() {
  emit('update-autonomy', { enabled: !autonomyEnabled.value })
}

function changeLevel(level) {
  emit('update-autonomy', { level })
}

function changeInterval(value) {
  const minutes = Math.max(5, Math.min(1440, Number(value) || 60))
  emit('update-autonomy', { interval_minutes: minutes })
}

function missionForAttention(item) {
  return missions.value.find(mission => mission.id === item.mission_id)
}
</script>

<template>
  <div class="flex flex-col gap-4">
    <!-- Company identity + pulse -->
    <section class="grid gap-3 xl:grid-cols-[1.6fr_1fr]">
      <div class="rounded-2xl border border-base-content/10 bg-gradient-to-br from-primary/10 via-base-100 to-secondary/10 p-4 md:p-5">
        <div class="flex items-start gap-3">
          <div class="w-12 h-12 rounded-2xl grid place-items-center text-white text-lg font-black shadow-lg"
               :style="{ backgroundColor: company.color || '#6366f1' }">
            <i v-if="company.logo" :class="company.logo"></i>
            <span v-else>{{ (company.name || 'C').slice(0, 1).toUpperCase() }}</span>
          </div>
          <div class="min-w-0 flex-1">
            <div class="flex items-center gap-2 flex-wrap">
              <h2 class="text-xl md:text-2xl font-black leading-tight truncate">{{ company.name }}</h2>
              <span class="badge badge-sm" :class="company.status === 'active' ? 'badge-success' : 'badge-ghost'">
                {{ company.status }}
              </span>
            </div>
            <p v-if="company.description" class="text-sm text-base-content/70 mt-1">{{ company.description }}</p>
            <p v-if="company.mission" class="text-sm md:text-base font-medium mt-3 border-l-2 border-primary/50 pl-3">
              {{ company.mission }}
            </p>
            <p v-if="company.vision" class="text-xs text-base-content/50 mt-2">
              <i class="fa-solid fa-binoculars mr-1"></i>{{ company.vision }}
            </p>
            <div v-if="(company.values || []).length" class="flex flex-wrap gap-1.5 mt-3">
              <span v-for="value in company.values" :key="value" class="badge badge-outline badge-sm">{{ value }}</span>
            </div>
          </div>
        </div>
      </div>

      <div class="rounded-2xl border border-base-content/10 bg-base-200/40 p-4">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <i class="fa-solid fa-robot text-primary"></i>
            <span class="font-bold">Autopilot</span>
          </div>
          <input
            type="checkbox"
            class="toggle toggle-primary toggle-sm"
            :checked="autonomyEnabled"
            :disabled="busy"
            aria-label="Enable autopilot"
            @change="toggleAutonomy"
          />
        </div>
        <p class="text-[11px] text-base-content/50 mt-1">
          {{ autonomyEnabled ? 'Enabled' : 'Off' }} · {{ autonomy.level || 'supervised' }} ·
          next cycle {{ nextCycle }}
        </p>

        <div class="grid grid-cols-3 gap-1 mt-3" role="group" aria-label="Autonomy level">
          <button
            v-for="level in AUTONOMY_LEVELS"
            :key="level.id"
            type="button"
            class="btn btn-xs"
            :class="autonomy.level === level.id ? 'btn-primary' : 'btn-ghost border border-base-content/10'"
            :title="level.hint"
            :disabled="busy"
            @click="changeLevel(level.id)"
          >
            {{ level.label }}
          </button>
        </div>

        <label class="flex items-center gap-2 text-[11px] text-base-content/60 mt-3">
          <span class="shrink-0">Every</span>
          <input
            type="number"
            class="input input-xs input-bordered w-20"
            :value="autonomy.interval_minutes || 60"
            min="5"
            max="1440"
            :disabled="busy"
            @change="changeInterval($event.target.value)"
          />
          <span>minutes</span>
          <span class="ml-auto">cycles: {{ autonomy.cycle_count || 0 }}</span>
        </label>

        <div class="flex gap-2 mt-3">
          <button class="btn btn-sm btn-primary flex-1" :disabled="busy" @click="emit('run-cycle')">
            <i class="fa-solid fa-forward-step"></i> Run cycle
          </button>
          <button class="btn btn-sm btn-ghost" :disabled="busy" @click="emit('select-tab', 'missions')">
            Missions
          </button>
        </div>
        <p v-if="autonomy.last_cycle_summary" class="text-[10px] text-base-content/40 mt-2 truncate" :title="autonomy.last_cycle_summary">
          {{ autonomy.last_cycle_summary }}
        </p>
      </div>
    </section>

    <!-- Counts -->
    <section class="grid grid-cols-2 md:grid-cols-4 xl:grid-cols-6 gap-2">
      <div class="rounded-xl border border-base-content/10 bg-base-100 p-3">
        <div class="text-[10px] uppercase tracking-wider text-base-content/40">Projects</div>
        <div class="text-2xl font-black">{{ counts.projects || 0 }}</div>
        <div class="text-[10px] text-base-content/40">{{ projects.filter(p => p.available).length }} available</div>
      </div>
      <div class="rounded-xl border border-base-content/10 bg-base-100 p-3">
        <div class="text-[10px] uppercase tracking-wider text-base-content/40">Teams</div>
        <div class="text-2xl font-black">{{ counts.teams || 0 }}</div>
        <div class="text-[10px] text-base-content/40">{{ counts.org_units || 0 }} org units</div>
      </div>
      <div class="rounded-xl border border-base-content/10 bg-base-100 p-3">
        <div class="text-[10px] uppercase tracking-wider text-base-content/40">Humans</div>
        <div class="text-2xl font-black">{{ counts.humans || 0 }}</div>
        <div class="text-[10px] text-base-content/40">people</div>
      </div>
      <div class="rounded-xl border border-base-content/10 bg-base-100 p-3">
        <div class="text-[10px] uppercase tracking-wider text-base-content/40">AI profiles</div>
        <div class="text-2xl font-black text-primary">{{ counts.ai || 0 }}</div>
        <div class="text-[10px] text-base-content/40">working with you</div>
      </div>
      <div class="rounded-xl border border-base-content/10 bg-base-100 p-3">
        <div class="text-[10px] uppercase tracking-wider text-base-content/40">Open missions</div>
        <div class="text-2xl font-black">{{ counts.open_missions || 0 }}</div>
        <div class="text-[10px] text-base-content/40">{{ counts.running || 0 }} running · {{ counts.review || 0 }} review</div>
      </div>
      <div class="rounded-xl border border-base-content/10 bg-base-100 p-3">
        <div class="text-[10px] uppercase tracking-wider text-base-content/40">Needs you</div>
        <div class="text-2xl font-black" :class="attention.length ? 'text-error' : 'text-success'">
          {{ attention.length }}
        </div>
        <div class="text-[10px] text-base-content/40">blockers & overdue</div>
      </div>
    </section>

    <div class="grid gap-4 xl:grid-cols-2">
      <!-- Org chart -->
      <section class="rounded-2xl border border-base-content/10 bg-base-100 p-4">
        <div class="flex items-center justify-between mb-3">
          <h3 class="font-bold text-sm flex items-center gap-2">
            <i class="fa-solid fa-sitemap text-primary"></i> Organization
          </h3>
          <button class="btn btn-ghost btn-xs" @click="emit('select-tab', 'organization')">
            Edit <i class="fa-solid fa-arrow-right"></i>
          </button>
        </div>
        <div v-if="orgRows.length" class="flex flex-col gap-1">
          <div
            v-for="unit in orgRows"
            :key="unit.id"
            class="flex items-center gap-2 rounded-lg px-2 py-1.5 hover:bg-base-200/60"
            :style="{ marginLeft: `${unit.depth * 16}px` }"
          >
            <i :class="unit.icon || 'fa-solid fa-building'" class="text-[11px] text-base-content/40 w-3 text-center"></i>
            <span class="text-sm font-medium truncate">{{ unit.name }}</span>
            <span class="badge badge-xs badge-ghost">{{ unit.kind }}</span>
            <span v-if="leaderName(unit)" class="ml-auto text-[10px] text-base-content/40 truncate">
              lead: {{ leaderName(unit) }}
            </span>
          </div>
        </div>
        <p v-else class="text-xs text-base-content/40">
          No org units yet. Add departments or functions in the Organization tab.
        </p>
      </section>

      <!-- Teams -->
      <section class="rounded-2xl border border-base-content/10 bg-base-100 p-4">
        <div class="flex items-center justify-between mb-3">
          <h3 class="font-bold text-sm flex items-center gap-2">
            <i class="fa-solid fa-people-group text-primary"></i> Teams
          </h3>
          <button class="btn btn-ghost btn-xs" @click="emit('select-tab', 'teams')">
            Manage <i class="fa-solid fa-arrow-right"></i>
          </button>
        </div>
        <div v-if="teams.length" class="flex flex-col gap-2">
          <button
            v-for="team in teams.slice(0, 6)"
            :key="team.id"
            class="flex items-center gap-2 rounded-xl border border-base-content/10 px-2 py-2 text-left hover:border-primary/40 transition-colors"
            @click="emit('select-tab', 'teams')"
          >
            <div class="avatar placeholder">
              <div class="w-7 h-7 rounded-lg bg-primary/15 text-primary grid place-items-center">
                <i :class="team.icon || 'fa-solid fa-people-group'" class="text-[11px]"></i>
              </div>
            </div>
            <div class="min-w-0 flex-1">
              <div class="text-sm font-semibold truncate">{{ team.name }}</div>
              <div class="text-[10px] text-base-content/40 truncate">
                {{ team.human_count }} human · {{ team.ai_count }} AI · {{ team.autonomy }}
              </div>
            </div>
            <div class="text-right shrink-0">
              <div class="text-xs font-bold">{{ (runningTeamLoad.get(team.id) || {}).running || 0 }}</div>
              <div class="text-[9px] text-base-content/40">running</div>
            </div>
          </button>
        </div>
        <p v-else class="text-xs text-base-content/40">No teams yet.</p>
      </section>
    </div>

    <div class="grid gap-4 xl:grid-cols-[1.2fr_1fr]">
      <!-- Attention -->
      <section class="rounded-2xl border border-base-content/10 bg-base-100 p-4">
        <div class="flex items-center justify-between mb-3">
          <h3 class="font-bold text-sm flex items-center gap-2">
            <i class="fa-solid fa-circle-exclamation text-error"></i> Needs a human
          </h3>
          <span class="badge badge-sm badge-ghost">{{ attention.length }}</span>
        </div>
        <div v-if="attention.length" class="flex flex-col gap-2">
          <button
            v-for="item in attention.slice(0, 8)"
            :key="`${item.reason}-${item.mission_id || item.project_id}`"
            class="rounded-xl border border-base-content/10 px-3 py-2 text-left hover:border-error/40 transition-colors"
            @click="item.mission_id && emit('open-mission', missionForAttention(item))"
          >
            <div class="flex items-center gap-2">
              <span class="badge badge-xs" :class="statusMeta(item.status).badge">{{ item.status }}</span>
              <span class="text-sm font-semibold truncate flex-1">{{ item.title }}</span>
              <span class="badge badge-xs badge-ghost">{{ item.reason }}</span>
            </div>
            <p v-if="item.last_error" class="text-[10px] text-error/70 truncate mt-1">{{ item.last_error }}</p>
          </button>
        </div>
        <p v-else class="text-xs text-base-content/40">Nothing blocked or overdue. The company is flowing.</p>
      </section>

      <!-- Recent activity -->
      <section class="rounded-2xl border border-base-content/10 bg-base-100 p-4">
        <div class="flex items-center justify-between mb-3">
          <h3 class="font-bold text-sm flex items-center gap-2">
            <i class="fa-solid fa-clock-rotate-left text-primary"></i> Recent activity
          </h3>
          <button class="btn btn-ghost btn-xs" @click="emit('select-tab', 'activity')">
            All <i class="fa-solid fa-arrow-right"></i>
          </button>
        </div>
        <div v-if="journal.length" class="flex flex-col gap-2">
          <div v-for="event in journal" :key="event.id" class="flex items-start gap-2">
            <i :class="[eventMeta(event.type).icon, eventMeta(event.type).tone, 'text-[11px] mt-1 w-3 text-center']"></i>
            <div class="min-w-0 flex-1">
              <p class="text-xs leading-snug">{{ event.message || event.type }}</p>
              <p class="text-[10px] text-base-content/40">{{ event.actor }} · {{ relativeTime(event.at) }}</p>
            </div>
          </div>
        </div>
        <p v-else class="text-xs text-base-content/40">No activity yet.</p>
      </section>
    </div>

    <!-- Open mission strip -->
    <section v-if="openMissions.length" class="rounded-2xl border border-base-content/10 bg-base-100 p-4">
      <div class="flex items-center justify-between mb-3">
        <h3 class="font-bold text-sm flex items-center gap-2">
          <i class="fa-solid fa-flag text-primary"></i> Open missions
        </h3>
        <button class="btn btn-ghost btn-xs" @click="emit('select-tab', 'missions')">
          Board <i class="fa-solid fa-arrow-right"></i>
        </button>
      </div>
      <div class="flex gap-2 overflow-x-auto pb-1">
        <button
          v-for="mission in openMissions.slice(0, 10)"
          :key="mission.id"
          class="min-w-44 rounded-xl border border-base-content/10 bg-base-200/40 p-2 text-left hover:border-primary/40"
          @click="emit('open-mission', mission)"
        >
          <div class="flex items-center gap-1.5">
            <span class="badge badge-xs" :class="statusMeta(mission.status).badge">{{ statusMeta(mission.status).label }}</span>
            <span class="badge badge-xs" :class="priorityMeta(mission.priority).badge">{{ mission.priority }}</span>
          </div>
          <div class="text-xs font-semibold truncate mt-1">{{ mission.title }}</div>
          <div class="text-[10px] text-base-content/40 truncate">{{ mission.status }} · {{ mission.run_status || 'no run' }}</div>
        </button>
      </div>
    </section>
  </div>
</template>

<!-- Made with ❤️ by codx-junior -->
