<script setup>
import HomeViewVue from '@/views/HomeView.vue'
import SplitViewVue from '@/views/SplitView.vue'
import SharedView from '@/views/SharedView.vue'
import Login from './components/user/Login.vue';
import Wizard from './components/wizards/Wizard.vue'
</script>

<template>
  <div class="w-full h-full flex relative bg-base-100 relative" :data-theme="$ui.theme" v-if="$ui.uiReady">
    <div class="absolute top-0 h-1" 
      :class="$session.apiCalls && 'w-full bg-secondary/70 animate-pulse z-50'"></div>
    <SharedView v-if="isSharedScreen" />
    <HomeViewVue v-if="isMobileScreen" />
    <SplitViewVue v-if="isSplitterScreen" />
    <Login v-if="isLogin" />
    <div class="absolute top-0 right-0 p-2">
      <div class="p-2 text-xs bg-error/30 hover:bg-error text-white rounded-md" v-if="errorNotifications.length">
        <div class="click" v-for="notification in errorNotifications" :key="notification.ts" @click="$ui.removeNotification(notification)">
          <pre><span class="click hover:underline">(X)</span>[{{ notification.ts }}] ERROR: {{ notification.text }}</pre>
        </div>
      </div>
      <div class="p-2 text-xs bg-info/30 hover:bg-sky-700 text-white rounded-md" v-if="infoNotifications.length">
        <div class="click" v-for="notification in infoNotifications" :key="notification.ts" @click="$ui.removeNotification(notification)">
          <pre><span class="click hover:underline">(X)</span>[{{ notification.ts }}] {{ notification.text }}</pre>
        </div>
      </div>
    </div>
    <modal v-if="openWizard">
      <Wizard :wizard="openWizard" @close="openWizard = null" />
    </modal>
  </div>
  <div class="flex flex-col items-center justify-center w-full h-full font-2xl px-4 py-2" v-else>
    <div class="animate-pulse font-mono text-green-600">Wake up, codx-junior...</div>
  </div>
</template>
<script>
export default {
  data () {
    return {
      openWizard: false
    }
  },
  created () {
  },
  computed: {
    infoNotifications() {
      return this.$ui.notifications.filter(n => n.type !== 'error')
    },
    errorNotifications() {
      return this.$ui.notifications.filter(n => n.type === 'error')
    },
    isSharedScreen () {
      return this.$user && this.$route.name === 'codx-junior-shared'
    },
    isMobileScreen () {
      return this.$user && !this.isSharedScreen && this.$ui.isMobile
    },
    isSplitterScreen () {
      return this.$user && !this.isSharedScreen && !this.$ui.isMobile
    },
    isLogin () {
      return !this.$user
    }
  },
  watch: {
  },
  methods: {
    launchIssueWizard(wizard) {
      this.openWizard = wizard
    }
  },
  expose: ['launchIssueWizard']
}
</script>
