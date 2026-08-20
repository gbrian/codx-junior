<script setup>
import SplitViewVue from '@/views/SplitView.vue'
import Login from './components/user/Login.vue'
import NewProject from './components/project/NewProject.vue'
import ProjectLoadingOverlay from './components/project/ProjectLoadingOverlay.vue'
import HomeMobile from './views/HomeMobile.vue'
import TeamView from './views/TeamView.vue'
</script>

<template>
  <div class="w-full h-full relative bg-base-300" :data-theme="$ui.theme" v-if="$ui.uiReady">
    <Login v-if="isLogin" />
    
    <div class="h-full w-full" v-else>
      <HomeMobile v-if="$ui.isMobile" />
      <TeamView />

      <modal class="w-fit h-2/3" 
        close="true" @close="$ui.showNewProject(false)" v-if="$ui.newProject">
        <NewProject />
      </modal>

      <!-- Project Loading Overlay -->
      <!-- ProjectLoadingOverlay 
        ref="loadingOverlay"
        data-test="project-loading-overlay"
        @retry="retryProjectLoad"
        @cancel="cancelProjectLoad"
      /-->

      <!-- Notifications Panel -->
      <div class="hidden absolute top-0 right-0 p-2">
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
    </div>
  </div>
  
  <div class="flex flex-col items-center justify-center w-full h-full font-2xl px-4 py-2" v-else>
    <div class="animate-pulse font-mono text-green-600">Wake up, codx-junior...</div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      pendingProjectSwitch: null
    }
  },
  computed: {
    infoNotifications() {
      return this.$ui.notifications.filter(n => n.type !== 'error')
    },
    errorNotifications() {
      return this.$ui.notifications.filter(n => n.type === 'error')
    },
    isSharedScreen() {
      return this.$user && this.$route.name === 'codx-junior-shared'
    },
    isMobileScreen() {
      return this.$user && !this.isSharedScreen && this.$ui.isMobile
    },
    isSplitterScreen() {
      return this.$user && !this.isSharedScreen && !this.$ui.isMobile
    },
    isLogin() {
      return !this.$user
    }
  },
  watch: {
    '$ui.projectLoadingState': {
      handler(newState) {
        if (!newState || !newState.isLoading) return
        
        const overlay = this.$refs.loadingOverlay
        if (overlay && typeof overlay.startLoading === 'function') {
          overlay.startLoading(newState.projectName)
        }
      },
      deep: true
    }
  },
  methods: {
    retryProjectLoad() {
      if (this.pendingProjectSwitch) {
        this.$storex.projects.activeProjectChanged(this.pendingProjectSwitch)
      }
    },

    cancelProjectLoad() {
      this.pendingProjectSwitch = null
      this.$storex.ui.setProjectLoadingState({ isLoading: false })
    }
  }
}
</script>