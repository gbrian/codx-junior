<script setup>
import BrowserVue from '../browser/Browser.vue';
</script>
<template>
  <BrowserVue class="h-full w-full" :token="$ui.monitors[app]"  />
</template>
<script>
export default {
  props: ['app']
}
</script>