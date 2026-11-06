<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { $storex } from '@/store'
import { MOBILE_APP_GROUPS, MOBILE_TONES } from '@/config/mobile'

const route = useRoute()
const router = useRouter()

const search = ref('')
const searchInput = ref(null)
const projectsOpen = ref(false)

const open = computed(() => $storex.ui.mobileMenuOpen)
const activeProject = computed(() => $storex.projects.activeProject)
const activeProjectId = computed(() => activeProject.value?.project_id || null)
const user = computed(() => $storex.users.user || {})
const avatar = computed(() => user.value?.avatar || '')
const username = computed(() => user.value?.username || 'User')
const initial = computed(() => (username.value || 'U').trim().charAt(0).toUpperCase())
const email = computed(() => user.value?.email || '')
const connected = computed(() => $storex.session.connected !== false)
const coinBalance = computed(() => {
  const balance = user.value?.wallet?.balance_cxjcoins
  return balance == null ? null : Number(balance).toFixed(2)
})

const allProjects = computed(() => $storex.projects.allProjects || [])
const pinnedIds = computed(() => new Set($storex.ui.pinnedProjects || []))
const projects = computed(() => {
  const activeId = activeProjectId.value
  return [...allProjects.value].sort((a, b) => {
    if (a.project_id === activeId) return -1
    if (b.project_id === activeId) return 1
    const pinnedDiff = Number(pinnedIds.value.has(b.project_id)) - Number(pinnedIds.value.has(a.project_id))
    if (pinnedDiff) return pinnedDiff
    return (a.project_name || '').localeCompare(b.project_name || '')
  })
})

const workspaces = computed(() => $storex.projects.projectApps || [])

const query = computed(() => search.value.trim().toLowerCase())

function matches(text) {
  return `${text || ''}`.toLowerCase().includes(query.value)
}

const filteredGroups = computed(() => {
  if (!query.value) return MOBILE_APP_GROUPS
  return MOBILE_APP_GROUPS
    .map(group => ({
      ...group,
      apps: group.apps.filter(app =>
        matches(app.title) || matches(app.description) || matches(app.key) || matches(group.label)
      )
    }))
    .filter(group => group.apps.length)
})

const filteredProjects = computed(() => {
  if (!query.value) return []
  return projects.value.filter(project => matches(project.project_name))
})

const hasResults = computed(() =>
  filteredGroups.value.length > 0 || filteredProjects.value.length > 0
)

watch(open, isOpen => {
  document.documentElement.classList.toggle('mobile-menu-open', !!isOpen)
  if (isOpen) {
    search.value = ''
    projectsOpen.value = false
  }
})

// A tab tap, an app tile or a browser back gesture all end with a route change:
// never leave the launcher covering the destination.
watch(() => route.fullPath, () => {
  if ($storex.ui.mobileMenuOpen) $storex.ui.closeMobileMenu()
})

function close() {
  $storex.ui.closeMobileMenu()
}

function openSearch() {
  searchInput.value?.focus()
}

function openApp(app) {
  close()
  if (!app) return
  if (app.action === 'new-chat') {
    router.push({ name: 'new-chat' })
    return
  }
  if (app.action === 'chats') {
    router.push({ name: 'chats' })
    return
  }
  $storex.ui.openApp({ appKey: app.key })
}

function goTo(name) {
  close()
  router.push({ name })
}

async function openProject(project) {
  if (!project?.project_id) return
  if (project.project_id === activeProjectId.value) {
    projectsOpen.value = false
    return
  }
  close()
  try {
    await $storex.projects.activeProjectChanged(project)
    // Same landing behaviour as the desktop project switch: the new project
    // opens on its home instead of keeping a screen from the previous one.
    if (route.name !== 'home') router.push({ name: 'home' })
  } catch (error) {
    console.error('[MobileMenu] cannot switch project', error)
    $storex.ui.addNotification({ text: 'Could not switch project', type: 'error' })
  }
}

function openWorkspace(workspace) {
  close()
  $storex.ui.openWorkspace(workspace)
}

function newProject() {
  close()
  $storex.ui.showNewProject(true)
}

function logout() {
  close()
  $storex.users.logout()
}

function toneClass(tone) {
  return MOBILE_TONES[tone] || MOBILE_TONES.primary
}
</script>

<template>
  <Teleport to="body">
    <Transition name="mobile-menu">
      <div
        v-if="open"
        class="mobile-menu-root fixed inset-0 z-[110] bg-base-300 text-base-content"
        role="dialog"
        aria-modal="true"
        aria-label="Menu"
      >
        <div class="flex h-full flex-col">
          <!-- ── Header: identity + search ─────────────────────────────── -->
          <header class="safe-area-top shrink-0 border-b border-base-content/10 bg-base-200">
            <div class="flex h-14 items-center gap-3 px-4">
              <img src="/only_icon.png" alt="codx-junior" class="h-8 w-8 rounded-lg" />
              <div class="min-w-0 flex-1">
                <h1 class="text-[15px] font-bold leading-tight">codx-junior</h1>
                <p class="flex items-center gap-1.5 truncate text-[10px] text-base-content/45">
                  <span
                    class="h-1.5 w-1.5 rounded-full"
                    :class="connected ? 'bg-success' : 'bg-error'"
                    aria-hidden="true"
                  ></span>
                  {{ connected ? 'Connected' : 'Offline' }} · {{ activeProject?.project_name || 'No project' }}
                </p>
              </div>
              <button type="button" class="mobile-icon-btn" aria-label="Close menu" @click="close">
                <i class="fa-solid fa-xmark text-lg"></i>
              </button>
            </div>

            <div class="px-4 pb-3">
              <label class="flex h-11 items-center gap-2 rounded-xl border border-base-content/10 bg-base-100 px-3 focus-within:border-primary/50">
                <i class="fa-solid fa-magnifying-glass text-xs text-base-content/40" aria-hidden="true"></i>
                <input
                  ref="searchInput"
                  v-model="search"
                  type="search"
                  enterkeyhint="search"
                  placeholder="Search apps and projects"
                  class="min-w-0 flex-1 bg-transparent text-sm outline-none placeholder:text-base-content/35"
                  aria-label="Search apps and projects"
                  @click="openSearch"
                />
                <button
                  v-if="search"
                  type="button"
                  class="grid h-6 w-6 place-items-center rounded-full bg-base-content/10 text-[10px]"
                  aria-label="Clear search"
                  @click="search = ''"
                >
                  <i class="fa-solid fa-xmark"></i>
                </button>
              </label>
            </div>
          </header>

          <!-- ── Scrollable body ───────────────────────────────────────── -->
          <div class="mobile-menu-scroll flex-1 overflow-y-auto overscroll-contain px-4 pb-8">
            <!-- Active project + switcher -->
            <section class="mt-3">
              <button
                type="button"
                class="flex w-full items-center gap-3 rounded-2xl border border-base-content/10 bg-base-100 p-3 text-left active:bg-base-content/5"
                :aria-expanded="projectsOpen"
                @click="projectsOpen = !projectsOpen"
              >
                <img
                  :src="activeProject?.project_icon || '/only_icon.png'"
                  :alt="activeProject?.project_name || 'Project'"
                  class="h-11 w-11 shrink-0 rounded-xl border border-base-content/10 object-cover"
                />
                <span class="min-w-0 flex-1">
                  <span class="block text-[10px] font-semibold uppercase tracking-wider text-base-content/40">Active project</span>
                  <span class="block truncate text-sm font-bold leading-tight">
                    {{ activeProject?.project_name || 'Select a project' }}
                  </span>
                </span>
                <i
                  class="fa-solid text-[11px] text-base-content/40 transition-transform"
                  :class="projectsOpen ? 'fa-chevron-up' : 'fa-chevron-down'"
                  aria-hidden="true"
                ></i>
              </button>

              <div
                v-if="projectsOpen"
                class="mt-2 overflow-hidden rounded-2xl border border-base-content/10 bg-base-100"
              >
                <div class="max-h-72 overflow-y-auto overscroll-contain p-1">
                  <button
                    v-for="project in projects"
                    :key="project.project_id"
                    type="button"
                    class="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left active:bg-base-content/10"
                    :class="project.project_id === activeProjectId ? 'bg-primary/10' : ''"
                    @click="openProject(project)"
                  >
                    <img
                      :src="project.project_icon || '/only_icon.png'"
                      :alt="project.project_name"
                      class="h-8 w-8 shrink-0 rounded-lg border border-base-content/10 object-cover"
                    />
                    <span class="min-w-0 flex-1 truncate text-sm">{{ project.project_name }}</span>
                    <i
                      v-if="pinnedIds.has(project.project_id)"
                      class="fa-solid fa-thumbtack text-[10px] text-warning/70"
                      aria-label="Pinned"
                    ></i>
                    <i
                      v-if="project.project_id === activeProjectId"
                      class="fa-solid fa-check text-xs text-primary"
                      aria-label="Active"
                    ></i>
                  </button>
                  <p v-if="!projects.length" class="px-3 py-4 text-center text-xs text-base-content/40">
                    No projects yet
                  </p>
                </div>

                <button
                  type="button"
                  class="flex w-full items-center gap-3 border-t border-base-content/10 px-3 py-3 text-left text-sm text-primary active:bg-base-content/10"
                  @click="newProject"
                >
                  <span class="grid h-8 w-8 place-items-center rounded-lg bg-primary/15">
                    <i class="fa-solid fa-plus text-xs"></i>
                  </span>
                  New project
                </button>
              </div>
            </section>

            <!-- Project matches while searching -->
            <section v-if="query && filteredProjects.length" class="mt-5">
              <h2 class="mb-2 px-1 text-[11px] font-bold uppercase tracking-wider text-base-content/45">Projects</h2>
              <div class="overflow-hidden rounded-2xl border border-base-content/10 bg-base-100">
                <button
                  v-for="project in filteredProjects"
                  :key="'sp-' + project.project_id"
                  type="button"
                  class="flex w-full items-center gap-3 border-b border-base-content/5 px-3 py-2.5 text-left last:border-b-0 active:bg-base-content/10"
                  @click="openProject(project)"
                >
                  <img
                    :src="project.project_icon || '/only_icon.png'"
                    :alt="project.project_name"
                    class="h-8 w-8 rounded-lg object-cover"
                  />
                  <span class="min-w-0 flex-1 truncate text-sm">{{ project.project_name }}</span>
                  <i class="fa-solid fa-chevron-right text-[10px] text-base-content/25"></i>
                </button>
              </div>
            </section>

            <!-- App groups -->
            <section v-for="group in filteredGroups" :key="group.id" class="mt-5">
              <div class="mb-2 flex items-baseline justify-between gap-2 px-1">
                <h2 class="text-[11px] font-bold uppercase tracking-wider text-base-content/45">{{ group.label }}</h2>
                <span class="truncate text-[10px] text-base-content/30">{{ group.hint }}</span>
              </div>

              <div class="grid grid-cols-2 gap-2">
                <button
                  v-for="app in group.apps"
                  :key="app.key"
                  type="button"
                  class="mobile-app-tile flex min-h-[6.5rem] flex-col items-start gap-2 rounded-2xl border border-base-content/10 bg-base-100 p-3 text-left transition-colors active:bg-base-content/5"
                  @click="openApp(app)"
                >
                  <span class="grid h-10 w-10 place-items-center rounded-xl" :class="toneClass(app.tone)">
                    <i :class="app.icon" class="text-base" aria-hidden="true"></i>
                  </span>
                  <span class="min-w-0">
                    <span class="block text-[13px] font-semibold leading-tight">{{ app.title }}</span>
                    <span class="mt-0.5 line-clamp-2 block text-[10px] leading-snug text-base-content/45">
                      {{ app.description }}
                    </span>
                  </span>
                </button>
              </div>
            </section>

            <!-- Workspaces -->
            <section v-if="!query && workspaces.length" class="mt-5">
              <div class="mb-2 flex items-baseline justify-between px-1">
                <h2 class="text-[11px] font-bold uppercase tracking-wider text-base-content/45">Workspaces</h2>
                <button type="button" class="text-[10px] font-medium text-primary" @click="goTo('workspaces')">
                  Manage
                </button>
              </div>
              <div class="overflow-hidden rounded-2xl border border-base-content/10 bg-base-100">
                <button
                  v-for="workspace in workspaces"
                  :key="workspace.key"
                  type="button"
                  class="flex w-full items-center gap-3 border-b border-base-content/5 px-3 py-3 text-left last:border-b-0 active:bg-base-content/10"
                  @click="openWorkspace(workspace)"
                >
                  <span class="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-base-content/5 text-base-content/60">
                    <i :class="workspace.icon || 'fa-solid fa-cube'" class="text-sm"></i>
                  </span>
                  <span class="min-w-0 flex-1">
                    <span class="block truncate text-sm">{{ workspace.name }}</span>
                    <span class="block truncate text-[10px] text-base-content/40">{{ workspace.workspaceName }}</span>
                  </span>
                  <i class="fa-solid fa-arrow-up-right-from-square text-[10px] text-base-content/25"></i>
                </button>
              </div>
            </section>

            <!-- No results -->
            <div v-if="!hasResults" class="mt-16 flex flex-col items-center gap-3 text-center text-base-content/40">
              <i class="fa-solid fa-magnifying-glass text-3xl"></i>
              <p class="text-sm">Nothing matches “{{ search }}”</p>
            </div>

            <!-- Account / quick actions -->
            <section v-if="!query" class="mt-6">
              <h2 class="mb-2 px-1 text-[11px] font-bold uppercase tracking-wider text-base-content/45">Account</h2>
              <div class="overflow-hidden rounded-2xl border border-base-content/10 bg-base-100">
                <div class="flex items-center gap-3 border-b border-base-content/5 px-3 py-3">
                  <img v-if="avatar" :src="avatar" :alt="username" class="h-10 w-10 rounded-full object-cover" />
                  <span
                    v-else
                    class="grid h-10 w-10 place-items-center rounded-full bg-primary/15 text-sm font-bold text-primary"
                    aria-hidden="true"
                  >{{ initial }}</span>
                  <div class="min-w-0 flex-1">
                    <p class="truncate text-sm font-semibold">{{ username }}</p>
                    <p class="truncate text-[10px] text-base-content/40">{{ email }}</p>
                  </div>
                  <span
                    v-if="coinBalance != null"
                    class="flex items-center gap-1 rounded-full bg-warning/15 px-2 py-1 text-[10px] font-semibold text-warning"
                  >
                    <i class="fa-solid fa-coins text-[9px]"></i>{{ coinBalance }}
                  </span>
                </div>

                <button
                  v-for="action in [
                    { key: 'account', label: 'My account', icon: 'fa-solid fa-user' },
                    { key: 'settings', label: 'Project settings', icon: 'fa-solid fa-gear' },
                    { key: 'global-settings', label: 'Global settings', icon: 'fa-solid fa-sliders' }
                  ]"
                  :key="action.key"
                  type="button"
                  class="flex w-full items-center gap-3 border-b border-base-content/5 px-3 py-3 text-left text-sm last:border-b-0 active:bg-base-content/10"
                  @click="openApp({ key: action.key })"
                >
                  <span class="grid h-8 w-8 place-items-center rounded-lg bg-base-content/5 text-base-content/60">
                    <i :class="action.icon" class="text-xs"></i>
                  </span>
                  <span class="flex-1">{{ action.label }}</span>
                  <i class="fa-solid fa-chevron-right text-[10px] text-base-content/25"></i>
                </button>

                <button
                  type="button"
                  class="flex w-full items-center gap-3 border-t border-base-content/10 px-3 py-3 text-left text-sm text-error active:bg-error/10"
                  @click="logout"
                >
                  <span class="grid h-8 w-8 place-items-center rounded-lg bg-error/15">
                    <i class="fa-solid fa-right-from-bracket text-xs"></i>
                  </span>
                  <span class="flex-1">Log out</span>
                </button>
              </div>
            </section>

            <p class="mt-6 text-center text-[10px] text-base-content/25">
              codx-junior · mobile
            </p>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>
