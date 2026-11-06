<script setup>
import { computed, onBeforeUnmount, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { $storex } from '@/store'
import { MOBILE_ROUTE_TITLES } from '@/config/mobile'
import { useMobileViewport } from '@/composables/useMobileViewport'
import MobileTopBar from './MobileTopBar.vue'
import MobileTabBar from './MobileTabBar.vue'
import MobileMenu from './MobileMenu.vue'

const route = useRoute()
const router = useRouter()
const { height, keyboardOpen } = useMobileViewport()

const meta = computed(() => route.meta?.mobile || {})
const project = computed(() => $storex.projects.activeProject)
const title = computed(() => meta.value.title || MOBILE_ROUTE_TITLES[route.name] || 'codx-junior')
const subtitle = computed(() => project.value?.project_name || 'codx-junior')

const projectLoading = computed(() => $storex.ui.projectLoadingState || {})

const hideTopBar = computed(() => !!meta.value.hideTopBar)
const hideTabs = computed(() => !!meta.value.hideTabs || keyboardOpen.value)
const fullScreen = computed(() => !!meta.value.fullScreen)

// Tab roots own their header/menu; every other screen gets the generic app bar
// with a back arrow. A route can override this with `meta.mobile.back`.
const showBack = computed(() => meta.value.back ?? ![
  'home',
  'chats',
  'kanban',
  'activity',
  'messenger',
  'chat',
  'chat-workspace'
].includes(route.name))

const shellStyle = computed(() => ({
  height: height.value ? `${height.value}px` : '100%'
}))

function openMenu() {
  $storex.ui.openMobileMenu()
}

function closeMenu() {
  if ($storex.ui.mobileMenuOpen) $storex.ui.closeMobileMenu()
}

// A new screen always starts with the launcher closed. Blurring the focused
// field closes the on-screen keyboard, which otherwise stays open (and covers
// the destination) after tapping a result.
watch(() => route.fullPath, () => {
  closeMenu()
  const active = document.activeElement
  if (active && typeof active.blur === 'function' && ['INPUT', 'TEXTAREA', 'SELECT'].includes(active.tagName)) {
    active.blur()
  }
})

onMounted(() => {
  // Deep links to the dockview workspace are meaningless on a phone. Keep the
  // user on a mobile screen instead of rendering the desktop window manager.
  if (route.name === 'codx-junior-split') {
    router.replace({ name: 'home' })
    return
  }
  closeMenu()
})

onBeforeUnmount(() => {
  document.documentElement.classList.remove('mobile-menu-open')
})
</script>

<template>
  <div
    v-if="!fullScreen"
    class="mobile-shell flex w-full flex-col overflow-hidden bg-base-300 text-base-content"
    :style="shellStyle"
  >
    <MobileTopBar
      v-if="!hideTopBar"
      :title="title"
      :subtitle="subtitle"
      :show-back="showBack"
      @menu="openMenu"
    />

    <!-- Screens that own their header still need the iOS status-bar inset. -->
    <div v-if="hideTopBar" class="safe-area-top shrink-0 bg-base-300" aria-hidden="true"></div>

    <main class="mobile-content relative flex min-h-0 flex-1 flex-col overflow-hidden">
      <RouterView v-slot="{ Component }">
        <Transition name="mobile-page" mode="out-in">
          <div class="h-full w-full">
            <component :is="Component" />
          </div>
        </Transition>
      </RouterView>
    </main>

    <MobileTabBar v-if="!hideTabs" />

    <!-- Project switch feedback: switching project reloads settings, chats,
         models and boards. Without this the launcher closes and the old screen
         sits frozen until the new project is ready. -->
    <Transition name="mobile-page">
      <div
        v-if="projectLoading.isLoading"
        class="fixed inset-0 z-[105] flex flex-col items-center justify-center gap-3 bg-base-300/95 px-8 text-center backdrop-blur-sm"
        role="status"
        aria-live="polite"
        aria-busy="true"
      >
        <span class="loading loading-spinner loading-lg text-primary"></span>
        <p class="text-sm font-semibold text-base-content/80">
          Loading {{ projectLoading.projectName || 'project' }}…
        </p>
        <p class="text-[11px] text-base-content/40">
          Settings, chats and boards are being prepared
        </p>
      </div>
    </Transition>

    <MobileMenu />
  </div>

  <RouterView v-else />
</template>
