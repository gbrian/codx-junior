<script setup>
import Login from './components/user/Login.vue'
import NewProject from './components/project/NewProject.vue'
import Toast from './components/Toast.vue'
</script>

<template>
  <div class="w-full h-full relative bg-base-300" :data-theme="$ui.theme" v-if="$ui.uiReady">
    <Login v-if="isLogin" />
    
    <div class="h-full w-full" v-else>
      <!-- All views are now managed by the router -->
      <RouterView />

      <modal class="w-fit h-2/3" 
        close="true" @close="$ui.showNewProject(false)" v-if="$ui.newProject">
        <NewProject />
      </modal>

      <!-- Toast Notifications -->
      <Toast ref="toastComponent" />
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
  mounted() {
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