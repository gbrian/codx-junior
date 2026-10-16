<script setup>
import Chat from './Chat.vue'
</script>

<template>
  <div class="flex flex-col h-full bg-base-200 border-l border-base-content/10 rounded-r-lg overflow-hidden">
    <!-- Header -->
    <div class="flex items-center justify-between px-4 py-3 border-b border-base-content/10 shrink-0">
      <div class="flex items-center gap-2 min-w-0">
        <i class="fa-solid fa-comments text-primary text-sm shrink-0"></i>
        <h3 class="text-sm font-semibold truncate">Meeting Chat</h3>
      </div>
      <button
        @click="$emit('close')"
        class="btn btn-ghost btn-xs btn-circle"
        title="Close chat panel"
      >
        <i class="fa-solid fa-xmark text-xs"></i>
      </button>
    </div>

    <!-- Chat Content -->
    <div class="flex-1 min-h-0 overflow-hidden">
      <Chat
        v-if="chat"
        :chat="chat"
        :showHidden="false"
        class="h-full"
      />
      <div v-else class="flex items-center justify-center h-full text-base-content/40 p-4 text-center">
        <div>
          <i class="fa-solid fa-comments text-2xl mb-2 block"></i>
          <p class="text-sm">No chat selected</p>
        </div>
      </div>
    </div>

    <!-- Resize handle -->
    <div
      @mousedown="startResize"
      class="w-1 bg-base-content/0 hover:bg-primary/40 cursor-col-resize transition-colors duration-200 shrink-0 absolute left-0 top-0 bottom-0"
      style="width: 4px; margin-left: -2px;"
      title="Drag to resize"
    ></div>
  </div>
</template>

<script>
export default {
  name: 'MeetChatPanel',
  props: {
    chat: { type: Object, default: null }
  },
  emits: ['close', 'resize'],
  methods: {
    startResize(event) {
      event.preventDefault()
      const startX = event.clientX
      const startWidth = this.$el.offsetWidth

      const handleMouseMove = (moveEvent) => {
        const delta = moveEvent.clientX - startX
        const newWidth = Math.max(250, startWidth + delta)
        this.$emit('resize', newWidth)
      }

      const handleMouseUp = () => {
        document.removeEventListener('mousemove', handleMouseMove)
        document.removeEventListener('mouseup', handleMouseUp)
      }

      document.addEventListener('mousemove', handleMouseMove)
      document.addEventListener('mouseup', handleMouseUp)
    }
  }
}
</script>