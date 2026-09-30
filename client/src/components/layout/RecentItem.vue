<script setup>
</script>

<template>
  <button
    class="flex items-center gap-3 px-3 py-2 rounded-lg w-full text-left text-base-content/70 hover:bg-white/5 hover: transition-colors group"
    @click="$emit('click')"
  >
    <i class="fas fa-circle text-yellow-500/80 text-xs shrink-0"></i>
    <span class="text-sm truncate flex-1">{{ name }}</span>
  </button>
</template>

<script>
export default {
  props: {
    name: { type: String, required: true }
  },
  emits: ['click']
}
</script>