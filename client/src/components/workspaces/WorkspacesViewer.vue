<script setup>
import Iframe from '../Iframe.vue';
</script>
<template>
  <div>
    <div v-if="showTabs" class="tabs tabs-lift">
      <div class="tab" v-for="tab in workspaces" :key="tab.workspace.id"
        @click="selectedTab = tab"
      >
        <i :class="tab.app.icon || 'fa-regular fa-window-maximize'" class="size-4 me-2"></i>
        <span>{{ tab.workspace.name }} - {{ tab.app.name }}</span>
      </div>
    </div>
    <Iframe :url="`/workspace/${selectedTab.port}`" v-if="selectedTab" />
  </div>
</template>

<script>
export default {
  data() {
    return {
      selectedTab: null
    }
  },
  created() {
    this.selectedTab = this.workspaces[0] 
  },
  computed: {
    workspaces() {
      return this.$storex.projects.openedWorkspaces
    },
    showTabs() {
      return this.workspaces.length > 1;
    }
  }
}
</script>
