<script setup>
defineProps({
  scale: { type: Number, default: 1 },
  minScale: { type: Number, default: 0.1 },
  maxScale: { type: Number, default: 5 },
  editable: { type: Boolean, default: true },
  editing: { type: Boolean, default: false },
  expanded: { type: Boolean, default: false },
  showLabels: { type: Boolean, default: false }
})

defineEmits(['zoom-in', 'zoom-out', 'fit', 'reset', 'edit', 'expand', 'shrink'])
</script>

<template>
  <div
    class="flex items-center gap-0.5 rounded-lg border border-base-content/10 bg-base-200/95 px-1 py-0.5 shadow-lg backdrop-blur-sm"
    @pointerdown.stop
    @click.stop
  >
    <button
      class="btn btn-xs btn-ghost px-2 tooltip tooltip-bottom"
      data-tip="Zoom out (-)"
      aria-label="Zoom out"
      :disabled="scale <= minScale"
      @click="$emit('zoom-out')"
    >
      <i class="fa-solid fa-magnifying-glass-minus"></i>
    </button>

    <button
      class="btn btn-xs btn-ghost min-w-14 font-mono text-[11px] tabular-nums"
      :aria-label="`Reset zoom (currently ${Math.round(scale * 100)} percent)`"
      title="Reset to 100% (1)"
      @click="$emit('reset')"
    >
      {{ Math.round(scale * 100) }}%
    </button>

    <button
      class="btn btn-xs btn-ghost px-2 tooltip tooltip-bottom"
      data-tip="Zoom in (+)"
      aria-label="Zoom in"
      :disabled="scale >= maxScale"
      @click="$emit('zoom-in')"
    >
      <i class="fa-solid fa-magnifying-glass-plus"></i>
    </button>

    <div class="mx-0.5 h-4 w-px bg-base-content/15"></div>

    <button
      class="btn btn-xs btn-ghost px-2 tooltip tooltip-bottom"
      data-tip="Fit to view (0)"
      aria-label="Fit diagram to view"
      @click="$emit('fit')"
    >
      <i class="fa-solid fa-crop"></i>
      <span v-if="showLabels" class="ml-1 hidden md:inline">Fit</span>
    </button>

    <template v-if="editable && !editing">
      <button
        class="btn btn-xs btn-ghost px-2 tooltip tooltip-bottom"
        data-tip="Edit diagram source"
        aria-label="Edit diagram source"
        @click="$emit('edit')"
      >
        <i class="fa-solid fa-pen-to-square"></i>
        <span v-if="showLabels" class="ml-1 hidden md:inline">Edit</span>
      </button>
    </template>

    <button
      v-if="!expanded"
      class="btn btn-xs btn-ghost px-2 tooltip tooltip-bottom"
      data-tip="Expand diagram"
      aria-label="Expand diagram in fullscreen"
      @click="$emit('expand')"
    >
      <i class="fa-solid fa-up-right-from-square"></i>
    </button>
    <button
      v-else
      class="btn btn-xs btn-ghost px-2 tooltip tooltip-bottom"
      data-tip="Exit fullscreen"
      aria-label="Exit fullscreen"
      @click="$emit('shrink')"
    >
      <i class="fa-solid fa-compress"></i>
    </button>
  </div>
</template>
