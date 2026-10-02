<script setup>
import Collapsible from '@/components/Collapsible.vue'
</script>

<template>
  <div class="card bg-base-100 shadow">
    <Collapsible>
      <template #icon>
        <i class="fa-solid fa-filter text-xs opacity-60"></i>
      </template>
      <template #title>Filters</template>

      <template #summary>
        <span v-for="chip in activeChips" :key="chip" class="badge badge-sm badge-primary">
          {{ chip }}
        </span>
      </template>

      <template #actions>
        <div class="flex flex-wrap items-center gap-1 mr-1" @click.stop>
          <!-- Date presets -->
          <button
            v-for="p in presets"
            :key="p.label"
            class="btn btn-xs"
            :class="activePreset === p.label ? 'btn-primary' : 'btn-ghost'"
            @click="applyPreset(p)"
          >{{ p.label }}</button>

          <div class="w-px h-4 bg-base-300 mx-1"></div>

          <!-- Auto-refresh -->
          <div class="flex items-center gap-1">
            <i
              class="fa-solid fa-clock text-xs"
              :class="modelValue.autoRefresh ? 'text-success animate-pulse' : 'text-base-content-ERROR-40'"
            ></i>
            <select
              :value="modelValue.autoRefresh"
              class="select select-bordered select-xs w-24"
              @change="emit('update:modelValue', { ...modelValue, autoRefresh: +$event.target.value || null })"
            >
              <option :value="null">Off</option>
              <option :value="30">30s</option>
              <option :value="60">1 min</option>
              <option :value="300">5 min</option>
            </select>
          </div>
        </div>
      </template>

      <template #default>
        <div class="card-body py-3 px-4">
          <div class="flex flex-wrap items-center gap-3">

            <!-- Date range -->
            <div class="flex items-center gap-2 flex-wrap">
              <i class="fa-regular fa-calendar text-base-content/50 text-sm"></i>
              <div class="flex items-center gap-1">
                <label class="text-xs text-base-content/60">From</label>
                <input type="date" :value="modelValue.startDate"
                  class="input input-bordered input-sm w-36"
                  @change="update('startDate', $event.target.value)" />
              </div>
              <div class="flex items-center gap-1">
                <label class="text-xs text-base-content/60">To</label>
                <input type="date" :value="modelValue.endDate"
                  class="input input-bordered input-sm w-36"
                  @change="update('endDate', $event.target.value)" />
              </div>
            </div>

            <!-- Direction: request | response | all -->
            <div class="flex items-center gap-1">
              <label class="text-xs text-base-content/60">Direction</label>
              <select :value="modelValue.direction" class="select select-bordered select-sm w-32"
                @change="update('direction', $event.target.value)">
                <option value="">All</option>
                <option value="request">Request</option>
                <option value="response">Response</option>
              </select>
            </div>

            <!-- Model -->
            <div class="flex items-center gap-1">
              <label class="text-xs text-base-content/60">Model</label>
              <select :value="modelValue.model" class="select select-bordered select-sm w-40"
                @change="update('model', $event.target.value)">
                <option value="">All models</option>
                <option v-for="m in models" :key="m" :value="m">{{ m }}</option>
              </select>
            </div>

            <!-- Provider -->
            <div class="flex items-center gap-1">
              <label class="text-xs text-base-content/60">Provider</label>
              <select :value="modelValue.provider" class="select select-bordered select-sm w-36"
                @change="update('provider', $event.target.value)">
                <option value="">All providers</option>
                <option v-for="p in providers" :key="p" :value="p">{{ p }}</option>
              </select>
            </div>

            <!-- Session ID -->
            <div class="flex items-center gap-1">
              <label class="text-xs text-base-content/60">Session</label>
              <input type="text" :value="modelValue.sessionId" placeholder="Session ID"
                class="input input-bordered input-sm w-36"
                @change="update('sessionId', $event.target.value)" />
            </div>

            <!-- Admin: username -->
            <div v-if="isAdmin" class="flex items-center gap-1">
              <label class="text-xs text-base-content/60">User</label>
              <input type="text" :value="modelValue.username" placeholder="All users"
                class="input input-bordered input-sm w-32"
                @change="update('username', $event.target.value)" />
            </div>

            <!-- Admin: project (field name is "project" in backend, not project_name) -->
            <div v-if="isAdmin" class="flex items-center gap-1">
              <label class="text-xs text-base-content/60">Project</label>
              <input type="text" :value="modelValue.project" placeholder="All projects"
                class="input input-bordered input-sm w-36"
                @change="update('project', $event.target.value)" />
            </div>

            <!-- Tags search -->
            <div class="flex items-center gap-1">
              <label class="text-xs text-base-content/60">Tags</label>
              <input type="text" :value="modelValue.tags" placeholder="Filter by tag"
                class="input input-bordered input-sm w-28"
                @change="update('tags', $event.target.value)" />
            </div>

            <button class="btn btn-xs btn-ghost" @click="$emit('clear')">
              <i class="fa-solid fa-filter-circle-xmark text-xs"></i>
              Clear
            </button>
          </div>
        </div>
      </template>
    </Collapsible>
  </div>
</template>

<script>
export default {
  name: 'LogsFilterBar',
  emits: ['update:modelValue', 'clear', 'change'],
  props: {
    modelValue: { type: Object, required: true },
    isAdmin: { type: Boolean, default: false },
    models: { type: Array, default: () => [] },
    providers: { type: Array, default: () => [] },
  },
  data() {
    return {
      activePreset: '7d',
      presets: [
        { label: 'Today', type: 'today' },
        { label: '7d', days: 7 },
        { label: '30d', days: 30 },
        { label: '90d', days: 90 },
        { label: 'All time', type: 'allTime' },
      ]
    }
  },
  computed: {
    activeChips() {
      const chips = []
      const f = this.modelValue
      if (f.startDate || f.endDate) chips.push(`${f.startDate || '…'} → ${f.endDate || '…'}`)
      if (f.direction) chips.push(`Dir: ${f.direction}`)
      if (f.model) chips.push(`Model: ${f.model}`)
      if (f.provider) chips.push(`Provider: ${f.provider}`)
      if (f.sessionId) chips.push(`Session: ${f.sessionId.slice(0, 8)}…`)
      if (f.username) chips.push(`User: ${f.username}`)
      if (f.project) chips.push(`Project: ${f.project}`)
      if (f.tags) chips.push(`Tags: ${f.tags}`)
      return chips
    }
  },
  methods: {
    update(key, value) {
      this.$emit('update:modelValue', { ...this.modelValue, [key]: value })
      this.$emit('change')
    },
    applyPreset(preset) {
      this.activePreset = preset.label
      const today = new Date()
      const todayStr = today.toISOString().split('T')[0]
      let startDate = todayStr
      if (preset.type === 'today') {
        startDate = todayStr
      } else if (preset.type === 'allTime') {
        startDate = '2024-01-01'
      } else {
        const d = new Date()
        d.setDate(today.getDate() - preset.days)
        startDate = d.toISOString().split('T')[0]
      }
      this.$emit('update:modelValue', { ...this.modelValue, startDate, endDate: todayStr })
      this.$emit('change')
    }
  }
}
</script>