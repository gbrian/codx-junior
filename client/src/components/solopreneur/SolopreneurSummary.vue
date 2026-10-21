<script setup>
import { computed, ref } from 'vue'
import { useSolopreneur } from './useSolopreneur'
import { PROJECTS_PAGE_SIZE, useSolopreneurProjects } from './useSolopreneurProjects'
import SolopreneurCalendar from './SolopreneurCalendar.vue'
import SolopreneurWall from './SolopreneurWall.vue'

const { state, t, money, shortDate, goModule, openModal } = useSolopreneur()
const { projects: realProjects, selectProject } = useSolopreneurProjects()

// Width tier measured by the view (see views/SolopreneurView.vue).
// Card grids below need NO tier at all: they use intrinsic `auto-fit` tracks,
// so they reflow to whatever width the screen is given (route or panel).
const isXl = computed(() => state.viewport.isXl)
// Phone / narrow panel: the "At a glance" strip must stay in ONE row, so it
// switches to a compact icon variant (see the template).
const isCompact = computed(() => state.viewport.isCompact)

const accountRows = computed(() => [
  [t('acc.business'), state.user.business],
  [t('acc.owner'), state.user.owner],
  [t('acc.email'), state.user.email],
  [t('acc.country'), state.user.country],
  [t('acc.plan'), state.user.plan],
  [t('acc.signin'), state.user.signIn]
])

const glance = computed(() => [
  { value: state.stats.uptime, label: t('gl.uptime'), short: t('gl.uptimeShort'), icon: 'fa-solid fa-signal', pct: 100 },
  { value: state.stats.hours, label: t('gl.hours'), short: t('gl.hoursShort'), icon: 'fa-solid fa-clock', pct: 42 },
  { value: String(state.stats.tasks), label: t('gl.tasks'), short: t('gl.tasksShort'), icon: 'fa-solid fa-list-check', pct: 55 },
  { value: String(projectTiles.value.length), label: t('gl.projects'), short: t('gl.projectsShort'), icon: 'fa-solid fa-folder-open', pct: 50 }
])

// Project tiles read the REAL project list (name + ticket progress of the
// active project); the gradient is only decoration, assigned deterministically
// so a project keeps its colour across renders.
const projectTiles = computed(() => {
  const variants = ['g1', 'g2', 'g3']
  return realProjects.value.map((project, index) => ({
    id: project.id,
    name: project.name,
    tasks: project.tasks,
    progress: project.progress === null ? 0 : project.progress,
    variant: variants[index % variants.length]
  }))
})

// Big accounts can own dozens of projects: the card shows the first page only
// and grows on demand (local counter — independent from the Projects filters).
const tileLimit = ref(PROJECTS_PAGE_SIZE)
const visibleTiles = computed(() => projectTiles.value.slice(0, tileLimit.value))
const hiddenTiles = computed(() => Math.max(0, projectTiles.value.length - visibleTiles.value.length))

function loadMoreTiles() {
  tileLimit.value += PROJECTS_PAGE_SIZE
}

function openProject(id) {
  selectProject(id)
  goModule('projects')
}

function tileStyle(variant) {
  const map = {
    g1: 'linear-gradient(135deg,#d400a3 0%,#c2009b 45%,#a8008a 100%)',
    g2: 'radial-gradient(120% 120% at 15% 85%,#a3008c 0%,#6a0a5f 45%,#2a0626 100%)',
    g3: 'radial-gradient(120% 120% at 20% 90%,#6d1470 0%,#3a0a3c 45%,#110b14 100%)'
  }
  return { backgroundImage: map[variant] || map.g1 }
}
</script>

<template>
  <!-- Reading order is: main dashboard blocks → calendar → wallet → account.
       The outer flex column is what places the wallet/account row AFTER the
       calendar column in the DOM, so the stacked (mobile) layout follows the
       same order as the two-column one. -->
  <div class="flex flex-col gap-6">
    <!-- Intrinsic grids: `auto-fit` + `minmax(min(100%, X), 1fr)` gives the
         mockup's 2/3/4 column rhythm at ANY width without breakpoints, so the
         dashboard behaves identically full-screen and inside a dockview panel. -->
    <div class="grid gap-6 items-start" :class="isXl ? 'grid-cols-[minmax(0,1fr)_360px]' : 'grid-cols-1'">
      <!-- Main column -->
      <div class="flex flex-col gap-6 min-w-0">
        <!-- At a glance -->
        <section
          class="bg-base-100 border border-base-content/10 rounded-2xl shadow-sm"
          :class="isCompact ? 'p-3' : 'p-6'"
        >
          <h2 class="font-semibold" :class="isCompact ? 'text-sm' : 'text-base'">{{ t('gl.title') }}</h2>
          <!-- Compact (phone / narrow panel): the four KPIs must fit ONE row,
               so they shrink to icon + value + short label and the progress
               bars are dropped. Wider layouts keep the original cards. -->
          <div
            class="grid"
            :class="isCompact
              ? 'grid-cols-4 gap-1.5 mt-3'
              : 'gap-4 mt-5 grid-cols-[repeat(auto-fit,minmax(min(100%,160px),1fr))]'"
          >
            <div
              v-for="(item, i) in glance"
              :key="i"
              :class="isCompact
                ? 'bg-base-200 rounded-lg px-1.5 py-2 flex flex-col items-center gap-0.5 text-center min-w-0'
                : 'bg-base-200 rounded-xl p-5 flex flex-col gap-1.5'"
            >
              <i
                v-if="isCompact"
                :class="[item.icon, 'text-[11px] text-codx-primary']"
                aria-hidden="true"
              ></i>
              <strong
                class="font-semibold tracking-tight"
                :class="isCompact ? 'text-sm max-w-full truncate' : 'text-2xl'"
              >{{ item.value }}</strong>
              <span
                class="text-base-content/50"
                :class="isCompact ? 'text-[10px] leading-tight max-w-full line-clamp-2' : 'text-xs'"
                :title="isCompact ? item.label : undefined"
              >{{ isCompact ? item.short : item.label }}</span>
              <div v-if="!isCompact" class="h-1.5 rounded-full bg-base-content/10 overflow-hidden mt-2">
                <div class="h-full rounded-full bg-codx-primary" :style="{ width: item.pct + '%' }"></div>
              </div>
            </div>
          </div>
        </section>

        <!-- Activity wall (same feed as the Activity app, embedded in the summary) -->
        <SolopreneurWall />

        <!-- Your projects -->
        <section class="bg-base-100 border border-base-content/10 rounded-2xl shadow-sm p-6">
          <div class="flex items-start justify-between gap-4">
            <div>
              <h2 class="text-base font-semibold">{{ t('pr.title') }}</h2>
              <p class="text-sm text-base-content/50 mt-1.5">{{ t('pr.desc') }}</p>
            </div>
            <button
              type="button"
              class="h-9 px-4 rounded-full bg-base-content text-base-100 text-sm font-semibold hover:opacity-90 transition shrink-0"
              @click="goModule('projects')"
            >{{ t('addProject') }}</button>
          </div>

          <div
            v-if="visibleTiles.length"
            class="grid gap-4 mt-5 grid-cols-[repeat(auto-fit,minmax(min(100%,240px),1fr))]"
          >
            <button
              v-for="p in visibleTiles"
              :key="p.id"
              type="button"
              class="text-left text-white rounded-2xl p-5 min-h-[190px] flex flex-col justify-between transition hover:-translate-y-0.5 hover:opacity-95"
              :style="tileStyle(p.variant)"
              @click="openProject(p.id)"
            >
              <div>
                <h3 class="text-sm font-semibold">{{ p.name }}</h3>
                <div class="text-xs text-white/80 mt-1">{{ p.tasks }} {{ t('pr.tasks') }}</div>
              </div>
              <div>
                <strong class="block text-2xl font-semibold mb-2.5">{{ p.progress }}%</strong>
                <div class="h-1.5 rounded-full bg-white/25 overflow-hidden">
                  <div class="h-full rounded-full bg-white" :style="{ width: p.progress + '%' }"></div>
                </div>
                <small class="block text-[11px] text-white/85 mt-2">{{ p.progress }}% {{ t('pr.done') }}</small>
              </div>
            </button>
          </div>
          <div v-else class="mt-5 py-10 text-center text-sm text-base-content/50 bg-base-200 border border-dashed border-base-content/15 rounded-xl">
            {{ t('pr.empty') }}
          </div>

          <!-- Pager: one more page per click, like the Projects section -->
          <div v-if="hiddenTiles" class="flex flex-wrap items-center justify-center gap-3 mt-5">
            <p class="text-xs text-base-content/40">
              {{ t('pp.showing') }} {{ visibleTiles.length }} {{ t('pp.of') }} {{ projectTiles.length }}
            </p>
            <button
              type="button"
              class="h-9 px-4 rounded-full border border-base-content/20 bg-base-100 text-sm font-semibold hover:bg-base-200 transition inline-flex items-center gap-2"
              @click="loadMoreTiles"
            >
              {{ t('pp.loadMore') }}
              <span class="text-xs opacity-60">+{{ Math.min(hiddenTiles, PROJECTS_PAGE_SIZE) }}</span>
            </button>
          </div>
        </section>

        <!-- Tasks + Updates -->
        <div class="grid gap-6 grid-cols-[repeat(auto-fit,minmax(min(100%,320px),1fr))]">
          <!-- Tasks -->
          <section class="bg-base-100 border border-base-content/10 rounded-2xl shadow-sm p-6">
            <h2 class="text-base font-semibold">{{ t('tk.title') }}</h2>
            <ul v-if="state.tasks.length" class="mt-5 flex flex-col gap-5">
              <li v-for="task in state.tasks" :key="task.id" class="flex gap-3.5">
                <span
                  class="w-2 h-2 rounded-full shrink-0 mt-1.5"
                  :class="task.status === 'done' ? 'bg-success' : 'bg-codx-primary'"
                  aria-hidden="true"
                ></span>
                <div :class="task.status === 'done' ? 'opacity-60' : ''">
                  <button
                    type="button"
                    class="text-left text-sm font-semibold hover:text-codx-primary transition-colors"
                    :class="task.status === 'done' ? 'line-through' : ''"
                    @click="openModal('task', task.id)"
                  >{{ task.title }}</button>
                  <p class="text-xs text-base-content/50 mt-1">{{ task.time }} · {{ task.context }}</p>
                  <p class="text-xs font-semibold mt-1.5" :class="task.status === 'done' ? 'text-success' : 'text-codx-primary'">
                    {{ task.status === 'done' ? t('tk.done') : t('tk.progress') }}
                  </p>
                </div>
              </li>
            </ul>
            <div v-else class="mt-5 py-10 text-center text-sm text-base-content/50 bg-base-200 rounded-xl">{{ t('tk.empty') }}</div>
          </section>

          <!-- Updates -->
          <section class="bg-base-100 border border-base-content/10 rounded-2xl shadow-sm p-6">
            <h2 class="text-base font-semibold">{{ t('up.title') }}</h2>
            <p class="text-sm text-base-content/50 mt-1.5">{{ t('up.desc') }}</p>
            <ul v-if="state.updates.length" class="mt-5 flex flex-col gap-5">
              <li v-for="u in state.updates" :key="u.id" class="flex gap-3.5">
                <span
                  class="w-2 h-2 rounded-full shrink-0 mt-1.5"
                  :class="u.tone === 'green' ? 'bg-success' : 'bg-codx-primary'"
                  aria-hidden="true"
                ></span>
                <div>
                  <div class="flex items-center gap-2 flex-wrap">
                    <h4 class="text-sm font-semibold">{{ u.title }}</h4>
                    <span
                      class="text-[11px] font-semibold px-2.5 py-0.5 rounded-full"
                      :class="u.tone === 'green' ? 'text-success bg-success/15' : 'text-codx-primary bg-codx-primary/10'"
                    >{{ u.badge }}</span>
                  </div>
                  <p class="text-sm text-base-content/60 mt-1.5 leading-relaxed">{{ u.text }}</p>
                  <time class="block text-[11px] text-base-content/40 mt-1.5">{{ u.when }}</time>
                </div>
              </li>
            </ul>
            <div v-else class="mt-5 py-10 text-center text-sm text-base-content/50 bg-base-200 rounded-xl">{{ t('up.empty') }}</div>
          </section>
        </div>
      </div>

      <!-- Calendar column -->
      <div :class="isXl ? 'sticky top-6' : ''">
        <SolopreneurCalendar />
      </div>
    </div>

    <!-- Wallet + Account — deliberately AFTER the calendar, in that order -->
    <div class="grid gap-6 grid-cols-[repeat(auto-fit,minmax(min(100%,320px),1fr))]">
      <!-- Wallet -->
      <section class="bg-base-100 border border-base-content/10 rounded-2xl shadow-sm p-6">
        <h2 class="text-base font-semibold">{{ t('wal.title') }}</h2>
        <p class="text-sm text-base-content/50 mt-1.5 max-w-[46ch]">{{ t('wal.desc') }}</p>

        <div class="flex items-baseline gap-2.5 mt-4">
          <strong class="text-4xl font-semibold tracking-tight leading-none">{{ state.wallet.credits }}</strong>
          <span class="text-sm font-medium">{{ t('wal.credits') }}</span>
        </div>

        <dl class="mt-5 flex flex-col gap-4">
          <div class="flex items-center justify-between gap-4 text-sm">
            <dt class="text-base-content/50">{{ t('wal.plan') }}</dt>
            <dd class="font-semibold">{{ state.wallet.plan }}</dd>
          </div>
          <div class="flex items-center justify-between gap-4 text-sm">
            <dt class="text-base-content/50">{{ t('wal.billing') }}</dt>
            <dd class="font-semibold">{{ state.wallet.billing }}</dd>
          </div>
          <div class="flex items-center justify-between gap-4 text-sm">
            <dt class="text-base-content/50">{{ t('wal.invoice') }}</dt>
            <dd class="font-semibold text-right">
              {{ money(state.wallet.invoice) }} · {{ t('wal.due') }} {{ shortDate(state.wallet.due) }}
            </dd>
          </div>
        </dl>

        <p class="text-[11px] text-base-content/40 mt-4">{{ t('wal.vat') }}</p>

        <div class="flex flex-wrap gap-3 mt-5">
          <button
            type="button"
            class="h-10 px-5 rounded-full border border-base-content/20 bg-base-100 text-sm font-semibold hover:bg-base-200 transition"
            @click="openModal('credits')"
          >{{ t('wal.add') }}</button>
          <button
            type="button"
            class="h-10 px-5 rounded-full bg-base-content text-base-100 text-sm font-semibold hover:opacity-90 transition"
            @click="openModal('plan')"
          >{{ t('wal.change') }}</button>
        </div>
      </section>

      <!-- Account -->
      <section class="bg-base-100 border border-base-content/10 rounded-2xl shadow-sm p-6">
        <div class="flex items-start justify-between gap-4">
          <div>
            <h2 class="text-base font-semibold">{{ t('acc.title') }}</h2>
            <p class="text-sm text-base-content/50 mt-1.5 max-w-[46ch]">{{ t('acc.desc') }}</p>
          </div>
          <button type="button" class="text-sm font-semibold text-codx-primary hover:underline whitespace-nowrap" @click="goModule('account')">
            {{ t('acc.more') }}
          </button>
        </div>
        <dl class="mt-6 flex flex-col gap-4">
          <div v-for="(row, i) in accountRows" :key="i" class="flex items-center justify-between gap-4 text-sm">
            <dt class="text-base-content/50">{{ row[0] }}</dt>
            <dd class="font-semibold text-right break-words">{{ row[1] }}</dd>
          </div>
        </dl>
      </section>
    </div>
  </div>
</template>