<script setup>
import HomeViewVue from './views/HomeView.vue'
import SplitViewVue from './views/SplitView.vue'
</script>

<template>
  <div class="w-full h-full flex relative bg-transparent" data-theme="dark">
    <HomeViewVue v-if="$ui.isMobile" />
    <SplitViewVue v-else />
  </div>
</template>
<script>
export default {
  data () {
    return {
    }
  },
  created () {
  },
  computed: {
  },
  watch: {
  },
  methods: {
  }
}
</script>
