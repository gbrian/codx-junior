<script setup>
import { APP_COMPONENTS_MAP, ADDITIONAL_COMPONENTS } from '../../config/appComponentsMap.js'
import ViewProperties from '../main-menu/ViewProperties.vue'
import EmptyStateWelcome from './EmptyStateWelcome.vue'
</script>

<template>
  <div class="w-full h-full relative">
    <!-- Single app view container - renders activeApp only -->
    <div v-if="activeApp" class="w-full h-full">
      <component 
        :is="activeApp.component || 'app-window'" 
        :params="{ ...activeApp.params, app: activeApp, tabName: activeApp.name }"
        class="w-full h-full"
      />
    </div>

    <!-- Welcome state when no app is active -->
    <div v-else class="w-full h-full">
      <EmptyStateWelcome />
    </div>

    <!-- ViewProperties modal -->
    <modal close="true" @close="closeViewEditor" v-if="viewEditor">
      <ViewProperties
        :view="viewEditor.view"
        @close="closeViewEditor"
        @confirm="closeViewEditor"
      />
    </modal>
  </div>
</template>

<script>
export default {
  name: 'VibeDesktop',
  components: {
    ...APP_COMPONENTS_MAP,
    ...ADDITIONAL_COMPONENTS,
    ViewProperties,
    EmptyStateWelcome
  },
  computed: {
    activeApp() {
      return this.$storex.ui.activeApp
    },
    viewEditor() {
      return this.$storex.ui.viewEditor
    }
  },
  methods: {
    closeViewEditor() {
      this.$storex.ui.closeViewEditor()
    }
  }
}
</script>