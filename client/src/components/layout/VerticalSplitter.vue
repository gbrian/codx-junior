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
// Stable per-instance id. It MUST be generated once: radix-vue registers the
// panels by id (and the panel ids are derived from it), so an id that changes
// between renders makes both panels unregister/re-register — which happened on
// every re-render while the handle was dragged.
let splitterUid = 0

// `layout` fires on every pointer move while the handle is dragged (60–200
// events/s). Nothing below reacts to them synchronously: the sizes are kept in
// NON-reactive instance state and committed once the gesture settles.
const LAYOUT_SETTLE_MS = 150

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
      groupId: `splitter-group-${++splitterUid}`,
      // Sizes radix-vue uses to SEED the panels (persisted layout on mount).
      // Intentionally NOT updated from the live layout on every event: binding
      // the panel's own output (`layout`) back to its input (`defaultSize`)
      // re-entered radix's layout calculation on each pointer move
      // (`layout` → `defaultSize` → `layout` …). It is committed once per
      // gesture, see `commitLayout()`.
      seededLayout: null
    }
  },
  computed: {
    // Left panel size: the remembered value wins, then the configured default.
    leftSize() {
      const saved = this.seededLayout?.[0]
      return saved != null ? saved : (this.panels?.left?.defaultSize || 20)
    },
    // Right panel size: the remembered value wins, then the configured default.
    rightSize() {
      const saved = this.seededLayout?.[1]
      return saved != null ? saved : (this.panels?.right?.defaultSize || 20)
    }
  },
  watch: {
    // Load (or reload) the persisted layout when the key changes / on mount.
    persistKey: {
      immediate: true,
      handler(key) {
        const layout = this.readLayout(key)
        this.seededLayout = layout
        // Do not re-emit/re-persist a layout we already know about
        this.dragState().lastCommitted = layout ? this.signature(layout) : null
      }
    }
  },
  beforeUnmount() {
    const state = this.dragState()
    clearTimeout(state.timer)
    // Keep the last split for the next mount without emitting anything
    if (state.sizes) this.writeLayout(this.persistKey, state.sizes)
  },
  methods: {
    // Non-reactive drag bookkeeping. It changes on EVERY `layout` event, so it
    // must stay out of `data()`: a reactive write there re-rendered this
    // component — and both slots (board canvas, chat/messages, diff panes) —
    // on every pointer move.
    dragState() {
      if (!this.splitterDragState) {
        this.splitterDragState = { sizes: null, lastCommitted: null, timer: null }
      }
      return this.splitterDragState
    },
    // Comparable signature of a layout. Rounded so sub-0.01% jitter produced by
    // the panels' normalisation does not look like a new layout.
    signature(sizes) {
      return (sizes || []).map(size => Number(size).toFixed(2)).join(':')
    },
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
    // Splitter layout changed (user resizing, or a panel was added/removed).
    // Fires continuously during a drag — keep it write-free (see `dragState`).
    onLayout(sizes) {
      // Only meaningful while BOTH panels are present: closing the side panel
      // collapses the layout to a single [100] entry and must not wipe the
      // remembered split.
      if (!this.$slots.left || !this.$slots.right) return
      if (!Array.isArray(sizes) || sizes.length < 2) return

      const state = this.dragState()
      state.sizes = [sizes[0], sizes[1]]

      // Echo of a layout we already committed — nothing to do
      if (this.signature(state.sizes) === state.lastCommitted) return

      // Commit once the handle stops moving instead of on every event
      clearTimeout(state.timer)
      state.timer = setTimeout(() => this.commitLayout(), LAYOUT_SETTLE_MS)
    },
    // Single commit per gesture: remember, persist and notify ONCE.
    commitLayout() {
      const state = this.dragState()
      const sizes = state.sizes
      if (!sizes) return

      const signature = this.signature(sizes)
      if (signature === state.lastCommitted) return
      state.lastCommitted = signature

      // Keep the split for the next mount / when the optional panel is
      // re-opened (one reactive write per gesture, not per pointer move)
      this.seededLayout = [...sizes]
      this.writeLayout(this.persistKey, sizes)
      this.$emit('resize', { sizes: [...sizes], left: sizes[0], right: sizes[1] })
    }
  }
}
</script>