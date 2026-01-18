<script setup>
import { SplitterGroup, SplitterPanel, SplitterResizeHandle } from 'radix-vue'
import CodxJuniorVue from '../views/CodxJunior.vue'
import NavigationBar from '../components/NavigationBar.vue'
import LogViewerVue from './LogViewer.vue'
import StatuBar from './StatuBar.vue'
import Navigator from './windowManager/Navigator.vue'
import VerticalSplitter from './layout/VerticalSplitter.vue'
import RightBarVue from './project/RightBar.vue'
</script>

<template>
  <div class="flex">
    <div class="bg-base-300 flex flex-col h-full pt-2 grow">
      <NavigationBar class="pt-2 px-2 border-b-2 border-slate-400/30 mb-2" :right="true" 
        @mouseenter="mouseOnNavigation = true" 
        @mouseover="mouseOnNavigation = true"
        @mouseleave="mouseOnNavigation = false"
        @blur="mouseOnNavigation = false" 
        v-if="showNavigationBar"  
      />

      <VerticalSplitter class="grow flex h-full min-h-96" 
        :panels="{ left: { defaultSize: 60 }, right: { defaultSize: 40 }}"
      >
        
        <template v-slot:left v-if="$ui.activeApp">
          <Navigator class="w-full h-full" />

        </template>
        <template v-slot:right v-if="$ui.activeTab || $ui.showLogs">

          <VerticalSplitter class="grow flex h-full min-h-96" 
            :panels="{ left: { defaultSize: 60 }, right: { defaultSize: 40 }}"
          >
        
            <template v-slot:left v-if="$ui.activeTab">
              <CodxJuniorVue ref="codxJunior" 
                class="h-full w-full" 
                :class="[ activeApp ? 'px-2' : '@xl:mx-10 @2xl:mx-20' ]"
                :style="`zoom:${ zoom }`" 
                v-if="!$ui.isMobile || !$ui.activeApp"
              />

            </template>
            <template v-slot:right v-if="$ui.showLogs">
              <LogViewerVue class="text-xs bg-base-300 w-full h-full" />
            
            </template>
          </VerticalSplitter>

        </template>
      </VerticalSplitter>
      <StatuBar />

    </div>
    <RightBarVue />
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
