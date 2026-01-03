<script setup>
import Iframe from '../Iframe.vue';
</script>
<template>
  <Iframe :key="$ui.activeApp.path" :url="$ui.activeApp.path"></Iframe>
</template>
<script>
    export default {
    }
</script>