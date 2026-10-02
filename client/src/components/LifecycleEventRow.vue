<script setup>
import ChatEntryEvent from './ChatEntryEvent.vue'
</script>

<template>
  <ChatEntryEvent 
    :lifecycleEvent="lifecycleEvent" 
    :compact="true"
  />
</template>

<script>
export default {
  props: {
    lifecycleEvent: {
      type: Object,
      required: true
    }
  }
}
</script>