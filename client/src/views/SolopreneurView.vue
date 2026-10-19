<script setup>
import { computed, ref, watch, onMounted, onBeforeUnmount } from 'vue'
import { useRoute } from 'vue-router'
import { $storex } from '@/store'
import { useSolopreneur } from '@/components/solopreneur/useSolopreneur'
import SolopreneurSidebar from '@/components/solopreneur/SolopreneurSidebar.vue'
import SolopreneurTopbar from '@/components/solopreneur/SolopreneurTopbar.vue'
import SolopreneurSummary from '@/components/solopreneur/SolopreneurSummary.vue'
import SolopreneurAccount from '@/components/solopreneur/SolopreneurAccount.vue'
import SolopreneurProjects from '@/components/solopreneur/SolopreneurProjects.vue'
import SolopreneurWallet from '@/components/solopreneur/SolopreneurWallet.vue'
import SolopreneurUpdates from '@/components/solopreneur/SolopreneurUpdates.vue'
import SolopreneurMessages from '@/components/solopreneur/SolopreneurMessages.vue'
import SolopreneurModal from '@/components/solopreneur/SolopreneurModal.vue'

// Dockview panels hand their `params` down to the panel component (same
// convention as views/ChatView.vue). Declaring it keeps it from leaking onto
// the root element as a DOM attribute when the view is hosted as a panel.
defineProps({ params: { type: Object, default: () => ({}) } })

const route = useRoute()
const { state, syncIdentity, closeModal, setModule, setViewportWidth } = useSolopreneur()

const rootEl = ref(null)
let resizeObserver = null

const VIEWS = {
  summary: SolopreneurSummary,
  account: SolopreneurAccount,
  projects: SolopreneurProjects,
  wallet: SolopreneurWallet,
  updates: SolopreneurUpdates,
  messages: SolopreneurMessages
}

// ── Active module ───────────────────────────────────────────────────────────
// This screen has TWO hosts (see router/index.ts + config/apps.js):
//
//   • single / mobile mode → "/solopreneur/:module?" — the ROUTE owns it.
//   • desktop mode         → a dockview panel on ".../desktop" — the route must
//     stay put, so the shared state owns it (`state.module`, switched by the
//     sidebar through goModule()).
//
// Here we only mirror ROUTE → state, and only while the solopreneur route is
// the active one; when hosted in a panel the state keeps whatever was clicked.
const activeModule = computed(() => state.module)
const currentView = computed(() => VIEWS[activeModule.value])

watch(
  () => [route.name, route.params.module],
  () => {
    if (route.name === 'solopreneur') setModule(route.params.module || 'summary')
  },
  { immediate: true }
)

// ── Responsive shell ────────────────────────────────────────────────────────
// Breakpoints cannot describe this screen: as a dockview panel it is narrower
// than the window, and inside the route host it is the window. Media queries
// would read the window, container queries ("@container" + "@5xl:") proved
// unreliable here — the rail kept `w-full` while the row direction was already
// applied, so `shrink-0` let it swallow the whole row and the content column
// (`flex-1 min-w-0`) collapsed to 0px: only the left bar was visible.
//
// So we MEASURE the width the view actually gets and publish it to the shared
// state (`setViewportWidth`). Components then switch between mutually exclusive
// class sets, which cannot be reordered by the CSS build.
function measure() {
  const el = rootEl.value
  if (!el) return
  const width = el.clientWidth || el.getBoundingClientRect().width
  setViewportWidth(width)
}

// Close any open dialog when the module changes (nav click / deep link / back).
watch(activeModule, () => closeModal())

// Overlay real identity (current user + active project) on the seeded profile.
watch(() => $storex.projects.activeProject, () => syncIdentity())

function onKeydown(e) {
  if (e.key === 'Escape' && state.ui.modal) closeModal()
}

onMounted(() => {
  syncIdentity()
  measure()

  if (typeof ResizeObserver !== 'undefined') {
    resizeObserver = new ResizeObserver(measure)
    if (rootEl.value) resizeObserver.observe(rootEl.value)
  }

  // ResizeObserver is the primary source; the window listener keeps the tiers
  // correct even if the host resizes without changing this element's box.
  window.addEventListener('resize', measure)
  window.addEventListener('keydown', onKeydown)
})

onBeforeUnmount(() => {
  if (resizeObserver) {
    resizeObserver.disconnect()
    resizeObserver = null
  }
  window.removeEventListener('resize', measure)
  window.removeEventListener('keydown', onKeydown)
})
</script>

<template>
  <!-- Explicit, non-overlapping classes: `flex-row` always ships with the fixed
       rail width, `flex-col` always with `w-full`. That pairing is what keeps
       the content column from collapsing in the desktop (panel) host. -->
  <div
    ref="rootEl"
    class="h-full w-full min-h-0 overflow-hidden bg-base-200 text-base-content flex"
    :class="state.viewport.isWide ? 'flex-row' : 'flex-col'"
  >
    <SolopreneurSidebar :active-module="activeModule" :wide="state.viewport.isWide" />

    <div class="flex-1 min-w-0 min-h-0 flex flex-col overflow-hidden">
      <SolopreneurTopbar />

      <main class="flex-1 min-h-0 overflow-y-auto px-4 md:px-8 xl:px-10 py-6" role="main">
        <component :is="currentView" :key="activeModule" />
      </main>
    </div>

    <SolopreneurModal />
  </div>
</template>