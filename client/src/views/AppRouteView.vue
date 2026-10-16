<script setup>
import { APP_COMPONENTS_MAP } from '@/config/appComponentsMap.js'
import { APPS, getPendingParams } from '@/config/apps.js'
</script>

<template>
  <div class="w-full h-full">
    <component
      v-if="component"
      :is="component"
      :params="params"
      class="w-full h-full"
    />
    <div v-else class="flex items-center justify-center w-full h-full text-base-content/40">
      <div class="flex flex-col items-center gap-2">
        <i class="fa-solid fa-triangle-exclamation text-2xl"></i>
        <span class="text-sm">Unknown app route: {{ appKey }}</span>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'AppRouteView',
  data() {
    return {
      appKey: null
    }
  },
  computed: {
    def() {
      return APPS[this.appKey] || null
    },
    component() {
      return this.def ? APP_COMPONENTS_MAP[this.def.component] : null
    },
    // Prefer the full payload handed over by openApp(); fall back to route
    // params/query so deep-links still render something sensible.
    params() {
      if (!this.def) return {}
      const pending = getPendingParams(this.def.id)
      if (pending) return pending
      return { ...this.$route.params, ...this.$route.query }
    }
  },
  watch: {
    '$route.fullPath': {
      immediate: true,
      handler() {
        this.appKey = this.$route?.meta?.app || null
      }
    }
  }
}
</script>