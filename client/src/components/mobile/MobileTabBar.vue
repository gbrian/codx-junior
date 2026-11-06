<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { $storex } from '@/store'
import { MOBILE_TABS } from '@/config/mobile'

const route = useRoute()
const router = useRouter()

const menuOpen = computed(() => $storex.ui.mobileMenuOpen)

const activeTab = computed(() => {
  if (menuOpen.value) return 'more'
  const explicit = route.meta?.mobile?.tab
  if (explicit) return explicit
  const name = route.name
  if (name === 'home' || name === 'root') return 'home'
  if (name === 'chats' || name === 'chat' || name === 'chat-workspace' || name === 'new-chat') return 'chats'
  if (name === 'kanban') return 'tasks'
  if (name === 'activity') return 'activity'
  return 'more'
})

function select(tab) {
  if (tab.action === 'menu') {
    $storex.ui.openMobileMenu()
    return
  }
  // Tapping the tab you are already on is a no-op instead of a redundant
  // route push (which would add history entries and re-mount the screen).
  if (route.meta?.mobile?.tab === tab.key && route.name === tab.route?.name) return
  $storex.ui.closeMobileMenu()
  router.push(tab.route)
}
</script>

<template>
  <nav
    class="mobile-tabbar relative z-30 shrink-0 border-t border-base-content/10 bg-base-200/95 backdrop-blur-md"
    aria-label="Primary navigation"
    role="tablist"
  >
    <div class="safe-area-bottom">
      <div class="grid h-[3.75rem] grid-cols-5">
        <button
          v-for="tab in MOBILE_TABS"
          :key="tab.key"
          type="button"
          role="tab"
          class="relative flex min-w-0 flex-col items-center justify-center gap-0.5 px-1 transition-colors duration-150 active:bg-base-content/5"
          :class="activeTab === tab.key ? 'text-primary' : 'text-base-content/50'"
          :aria-selected="activeTab === tab.key"
          :aria-label="tab.label"
          @click="select(tab)"
        >
          <span
            class="absolute top-0 h-0.5 w-8 rounded-full bg-primary transition-opacity duration-150"
            :class="activeTab === tab.key ? 'opacity-100' : 'opacity-0'"
            aria-hidden="true"
          ></span>
          <i :class="tab.icon" class="text-[1.15rem] leading-none" aria-hidden="true"></i>
          <span class="max-w-full truncate text-[10px] font-medium leading-none">{{ tab.label }}</span>
        </button>
      </div>
    </div>
  </nav>
</template>
