<script setup>
import { computed, onMounted, ref } from 'vue'
import { useSolopreneur } from './useSolopreneur'
import { PROJECTS_PAGE_SIZE, useSolopreneurProjects } from './useSolopreneurProjects'

const { t, goModule } = useSolopreneur()

const {
  ui,
  filteredProjects,
  visibleProjects,
  hiddenProjects,
  hasMoreProjects,
  searchableProjects,
  loadMoreProjects,
  filterCounts,
  selectedProject,
  statusRows,
  recentChats,
  statusLabel,
  countSprintTasks,
  countSprintDone,
  relative,
  ensureReady,
  selectProject,
  selectProjectByName,
  backToList,
  setTab,
  setFilter,
  setQuery,
  openFullSettings,
  createProject,
  openSprintBoard,
  showTicketsOnHold
} = useSolopreneurProjects()

// ── filters (projects list) ─────────────────────────────────────────────────
const chips = computed(() => [
  { value: 'all', label: t('pp.all'), count: filterCounts.value.all },
  { value: 'active', label: t('pp.active'), count: filterCounts.value.active },
  { value: 'sprints', label: t('pp.withSprints'), count: filterCounts.value.sprints }
])

// The active project's "on hold" tasks are the real "needs you" signal.
const holdCount = computed(() => {
  const active = filteredProjects.value.find(p => p.active)
  return active ? active.onhold : 0
})

const tabs = computed(() => [
  { value: 'overview', label: t('pp.tabOverview') },
  { value: 'sprints', label: t('pp.tabSprints') },
  { value: 'settings', label: t('pp.tabSettings') }
])

function projectTypeLabel(board) {
  return board.type === 'sprint' ? t('pp.typeSprint') : t('pp.typeKanban')
}

function statusPillClass(active) {
  return active ? 'text-success bg-success/15' : 'text-base-content/60 bg-base-content/10'
}

async function openSettings(id) {
  await selectProject(id)
  setTab('settings')
}

// ── new project dialog ──────────────────────────────────────────────────────
const showNewProject = ref(false)
const newName = ref('')
const newRepo = ref('')

function openNewProject() {
  newName.value = ''
  newRepo.value = ''
  ui.errors = {}
  showNewProject.value = true
}

function closeNewProject() {
  showNewProject.value = false
  ui.errors = {}
}

async function submitProject() {
  const created = await createProject({ name: newName.value, repo: newRepo.value })
  if (!created) return
  closeNewProject()
  await selectProjectByName(created)
}

onMounted(() => {
  ensureReady()
})
</script>

<template>
  <div class="mx-auto w-full max-w-6xl flex flex-col gap-6">
    <!-- ══════════════ PROJECTS LIST ══════════════ -->
    <template v-if="!selectedProject">
      <!-- Needs you banner -->
      <div
        v-if="holdCount"
        class="flex flex-wrap items-center justify-between gap-4 bg-codx-primary/5 border border-codx-primary/20 rounded-2xl px-5 py-4"
      >
        <div>
          <strong class="text-sm font-semibold">{{ t('sp.banner') }}</strong>
        </div>
        <button
          type="button"
          class="h-9 px-4 rounded-full bg-base-content text-base-100 text-sm font-semibold hover:opacity-90 transition"
          @click="showTicketsOnHold"
        >{{ t('sp.showMe') }}</button>
      </div>

      <!-- Header -->
      <div class="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 class="text-lg font-semibold">{{ t('pp.title') }}</h2>
          <p class="text-sm text-base-content/50 mt-1.5">{{ t('pp.desc') }}</p>
        </div>
        <button
          type="button"
          class="h-10 px-5 rounded-full bg-base-content text-base-100 text-sm font-semibold hover:opacity-90 transition shrink-0"
          @click="openNewProject"
        >{{ t('pp.add') }}</button>
      </div>

      <!-- Filters + search -->
      <div class="flex flex-wrap items-center gap-3">
        <div class="flex flex-wrap gap-2" role="group" :aria-label="t('pp.title')">
          <button
            v-for="chip in chips"
            :key="chip.value"
            type="button"
            class="h-9 px-4 rounded-full border text-sm font-semibold inline-flex items-center gap-2 transition"
            :class="ui.filter === chip.value
              ? 'bg-base-content border-base-content text-base-100'
              : 'bg-base-100 border-base-content/15 text-base-content/60 hover:bg-base-200'"
            :aria-pressed="ui.filter === chip.value"
            @click="setFilter(chip.value)"
          >
            {{ chip.label }}
            <span class="text-xs opacity-60">{{ chip.count }}</span>
          </button>
        </div>
        <div class="grow"></div>
        <!-- Free-text search: only when the catalogue needs more than one page -->
        <template v-if="searchableProjects">
          <label class="sr-only" for="solo-projects-search">{{ t('pp.search') }}</label>
          <input
            id="solo-projects-search"
            :value="ui.query"
            type="search"
            autocomplete="off"
            :placeholder="t('pp.search')"
            class="h-10 w-full sm:w-64 rounded-full border border-base-content/15 bg-base-100 px-4 text-sm outline-none focus:border-codx-primary focus:ring-2 focus:ring-codx-primary/20"
            @input="setQuery($event.target.value)"
          />
        </template>
      </div>

      <!-- Cards — one page at a time (PROJECTS_PAGE_SIZE) -->
      <div
        v-if="filteredProjects.length"
        class="grid gap-5 grid-cols-[repeat(auto-fit,minmax(min(100%,280px),1fr))]"
      >
        <article
          v-for="p in visibleProjects"
          :key="p.id"
          class="bg-base-100 border border-base-content/10 rounded-2xl shadow-sm p-5 flex flex-col"
        >
          <div class="flex items-start justify-between gap-3">
            <div class="flex items-center gap-2.5 min-w-0">
              <span class="w-8 h-8 rounded-lg overflow-hidden bg-base-200 shrink-0 grid place-items-center">
                <img v-if="p.icon" :src="p.icon" alt="" class="w-full h-full object-cover" />
                <i v-else class="fa-solid fa-folder text-[11px] text-base-content/40"></i>
              </span>
              <h3 class="text-sm font-semibold truncate" :title="p.name">{{ p.name }}</h3>
            </div>
            <span
              class="text-[11px] font-semibold px-2.5 py-1 rounded-full whitespace-nowrap"
              :class="statusPillClass(p.active)"
            >{{ p.active ? t('pp.activeBadge') : t('pp.idleBadge') }}</span>
          </div>

          <p class="text-sm text-base-content/50 mt-3 min-h-[40px] leading-relaxed">
            {{ p.active ? t('pp.activeHint') : t('pp.idleHint') }}
          </p>

          <div class="h-1.5 rounded-full bg-base-content/10 overflow-hidden">
            <div class="h-full rounded-full bg-codx-primary" :style="{ width: (p.progress || 0) + '%' }"></div>
          </div>
          <p class="text-xs text-base-content/50 mt-2">
            {{ p.progress === null ? t('pp.progressUnknown') : p.progress + '% ' + t('pp.done') }}
            · {{ p.tasks }} {{ t('pp.tasks') }}
            <template v-if="p.updated"> · {{ t('pp.updated') }} {{ relative(p.updated) }}</template>
          </p>

          <div class="flex flex-wrap gap-2.5 mt-4">
            <button
              type="button"
              class="h-9 px-4 rounded-full bg-base-content text-base-100 text-sm font-semibold hover:opacity-90 transition"
              @click="selectProject(p.id)"
            >{{ t('pp.open') }}</button>
            <button
              type="button"
              class="h-9 px-4 rounded-full border border-base-content/20 bg-base-100 text-sm font-semibold hover:bg-base-200 transition"
              @click="openSettings(p.id)"
            >{{ t('pp.settings') }}</button>
          </div>
        </article>
      </div>

      <div
        v-else
        class="py-14 text-center text-sm text-base-content/50 bg-base-100 border border-dashed border-base-content/15 rounded-2xl"
      >
        {{ ui.query.trim() ? t('pp.noMatch') : t('pp.empty') }}
      </div>

      <!-- Pager: "Showing 4 of 23" + one page per click -->
      <div
        v-if="filteredProjects.length > PROJECTS_PAGE_SIZE"
        class="flex flex-col items-center gap-3"
      >
        <p class="text-xs text-base-content/40" aria-live="polite">
          {{ t('pp.showing') }} {{ visibleProjects.length }} {{ t('pp.of') }} {{ filteredProjects.length }}
        </p>
        <button
          v-if="hasMoreProjects"
          type="button"
          class="h-10 px-5 rounded-full border border-base-content/20 bg-base-100 text-sm font-semibold hover:bg-base-200 transition inline-flex items-center gap-2"
          @click="loadMoreProjects"
        >
          {{ t('pp.loadMore') }}
          <span class="text-xs opacity-60">+{{ Math.min(hiddenProjects, PROJECTS_PAGE_SIZE) }}</span>
        </button>
      </div>
    </template>

    <!-- ══════════════ PROJECT DETAIL ══════════════ -->
    <template v-else>
      <!-- Breadcrumb -->
      <nav class="flex items-center gap-2 text-sm text-base-content/40 min-w-0" aria-label="Breadcrumb">
        <button
          type="button"
          class="font-semibold text-base-content/60 hover:text-codx-primary transition-colors"
          @click="backToList"
        >{{ t('pp.back') }}</button>
        <span aria-hidden="true">/</span>
        <span class="truncate text-base-content/60">{{ selectedProject.name }}</span>
      </nav>

      <!-- Head -->
      <div class="flex flex-wrap items-start justify-between gap-4">
        <div class="min-w-0">
          <h1 class="text-2xl font-semibold tracking-tight flex flex-wrap items-center gap-3">
            <span class="truncate">{{ selectedProject.name }}</span>
            <span
              class="text-[11px] font-semibold px-2.5 py-1 rounded-full"
              :class="statusPillClass(selectedProject.active)"
            >{{ selectedProject.active ? t('pp.activeBadge') : t('pp.idleBadge') }}</span>
          </h1>
          <p class="text-sm text-base-content/50 mt-2 break-all">{{ selectedProject.path }}</p>
        </div>
        <button
          type="button"
          class="h-10 px-5 rounded-full bg-base-content text-base-100 text-sm font-semibold hover:opacity-90 transition disabled:opacity-40 disabled:cursor-not-allowed shrink-0"
          :disabled="!selectedProject.sprintBoards.length"
          @click="openSprintBoard()"
        >{{ t('pp.openBoard') }}</button>
      </div>

      <!-- Tabs -->
      <div class="flex gap-1 border-b border-base-content/10 overflow-x-auto" role="tablist">
        <button
          v-for="tab in tabs"
          :key="tab.value"
          type="button"
          role="tab"
          class="px-4 py-2.5 text-sm whitespace-nowrap border-b-2 -mb-px transition-colors"
          :class="ui.tab === tab.value
            ? 'border-codx-primary text-base-content font-semibold'
            : 'border-transparent text-base-content/50 hover:text-base-content'"
          :aria-selected="ui.tab === tab.value"
          @click="setTab(tab.value)"
        >{{ tab.label }}</button>
      </div>

      <div class="grid gap-6 items-start grid-cols-[repeat(auto-fit,minmax(min(100%,320px),1fr))]">
        <!-- Main column -->
        <div class="flex flex-col gap-6 min-w-0">
          <!-- OVERVIEW -->
          <template v-if="ui.tab === 'overview'">
            <section class="bg-base-100 border border-base-content/10 rounded-2xl shadow-sm p-6">
              <h2 class="text-base font-semibold">{{ t('pp.byStatus') }}</h2>
              <div
                v-if="statusRows.length"
                class="grid gap-4 mt-5 grid-cols-[repeat(auto-fit,minmax(min(100%,140px),1fr))]"
              >
                <div v-for="row in statusRows" :key="row.value" class="bg-base-200 rounded-xl p-4 flex flex-col gap-1.5">
                  <strong class="text-2xl font-semibold tracking-tight">{{ row.count }}</strong>
                  <span class="text-xs text-base-content/50">{{ row.label }}</span>
                  <div class="h-1.5 rounded-full bg-base-content/10 overflow-hidden mt-2">
                    <div class="h-full rounded-full bg-codx-primary" :style="{ width: row.pct + '%' }"></div>
                  </div>
                </div>
              </div>
              <p v-else class="text-sm text-base-content/50 mt-4">{{ t('pp.noTasks') }}</p>
            </section>

            <section class="bg-base-100 border border-base-content/10 rounded-2xl shadow-sm p-6">
              <h2 class="text-base font-semibold">{{ t('pp.recent') }}</h2>
              <ul v-if="recentChats.length" class="mt-5 flex flex-col gap-4">
                <li v-for="chat in recentChats" :key="chat.id" class="flex gap-3.5">
                  <span
                    class="w-2 h-2 rounded-full shrink-0 mt-1.5"
                    :class="(chat.status || 'todo') === 'done' ? 'bg-success'
                      : (chat.status || 'todo') === 'onhold' ? 'bg-warning' : 'bg-codx-primary'"
                    aria-hidden="true"
                  ></span>
                  <div class="min-w-0">
                    <p class="text-sm font-semibold truncate" :title="chat.name">{{ chat.name || t('sp.untitled') }}</p>
                    <p class="text-xs text-base-content/50 mt-1">
                      {{ statusLabel(chat.status || 'todo') }} · {{ relative(chat.updated_at) }}
                    </p>
                  </div>
                </li>
              </ul>
              <p v-else class="text-sm text-base-content/50 mt-4">{{ t('pp.recentEmpty') }}</p>
            </section>
          </template>

          <!-- SPRINTS -->
          <template v-else-if="ui.tab === 'sprints'">
            <section class="bg-base-100 border border-base-content/10 rounded-2xl shadow-sm p-6">
              <div class="flex items-start justify-between gap-4">
                <h2 class="text-base font-semibold">{{ t('pp.sprints') }}</h2>
                <button
                  type="button"
                  class="h-9 px-4 rounded-full border border-base-content/20 bg-base-100 text-sm font-semibold hover:bg-base-200 transition shrink-0"
                  @click="goModule('sprints')"
                >{{ t('pp.openBoard') }}</button>
              </div>

              <div v-if="selectedProject.sprintBoards.length" class="flex flex-col gap-3 mt-5">
                <button
                  v-for="board in selectedProject.sprintBoards"
                  :key="board.id"
                  type="button"
                  class="w-full text-left border border-base-content/10 rounded-xl px-4 py-3 hover:bg-base-200 transition-colors flex items-center gap-4"
                  @click="openSprintBoard(board.id)"
                >
                  <div class="min-w-0 flex-1">
                    <h3 class="text-sm font-semibold truncate">{{ board.title }}</h3>
                    <small class="text-xs text-base-content/50">
                      {{ countSprintDone(board.id) }} / {{ countSprintTasks(board.id) }} {{ t('pp.done') }}
                      <template v-if="board.last_update"> · {{ relative(board.last_update) }}</template>
                    </small>
                  </div>
                  <i class="fa-solid fa-chevron-right text-xs text-base-content/30"></i>
                </button>
              </div>

              <div v-else class="mt-5 py-10 text-center text-sm text-base-content/50 bg-base-200 border border-dashed border-base-content/15 rounded-xl">
                <p>{{ t('pp.noSprints') }}</p>
                <button
                  type="button"
                  class="mt-4 h-9 px-4 rounded-full bg-base-content text-base-100 text-sm font-semibold hover:opacity-90 transition"
                  @click="goModule('sprints')"
                >{{ t('pp.createSprint') }}</button>
              </div>
            </section>
          </template>

          <!-- SETTINGS -->
          <template v-else>
            <section class="bg-base-100 border border-base-content/10 rounded-2xl shadow-sm p-6">
              <h2 class="text-base font-semibold">{{ t('pp.settings') }}</h2>
              <p class="text-sm text-base-content/50 mt-1.5">{{ t('pp.settingsDesc') }}</p>

              <dl class="mt-6 flex flex-col gap-4">
                <div class="flex items-start justify-between gap-4 text-sm">
                  <dt class="text-base-content/50 shrink-0">{{ t('pp.name') }}</dt>
                  <dd class="font-semibold text-right break-words">{{ selectedProject.name }}</dd>
                </div>
                <div class="flex items-start justify-between gap-4 text-sm">
                  <dt class="text-base-content/50 shrink-0">{{ t('pp.folder') }}</dt>
                  <dd class="font-semibold text-right break-all">{{ selectedProject.path || t('pp.never') }}</dd>
                </div>
                <div class="flex items-center justify-between gap-4 text-sm">
                  <dt class="text-base-content/50">{{ t('pp.boards') }}</dt>
                  <dd class="font-semibold">{{ selectedProject.boards.length }}</dd>
                </div>
                <div class="flex items-center justify-between gap-4 text-sm">
                  <dt class="text-base-content/50">{{ t('pp.sprints') }}</dt>
                  <dd class="font-semibold">{{ selectedProject.sprintBoards.length }}</dd>
                </div>
                <div class="flex items-center justify-between gap-4 text-sm">
                  <dt class="text-base-content/50">{{ t('pp.tasks') }}</dt>
                  <dd class="font-semibold">{{ selectedProject.tasks }}</dd>
                </div>
                <div class="flex items-center justify-between gap-4 text-sm">
                  <dt class="text-base-content/50">{{ t('pp.lastUpdate') }}</dt>
                  <dd class="font-semibold">{{ selectedProject.updated ? relative(selectedProject.updated) : t('pp.never') }}</dd>
                </div>
              </dl>

              <div class="flex flex-wrap gap-3 mt-6">
                <button
                  type="button"
                  class="h-10 px-5 rounded-full bg-base-content text-base-100 text-sm font-semibold hover:opacity-90 transition"
                  @click="openFullSettings"
                >{{ t('pp.fullSettings') }}</button>
              </div>
            </section>

            <section class="bg-base-100 border border-base-content/10 rounded-2xl shadow-sm p-6">
              <h2 class="text-base font-semibold">{{ t('pp.boards') }}</h2>
              <ul v-if="selectedProject.boards.length" class="mt-5 flex flex-col gap-3">
                <li
                  v-for="board in selectedProject.boards"
                  :key="board.id"
                  class="flex items-center gap-3 border border-base-content/10 rounded-xl px-4 py-3"
                >
                  <i
                    class="fa-solid text-xs text-base-content/40"
                    :class="board.type === 'sprint' ? 'fa-table-columns' : 'fa-table-list'"
                    aria-hidden="true"
                  ></i>
                  <span class="text-sm font-semibold truncate flex-1">{{ board.title }}</span>
                  <span class="text-[11px] font-semibold px-2.5 py-1 rounded-full bg-base-200 text-base-content/60">
                    {{ projectTypeLabel(board) }}
                  </span>
                  <span v-if="board.last_update" class="text-xs text-base-content/40 hidden sm:inline">
                    {{ relative(board.last_update) }}
                  </span>
                </li>
              </ul>
              <p v-else class="text-sm text-base-content/50 mt-4">{{ t('pp.noSprints') }}</p>
            </section>
          </template>
        </div>

        <!-- Side facts -->
        <aside class="bg-base-100 border border-base-content/10 rounded-2xl shadow-sm p-6">
          <h2 class="text-base font-semibold">{{ t('pp.facts') }}</h2>
          <dl class="mt-5 flex flex-col gap-4">
            <div class="flex items-center justify-between gap-4 text-sm">
              <dt class="text-base-content/50">{{ t('pp.boards') }}</dt>
              <dd class="font-semibold">{{ selectedProject.boards.length }}</dd>
            </div>
            <div class="flex items-center justify-between gap-4 text-sm">
              <dt class="text-base-content/50">{{ t('pp.sprints') }}</dt>
              <dd class="font-semibold">{{ selectedProject.sprintBoards.length }}</dd>
            </div>
            <div class="flex items-center justify-between gap-4 text-sm">
              <dt class="text-base-content/50">{{ t('pp.tasks') }}</dt>
              <dd class="font-semibold">{{ selectedProject.tasks }}</dd>
            </div>
            <div class="flex items-center justify-between gap-4 text-sm">
              <dt class="text-base-content/50">{{ t('pp.done') }}</dt>
              <dd class="font-semibold">{{ selectedProject.done }}</dd>
            </div>
            <div class="flex items-center justify-between gap-4 text-sm">
              <dt class="text-base-content/50">{{ t('sp.onhold') }}</dt>
              <dd class="font-semibold" :class="selectedProject.onhold ? 'text-warning' : ''">
                {{ selectedProject.onhold }}
              </dd>
            </div>
          </dl>

          <button
            v-if="selectedProject.onhold"
            type="button"
            class="mt-6 w-full h-9 px-4 rounded-full bg-base-content text-base-100 text-sm font-semibold hover:opacity-90 transition"
            @click="showTicketsOnHold"
          >{{ t('sp.showMe') }}</button>
        </aside>
      </div>
    </template>

    <!-- ══════════════ NEW PROJECT DIALOG ══════════════ -->
    <div v-if="showNewProject" class="fixed inset-0 z-[200] flex items-center justify-center px-4">
      <div class="absolute inset-0 bg-black/50 backdrop-blur-sm" @click="closeNewProject"></div>

      <div
        class="relative w-full max-w-lg bg-base-100 border border-base-content/10 rounded-2xl shadow-2xl p-6"
        role="dialog"
        aria-modal="true"
      >
        <h2 class="text-lg font-semibold">{{ t('pp.add') }}</h2>
        <p class="text-sm text-base-content/50 mt-1.5">{{ t('pp.newProjectDesc') }}</p>

        <form class="mt-5 flex flex-col gap-4" novalidate @submit.prevent="submitProject">
          <div class="flex flex-col gap-1.5">
            <label for="np-project-name" class="text-xs font-semibold text-base-content/60">{{ t('pp.name') }}</label>
            <input
              id="np-project-name"
              v-model="newName"
              type="text"
              :placeholder="t('pp.namePh')"
              class="h-11 rounded-xl border border-base-content/15 bg-base-100 px-4 text-sm outline-none focus:border-codx-primary focus:ring-2 focus:ring-codx-primary/20"
              :aria-invalid="!!ui.errors.name"
              autofocus
            />
            <span v-if="ui.errors.name" class="text-xs text-error">{{ ui.errors.name }}</span>
          </div>

          <div class="flex flex-col gap-1.5">
            <label for="np-project-repo" class="text-xs font-semibold text-base-content/60">{{ t('pp.repo') }}</label>
            <input
              id="np-project-repo"
              v-model="newRepo"
              type="text"
              placeholder="https://github.com/user/repo.git"
              class="h-11 rounded-xl border border-base-content/15 bg-base-100 px-4 text-sm font-mono outline-none focus:border-codx-primary"
            />
          </div>

          <div class="flex justify-end gap-3 pt-1">
            <button
              type="button"
              class="h-10 px-5 rounded-full border border-base-content/20 text-sm font-semibold hover:bg-base-200 transition"
              @click="closeNewProject"
            >{{ t('pp.cancel') }}</button>
            <button
              type="submit"
              :disabled="ui.busy"
              class="h-10 px-5 rounded-full bg-base-content text-base-100 text-sm font-semibold hover:opacity-90 transition disabled:opacity-40"
            >{{ t('pp.create') }}</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>