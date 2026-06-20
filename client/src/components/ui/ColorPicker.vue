<script setup>
</script>

<template>
  <div class="flex flex-wrap gap-1">
    <button
      v-for="color in palette"
      :key="color"
      class="w-6 h-6 rounded-lg border-2 transition-all hover:scale-110"
      :style="{ backgroundColor: color }"
      :class="modelValue === color ? 'border-white scale-110 ring-2 ring-primary' : 'border-transparent'"
      @click="$emit('update:modelValue', color)"
    />
  </div>
</template>

<script>
export default {
  name: 'ColorPicker',
  emits: ['update:modelValue'],
  props: {
    modelValue: { type: String, default: '#6366f1' },
    colors: { type: Array, default: null }
  },
  computed: {
    palette() {
      return this.colors || [
        '#6366f1', '#8b5cf6', '#ec4899', '#ef4444',
        '#f97316', '#eab308', '#22c55e', '#14b8a6',
        '#3b82f6', '#06b6d4', '#64748b', '#1e293b'
      ]
    }
  }
}
</script>