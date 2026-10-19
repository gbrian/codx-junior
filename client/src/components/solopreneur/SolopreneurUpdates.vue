<script setup>
import { ref, computed } from 'vue'
import { useSolopreneur } from './useSolopreneur'

const { state, t, markAllRead } = useSolopreneur()

const filter = ref('all')
const chips = computed(() => [
  { id: 'all', label: t('up.filterAll') },
  { id: 'system', label: t('up.filterSystem') },
  { id: 'release', label: t('up.filterRelease') }
])

const list = computed(() =>
  state.updates.filter(u => filter.value === 'all' || u.kind === filter.value)
)
</script>

<template>
  <div class="mx-auto w-full max-w-3xl">
    <section class="bg-base-100 border border-base-content/10 rounded-2xl shadow-sm p-6 md:p-8">
      <div class="flex items-start justify-between gap-4">
        <div>
          <h2 class="text-base font-semibold">{{ t('up.all') }}</h2>
          <p class="text-sm text-base-content/50 mt-1.5">{{ t('up.desc') }}</p>
        </div>
        <button
          type="button"
          class="h-9 px-4 rounded-full border border-base-content/20 bg-base-100 text-sm font-semibold hover:bg-base-200 transition shrink-0"
          @click="markAllRead"
        >{{ t('up.markAllRead') }}</button>
      </div>

      <!-- Filters -->
      <div class="flex flex-wrap gap-2 mt-5">
        <button
          v-for="c in chips"
          :key="c.id"
          type="button"
          class="h-8 px-3.5 rounded-full border text-xs font-semibold transition"
          :class="filter === c.id
            ? 'bg-base-content text-base-100 border-base-content'
            : 'border-base-content/20 text-base-content/60 hover:bg-base-200'"
          :aria-pressed="filter === c.id"
          @click="filter = c.id"
        >{{ c.label }}</button>
      </div>

      <!-- List -->
      <ul v-if="list.length" class="mt-6 flex flex-col gap-5">
        <li v-for="u in list" :key="u.id" class="flex gap-3.5">
          <span
            class="w-2 h-2 rounded-full shrink-0 mt-1.5"
            :class="u.tone === 'green' ? 'bg-success' : 'bg-codx-primary'"
            aria-hidden="true"
          ></span>
          <div>
            <div class="flex items-center gap-2 flex-wrap">
              <h4 class="text-sm font-semibold">{{ u.title }}</h4>
              <span
                class="text-[11px] font-semibold px-2.5 py-0.5 rounded-full"
                :class="u.tone === 'green' ? 'text-success bg-success/15' : 'text-codx-primary bg-codx-primary/10'"
              >{{ u.badge }}</span>
            </div>
            <p class="text-sm text-base-content/60 mt-1.5 leading-relaxed">{{ u.text }}</p>
            <time class="block text-[11px] text-base-content/40 mt-1.5">{{ u.when }}</time>
          </div>
        </li>
      </ul>
      <div v-else class="mt-6 py-12 text-center text-sm text-base-content/50 bg-base-200 rounded-xl">
        {{ t('up.empty') }}
      </div>
    </section>
  </div>
</template>