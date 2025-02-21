<script setup>
import HomeViewVue from '@/views/HomeView.vue'
import SplitViewVue from '@/views/SplitView.vue'
import SharedView from '@/views/SharedView.vue'

</script>

<template>
  <div class="w-full h-full flex relative bg-transparent relative" data-theme="dark" v-if="$ui.uiReady">
    <div class="absolute top-0 h-1" 
      :class="$session.apiCalls && 'w-full bg-secondary/70 animate-pulse z-50'"></div>
    <SharedView v-if="isSharedScreen" />
    <HomeViewVue v-if="isMobileScreen" />
    <SplitViewVue v-if="isSplitterScreen" />
    <div class="absolute top-0 right-0 p-2" v-if="$ui.notifications.length">
      <div class="p-2 text-xs bg-info/30 hover:bg-sky-700 text-white rounded-md">
        <div v-for="notification in $ui.notifications" :key="notification.ts">
          <pre><span class="click hover:underline" @click="$ui.removeNotification(notification)">(X)</span>[{{ notification.ts }}] {{ notification.text }}</pre>
          
        </div>
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
