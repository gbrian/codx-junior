<script setup>
import moment from 'moment'
</script>

<template>
  <div 
    v-if="parentChat"
    class="transition-all duration-200 rounded-md"
    :class="[
      isDisconnected 
        ? 'bg-warning/5 border-l-4 border-warning' 
        : 'bg-info/5 border-l-4 border-info'
    ]"
  >
    <div class="flex items-center justify-between px-3 py-1 gap-2">
      <!-- Left: Parent info -->
      <div class="flex items-center gap-2 min-w-0 flex-1">
        <i 
          :class="[
            'fa-solid text-xs shrink-0',
            isDisconnected ? 'fa-link-slash text-warning' : 'fa-link text-info'
          ]"
        ></i>
      </div>

      <!-- Right: Toggle button -->
      <button
        class="btn btn-xs btn-ghost shrink-0 transition-colors"
        :class="isDisconnected ? 'hover:text-warning' : 'hover:text-info'"
        @click="toggleParentDisconnect"
        :title="isDisconnected ? 'Reconnect parent context' : 'Disconnect parent context'"
      >
        <span class="text-xs font-medium">
            {{ isDisconnected ? 'Knowledge & files disconnected' : 'Context connected' }}
        </span>
      </button>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    parentChat: {
      type: Object,
      required: true
    },
    isDisconnected: {
      type: Boolean,
      default: false
    }
  },
  emits: ['toggle-disconnect'],
  methods: {
    toggleParentDisconnect() {
      this.$emit('toggle-disconnect')
    }
  }
}
</script>