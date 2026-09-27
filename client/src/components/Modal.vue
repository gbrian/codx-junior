<script setup>
</script>

<template>
  <div class="fixed inset-0 z-50 flex items-center justify-center p-4">
    <!-- Backdrop -->
    <div
      class="absolute inset-0 bg-black/60 backdrop-blur-sm transition-opacity duration-300"
      @click="close && $emit('close')"
    ></div>

    <!-- Modal Box -->
    <div
      v-bind="$attrs"
      class="relative z-10 bg-[#1a1a1a] rounded-lg shadow-2xl border border-white/10 max-h-[90vh] flex flex-col mx-0 md:mx-4 w-full md:w-auto md:max-w-2xl animate-in fade-in zoom-in-95 duration-300 hover:border-white/15 transition-all"
    >
      <!-- Header -->
      <div class="flex items-center justify-between px-6 py-4 border-b border-white/5">
        <slot name="header">
          <span class="text-base font-semibold text-white"></span>
        </slot>
        <button
          v-if="close"
          class="p-2 -mr-2 text-white/50 hover:text-white/90 hover:bg-white/8 rounded-lg transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-primary/50"
          @click="$emit('close')"
          aria-label="Close modal"
        >
          <i class="fa-solid fa-xmark text-lg"></i>
        </button>
      </div>

      <!-- Body -->
      <div class="flex-1 overflow-y-auto px-6 py-4 scrollbar-thin scrollbar-thumb-white/10 scrollbar-track-transparent">
        <slot></slot>
      </div>

      <!-- Footer -->
      <div v-if="$slots.footer" class="px-6 py-4 border-t border-white/5 flex justify-end gap-3 flex-shrink-0">
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
    scope: Element
  },
  emits: ['close'],
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