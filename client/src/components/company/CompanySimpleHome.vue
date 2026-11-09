<script setup>
import { computed } from 'vue'
import { memberAvatar, relativeTime, statusMeta } from './companyMeta'

/**
 * The ONE company screen.
 *
 * Managers don't need to learn a navigation tree: they see a friendly summary,
 * four obvious actions and the always-present assistant. Everything else
 * (teams, people, projects, missions, settings) is done by talking to
 * codx-junior.
 */
const props = defineProps({
  snapshot: { type: Object, default: null },
  canManage: { type: Boolean, default: false },
  canAdmin: { type: Boolean, default: false },
  busy: { type: Boolean, default: false }
})

const emit = defineEmits(['assistant'])

const company = computed(() => props.snapshot?.company || {})
const counts = computed(() => props.snapshot?.counts || {})
const members = computed(() => props.snapshot?.members || [])
const teams = computed(() => props.snapshot?.teams || [])
const projects = computed(() => props.snapshot?.projects || [])
const missions = computed(() => props.snapshot?.missions || [])
const journal = computed(() => (props.snapshot?.journal || []).slice(-4).reverse())
const budget = computed(() => props.snapshot?.budget || {})
const budgetProgress = computed(() => {
  const limit = Number(budget.value.daily_limit_cxjcoins || 0)
  if (limit <= 0) return 0
  return Math.min(100, Math.round((Number(budget.value.spent_today_cxjcoins || 0) / limit) * 100))
})
const showBudget = computed(() =>
  Number(budget.value.daily_limit_cxjcoins || 0) > 0
  || Number(budget.value.spent_total_cxjcoins || 0) > 0
)

const reviewMissions = computed(() =>
  missions.value.filter(mission => mission.status === 'review')
)
const runningMissions = computed(() =>
  missions.value.filter(mission => mission.status === 'running')
)
const approvalMissions = computed(() =>
  missions.value.filter(
    mission => ['pending', 'denied'].includes(mission.approval_status)
      && ['ready', 'blocked'].includes(mission.status)
  )
)

const firstAttention = computed(() =>
  reviewMissions.value[0] || approvalMissions.value[0] || runningMissions.value[0] || null
)

const simpleGreeting = computed(() => {
  const hour = new Date().getHours()
  if (hour < 12) return 'Good morning'
  if (hour < 18) return 'Good afternoon'
  return 'Good evening'
})

function ask(prompt) {
  emit('assistant', prompt)
}

function askAboutMission(mission) {
  if (!mission) return
  if (['pending', 'denied'].includes(mission.approval_status)) {
    ask('Show pending approvals')
    return
  }
  if (mission.status === 'review') {
    ask(`Review mission ${mission.title}`)
    return
  }
  ask(`What is happening with ${mission.title}?`)
}

function missionStatus(mission) {
  return statusMeta(mission.status)
}

function teamLead(team) {
  return team.lead_name || 'No lead yet'
}

function projectName(project) {
  return project.name || project.project_id
}
</script>

<template>
  <div class="flex flex-col gap-4 max-w-5xl mx-auto">
    <!-- Welcome + the four things a manager does most -->
    <section class="rounded-3xl border border-base-content/10 bg-gradient-to-br from-primary/10 via-base-100 to-secondary/10 p-5 md:p-7">
      <div class="flex items-start gap-4">
        <div class="w-14 h-14 rounded-2xl grid place-items-center text-white text-xl font-black shrink-0 shadow-lg"
             :style="{ backgroundColor: company.color || '#6366f1' }">
          <span v-if="!company.logo">{{ (company.name || 'C').slice(0, 1).toUpperCase() }}</span>
          <i v-else :class="company.logo"></i>
        </div>
        <div class="min-w-0 flex-1">
          <p class="text-xs font-semibold uppercase tracking-wider text-primary/70">{{ simpleGreeting }}</p>
          <h2 class="text-xl md:text-2xl font-black leading-tight">
            {{ company.name }}
          </h2>
          <p v-if="company.mission" class="text-sm text-base-content/60 mt-1">{{ company.mission }}</p>
          <p v-else class="text-sm text-base-content/60 mt-1">
            This is your company home. Tell codx-junior what you need and it will do the rest.
          </p>
          <div v-if="canManage" class="flex flex-wrap gap-1.5 mt-2.5">
            <button v-for="need in ['I need a developer', 'I need an IT team', 'I need a QA']"
                    :key="need" type="button"
                    class="btn btn-xs btn-ghost border border-base-content/15 normal-case"
                    @click="ask(need)">
              <i class="fa-solid fa-wand-magic-sparkles text-primary text-[10px]"></i>
              {{ need }}
            </button>
          </div>
        </div>
      </div>

      <div class="grid grid-cols-2 lg:grid-cols-4 gap-2.5 mt-5">
        <button v-if="canAdmin" type="button"
                class="rounded-2xl border border-primary/20 bg-base-100 p-3.5 text-left hover:border-primary hover:shadow-md transition-all"
                @click="ask('Add a person')">
          <span class="w-9 h-9 rounded-xl grid place-items-center bg-primary/15 text-primary mb-2">
            <i class="fa-solid fa-user-plus"></i>
          </span>
          <span class="block text-sm font-bold">Add a person</span>
          <span class="block text-[11px] text-base-content/50 mt-0.5">Give someone access to the company</span>
        </button>

        <button v-if="canManage" type="button"
                class="rounded-2xl border border-secondary/20 bg-base-100 p-3.5 text-left hover:border-secondary hover:shadow-md transition-all"
                @click="ask('I need a team')">
          <span class="w-9 h-9 rounded-xl grid place-items-center bg-secondary/15 text-secondary mb-2">
            <i class="fa-solid fa-people-group"></i>
          </span>
          <span class="block text-sm font-bold">Build my team</span>
          <span class="block text-[11px] text-base-content/50 mt-0.5">Tell me what you need and I'll choose the profiles</span>
        </button>

        <button v-if="canManage" type="button"
                class="rounded-2xl border border-accent/20 bg-base-100 p-3.5 text-left hover:border-accent hover:shadow-md transition-all"
                @click="ask('Create a mission')">
          <span class="w-9 h-9 rounded-xl grid place-items-center bg-accent/15 text-accent mb-2">
            <i class="fa-solid fa-flag"></i>
          </span>
          <span class="block text-sm font-bold">Start a mission</span>
          <span class="block text-[11px] text-base-content/50 mt-0.5">Ask the AI team to achieve an outcome</span>
        </button>

        <button type="button"
                class="rounded-2xl border border-base-content/10 bg-base-100 p-3.5 text-left hover:border-primary hover:shadow-md transition-all"
                @click="ask('What needs my attention?')">
          <span class="w-9 h-9 rounded-xl grid place-items-center bg-info/15 text-info mb-2">
            <i class="fa-solid fa-wand-magic-sparkles"></i>
          </span>
          <span class="block text-sm font-bold">Ask codx-junior</span>
          <span class="block text-[11px] text-base-content/50 mt-0.5">“What needs my attention?”</span>
        </button>
      </div>
    </section>

    <!-- Simple numbers -->
    <section class="grid grid-cols-2 md:grid-cols-4 gap-2.5">
      <button type="button" class="rounded-2xl border border-base-content/10 bg-base-100 p-3 text-left hover:border-primary/40"
              @click="ask('Who is in the company?')">
        <div class="text-2xl font-black">{{ members.length }}</div>
        <div class="text-[11px] uppercase tracking-wide text-base-content/45">People</div>
      </button>
      <button type="button" class="rounded-2xl border border-base-content/10 bg-base-100 p-3 text-left hover:border-primary/40"
              @click="ask('Show teams')">
        <div class="text-2xl font-black">{{ counts.teams || 0 }}</div>
        <div class="text-[11px] uppercase tracking-wide text-base-content/45">Teams</div>
      </button>
      <button type="button" class="rounded-2xl border border-base-content/10 bg-base-100 p-3 text-left hover:border-primary/40"
              @click="ask('Show projects')">
        <div class="text-2xl font-black">{{ counts.projects || 0 }}</div>
        <div class="text-[11px] uppercase tracking-wide text-base-content/45">Projects</div>
        <div v-if="counts.child_projects" class="text-[10px] text-base-content/35">
          + {{ counts.child_projects }} child
        </div>
      </button>
      <button type="button" class="rounded-2xl border border-base-content/10 bg-base-100 p-3 text-left hover:border-primary/40"
              @click="ask('What needs my attention?')">
        <div class="text-2xl font-black" :class="reviewMissions.length ? 'text-warning' : ''">
          {{ counts.open_missions || 0 }}
        </div>
        <div class="text-[11px] uppercase tracking-wide text-base-content/45">Open missions</div>
      </button>
    </section>

    <!-- Budget (only when a limit exists or money has been spent) -->
    <section v-if="showBudget" class="rounded-2xl border border-base-content/10 bg-base-100 p-3.5">
      <div class="flex items-center gap-2">
        <span class="w-8 h-8 rounded-lg grid place-items-center bg-warning/15 text-warning">
          <i class="fa-solid fa-coins"></i>
        </span>
        <div class="min-w-0 flex-1">
          <div class="text-xs font-bold">AI budget</div>
          <div class="text-[10px] text-base-content/50">
            {{ budget.spent_total_cxjcoins || 0 }} cxj spent in total
            <template v-if="Number(budget.daily_limit_cxjcoins || 0) > 0">
              · {{ budget.spent_today_cxjcoins || 0 }} / {{ budget.daily_limit_cxjcoins }} today
            </template>
          </div>
        </div>
        <span v-if="budget.over_daily_budget" class="badge badge-xs badge-error">over budget</span>
        <span v-else-if="Number(budget.daily_limit_cxjcoins || 0) > 0" class="badge badge-xs badge-ghost">
          {{ budget.remaining_today_cxjcoins }} left
        </span>
        <button type="button" class="btn btn-ghost btn-xs" @click="ask('How is our budget?')">
          Details
        </button>
      </div>
      <progress
        v-if="Number(budget.daily_limit_cxjcoins || 0) > 0"
        class="progress w-full h-1.5 mt-2"
        :class="budget.over_daily_budget ? 'progress-error' : 'progress-warning'"
        :value="budgetProgress"
        max="100"
      ></progress>
    </section>

    <!-- What needs a human -->
    <section v-if="firstAttention" class="rounded-2xl border border-warning/25 bg-warning/5 p-4">
      <div class="flex items-start justify-between gap-3">
        <div class="min-w-0">
          <h3 class="text-sm font-bold flex items-center gap-2">
            <i class="fa-solid fa-bell text-warning"></i>
            Needs your attention
          </h3>
          <p class="text-xs text-base-content/60 mt-1">
            <span class="badge badge-xs mr-1" :class="missionStatus(firstAttention).badge">
              {{ missionStatus(firstAttention).label }}
            </span>
            {{ firstAttention.title }}
          </p>
          <p v-if="firstAttention.status === 'review'" class="text-[11px] text-base-content/45 mt-1">
            The AI team finished this mission. Do you accept the result?
          </p>
          <p v-else-if="['pending', 'denied'].includes(firstAttention.approval_status)"
             class="text-[11px] text-base-content/45 mt-1">
            This mission needs your approval before it can run.
          </p>
        </div>
        <div class="flex flex-col gap-1.5 shrink-0">
          <button type="button" class="btn btn-warning btn-sm"
                  @click="askAboutMission(firstAttention)">
            {{
              ['pending', 'denied'].includes(firstAttention.approval_status)
                ? 'Review approval'
                : (firstAttention.status === 'review' ? 'Review it' : 'Ask about it')
            }}
          </button>
          <button type="button" class="btn btn-ghost btn-xs"
                  @click="ask('What needs my attention?')">See all</button>
        </div>
      </div>
    </section>

    <div class="grid gap-3 lg:grid-cols-2">
      <!-- Teams, in plain language -->
      <section class="rounded-2xl border border-base-content/10 bg-base-100 p-4">
        <div class="flex items-center justify-between gap-2">
          <h3 class="text-sm font-bold flex items-center gap-2">
            <i class="fa-solid fa-people-group text-secondary"></i> Teams
          </h3>
          <button v-if="canManage" type="button" class="btn btn-ghost btn-xs gap-1"
                  @click="ask('I need a team')">
            <i class="fa-solid fa-plus"></i> New
          </button>
        </div>
        <div v-if="!teams.length" class="text-xs text-base-content/50 mt-3">
          No teams yet. codx-junior can create one with you in a few questions.
        </div>
        <ul v-else class="mt-2 divide-y divide-base-content/5">
          <li v-for="team in teams.slice(0, 5)" :key="team.id" class="py-2 flex items-center gap-2">
            <span class="w-8 h-8 rounded-lg grid place-items-center bg-secondary/10 text-secondary shrink-0">
              <i :class="team.icon || 'fa-solid fa-people-group'"></i>
            </span>
            <span class="min-w-0 flex-1">
              <span class="block text-xs font-semibold truncate">{{ team.name }}</span>
              <span class="block text-[10px] text-base-content/45 truncate">
                {{ teamLead(team) }} · {{ team.human_count }} people · {{ team.ai_count }} AI
              </span>
            </span>
            <button type="button" class="btn btn-ghost btn-xs" @click="ask(`Who is in ${team.name}?`)">
              <i class="fa-solid fa-arrow-right"></i>
            </button>
          </li>
        </ul>
      </section>

      <!-- People, in plain language -->
      <section class="rounded-2xl border border-base-content/10 bg-base-100 p-4">
        <div class="flex items-center justify-between gap-2">
          <h3 class="text-sm font-bold flex items-center gap-2">
            <i class="fa-solid fa-user-group text-primary"></i> People
          </h3>
          <button v-if="canAdmin" type="button" class="btn btn-ghost btn-xs gap-1"
                  @click="ask('Add a person')">
            <i class="fa-solid fa-user-plus"></i> Add
          </button>
        </div>
        <div v-if="!members.length" class="text-xs text-base-content/50 mt-3">
          No people yet. Add the first person — codx-junior will walk you through it.
        </div>
        <ul v-else class="mt-2 divide-y divide-base-content/5">
          <li v-for="member in members.slice(0, 5)" :key="member.username" class="py-2 flex items-center gap-2">
            <span class="avatar">
              <span class="w-8 h-8 rounded-lg">
                <img :src="member.avatar || memberAvatar({ name: member.username })" :alt="member.username" />
              </span>
            </span>
            <span class="min-w-0 flex-1">
              <span class="block text-xs font-semibold truncate">{{ member.username }}</span>
              <span class="block text-[10px] text-base-content/45 truncate">
                {{ member.title || member.email || 'Company member' }}
              </span>
            </span>
            <span class="badge badge-xs" :class="member.company_role === 'admin' ? 'badge-error' : member.company_role === 'manager' ? 'badge-primary' : 'badge-ghost'">
              {{ member.company_role }}
            </span>
          </li>
        </ul>
      </section>
    </div>

    <!-- Projects / recent activity -->
    <div class="grid gap-3 lg:grid-cols-2">
      <section class="rounded-2xl border border-base-content/10 bg-base-100 p-4">
        <div class="flex items-center justify-between gap-2">
          <h3 class="text-sm font-bold flex items-center gap-2">
            <i class="fa-solid fa-cubes text-accent"></i> Projects
          </h3>
          <div v-if="canManage" class="flex items-center gap-1">
            <button type="button" class="btn btn-ghost btn-xs gap-1" @click="ask('Link a project')">
              <i class="fa-solid fa-link text-[10px]"></i> Add
            </button>
            <button type="button" class="btn btn-ghost btn-xs gap-1" @click="ask('Create a new project')">
              <i class="fa-solid fa-plus text-[10px]"></i> New
            </button>
          </div>
        </div>
        <div v-if="!projects.length" class="text-xs text-base-content/50 mt-3">
          No projects linked yet. Ask codx-junior to show or link projects.
        </div>
        <ul v-else class="mt-2 divide-y divide-base-content/5">
          <li v-for="project in projects.slice(0, 4)" :key="project.project_id" class="py-2">
            <div class="flex items-center gap-2">
              <i class="fa-solid fa-cube text-[10px] text-base-content/30"></i>
              <span class="text-xs font-semibold truncate flex-1">{{ projectName(project) }}</span>
              <span v-if="project.children?.length" class="badge badge-xs badge-ghost">
                {{ project.children.length }} child
              </span>
              <span v-else class="text-[10px] text-base-content/40">{{ project.role || 'linked' }}</span>
            </div>
            <div v-if="project.children?.length" class="pl-5 mt-1 space-y-0.5">
              <div v-for="child in project.children.slice(0, 3)" :key="child.project_id"
                   class="text-[10px] text-base-content/45 truncate">
                ↳ {{ child.project_name }}
              </div>
            </div>
          </li>
        </ul>
      </section>

      <section class="rounded-2xl border border-base-content/10 bg-base-100 p-4">
        <h3 class="text-sm font-bold flex items-center gap-2">
          <i class="fa-solid fa-clock-rotate-left text-base-content/40"></i> Latest activity
        </h3>
        <div v-if="!journal.length" class="text-xs text-base-content/50 mt-3">
          Nothing has happened yet.
        </div>
        <ul v-else class="mt-2 space-y-1.5">
          <li v-for="event in journal" :key="event.id" class="text-[11px] text-base-content/60 flex gap-2">
            <span class="w-1.5 h-1.5 rounded-full bg-primary/50 mt-1.5 shrink-0"></span>
            <span class="min-w-0">
              {{ event.message }}
              <span class="text-base-content/30">· {{ relativeTime(event.at) }}</span>
            </span>
          </li>
        </ul>
      </section>
    </div>

    <p class="text-center text-[11px] text-base-content/35 pb-2">
      <i class="fa-solid fa-wand-magic-sparkles text-primary/50 mr-1"></i>
      You can run the whole company by talking to codx-junior on the right.
    </p>
  </div>
</template>

<!-- Made with ❤️ by codx-junior -->
