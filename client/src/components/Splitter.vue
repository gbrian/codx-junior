<script setup>
import CodxJuniorVue from '../views/CodxJunior.vue'
import NavigationBar from '../components/NavigationBar.vue'
import LogViewerVue from './LogViewer.vue'
import StatuBar from './StatuBar.vue'
import Navigator from './windowManager/Navigator.vue'
import VerticalSplitter from './layout/VerticalSplitter.vue'
import VerticalBarVue from './project/VerticalBar.vue'
</script>

<template>
  <div class="flex flex-col h-full">
    <NavigationBar class="p-2 border-b-2 border-slate-400/30" :right="true" 
      @mouseenter="mouseOnNavigation = true" 
      @mouseover="mouseOnNavigation = true"
      @mouseleave="mouseOnNavigation = false"
      @blur="mouseOnNavigation = false" 
      v-if="showNavigationBar"  
    />
    <div class="flex grow">
      <div class="grow h-full overflow-auto min-h-96">
        <VerticalSplitter 
          :panels="{ left: { defaultSize: 60 }, right: { defaultSize: 40 }}"
        >
          
          <template v-slot:left v-if="$ui.activeApp">
            <Navigator class="w-full h-full" />

          </template>
          <template v-slot:right v-if="$ui.activeTab || $ui.showLogs">

          <VerticalSplitter class="grow flex h-full min-h-96 relative" 
            :panels="{ left: { defaultSize: 60 }, right: { defaultSize: 40 }}"
          >
            <template v-slot:left v-if="$ui.activeTab">
              <div class="flex flex-col items-center h-full">
                <CodxJuniorVue ref="codxJunior" 
                  class="h-full w-full" 
                  :class="[ activeApp ? 'px-2' : 'xl:mx-10 2xl:mx-20' ]"
                  :style="`zoom:${ zoom }`" 
                  v-if="!$ui.isMobile || !$ui.activeApp"
                />
              </div>
              </template>
              <template v-slot:right v-if="$ui.showLogs">
                <LogViewerVue class="text-xs bg-base-300 w-full h-full" />
              
              </template>
            </VerticalSplitter>

          </template>
        </VerticalSplitter>
      </div>
      <VerticalBarVue />
    </div>
    <StatuBar />
  </div>
</template>
<script>
export default {
  data() {
    return {
      mouseOnNavigation: false
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
    activeApp() {
      return this.$ui.activeApp
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
            || this.activeApp
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
