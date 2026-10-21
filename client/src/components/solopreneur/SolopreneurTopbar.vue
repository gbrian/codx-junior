<script setup>
import { ref, computed } from 'vue'
import { useSolopreneur } from './useSolopreneur'

// `openModal` is NOT needed here: the bar no longer creates projects or logs
// out (the account menu lives in the sidebar brand header, see
// SolopreneurSidebar.vue).
const { state, t, dateLine, goModule, setLang, searchResults } = useSolopreneur()

// The primary "+" captures a ticket; the whole dialog lives in the host view
// (views/SolopreneurView.vue) so this bar stays presentational.
const emit = defineEmits(['new-ticket'])

const LANGS = [
  { code: 'EN', label: 'English' },
  { code: 'ES', label: 'Español' },
  { code: 'FR', label: 'Français' }
]

const openMenu = ref('') // '' | 'search' | 'lang'
const query = ref('')
const results = computed(() => searchResults(query.value))

function closeMenus() { openMenu.value = '' }
function chooseResult(r) { closeMenus(); query.value = ''; goModule(r.module) }
function chooseLang(code) { setLang(code); closeMenus() }
</script>

<template>
  <!-- One row at every width: no `flex-wrap`. The greeting (`min-w-0`) is the
       only element allowed to shrink; the action group never does. -->
  <header
    class="shrink-0 bg-base-100 border-b border-base-content/10
           px-3 md:px-8 xl:px-10 py-2.5 md:py-3.5
           flex items-center gap-2 md:gap-3"
  >
    <!-- Greeting -->
    <div class="mr-auto min-w-0 flex-1">
      <h1 class="text-base md:text-xl font-semibold tracking-tight truncate leading-tight">
        {{ t('hello') }}, {{ state.user.first }}
      </h1>
      <p class="hidden sm:block text-sm text-base-content/50 truncate">{{ dateLine() }}</p>
    </div>

    <!-- Actions -->
    <div class="flex items-center gap-1.5 md:gap-2 shrink-0">
      <!-- Search -->
      <div class="relative shrink-0">
        <label class="sr-only" for="solo-search">{{ t('search') }}</label>
        <input
          id="solo-search"
          v-model="query"
          type="search"
          autocomplete="off"
          :placeholder="t('search')"
          class="h-9 md:h-10 w-24 sm:w-40 md:w-60 rounded-full border border-base-content/15 bg-base-100
                 px-3 md:px-4 text-sm outline-none focus:border-codx-primary focus:ring-2 focus:ring-codx-primary/20"
          @input="openMenu = 'search'"
          @focus="openMenu = 'search'"
        />
        <div
          v-if="openMenu === 'search' && query.trim()"
          class="absolute right-0 top-11 z-50 w-80 max-w-[80vw] bg-base-100 border border-base-content/10 rounded-xl shadow-2xl p-2"
        >
          <button
            v-for="(r, i) in results"
            :key="i"
            type="button"
            class="block w-full text-left px-3 py-2 rounded-lg hover:bg-base-200 transition-colors"
            @click="chooseResult(r)"
          >
            <div class="text-sm text-base-content truncate">{{ r.label }}</div>
            <div class="text-xs text-base-content/40">{{ r.meta }}</div>
          </button>
          <div v-if="!results.length" class="px-3 py-2 text-sm text-base-content/40">
            {{ t('search') }} · 0
          </div>
        </div>
      </div>

      <!-- Language -->
      <div class="relative shrink-0">
        <button
          type="button"
          class="h-9 md:h-10 inline-flex items-center gap-1.5 md:gap-2 px-2.5 md:px-4 rounded-full border border-base-content/15 bg-base-100 text-sm font-medium hover:bg-base-200 transition-colors"
          aria-haspopup="true"
          :aria-expanded="openMenu === 'lang'"
          @click="openMenu = openMenu === 'lang' ? '' : 'lang'"
        >
          <i class="fa-solid fa-globe text-base-content/60 hidden md:inline"></i>
          <span>{{ state.lang }}</span>
          <i class="fa-solid fa-chevron-down text-[10px] text-base-content/40 hidden md:inline"></i>
        </button>
        <div
          v-if="openMenu === 'lang'"
          class="absolute right-0 top-11 z-50 w-44 bg-base-100 border border-base-content/10 rounded-xl shadow-2xl p-1.5"
        >
          <button
            v-for="l in LANGS"
            :key="l.code"
            type="button"
            class="block w-full text-left px-3 py-2 rounded-lg text-sm hover:bg-base-200 transition-colors"
            :class="state.lang === l.code ? 'text-codx-primary font-semibold' : 'text-base-content/80'"
            @click="chooseLang(l.code)"
          >
            {{ l.label }}
          </button>
        </div>
      </div>

      <!-- Quick ticket — the primary action: capture a ticket without leaving home.
           It is the ONLY action of this bar: project creation and the account
           menu (Account / Wallet / Log out) do not belong here — the account
           entry point is the sidebar brand header, and projects are created from
           the Projects module. -->
      <button
        type="button"
        class="h-9 md:h-10 inline-flex items-center justify-center gap-2 px-3 md:px-5 rounded-full bg-base-content text-base-100 text-sm font-semibold hover:opacity-90 active:scale-95 transition shrink-0"
        :aria-label="t('sp.newTicket')"
        :title="t('sp.newTicket')"
        @click="emit('new-ticket')"
      >
        <i class="fa-solid fa-plus"></i>
        <span class="hidden md:inline">{{ t('sp.newTicket') }}</span>
      </button>
    </div>
  </header>

  <!-- Outside-click catcher for the dropdowns -->
  <div v-if="openMenu" class="fixed inset-0 z-40" @click="closeMenus"></div>
</template>