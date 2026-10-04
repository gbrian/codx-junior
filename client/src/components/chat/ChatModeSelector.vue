<script setup>
import ChatIcon from './ChatIcon.vue'
</script>

<template>
  <div class="w-full flex gap-2 select select-ghost">
    <ChatIcon :mode="selectedMode" />
    <select 
      :value="selectedMode"
      @change="selectMode"
    >
      <option v-for="mode in availableModes" :key="mode.value" :value="mode.value" class="flex gap-1">
        {{ mode.label }}
      </option>
    </select>
  </div>
</template>

<script>
export default {
  props: {
    selectedMode: {
      type: String,
      default: 'chat'
    }
  },
  emits: ['mode-changed'],
  computed: {
    availableModes() {
      return this.$storex.chats.availableChatModes
    }
  },
  methods: {
    selectMode(event) {
      const mode = event.target.value
      if (mode !== this.selectedMode) {
        this.$emit('mode-changed', mode)
      }
    }
  }
}
</script>