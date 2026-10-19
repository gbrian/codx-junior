<script setup>
import { useSolopreneur } from './useSolopreneur'

defineProps({
  activeModule: { type: String, default: 'summary' },
  // Width tier measured by the view (see views/SolopreneurView.vue). When true
  // the rail sits BESIDE the content (fixed 276px); otherwise it is a horizontal
  // rail ABOVE it (mobile / narrow panel).
  wide: { type: Boolean, default: false }
})

const { state, t, goModule, openModal } = useSolopreneur()
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
    <!-- Brand -->
    <div
      class="flex items-center justify-between gap-2"
      :class="wide ? 'px-0 py-0 mb-10' : 'px-4 py-3'"
    >
      <div class="flex items-center gap-2.5">
        <svg viewBox="0 0 24 24" width="26" height="26" aria-hidden="true" class="text-codx-primary">
          <rect x="2.5" y="2.5" width="19" height="19" rx="5.5" fill="none" stroke="currentColor" stroke-width="2.4" />
          <rect x="7" y="7" width="6" height="6" rx="1.6" fill="currentColor" />
        </svg>
        <span class="text-lg font-semibold tracking-tight">codx-junior</span>
      </div>
      <button
        v-if="!wide"
        type="button"
        class="p-2 rounded-lg text-base-content/60 hover:bg-base-200 transition-colors"
        :title="t('logout')"
        @click="openModal('logout')"
      >
        <i class="fa-solid fa-right-from-bracket"></i>
      </button>
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
    <nav
      class="flex gap-1"
      :class="wide
        ? 'flex-col gap-0.5'
        : 'flex-row px-2 pb-2 overflow-x-auto'"
      aria-label="Solopreneur"
    >
      <button
        v-for="id in ['summary', 'account', 'projects', 'wallet', 'updates', 'messages']"
        :key="id"
        type="button"
        class="flex items-center gap-3.5 px-3.5 py-2.5 rounded-xl text-sm font-medium whitespace-nowrap transition-colors shrink-0"
        :class="activeModule === id
          ? 'text-codx-primary font-semibold bg-codx-primary/5'
          : 'text-base-content/70 hover:text-base-content hover:bg-base-200'"
        :aria-current="activeModule === id ? 'page' : undefined"
        @click="goModule(id)"
      >
        <span
          class="w-2 h-2 rounded-full shrink-0"
          :class="activeModule === id ? 'bg-codx-primary' : 'bg-base-content/30'"
          aria-hidden="true"
        ></span>
        <span>{{ t('nav.' + id) }}</span>
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
  </aside>
</template>