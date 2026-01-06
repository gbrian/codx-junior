<script setup>
import Iframe from '../Iframe.vue';
import NoVNC from '../NoVNC.vue';
</script>
<template>
  <div class="w-full h-full">
    <NoVNC class="w-full h-full" :path="app.path" v-if="app.is_vnc"></NoVNC>
    <Iframe class="w-full h-full" :key="app.path" :url="app.path" v-else></Iframe>
  </div>
</template>
<script>
    export default {
      props: ['app']
    }
</script>