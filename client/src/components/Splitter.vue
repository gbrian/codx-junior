<script setup>
import { SplitterGroup, SplitterPanel, SplitterResizeHandle } from 'radix-vue'
import CoderVue from '../components/apps/Coder.vue'
import PreviewVue from '../components/apps/Preview.vue'
import CodxJuniorVue from '../views/CodxJunior.vue'
import NavigationBar from '../components/NavigationBar.vue'
import LogViewerVue from './LogViewer.vue'
import WorkspacesViewer from './workspaces/WorkspacesViewer.vue'
</script>

<template>
  <div class="bg-base-300 flex flex-col h-full">
    <NavigationBar class="px-2 border-b border-b-gray-800" :right="true" 
      @mouseenter="mouseOnNavigation = true" 
      @mouseover="mouseOnNavigation = true"
      @mouseleave="mouseOnNavigation = false"
      @blur="mouseOnNavigation = false" 
      v-if="showNavigationBar"  
    />
    <SplitterGroup id="splitter-group-1" class="relative grow @container" 
      direction="horizontal" auto-save-id="splitter-group-1">

      <SplitterPanel id="splitter-group-1-apps" :order="0" :min-size="20" :class="!$ui.showApp && 'hidden'">
        <SplitterGroup id="splitter-group-2" 
          :direction="isHorizontal ? 'horizontal' : 'vertical'"
          auto-save-id="splitter-group-2"
          v-if="$ui.appDivided !== 'none'"
        >
          <SplitterPanel id="splitter-group-2-coder" :order="0" :min-size="20" v-if="$ui.showCoder">
            <CoderVue class="h-full w-full" />
          </SplitterPanel>
          <SplitterResizeHandle id="splitter-group-2-resize-handle-1" class="bg-stone-800 hover:bg-slate-600"
            :class="isHorizontal ? 'w-1' : 'h-1'" v-if="$ui.showBrowser && $ui.showCoder" />
          <SplitterPanel id="splitter-group-2-preview" :min-size="20" class="" :order="1" v-if="$ui.showBrowser">
            <PreviewVue class="h-full w-full" :app="'preview'" />
          </SplitterPanel>
        </SplitterGroup>
        <div class="h-full w-full" v-if="$ui.showApp && $ui.appDivided === 'none'">
          <CoderVue class="h-full w-full" v-if="$ui.showCoder" />
          <PreviewVue class="h-full w-full" :app="'preview'"
            v-if="$ui.showBrowser" />
        </div>
      </SplitterPanel>

      <SplitterResizeHandle id="splitter-group-1-resize-handle-1" class="bg-stone-800 hover:bg-slate-600 w-1 hover:w-2 transition-all"
        v-if="$ui.showApp && showCodxJunior" />

      <SplitterPanel id="splitter-group-1-codx-junior" :order="1" :min-size="showCodxJuniorFloating ? 0 : $ui.showApp ?  20 : 100"
        :defaultSize="showCodxJuniorFloating ? 0 : $ui.codxJuniorWidth"
        class="flex items-center justify-center transition-all transition-discrete"
        :class="[
          showCodxJuniorFloating ? 'absolute z-50 right-0 top-0 bottom-0 border-red-600 w-2 opacity-30 hover:w-2/4 hover:opacity-90' : '',
          (showCodxJuniorFloating && mouseOnNavigation) && 'w-2/4 opacity-90',
          !showCodxJunior && 'hidden'
        ]"
        @resize="size => $ui.setCodxJuniorWidth(size)">
        <CodxJuniorVue ref="codxJunior" 
          class="h-full" 
          :class="[ showApp ? 'w-full' : 'w-full mx-10 2xl:mx-20' ]"
          :style="`zoom:${ zoom }`" 
          v-if="!$ui.isMobile || !$ui.showApp"
        />
      </SplitterPanel>

      <SplitterResizeHandle id="splitter-group-1-resize-handle-2" class="bg-stone-800 hover:bg-slate-600 w-1 hover:w-2 transition-all" :class="!$ui.showLogs && 'hidden'"/>

      <SplitterPanel id="splitter-group-1-logs" :order="3" :defaultSize="25" :minSize="20" class="flex items-center justify-center"
        v-if="$ui.showLogs">
        <LogViewerVue class="text-xs bg-base-300 w-full h-full" />
      </SplitterPanel>

      <!-- New SplitterPanel for WorkspacesViewer -->
      <SplitterResizeHandle id="splitter-group-1-resize-handle-3" class="bg-stone-800 hover:bg-slate-600 w-1 hover:w-2 transition-all" v-if="showWorkspaces" />

      <SplitterPanel id="splitter-group-1-panel-4" :order="4" :defaultSize="25" :minSize="20" class="flex items-center justify-center"
        v-if="showWorkspaces">
        <WorkspacesViewer class="w-full h-full" />
      </SplitterPanel>
    </SplitterGroup>
    <div class="h-6 bg-white/10">
    </div>
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
      return this.$ui.showApp && this.showCodxJunior ? 1.2 : 1
    },
    isHorizontal() {
      return this.$ui.appDivided === 'horizontal'
    },
    showCodxJunior() {
      return !!this.$ui.activeTab
    },
    showApp() {
      return this.$ui.showApp
    },
    showCodxJuniorFloating() {
      return this.$ui.floatingCodxJunior || 
        (this.$ui.showBrowser && this.$ui.showCoder) ||
        (this.$ui.isMobile && (this.showApp || this.$ui.showLogs))
    },
    showWorkspaces() {
      return this.$storex.projects.openedWorkspaces.length
    },
    showNavigationBar() {
      return !this.$ui.isMobile || !this.$projects.activeChat 
            || this.$ui.activeTab !== 'tasks'
            || this.showApp
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
