<script setup>
import ChatIcon from './ChatIcon.vue'
</script>

<template>
  <div class="w-full flex gap-2 select select-ghost bg-base-100">
    <ChatIcon :mode="selectedMode" />
    <select 
      :value="selectedMode"
      @change="selectMode"
    >
      <option v-for="mode in availableModes" :key="mode" :value="mode" class="flex gap-1">
        <ChatIcon :mode="mode" />
        <span class="capitalize">{{ mode }}</span>
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
  data() {
    return {
      availableModes: ['chat', 'task', 'topic', 'prview', 'browser', 'slides']
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