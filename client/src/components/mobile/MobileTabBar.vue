<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { $storex } from '@/store'
import { MOBILE_TABS } from '@/config/mobile'

const route = useRoute()
const router = useRouter()

const menuOpen = computed(() => $storex.ui.mobileMenuOpen)
const isCompanyMode = computed(() => $storex.users.isCompanyMode)

// Company mode gets a manager-oriented tab bar. The full application remains
// one tap away in "More" (which always contains everything).
const companyTabs = [
  {
    key: 'company',
    label: 'Company',
    icon: 'fa-solid fa-building-columns',
    route: { name: 'company-home' }
  },
  {
    key: 'assistant',
    label: 'Ask',
    icon: 'fa-solid fa-wand-magic-sparkles',
    action: 'assistant'
  },
  {
    key: 'add-person',
    label: 'Add person',
    icon: 'fa-solid fa-user-plus',
    route: { name: 'company-home', query: { assistant: 'add-person' } }
  },
  {
    key: 'create-team',
    label: 'New team',
    icon: 'fa-solid fa-people-group',
    route: { name: 'company-home', query: { assistant: 'create-team' } }
  },
  {
    key: 'more',
    label: 'More',
    icon: 'fa-solid fa-grip',
    action: 'menu'
  }
]

const tabs = computed(() => (isCompanyMode.value ? companyTabs : MOBILE_TABS))

const activeTab = computed(() => {
  if (menuOpen.value) return 'more'
  if (isCompanyMode.value) {
    return route.name === 'company-home' ? 'company' : 'more'
  }
  const explicit = route.meta?.mobile?.tab
  if (explicit) return explicit
  const name = route.name
  if (name === 'home' || name === 'root') return 'home'
  if (name === 'chats' || name === 'chat' || name === 'chat-workspace' || name === 'new-chat') return 'chats'
  if (name === 'kanban') return 'tasks'
  return 'more'
})

function select(tab) {
  if (tab.action === 'menu') {
    $storex.ui.openMobileMenu()
    return
  }
  if (tab.action === 'assistant') {
    const companyId = $storex.users.primaryCompanyId
    router.push({
      name: 'company-home',
      params: companyId ? { companyId } : {},
      query: { assistant: 'open' }
    })
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
      <div
        class="grid h-[3.75rem]"
        :style="{ gridTemplateColumns: `repeat(${tabs.length}, minmax(0, 1fr))` }"
      >
        <button
          v-for="tab in tabs"
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
