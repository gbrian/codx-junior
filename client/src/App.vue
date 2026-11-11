<script setup>
import { computed, onMounted, watch, watchEffect } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { $storex } from '@/store'
import Login from './components/user/Login.vue'
import Toast from './components/Toast.vue'
import DesktopSidebar from './components/layout/DesktopSidebar.vue'
import NewProject from './components/project/NewProject.vue'
import MobileShell from './components/mobile/MobileShell.vue'

const route = useRoute()
const router = useRouter()

const uiReady = computed(() => $storex.ui.uiReady)
const isLogin = computed(() => !$storex.users.user)
const isMobile = computed(() => $storex.ui.isMobile)
const isCompanyMode = computed(() => $storex.users.isCompanyMode)

// Solopreneur mode is a product shell of its own: it owns the full viewport on
// every device, so neither the desktop sidebar nor the mobile shell wraps it.
const isFullScreenRoute = computed(() => route.name === 'solopreneur')

// ── Company mode entry ──────────────────────────────────────────────────────
// Role-driven landing: a manager/company admin (or a member of any company)
// enters the company shell after login. The guard also does this when the user
// is already loaded; this watcher covers the normal bootstrap where the router
// guard runs before `users.login()` resolves.
//
// The redirect happens ONCE per browser session: switching to working mode (or
// following a deep link into a project) must not bounce the manager back.
const COMPANY_ENTRY_KEY = 'codx.company.entry'
// Only the bootstrap path ("/" after a login or a mode switch) auto-enters the
// company shell. A deep link into a project must keep working for managers.
const enteredFromRoot = ['/', ''].includes(window.location.pathname)

watch(
  [isCompanyMode, () => route.name, isLogin, uiReady],
  ([companyMode, routeName, login, ready]) => {
    if (!enteredFromRoot || !ready || login || !companyMode) return
    if (!['root', 'home'].includes(routeName)) return
    if (sessionStorage.getItem(COMPANY_ENTRY_KEY)) return
    sessionStorage.setItem(COMPANY_ENTRY_KEY, '1')
    const companyId = $storex.users.primaryCompanyId
    router.replace({
      name: 'company-home',
      params: companyId ? { companyId } : {}
    }).catch(() => {})
  },
  { immediate: true }
)

// Switching back into company mode should land on the company shell again.
watch(isCompanyMode, (value) => {
  if (!value) {
    sessionStorage.removeItem(COMPANY_ENTRY_KEY)
    return
  }
  if (!enteredFromRoot || route.name === 'company-home') return
  const companyId = $storex.users.primaryCompanyId
  router.replace({
    name: 'company-home',
    params: companyId ? { companyId } : {}
  }).catch(() => {})
})

function openAccountSettings() {
  $storex.ui.openApp({ appKey: 'account' })
}

// Teleported surfaces (the mobile launcher, action sheets, Reka poppers) live
// outside the themed wrapper. DaisyUI resolves `data-theme` from the document
// root, so mirror the active theme there — otherwise every overlay renders in
// the default light theme.
watchEffect(() => {
  const theme = $storex.ui.theme || 'dark'
  document.documentElement.setAttribute('data-theme', theme)
  document.documentElement.style.colorScheme = theme === 'dark' ? 'dark' : 'light'
  document.querySelector('meta[name="theme-color"]')
    ?.setAttribute('content', theme === 'dark' ? '#1f2937' : '#f3f4f6')
})

onMounted(() => {
  // The launcher must never survive a reload.
  if (isMobile.value) $storex.ui.closeMobileMenu()
})
</script>

<template>
  <div
    v-if="uiReady"
    class="relative h-full w-full bg-base-100"
    :data-theme="$ui.theme"
  >
    <Login v-if="isLogin" />

    <template v-else>
      <!-- Phones and tablets (<= 1024px): one purpose-built app shell. The
           desktop sidebar is not rendered at all — the mobile experience lives
           in components/mobile (top bar, tab bar, launcher). -->
      <MobileShell v-if="isMobile && !isFullScreenRoute" />

      <div v-else-if="isFullScreenRoute" class="h-full w-full">
        <RouterView />
      </div>

      <!-- Desktop / dockview shell -->
      <div v-else class="flex h-full w-full flex-row">
        <DesktopSidebar
          :user-name="$user?.username || 'User'"
          :user-subtitle="'Pro'"
          @settings="openAccountSettings"
        />

        <div class="flex min-h-0 min-w-0 grow flex-col">
          <RouterView />
        </div>
      </div>

      <Toast />

      <!-- Global "New project" modal — opened from any launcher
           (mobile menu, sidebar AppsSection, WindowsMenu, QuickBar) through the
           ui store flag `newProject`, and from the file explorer with
           `$ui.showNewProject({ path })` so the dialog starts on that folder. -->
      <modal
        v-if="$ui.newProject"
        close="true"
        @close="$ui.showNewProject(false)"
      >
        <!-- Keyed by the requested folder, so a new request re-initialises the
             form (and its prefilled path) instead of reusing the previous one. -->
        <NewProject :key="String($ui.newProject?.path || 'new-project')" />
      </modal>
    </template>
  </div>

  <div
    v-else
    class="flex h-full w-full flex-col items-center justify-center px-4 py-2 font-2xl"
  >
    <div class="animate-pulse font-mono text-green-600">Wake up, codx-junior...</div>
  </div>
</template>
