<script setup>
import moment from 'moment'
</script>

<template>
  <div 
    v-if="parentChat"
    class="transition-all duration-200 rounded-md tooltip"
    :data-tip="isDisconnected ? 'Knowledge & files disconnected' : 'Context connected'"
    :class="[
      isDisconnected 
        ? 'bg-warning/5 border-4 border-warning' 
        : 'bg-info/5 border-4 border-info'
    ]"
  >
    <button
      class="btn btn-xs btn-ghost shrink-0 transition-colors"
      :class="isDisconnected ? 'hover:text-warning' : 'hover:text-info'"
      @click="toggleParentDisconnect"
      :title="isDisconnected ? 'Reconnect parent context' : 'Disconnect parent context'"
    >
    <div class="flex items-center gap-2 min-w-0 flex-1">
        <i 
          :class="[
            'fa-solid text-xs shrink-0',
            isDisconnected ? 'fa-link-slash text-warning' : 'fa-link text-info'
          ]"
        ></i>
      </div>
    </button>
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