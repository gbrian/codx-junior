<script setup>
</script>
<template lang="pug">
  // Main container with flexbox layout for arranging child elements vertically
  .flex.flex-col.gap-2.h-full
    // Horizontal flexbox container with gap between elements, includes a label and an input for URL
    .flex.gap-2.text-xl
      span URL  // Label for the input field
      // Input field with two-way data binding to the 'url' data property
      input.input.input-xs.input-bordered.w-full(v-model="url")
    // Container that grows and occupies remaining space
    .w-full.grow
      // Iframe that dynamically loads the URL entered in the input field
      iframe.boder-0.w-full.h-full.p-0(:src="url")
</template>
<script>
  export default {
    data () {
      return {
        // Reactive data property to hold the URL entered by the user
        url: null
      }
    }
  }
</script>