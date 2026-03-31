<script setup>
import CodxJuniorVue from '../views/CodxJunior.vue'
import LogViewerVue from './LogViewer.vue'
import StatuBar from './StatuBar.vue'
import Navigator from './windowManager/Navigator.vue'
import VerticalSplitter from './layout/VerticalSplitter.vue'
import VerticalBarVue from './project/VerticalBar.vue'
</script>

<template>
  <div class="flex">
    <div class="grow flex flex-col h-full overflow-hidden">
      <VerticalSplitter 
        :panels="{ left: { defaultSize: 60 }, right: { defaultSize: 40 }}"
      > 
        <template v-slot:left v-if="$ui.activeApp">
          <Navigator class="w-full h-full" />
        </template>
        <template v-slot:right v-if="$ui.activeTab || $ui.showLogs">
          <VerticalSplitter class="grow flex h-full relative" 
            :panels="{ left: { defaultSize: 60 }, right: { defaultSize: 40 }}"
          >
            <template v-slot:left v-if="$ui.activeTab">
              <div class="h-full flex flex-col items-center">
                <CodxJuniorVue ref="codxJunior" 
                  class="h-full w-full px-2" 
                  :style="`zoom:${ zoom }`" 
                />
              </div>
            </template>
            <template v-slot:right v-if="$ui.showLogs">
              <div class="relative w-full h-full">
                <LogViewerVue class="text-xs bg-base-300 absolute top-0 left-0 w-full h-full overflow-auto" />
              </div>
            </template>
          </VerticalSplitter>
        </template>
      </VerticalSplitter>
      <StatuBar />
    </div>
    <VerticalBarVue />
  </div>
</template>
<script>
export default {
  data() {
    return {
    }
  },
  computed: {
    zoom() {
      return this.$ui.activeApp && this.showCodxJunior ? 1.2 : 1
    },
    isHorizontal() {
      return this.$ui.appDivided === 'horizontal'
    },
    showCodxJunior() {
      return !!this.$ui.activeTab
    },
    showCodxJuniorFloating() {
      return !this.$ui.isMobile && this.$ui.floatingCodxJunior
    },
    showWorkspaces() {
      return this.$storex.projects.openedWorkspaces.length
    },
    showNavigationBar() {
      return !this.$ui.isMobile || !this.$projects.activeChat 
            || this.$ui.activeTab !== 'tasks'
            || this.$ui.activeApp
    }
  },
  mounted() {
  },
  watch: {
  },
  methods: {
    onDblclickCodxJunior() {
      console.log("onDblclickCodxJunior")
    }
  }
}
</script>
