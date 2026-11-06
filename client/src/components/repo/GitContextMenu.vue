<script>
/**
 * Floating context menu shared by the git view sections.
 *
 * The host component owns the menu state (see `@/mixins/contextMenu`) and
 * passes an ordered list of items:
 *
 * ```js
 * { key, label, icon, hint, title, disabled, danger, run }
 * { key, divider: true }
 * ```
 *
 * Items are rendered in a fixed, viewport-clamped panel teleported to <body>,
 * so the menu is never clipped by the panel overflow (`overflow-hidden`) or
 * hidden behind a modal. Selection emits the whole item: the host can call
 * `item.run()` (the mixin does it for you).
 */
const MENU_WIDTH = 240
const VIEWPORT_MARGIN = 8

export default {
  name: 'GitContextMenu',
  props: {
    visible: { type: Boolean, default: false },
    position: { type: Object, default: () => ({ x: 0, y: 0 }) },
    title: { type: String, default: '' },
    items: { type: Array, default: () => [] }
  },
  emits: ['select', 'close'],
  data() {
    return {
      // Clamped position (the raw event position may overflow the viewport)
      offset: { x: 0, y: 0 },
      activeIndex: -1
    }
  },
  computed: {
    menuItems() {
      return (this.items || []).filter(item => item && (item.divider || item.label))
    },
    menuStyle() {
      return {
        left: `${this.offset.x}px`,
        top: `${this.offset.y}px`,
        width: `${MENU_WIDTH}px`
      }
    }
  },
  watch: {
    visible: {
      immediate: true,
      handler(value) {
        if (value) {
          this.offset = { ...this.position }
          this.open()
        } else {
          this.detachListeners()
        }
      }
    },
    position: {
      deep: true,
      handler(value) {
        if (!this.visible) return
        this.offset = { ...value }
        this.$nextTick(this.place)
      }
    },
    items: {
      deep: true,
      handler() {
        if (!this.visible) return
        this.activeIndex = -1
        this.$nextTick(this.place)
      }
    }
  },
  beforeUnmount() {
    this.detachListeners()
  },
  methods: {
    async open() {
      this.activeIndex = -1
      await this.$nextTick()
      if (!this.visible) return
      this.place()
      this.attachListeners()
      this.$refs.menu?.focus()
    },

    /**
     * Keep the panel inside the viewport: right/bottom clicks near the edges
     * open the menu upwards / leftwards instead of overflowing the screen.
     */
    place() {
      const el = this.$refs.menu
      if (!el) return
      const rect = el.getBoundingClientRect()
      const maxX = Math.max(VIEWPORT_MARGIN, window.innerWidth - rect.width - VIEWPORT_MARGIN)
      const maxY = Math.max(VIEWPORT_MARGIN, window.innerHeight - rect.height - VIEWPORT_MARGIN)
      this.offset = {
        x: Math.min(Math.max(this.offset.x, VIEWPORT_MARGIN), maxX),
        y: Math.min(Math.max(this.offset.y, VIEWPORT_MARGIN), maxY)
      }
    },

    attachListeners() {
      this.detachListeners()
      // Capture phase: close before the click reaches any underlying row.
      document.addEventListener('click', this.onDocumentClick, true)
      document.addEventListener('contextmenu', this.onDocumentContextMenu, true)
      document.addEventListener('keydown', this.onKeyDown)
      window.addEventListener('resize', this.place)
      window.addEventListener('scroll', this.onScroll, true)
    },

    detachListeners() {
      document.removeEventListener('click', this.onDocumentClick, true)
      document.removeEventListener('contextmenu', this.onDocumentContextMenu, true)
      document.removeEventListener('keydown', this.onKeyDown)
      window.removeEventListener('resize', this.place)
      window.removeEventListener('scroll', this.onScroll, true)
    },

    isInside(event) {
      return !!this.$refs.menu?.contains(event?.target)
    },

    onDocumentClick(event) {
      if (this.isInside(event)) return
      this.requestClose()
    },

    onDocumentContextMenu(event) {
      if (this.isInside(event)) return
      this.requestClose()
    },

    onScroll(event) {
      if (this.isInside(event)) return
      this.requestClose()
    },

    onKeyDown(event) {
      if (event.key === 'Escape') {
        event.preventDefault()
        event.stopPropagation()
        this.requestClose()
        return
      }
      if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
        event.preventDefault()
        event.stopPropagation()
        this.moveActive(event.key === 'ArrowDown' ? 1 : -1)
        return
      }
      if (event.key === 'Home' || event.key === 'End') {
        event.preventDefault()
        event.stopPropagation()
        this.moveActive(event.key === 'Home' ? -Infinity : Infinity)
        return
      }
      if (event.key === 'Enter' || event.key === ' ') {
        const item = this.menuItems[this.activeIndex]
        if (!item || item.divider || item.disabled) return
        event.preventDefault()
        event.stopPropagation()
        this.choose(item)
      }
    },

    /** Move the keyboard highlight, skipping dividers and disabled items */
    moveActive(delta) {
      const items = this.menuItems
      if (!items.length) return
      if (!Number.isFinite(delta)) {
        this.activeIndex = delta < 0 ? this.firstEnabled() : this.lastEnabled()
        return
      }
      let index = this.activeIndex
      for (let step = 0; step < items.length; step++) {
        index = (index + delta + items.length) % items.length
        const item = items[index]
        if (!item.divider && !item.disabled) {
          this.activeIndex = index
          return
        }
      }
    },

    firstEnabled() {
      return this.menuItems.findIndex(item => !item.divider && !item.disabled)
    },

    lastEnabled() {
      const items = this.menuItems
      for (let index = items.length - 1; index >= 0; index--) {
        if (!items[index].divider && !items[index].disabled) return index
      }
      return -1
    },

    isActive(index) {
      return this.activeIndex === index
    },

    choose(item) {
      if (!item || item.divider || item.disabled) return
      this.$emit('select', item)
      this.requestClose()
    },

    requestClose() {
      this.$emit('close')
    }
  }
}
</script>

<template>
  <Teleport to="body">
    <div
      v-if="visible"
      ref="menu"
      tabindex="-1"
      role="menu"
      class="fixed z-[60] bg-base-100 border border-base-content/10 rounded-lg shadow-xl py-1 outline-none"
      :style="menuStyle"
      @click.stop
      @contextmenu.prevent.stop
    >
      <div
        v-if="title"
        class="px-3 py-1.5 text-[10px] font-bold uppercase tracking-wide opacity-50 border-b border-base-content/10 truncate"
        :title="title"
      >{{ title }}</div>

      <template v-for="(item, index) in menuItems" :key="item.key || `divider-${index}`">
        <div v-if="item.divider" class="divider my-1"></div>
        <button
          v-else
          type="button"
          role="menuitem"
          class="w-full px-3 py-1.5 text-xs text-left flex items-center gap-2 transition-colors"
          :class="[
            item.danger ? 'text-error' : '',
            item.disabled
              ? 'opacity-40 cursor-not-allowed'
              : isActive(index)
                ? item.danger ? 'bg-error/10' : 'bg-base-200'
                : item.danger ? 'hover:bg-error/10' : 'hover:bg-base-200'
          ]"
          :disabled="item.disabled"
          :title="item.title || item.hint || item.label"
          @mouseenter="activeIndex = index"
          @click.stop="choose(item)"
        >
          <i
            class="fa-solid w-4 text-center shrink-0"
            :class="item.icon || 'fa-circle-dot'"
            aria-hidden="true"
          ></i>
          <span class="truncate grow">{{ item.label }}</span>
          <span v-if="item.hint" class="text-[10px] opacity-50 shrink-0">{{ item.hint }}</span>
        </button>
      </template>
    </div>
  </Teleport>
</template>
