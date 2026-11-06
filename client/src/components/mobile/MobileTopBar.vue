<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { $storex } from '@/store'

const props = defineProps({
  title: { type: String, default: 'codx-junior' },
  subtitle: { type: String, default: '' },
  showBack: { type: Boolean, default: false }
})

const emit = defineEmits(['menu'])

const route = useRoute()
const router = useRouter()

const project = computed(() => $storex.projects.activeProject)
const user = computed(() => $storex.users.user || {})
const avatar = computed(() => user.value?.avatar || '')
const username = computed(() => user.value?.username || 'User')
const initial = computed(() => (username.value || 'U').trim().charAt(0).toUpperCase())
const connected = computed(() => $storex.session.connected !== false)

function goBack() {
  if (window.history.state?.back) {
    router.back()
    return
  }
  // Deep link / fresh tab: there is no in-app history to go back to.
  if (route.name !== 'home') {
    router.push({ name: 'home' })
  }
}
</script>

<template>
  <header class="mobile-topbar relative z-30 shrink-0 border-b border-base-content/10 bg-base-200/90 backdrop-blur-md">
    <div class="safe-area-top">
      <div class="flex h-14 items-center gap-1 px-1.5">
        <!-- Back on nested screens, menu on tab-level screens -->
        <button
          v-if="showBack"
          type="button"
          class="mobile-icon-btn"
          aria-label="Go back"
          @click="goBack"
        >
          <i class="fa-solid fa-arrow-left text-base"></i>
        </button>
        <button
          v-else
          type="button"
          class="mobile-icon-btn"
          aria-label="Open menu"
          @click="emit('menu')"
        >
          <i class="fa-solid fa-bars text-base"></i>
        </button>

        <div class="min-w-0 flex-1 px-1">
          <h1 class="truncate text-[15px] font-semibold leading-tight text-base-content">
            {{ title }}
          </h1>
          <p class="flex items-center gap-1.5 truncate text-[10px] leading-tight text-base-content/45">
            <span
              class="inline-block h-1.5 w-1.5 shrink-0 rounded-full"
              :class="connected ? 'bg-success' : 'bg-error'"
              aria-hidden="true"
            ></span>
            <span class="truncate">{{ subtitle || project?.project_name || 'codx-junior' }}</span>
          </p>
        </div>

        <button
          type="button"
          class="flex h-10 min-w-10 items-center gap-1.5 rounded-full pl-1 pr-2 active:bg-base-content/10"
          :aria-label="`${username} — open menu`"
          @click="emit('menu')"
        >
          <img
            v-if="avatar"
            :src="avatar"
            :alt="username"
            class="h-8 w-8 rounded-full border border-base-content/15 object-cover"
          />
          <span
            v-else
            class="grid h-8 w-8 place-items-center rounded-full border border-primary/30 bg-primary/15 text-xs font-bold text-primary"
            aria-hidden="true"
          >{{ initial }}</span>
          <i class="fa-solid fa-chevron-down text-[9px] text-base-content/40" aria-hidden="true"></i>
        </button>
      </div>
    </div>
  </header>
</template>
