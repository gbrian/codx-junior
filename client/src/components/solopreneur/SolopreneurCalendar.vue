<script setup>
import { computed } from 'vue'
import { useSolopreneur } from './useSolopreneur'

const { state, t, openModal } = useSolopreneur()

const groups = computed(() => {
  const order = []
  state.events.forEach(e => { if (!order.includes(e.group)) order.push(e.group) })
  return order.map(group => ({ group, items: state.events.filter(e => e.group === group) }))
})
</script>

<template>
  <section class="bg-base-100 border border-base-content/10 rounded-2xl shadow-sm p-6">
    <h2 class="text-base font-semibold">{{ t('cal.title') }}</h2>

    <div class="mt-6 flex flex-col gap-6">
      <div v-for="g in groups" :key="g.group">
        <h3 class="text-[11px] font-semibold tracking-widest text-base-content/40 mb-3">{{ g.group }}</h3>
        <div class="border-l border-base-content/10 pl-4 flex flex-col gap-4">
          <button
            v-for="e in g.items"
            :key="e.id"
            type="button"
            class="text-left group"
            @click="openModal('event', e.id)"
          >
            <div class="text-sm font-semibold">{{ e.time }}</div>
            <div class="text-sm font-semibold group-hover:text-codx-primary transition-colors">{{ e.title }}</div>
            <div class="text-xs text-base-content/50">{{ e.meta }}</div>
          </button>
        </div>
      </div>
    </div>
  </section>
</template>