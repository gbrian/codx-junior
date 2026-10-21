<script setup>
</script>

<template>
  <div class="fixed inset-0 z-50 flex items-center justify-center" :class="fullscreen ? 'p-0' : 'p-4'">
    <!-- Backdrop -->
    <div
      class="absolute inset-0 bg-base-100/60 backdrop-blur-sm transition-opacity duration-300"
      @click="close && $emit('close')"
    ></div>

    <!-- Modal Box -->
    <div
      v-bind="$attrs"
      :class="boxClass()"
    >
      <!-- Header — rendered only when the host has something to put in it
           (`title` prop or `header` slot). An empty bar only ate vertical space:
           without it the body gets that room back. -->
      <div
        v-if="hasHeader()"
        class="flex items-center justify-between gap-3 pl-4 md:pl-6 pr-2 py-2 border-b border-base-content/5 flex-shrink-0"
      >
        <slot name="header">
          <h2 class="min-w-0 truncate text-sm md:text-base font-semibold">{{ title }}</h2>
        </slot>
        <button
          v-if="close"
          class="flex-shrink-0 p-2 text-base-content/50 hover:text-base-content/90 hover:bg-white/8 rounded-lg transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-primary/50"
          @click="$emit('close')"
          aria-label="Close modal"
        >
          <i class="fa-solid fa-xmark text-lg"></i>
        </button>
      </div>

      <!-- Body -->
      <div
        class="flex-1 overflow-y-auto scrollbar-thin scrollbar-thumb-white/10 scrollbar-track-transparent"
        :class="bodyClass()"
      >
        <slot></slot>
      </div>

      <!-- Footer -->
      <div v-if="$slots.footer" class="px-6 py-4 border-t border-base-content/5 flex justify-end gap-3 flex-shrink-0">
        <slot name="footer"></slot>
      </div>

      <!-- Headerless dialogs: the close button floats in the corner, which
           `bodyClass()` keeps free with extra right padding. -->
      <button
        v-if="close && !hasHeader()"
        class="absolute right-1.5 top-1.5 z-20 p-2 text-base-content/50 hover:text-base-content/90 hover:bg-base-content/5 rounded-lg transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-primary/50"
        @click="$emit('close')"
        aria-label="Close modal"
      >
        <i class="fa-solid fa-xmark text-lg"></i>
      </button>
    </div>
  </div>
</template>

<script>
export default {
  inheritAttrs: false,
  props: {
    close: Boolean,
    scope: Element,
    // Optional dialog title, rendered in the header. Without it (and without
    // the `header` slot) the header is not rendered at all.
    title: { type: String, default: '' },
    // Mobile/handheld mode: the dialog takes over the whole viewport, so there
    // is no backdrop gap to tap out of by accident and every pixel is usable.
    fullscreen: { type: Boolean, default: false }
  },
  emits: ['close'],
  methods: {
    // The header exists only when the host gives it content
    hasHeader() {
      return !!(this.title || this.$slots.header)
    },
    // Fullscreen drops the outline (radius, border, shadow) and the zoom-in
    // animation: a dialog that already fills the screen should not appear to
    // grow into it. `100dvh` keeps it exact while the mobile URL bar moves.
    boxClass() {
      const base = 'relative z-10 bg-base-300 flex flex-col'
      if (this.fullscreen) {
        return `${base} w-full h-[100dvh] max-h-[100dvh] rounded-none border-0 shadow-none`
      }
      return `${base} rounded-lg shadow-2xl border border-base-content/10 max-h-[90vh] mx-0 md:mx-4 w-full md:w-auto md:max-w-2xl animate-in fade-in zoom-in-95 duration-300 hover:border-base-content/15 transition-all`
    },
    // Headerless dialogs reserve the top-right corner for the floating close
    // button; with no close button nothing has to be reserved.
    bodyClass() {
      if (this.fullscreen) return 'px-4 py-3 md:px-6 md:py-4'
      if (this.hasHeader()) return 'px-6 py-4'
      return this.close ? 'pl-6 pr-12 py-4' : 'px-6 py-4'
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
  },
  beforeUnmount() {
    // Clean up when modal is destroyed
    if (this.$el.parentNode) {
      this.$el.parentNode.removeChild(this.$el)
    }
    document.removeEventListener('keydown', this.handleKeyDown)
  }
}
</script>