<script setup>
</script>

<template>
  <button
    class="click flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm text-base-content/60 hover:bg-white/8 hover: transition-colors w-full"
    :class="[
      isPrimary ? 'bg-white/10 ' : '',
      isCollapsed ? 'justify-center' : 'justify-start'
    ]"
    :title="isCollapsed ? label : ''"
    @click="$emit('click')"
  >
    <i :class="icon" class="w-5 text-center shrink-0"></i>
    
    <div v-if="!isCollapsed" class="flex items-center gap-2 flex-1">
      <span>{{ label }}</span>
      <span v-if="badge" class="ml-auto px-2 py-0.5 rounded text-xs bg-blue-500/30 text-blue-300">
        {{ badge }}
      </span>
    </div>

    <i v-if="expandable && !isCollapsed" :class="expanded ? 'fas fa-chevron-up' : 'fas fa-chevron-down'" class="ml-auto text-xs text-base-content/40"></i>
  </button>
</template>

<script>
export default {
  props: {
    icon: { type: String, required: true },
    label: { type: String, required: true },
    badge: { type: String, default: null },
    isCollapsed: { type: Boolean, default: false },
    isPrimary: { type: Boolean, default: false },
    expandable: { type: Boolean, default: false },
    expanded: { type: Boolean, default: false }
  },
  emits: ['click']
}
</script>