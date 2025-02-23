<script setup>
import BrowserVue from '../components/browser/Browser.vue'
</script>
<template>
  <BrowserVue class="h-full w-full" :token="$ui.monitors['shared']"  />
</template>
