<script setup>
</script>

<template>
  <div 
    class="absolute -top-1 right-0 z-20 flex gap-1 items-center bg-base-100/95 backdrop-blur-sm rounded-lg px-1 py-1 shadow-md border border-base-300 transition-all opacity-0 group-hover/header:opacity-100"
    @click.stop
  >
    <button
      class="btn btn-xs btn-ghost gap-1 tooltip tooltip-bottom"
      data-tip="Edit chapter"
      @click="$emit('edit')"
    >
      <i class="fa-solid fa-pen"></i>
    </button>
    <button
      class="btn btn-xs btn-ghost gap-1 tooltip tooltip-bottom"
      data-tip="Copy chapter"
      @click="$emit('copy')"
    >
      <i class="fa-solid fa-copy"></i>
    </button>
    <button
      class="btn btn-xs btn-ghost gap-1 tooltip tooltip-bottom"
      data-tip="Create task"
      @click="$emit('create-task')"
    >
      <i class="fa-solid fa-plus"></i>
    </button>
    <slot name="chapter-actions"></slot>
  </div>
</template>

<script>
export default {
  emits: ['edit', 'copy', 'create-task']
}
</script>