<script setup>
import { computed, ref } from 'vue'
import { eventMeta, formatDateTime, relativeTime, statusMeta } from './companyMeta'

const props = defineProps({
  snapshot: { type: Object, default: null },
  busy: { type: Boolean, default: false }
})

const emit = defineEmits(['refresh'])

const filter = ref('')

const events = computed(() => {
  const all = (props.snapshot?.journal || []).slice().reverse()
  const wanted = filter.value.trim().toLowerCase()
  if (!wanted) return all
  return all.filter(event =>
    `${event.type} ${event.message} ${event.actor}`.toLowerCase().includes(wanted)
  )
})

const attention = computed(() => props.snapshot?.attention || [])
const missions = computed(() => props.snapshot?.missions || [])

function missionFor(item) {
  return missions.value.find(mission => mission.id === item.mission_id)
}

function openMission(item) {
  return missionFor(item)
}
</script>

<template>
  <div class="flex flex-col gap-4">
    <header class="flex items-center justify-between gap-2">
      <div>
        <h2 class="text-lg font-black flex items-center gap-2">
          <i class="fa-solid fa-clock-rotate-left text-primary"></i> Activity
        </h2>
        <p class="text-xs text-base-content/50">
          The audit journal: every company change, dispatch and autonomy cycle, in order.
        </p>
      </div>
      <div class="flex gap-2">
        <input v-model="filter" class="input input-sm input-bordered w-48" placeholder="Filter events..." />
        <button class="btn btn-sm btn-ghost btn-square" title="Reload" :disabled="busy" @click="emit('refresh')">
          <i class="fa-solid fa-rotate" :class="busy ? 'animate-spin' : ''"></i>
        </button>
      </div>
    </header>

    <div class="grid gap-4 xl:grid-cols-[1.5fr_1fr]">
      <!-- Timeline -->
      <section class="rounded-2xl border border-base-content/10 bg-base-100 p-4">
        <div v-if="!events.length" class="py-10 text-center text-sm text-base-content/40">
          <i class="fa-solid fa-clock-rotate-left text-2xl mb-2 block"></i>
          No events yet.
        </div>
        <ol v-else class="relative border-l border-base-content/10 ml-2">
          <li v-for="event in events" :key="event.id" class="ml-4 pb-4 last:pb-0">
            <span class="absolute -left-[9px] mt-1 w-4 h-4 rounded-full bg-base-100 border border-base-content/20 grid place-items-center">
              <i :class="[eventMeta(event.type).icon, eventMeta(event.type).tone, 'text-[8px]']"></i>
            </span>
            <div class="flex items-start gap-2">
              <div class="min-w-0 flex-1">
                <p class="text-sm leading-snug">{{ event.message || event.type }}</p>
                <p class="text-[10px] text-base-content/40">
                  <span class="font-mono">{{ event.type }}</span> · {{ event.actor }} ·
                  <span :title="formatDateTime(event.at)">{{ relativeTime(event.at) }}</span>
                  <span v-if="event.mission_id" class="ml-1">· mission {{ event.mission_id.slice(-6) }}</span>
                </p>
              </div>
            </div>
          </li>
        </ol>
      </section>

      <!-- Attention -->
      <section class="rounded-2xl border border-base-content/10 bg-base-100 p-4 h-fit">
        <h3 class="font-bold text-sm flex items-center gap-2 mb-3">
          <i class="fa-solid fa-circle-exclamation text-error"></i> Needs a human
        </h3>
        <div v-if="attention.length" class="flex flex-col gap-2">
          <div v-for="item in attention" :key="`${item.reason}-${item.mission_id || item.project_id}`"
               class="rounded-lg border border-base-content/10 p-2">
            <div class="flex items-center gap-1.5">
              <span class="badge badge-xs" :class="statusMeta(item.status).badge">{{ item.status }}</span>
              <span class="text-xs font-semibold truncate flex-1">{{ item.title }}</span>
              <span class="badge badge-xs badge-ghost">{{ item.reason }}</span>
            </div>
            <p v-if="item.last_error" class="text-[10px] text-error/70 mt-1 line-clamp-2">{{ item.last_error }}</p>
            <div v-if="openMission(item)" class="text-[10px] text-base-content/40 mt-1">
              {{ openMission(item).team_id }} · {{ openMission(item).project_id }}
            </div>
          </div>
        </div>
        <p v-else class="text-xs text-base-content/40">Nothing needs attention.</p>
      </section>
    </div>
  </div>
</template>

<!-- Made with ❤️ by codx-junior -->
