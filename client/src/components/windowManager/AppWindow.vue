<script setup>
import Iframe from '../Iframe.vue';
import NoVNC from '../NoVNC.vue';
</script>
<template>
  <div class="w-full h-full" :class="loaded ? '': 'opacity-10'">
    <NoVNC class="w-full h-full" :path="app.path" v-if="app.is_vnc"></NoVNC>
    <Iframe class="w-full h-full" :key="app.path" :url="app.path" @loaded="loaded = true" v-else></Iframe>
  </div>
</template>
<script>
    export default {
      props: ['app'],
      data() {
        return {
          loaded: this.app.is_vnc
        }
      }
    }
</script>