<script setup>
import { ref } from 'vue'
import { useSolopreneur } from './useSolopreneur'

defineProps({
  activeModule: { type: String, default: 'summary' },
  // Width tier measured by the view (see views/SolopreneurView.vue). When true
  // the rail sits BESIDE the content (fixed 276px); otherwise it is a horizontal
  // rail ABOVE it (mobile / narrow panel).
  wide: { type: Boolean, default: false }
})

const { state, t, goModule, openModal, setLang } = useSolopreneur()

// Order mirrors the approved mockup: the work sections (projects, sprints)
// follow the summary, before the billing/support ones.
// "account" is NOT here: it lives in the header dropdown (Account / Wallet /
// Log out), so this row keeps only the sections you switch between.
const NAV = ['summary', 'projects', 'sprints', 'wallet', 'updates', 'messages']

// The horizontal (mobile / narrow panel) bar is icon-only: labels do not fit
// there, so each section gets one glyph. The vertical rail keeps the labels.
const ICONS = {
  summary: 'fa-solid fa-gauge-high',
  projects: 'fa-solid fa-folder',
  sprints: 'fa-solid fa-list-check',
  wallet: 'fa-solid fa-wallet',
  updates: 'fa-solid fa-bell',
  messages: 'fa-solid fa-comments'
}

// Languages offered in the account menu. `code` matches `state.lang` and the
// LANG_LOCALE map used by the date / money formatters.
const LANGS = [
  { code: 'EN', label: 'English' },
  { code: 'ES', label: 'Español' },
  { code: 'FR', label: 'Français' }
]

// Account menu. It lives in the brand row because that row is the TOP-MOST
// header of this screen on narrow layouts (above the nav row and the greeting
// topbar) — it replaces the logout icon that used to sit there.
const accountOpen = ref(false)
function toggleAccount() { accountOpen.value = !accountOpen.value }
function closeAccount() { accountOpen.value = false }
// Both destinations close the menu first, so the section / dialog is not
// painted underneath an open panel.
function chooseModule(id) { closeAccount(); goModule(id) }
function chooseLogout() { closeAccount(); openModal('logout') }
// The language selector lives here too (it used to sit in the greeting topbar):
// the menu STAYS OPEN on purpose, so the change is visible in place.
function chooseLang(code) { setLang(code) }
</script>

<template>
  <!-- Width, border and padding live in ONE ternary each: the wide classes and
       the narrow ones are never present at the same time, so no CSS ordering
       can leave the rail at `w-full` while the parent is already a row. -->
  <aside
    class="shrink-0 bg-base-100 border-base-content/10 flex flex-col"
    :class="wide
      ? 'w-[276px] h-full border-r px-6 py-8'
      : 'w-full border-b'"
  >
    <!-- Brand + account. On narrow layouts this IS the top header, so the
         account dropdown belongs here (right side) and not in the nav row. -->
    <div
      class="flex items-center justify-between gap-2"
      :class="wide ? 'px-0 py-0 mb-10' : 'px-4 py-3'"
    >
      <div class="flex items-center gap-2.5 min-w-0">
        <svg viewBox="0 0 24 24" width="26" height="26" aria-hidden="true" class="text-codx-primary shrink-0">
          <rect x="2.5" y="2.5" width="19" height="19" rx="5.5" fill="none" stroke="currentColor" stroke-width="2.4" />
          <rect x="7" y="7" width="6" height="6" rx="1.6" fill="currentColor" />
        </svg>
        <span class="text-lg font-semibold tracking-tight truncate">codx-junior</span>
      </div>

      <!-- Account trigger: avatar + wallet credits (credits only where there is
           room — the wide rail is 228px of content and already shows the
           identity block, so there it stays avatar + chevron). The wrapper rises
           above the outside-click catcher (`z-40`) while open, so the same click
           that closes the menu can also reopen it. -->
      <div class="relative shrink-0" :class="accountOpen ? 'z-50' : ''">
        <button
          type="button"
          class="inline-flex items-center gap-1.5 pl-1 pr-1.5 py-1 rounded-full
                 border border-base-content/15 bg-base-100 text-sm
                 hover:bg-base-200 active:scale-95 transition"
          aria-haspopup="true"
          :aria-expanded="accountOpen"
          :aria-label="t('nav.account')"
          :title="state.user.name"
          @click="toggleAccount"
        >
          <span class="w-7 h-7 rounded-full overflow-hidden shrink-0 grid place-items-center text-[11px] font-semibold text-white bg-codx-primary">
            <img
              v-if="state.user.avatar"
              :src="state.user.avatar"
              :alt="state.user.name"
              class="w-full h-full object-cover"
            />
            <span v-else aria-hidden="true">{{ state.user.initials }}</span>
          </span>
          <template v-if="!wide">
            <i class="fa-solid fa-wallet text-[11px] text-base-content/40" aria-hidden="true"></i>
            <span class="text-xs font-semibold tabular-nums">{{ state.wallet.credits }}</span>
          </template>
          <i class="fa-solid fa-chevron-down text-[10px] text-base-content/40" aria-hidden="true"></i>
        </button>

        <div
          v-if="accountOpen"
          class="absolute right-0 top-11 z-50 w-56 max-w-[calc(100vw-2rem)] bg-base-100 border border-base-content/10 rounded-xl shadow-2xl p-1.5"
        >
          <div class="px-3 py-2 mb-1 border-b border-base-content/10">
            <div class="text-sm font-semibold truncate">{{ state.user.name }}</div>
            <div class="text-xs text-base-content/50 truncate">{{ state.user.email }}</div>
          </div>
          <button
            type="button"
            class="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm text-base-content/80 hover:bg-base-200 transition-colors"
            :class="state.module === 'account' ? 'text-codx-primary font-semibold' : ''"
            @click="chooseModule('account')"
          >
            <i class="fa-solid fa-user w-4 text-center" aria-hidden="true"></i>
            <span>{{ t('nav.account') }}</span>
          </button>
          <button
            type="button"
            class="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm text-base-content/80 hover:bg-base-200 transition-colors"
            :class="state.module === 'wallet' ? 'text-codx-primary font-semibold' : ''"
            @click="chooseModule('wallet')"
          >
            <i class="fa-solid fa-wallet w-4 text-center" aria-hidden="true"></i>
            <span>{{ t('nav.wallet') }}</span>
          </button>

          <!-- Language: moved here from the greeting topbar. Three short codes
               fit the 224px panel, so no nested dropdown is needed. -->
          <div class="mt-1 pt-2 border-t border-base-content/10">
            <div class="px-3 pb-1.5 text-[11px] font-semibold uppercase tracking-wide text-base-content/40">
              {{ t('language') }}
            </div>
            <div class="flex gap-1 px-1.5 pb-1">
              <button
                v-for="l in LANGS"
                :key="l.code"
                type="button"
                class="flex-1 px-1 py-1.5 rounded-lg text-xs font-semibold border transition-colors"
                :class="state.lang === l.code
                  ? 'border-codx-primary bg-codx-primary/5 text-codx-primary'
                  : 'border-base-content/15 text-base-content/60 hover:bg-base-200'"
                :aria-pressed="state.lang === l.code"
                :title="l.label"
                @click="chooseLang(l.code)"
              >
                {{ l.code }}
              </button>
            </div>
          </div>

          <button
            type="button"
            class="w-full flex items-center gap-2.5 px-3 py-2 mt-1 rounded-lg text-sm text-base-content/80 hover:bg-base-200 transition-colors border-t border-base-content/10"
            @click="chooseLogout()"
          >
            <i class="fa-solid fa-right-from-bracket w-4 text-center" aria-hidden="true"></i>
            <span>{{ t('logout') }}</span>
          </button>
        </div>
      </div>
    </div>

    <!-- User (rail layouts) -->
    <div v-if="wide" class="flex items-center gap-3.5 px-1 mb-11">
      <span
        v-if="state.user.avatar"
        class="w-11 h-11 rounded-full overflow-hidden shrink-0"
      >
        <img :src="state.user.avatar" :alt="state.user.name" class="w-full h-full object-cover" />
      </span>
      <span
        v-else
        class="w-11 h-11 rounded-full shrink-0 grid place-items-center text-white text-sm font-semibold bg-codx-primary"
        aria-hidden="true"
      >{{ state.user.initials }}</span>
      <div class="min-w-0">
        <div class="text-sm font-semibold truncate">{{ state.user.name }}</div>
        <div class="text-xs text-base-content/50 truncate">{{ state.user.email }}</div>
      </div>
    </div>

    <!-- Navigation -->
    <!-- Wide rail: dot + label. Horizontal bar (mobile): icon only, the label
         stays in `title` / `aria-label` so the row fits a phone width. -->
    <nav
      class="flex gap-1"
      :class="wide
        ? 'flex-col gap-0.5'
        : 'flex-row items-center justify-between px-2 pb-2 overflow-x-auto'"
      aria-label="Solopreneur"
    >
      <button
        v-for="id in NAV"
        :key="id"
        type="button"
        class="flex items-center rounded-xl text-sm font-medium whitespace-nowrap transition-colors shrink-0"
        :class="[
          wide ? 'gap-3.5 px-3.5 py-2.5' : 'justify-center w-11 h-10',
          activeModule === id
            ? 'text-codx-primary font-semibold bg-codx-primary/5'
            : 'text-base-content/70 hover:text-base-content hover:bg-base-200'
        ]"
        :aria-current="activeModule === id ? 'page' : undefined"
        :aria-label="!wide ? t('nav.' + id) : undefined"
        :title="!wide ? t('nav.' + id) : undefined"
        @click="goModule(id)"
      >
        <template v-if="wide">
          <span
            class="w-2 h-2 rounded-full shrink-0"
            :class="activeModule === id ? 'bg-codx-primary' : 'bg-base-content/30'"
            aria-hidden="true"
          ></span>
          <span>{{ t('nav.' + id) }}</span>
        </template>
        <i
          v-else
          class="text-base"
          :class="ICONS[id]"
          aria-hidden="true"
        ></i>
      </button>
    </nav>

    <!-- Footer (rail layouts) -->
    <div v-if="wide" class="flex mt-auto flex-col gap-3 pt-6">
      <button
        type="button"
        class="flex items-center gap-3.5 px-3.5 py-2.5 rounded-xl text-sm font-medium text-base-content/70 hover:text-base-content hover:bg-base-200 transition-colors"
        @click="openModal('logout')"
      >
        <i class="fa-solid fa-right-from-bracket text-base"></i>
        <span>{{ t('logout') }}</span>
      </button>
      <p class="text-[11px] text-base-content/40 px-3.5">
        {{ t('madeWith') }} <span aria-hidden="true">♡</span> by codx-junior
      </p>
    </div>

    <!-- Outside-click catcher for the account dropdown -->
    <div v-if="accountOpen" class="fixed inset-0 z-40" @click="closeAccount"></div>
  </aside>
</template>