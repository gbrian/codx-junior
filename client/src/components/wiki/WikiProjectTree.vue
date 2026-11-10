<script setup>
defineProps({
  nodes: { type: Array, default: () => [] },
  current: { type: String, default: '' }
})
defineEmits(['select'])
</script>

<template>
  <ul class="space-y-0.5">
    <li v-for="node in nodes" :key="node.project_id || node.name">
      <button
        class="flex w-full items-center gap-2 rounded-md py-1 text-left text-[0.8rem] transition-colors"
        :class="node.is_current || node.name === current
          ? 'bg-base-content/10 font-semibold'
          : 'hover:bg-base-content/5'"
        :style="{ paddingLeft: `${Math.min(3, node.depth || 0) * 0.6 + 0.35}rem` }"
        :title="node.description"
        @click="$emit('select', node.name)"
      >
        <span class="status-badge" :class="'status-' + (node.status || 'pending')"></span>
        <i class="fa-regular fa-folder text-[0.68rem] opacity-45"></i>
        <span class="min-w-0 flex-1 truncate">{{ node.title || node.name }}</span>
        <span v-if="node.page_count" class="text-[0.62rem] opacity-40">{{ node.page_count }}</span>
      </button>
      <WikiProjectTree
        v-if="node.children?.length"
        :nodes="node.children"
        :current="current"
        class="ml-3 border-l border-base-content/10 pl-1"
        @select="$emit('select', $event)"
      />
    </li>
  </ul>
</template>

<style scoped>
.status-badge {
  display: inline-block;
  height: 0.45rem;
  width: 0.45rem;
  flex-shrink: 0;
  border-radius: 9999px;
  background: #94a3b8;
}
.status-badge.status-ready { background: #22c55e; }
.status-badge.status-pending { background: #f59e0b; }
.status-badge.status-disabled { background: #94a3b8; }
</style>
