<script setup>
import HomeViewVue from '@/views/HomeView.vue'
import SplitViewVue from '@/views/SplitView.vue'
import SharedView from '@/views/SharedView.vue'

</script>

<template>
  <div class="w-full h-full flex relative bg-transparent relative" data-theme="dark" v-if="$ui.uiReady">
    <SharedView v-if="isSharedScreen" />
    <HomeViewVue v-if="isMobileScreen" />
    <SplitViewVue v-if="isSplitterScreen" />
    <div class="toast toast-top toast-end">
      <div :class="`alert alert-${n.type}`" v-for="n in $session.notifications" :key="n.id">
        <span>{{ n.text }}</span>
        <button class="btn btn-sm btn-circle btn-ghost" @click="$session.removeNotification(n)">
          <i class="fa-regular fa-circle-xmark"></i>
        </button>
      </div>
    </div>
    <div class="absolute right-0 top-1 z-50 py-1 px-2 rounded-l text-white"
       v-if="$session.apiCalls">
       <div class="flex gap-2 items-center">
        <span class="loading loading-sm loading-spinner text-secondary"></span>
        <span class="animate-pulse"> thinking....</span>
      </div>
    </div>
  </div>
  <div class="flex flex-col items-center justify-center w-full h-full font-2xl px-4 py-2" v-else>
    <div class="animate-pulse font-mono text-green-600">Wake up, codx-junior...</div>
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
    isSharedScreen () {
      return this.$route.name === 'codx-junior-shared'
    },
    isMobileScreen () {
      return !this.isSharedScreen && this.$ui.isMobile
    },
    isSplitterScreen () {
      return !this.isSharedScreen && !this.$ui.isMobile
    }
  },
  watch: {
  },
  methods: {
  }
}
</script>
