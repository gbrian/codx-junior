<script setup>
</script>

<template>
  <!--
    Mobile (<768px): bottom sheet — full width, 85% height, anchored to the bottom
    edge with a grab handle to drag down and dismiss.
    Desktop (md+): centered dialog (unchanged behaviour); `sizeClass` picks the width.
    The element is teleported to the app root on mount (see script below).
  -->
  <div class="fixed inset-0 z-50 flex items-end justify-center p-0 md:items-center md:p-4">
    <!-- Backdrop -->
    <div
      class="absolute inset-0 bg-base-100/60 backdrop-blur-sm transition-opacity duration-300"
      @click="close && $emit('close')"
    ></div>

    <!-- Modal Box -->
    <div
      v-bind="$attrs"
      role="dialog"
      aria-modal="true"
      :class="[
        'relative z-10 bg-base-300 shadow-2xl border border-base-content/10 flex flex-col w-full h-[85%] mx-0 rounded-t-2xl pb-[env(safe-area-inset-bottom)] md:h-auto md:max-h-[90vh] md:w-auto md:mx-4 md:rounded-lg md:pb-0 hover:border-base-content/15 transition-all',
        isMobile
          ? 'animate-in fade-in slide-in-from-bottom-full duration-300'
          : 'animate-in fade-in zoom-in-95 duration-300',
        sizeClass
      ]"
      :style="dragStyle"
    >
      <!-- Grab handle (mobile only) — drag down to dismiss the sheet -->
      <div
        class="flex md:hidden justify-center pt-3 pb-2 cursor-grab touch-none select-none shrink-0"
        @pointerdown="onHandlePointerDown"
        aria-hidden="true"
      >
        <span class="w-10 h-1.5 rounded-full bg-base-content/20"></span>
      </div>

      <!-- Header -->
      <div class="flex items-center justify-between px-6 py-4 border-b border-base-content/5 shrink-0">
        <slot name="header">
          <span class="text-base font-semibold "></span>
        </slot>
        <button
          v-if="close"
          class="p-2 -mr-2 text-base-content/50 hover:text-base-content/90 hover:bg-white/8 rounded-lg transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-primary/50"
          @click="$emit('close')"
          aria-label="Close modal"
        >
          <i class="fa-solid fa-xmark text-lg"></i>
        </button>
      </div>

      <!-- Body -->
      <div class="flex-1 min-h-0 overflow-y-auto overscroll-contain px-6 py-4 scrollbar-thin scrollbar-thumb-white/10 scrollbar-track-transparent">
        <slot></slot>
      </div>

      <!-- Footer -->
      <div v-if="$slots.footer" class="px-6 py-4 border-t border-base-content/5 flex justify-end gap-3 flex-shrink-0">
        <slot name="footer"></slot>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  inheritAttrs: false,
  props: {
    close: Boolean,
    scope: Element,
    // Width preset. `md` preserves the previous default (`md:max-w-2xl`).
    // Use e.g. `full`/`xl` for large, editor-like content.
    size: {
      type: String,
      default: 'md'
    }
  },
  emits: ['close'],
  data() {
    return {
      // Fallback mobile detection when the global $ui store isn't available.
      isMobileViewport: false,
      // Drag-to-dismiss state for the mobile bottom sheet.
      dragging: false,
      dragStartY: 0,
      dragOffset: 0
    }
  },
  computed: {
    sizeClass() {
      const sizes = {
        sm: 'md:max-w-md',
        md: 'md:max-w-2xl',
        lg: 'md:max-w-4xl',
        xl: 'md:max-w-6xl',
        full: 'md:max-w-[95vw]'
      }
      return sizes[this.size] || sizes.md
    },
    isMobile() {
      // Prefer the app-wide UI store, fall back to a media query.
      return this.$ui?.isMobile ?? this.isMobileViewport
    },
    // Only set an inline transform while dragging. `transition: none` keeps the
    // sheet glued to the finger instead of animating through `transition-all`.
    dragStyle() {
      if (!this.dragging) return null
      return { transform: `translateY(${this.dragOffset}px)`, transition: 'none' }
    }
  },
  created() {
    // Resolve the mobile viewport before the first render so the correct enter
    // animation (slide-up vs zoom) is used straight away.
    if (window.matchMedia) {
      this.mq = window.matchMedia('(max-width: 767px)')
      this.isMobileViewport = this.mq.matches
      this.onMqChange = (e) => { this.isMobileViewport = e.matches }
      this.mq.addEventListener('change', this.onMqChange)
    }
  },
  mounted() {
    // Attach to the provided scope element, or fall back to the root App element
    const target = this.scope || this.$root.$el
    target.appendChild(this.$el)

    // Add ESC key listener
    this.handleKeyDown = (e) => {
      if (e.key === 'Escape' && this.close) {
        this.$emit('close')
      }
    }
    document.addEventListener('keydown', this.handleKeyDown)

    // Sheet drag listeners live on window so the gesture keeps tracking even
    // when the pointer leaves the (small) grab handle.
    window.addEventListener('pointermove', this.onPointerMove)
    window.addEventListener('pointerup', this.onPointerUp)
  },
  beforeUnmount() {
    // Clean up when modal is destroyed
    if (this.$el.parentNode) {
      this.$el.parentNode.removeChild(this.$el)
    }
    document.removeEventListener('keydown', this.handleKeyDown)
    this.mq?.removeEventListener('change', this.onMqChange)
    window.removeEventListener('pointermove', this.onPointerMove)
    window.removeEventListener('pointerup', this.onPointerUp)
  },
  methods: {
    onHandlePointerDown(event) {
      this.dragging = true
      this.dragStartY = event.clientY
      this.dragOffset = 0
      // Capture the pointer so the drag is not lost when it leaves the handle.
      try { event.currentTarget.setPointerCapture?.(event.pointerId) } catch {}
    },
    onPointerMove(event) {
      if (!this.dragging) return
      // Only allow dragging downwards.
      this.dragOffset = Math.max(0, event.clientY - this.dragStartY)
    },
    onPointerUp() {
      if (!this.dragging) return
      const shouldClose = this.dragOffset > 110
      this.dragging = false
      this.dragOffset = 0
      if (shouldClose && this.close) this.$emit('close')
    }
  }
}
</script>