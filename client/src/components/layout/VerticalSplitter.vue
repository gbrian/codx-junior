<script setup>
import { SplitterGroup, SplitterPanel, SplitterResizeHandle } from 'radix-vue'
</script>

<template>
  <!-- Split mode (default): resizable side-by-side panels -->
  <SplitterGroup v-if="split" :id="groupId" direction="horizontal" @layout="onLayout">
    <SplitterPanel
      :id="`${groupId}-panel-splitter-1`"
      :min-size="panels?.left?.minSize || 10"
      :collapsible="panels?.left?.collapsible || true"
      :defaultSize="leftSize"
      :class="panels?.left?.class"
      :style="panels?.left?.style"
      style="overflow: auto !important"
      :order="1"
      v-if="$slots.left"
    >
      <slot name="left"></slot>
    </SplitterPanel>

    <!-- Divider: `showHandle` reveals a grip so the dragger is easy to find/use -->
    <SplitterResizeHandle
      :id="`${groupId}-panel-divider`"
      class="relative shrink-0 w-2 cursor-col-resize outline-none transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-primary/50"
      :class="showHandle
        ? 'group bg-base-200 hover:bg-primary/10 active:bg-primary/20'
        : 'border-r border-base-100 hover:bg-slate-600'"
      v-if="$slots.left && $slots.right"
    >
      <span
        v-if="showHandle"
        aria-hidden="true"
        class="pointer-events-none absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-1 h-10 rounded-full bg-base-content/20 transition-colors duration-150 group-hover:bg-primary/70 group-focus-visible:bg-primary"
      ></span>
    </SplitterResizeHandle>

    <SplitterPanel
      :id="`${groupId}-panel-splitter-2`"
      :min-size="panels?.right?.minSize || 10"
      :collapsible="panels?.right?.collapsible || true"
      :defaultSize="rightSize"
      :class="panels?.right?.class"
      :style="panels?.right?.style"
      style="overflow: auto !important"
      :order="2"
      v-if="$slots.right"
    >
      <slot name="right"></slot>
    </SplitterPanel>
  </SplitterGroup>

  <!-- Non-split fallback (mobile): plain, non-resizable container (no SplitterGroup) -->
  <div v-else class="flex h-full w-full min-h-0 overflow-hidden">
    <div class="flex-1 min-w-0 min-h-0 overflow-hidden">
      <slot name="left"></slot>
    </div>
    <div
      v-if="$slots.right"
      class="flex-1 min-w-0 min-h-0 overflow-hidden"
    >
      <slot name="right"></slot>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    // Per-panel sizing/class config: { left: {...}, right: {...} }
    panels: { type: Object, default: () => ({}) },
    // Render the splitter. Set to false (e.g. on mobile) to render the slots
    // inside a plain container instead of a resizable SplitterGroup.
    split: { type: Boolean, default: true },
    // Make the resize dragger clearly visible (grip + hover) so it is discoverable.
    showHandle: { type: Boolean, default: false },
    // When set, the last panel layout (sizes) is persisted in localStorage under
    // this key and reused the next time the splitter (or its optional panel) is
    // shown again. Left unset, the component keeps no state (current behaviour).
    persistKey: { type: String, default: null }
  },
  emits: ['resize'],
  data() {
    return {
      // Last known layout (array of panel sizes, %). Seeds `leftSize`/`rightSize`
      // so a panel that is re-mounted keeps the split the user last chose.
      savedLayout: null,
      // Debounce handle used while persisting during a drag.
      persistTimer: null
    }
  },
  computed: {
    groupId() {
      const t = this.generateUID()
      return `splitter-group-${t}`
    },
    // Left panel size: the persisted value wins, then the configured default.
    leftSize() {
      const saved = this.savedLayout?.[0]
      return saved != null ? saved : (this.panels?.left?.defaultSize || 20)
    },
    // Right panel size: the persisted value wins, then the configured default.
    rightSize() {
      const saved = this.savedLayout?.[1]
      return saved != null ? saved : (this.panels?.right?.defaultSize || 20)
    }
  },
  watch: {
    // Load (or reload) the persisted layout when the key changes / on mount.
    persistKey: {
      immediate: true,
      handler(key) {
        this.savedLayout = this.readLayout(key)
      }
    }
  },
  beforeUnmount() {
    clearTimeout(this.persistTimer)
  },
  methods: {
    // localStorage key for a given persist key
    storageKey(key) {
      return `splitter-layout:${key}`
    },
    // Read the persisted layout (array of panel sizes) for a given key
    readLayout(key) {
      if (!key) return null
      try {
        const raw = localStorage.getItem(this.storageKey(key))
        const parsed = raw ? JSON.parse(raw) : null
        return Array.isArray(parsed) && parsed.length ? parsed : null
      } catch (e) {
        return null
      }
    },
    // Persist the layout so it is reused the next time the panel is shown
    writeLayout(key, layout) {
      if (!key || !layout) return
      try {
        localStorage.setItem(this.storageKey(key), JSON.stringify(layout))
      } catch (e) {
        // Storage may be unavailable (private mode / quota) — ignore
      }
    },
    // Splitter layout changed (user resized, or a panel was added/removed).
    // Only remember it while BOTH panels are present so closing the side panel
    // (which collapses the layout to a single [100] entry) does not wipe the
    // remembered split.
    onLayout(sizes) {
      if (!this.$slots.left || !this.$slots.right) return
      if (!Array.isArray(sizes) || sizes.length < 2) return
      this.savedLayout = [...sizes]
      this.$emit('resize', { sizes: [...sizes], left: sizes[0], right: sizes[1] })
      // Debounce the write: radix fires `layout` continuously during a drag.
      clearTimeout(this.persistTimer)
      this.persistTimer = setTimeout(() => {
        this.writeLayout(this.persistKey, this.savedLayout)
      }, 200)
    }
  }
}
</script>