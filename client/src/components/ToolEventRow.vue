<script setup>
import ChatEntryTools from './ChatEntryTools.vue'
</script>

<template>
  <ChatEntryTools 
    :toolEvent="toolEvent" 
    :compact="true"
  />
</template>

<script>
export default {
  props: {
    toolEvent: {
      type: Object,
      required: true
    }
  }
}
</script>