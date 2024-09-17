<script setup>
</script>
<template lang="pug">
  .flex.flex-col.gap-2.h-full
    .flex.gap-2.text-xl
      span URL
      input.input.input-xs.input-bordered.w-full(v-model="url")
    .w-full.grow
      iframe.boder-0.w-full.h-full.p-0(:src="url")
</template>
<script>
  export default {
    data () {
      return {
        url: null
      }
    }
  }
</script>