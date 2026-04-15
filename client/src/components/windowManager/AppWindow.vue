<script setup>
import Iframe from '../Iframe.vue';
import NoVNC from '../NoVNC.vue';
</script>
<template>
  <div class="w-full h-full" :class="loaded ? '': 'opacity-10'">
    <NoVNC class="w-full h-full" :path="theApp.path" v-if="theApp.is_vnc"></NoVNC>
    <Iframe class="w-full h-full" :key="theApp.path" :url="theApp.path" @loaded="loaded = true" v-else></Iframe>
  </div>
</template>
<script>
    export default {
      name: "AppWindow",
      props: ['app', 'params'],
      data() {
        return {
          loaded: false
        }
      },
      created() {
        this.loaded = (this.app || this.params?.params.app).is_vnc
      },
      computed: {
        theApp() {
          return (this.app || this.params?.params.app)
        }
      }
    }
</script>