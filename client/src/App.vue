<script setup>
import HomeViewVue from './views/HomeView.vue'
import SplitViewVue from './views/SplitView.vue'
</script>

<template>
  <div class="w-full h-full flex relative bg-transparent relative" data-theme="dark">
    <HomeViewVue v-if="$ui.isMobile" />
    <SplitViewVue v-else />
    <div class="toast toast-top toast-end">
      <div :class="`alert alert-${n.type}`" v-for="n in $session.notifications" :key="n.id">
        <span>{{ n.text }}</span>
        <button class="btn btn-sm btn-circle btn-ghost" @click="$session.removeNotification(n)">
          <i class="fa-regular fa-circle-xmark"></i>
        </button>
      </div>
    </div>
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
