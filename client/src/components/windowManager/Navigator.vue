<script setup>
import Iframe from '../Iframe.vue';
import NoVNC from '../NoVNC.vue';
</script>
<template>
  <NoVNC :path="$ui.activeApp.path" v-if="$ui.activeApp.is_vnc"></NoVNC>
  <Iframe :key="$ui.activeApp.path" :url="$ui.activeApp.path" v-else></Iframe>
</template>
<script>
    export default {
    }
</script>