<script setup>
import Login from './components/user/Login.vue'
import Toast from './components/Toast.vue'
import DesktopSidebar from './components/layout/DesktopSidebar.vue'
import MobileBottomBar from './components/layout/MobileBottomBar.vue'
</script>

<template>
  <div class="w-full h-full relative bg-base-300" :data-theme="$ui.theme" v-if="$ui.uiReady">
    <Login v-if="isLogin" />
    
    <div class="h-full w-full flex" v-else :class="layoutClasses">
      <!-- Desktop Sidebar (Landscape on desktop) -->
      <DesktopSidebar
        v-if="isDesktopLandscape"
        :user-name="$user?.username || 'User'"
        :user-subtitle="'Pro'"
        @settings="openAccountSettings"
      />

      <!-- Mobile Sidebar Overlay (Mobile only, slides from left) -->
      <div
        v-if="isMobile && showMobileSidebarOverlay"
        class="fixed inset-0 z-100 bg-black/50 transition-opacity duration-200 md:hidden"
        @click="showMobileSidebarOverlay = false"
      ></div>

      <!-- Mobile Sidebar (Slides from left on mobile) -->
      <DesktopSidebar
        v-if="isMobile"
        :user-name="$user?.username || 'User'"
        :user-subtitle="'Pro'"
        :is-mobile="true"
        :is-mobile-expanded="showMobileSidebarOverlay"
        class="z-150"
        @close="showMobileSidebarOverlay = false"
        @settings="openAccountSettings"
      />

      <!-- Main Content with Router -->
      <div class="grow">
        <RouterView />
      </div>

      <!-- Mobile Bottom Bar (Portrait on mobile) -->
      <MobileBottomBar
        v-if="isMobilePortrait && showMobileBottomBar"
        :user-name="$user?.username || 'User'"
        @show-menu="showMobileSidebarOverlay = true"
      />

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
      pendingProjectSwitch: null,
      windowWidth: 0,
      windowHeight: 0,
      showMobileSidebarOverlay: false
    }
  },
  computed: {
    isLogin() {
      return !this.$user
    },
    isDesktop() {
      return this.windowWidth >= 768
    },
    isMobile() {
      return this.windowWidth < 768
    },
    isLandscape() {
      return this.windowWidth > this.windowHeight
    },
    isPortrait() {
      return this.windowHeight > this.windowWidth
    },
    isDesktopLandscape() {
      return this.isDesktop && this.isLandscape
    },
    isMobileLandscape() {
      return this.isMobile && this.isLandscape
    },
    isMobilePortrait() {
      return this.isMobile && this.isPortrait
    },
    layoutClasses() {
      if (this.isMobilePortrait) {
        return 'flex-col'
      }
      return 'flex-row'
    },
    infoNotifications() {
      return this.$ui.notifications.filter(n => n.type !== 'error')
    },
    errorNotifications() {
      return this.$ui.notifications.filter(n => n.type === 'error')
    },
    showMobileBottomBar() {
      const { name, params } = this.$route
      return name != 'chat' || !params?.chatId
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
    },
    '$route'() {
      this.showMobileSidebarOverlay = false
    }
  },
  mounted() {
    this.updateDimensions()
    window.addEventListener('resize', this.updateDimensions)
  },
  beforeUnmount() {
    window.removeEventListener('resize', this.updateDimensions)
  },
  methods: {
    updateDimensions() {
      this.windowWidth = window.innerWidth
      this.windowHeight = window.innerHeight
    },
    retryProjectLoad() {
      if (this.pendingProjectSwitch) {
        this.$storex.projects.activeProjectChanged(this.pendingProjectSwitch)
      }
    },
    cancelProjectLoad() {
      this.pendingProjectSwitch = null
      this.$storex.ui.setProjectLoadingState({ isLoading: false })
    },
    openAccountSettings() {
      this.$emit('settings')
    }
  }
}
</script>