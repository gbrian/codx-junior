<script setup>
import { SplitterGroup, SplitterPanel, SplitterResizeHandle } from 'radix-vue'
import BrowserVue from './browser/Browser.vue'
import CoderVue from '../components/apps/Coder.vue'
import PreviewVue from '../components/apps/Preview.vue'
import CodxJuniorVue from '../views/CodxJunior.vue'
import NavigationBar from '../components/NavigationBar.vue'
import LogViewerVue from './LogViewer.vue'
</script>

<template>
  <div class="bg-base-300 flex">
    <SplitterGroup id="splitter-group-1" class="relative" 
      direction="horizontal" auto-save-id="splitter-group-1">
      <SplitterPanel id="splitter-group-1-panel-1" :order="0" :min-size="20" class="" v-if="$ui.showApp">
        <SplitterGroup id="splitter-group-2" 
          :direction="isHorizontal ? 'horizontal' : 'vertical'"
          auto-save-id="splitter-group-2"
          v-if="$ui.appDivided !== 'none'"
        >
          <SplitterPanel id="splitter-group-2-panel-1" :order="0" :min-size="20" v-if="$ui.showCoder">
            <CoderVue class="h-full w-full" />
          </SplitterPanel>
          <SplitterResizeHandle id="splitter-group-2-resize-handle-1" class="bg-stone-800 hover:bg-slate-600"
            :class="isHorizontal ? 'w-1' : 'h-1'" v-if="$ui.showBrowser && $ui.showCoder" />
          <SplitterPanel id="splitter-group-2-panel-2" :min-size="20" class="" :order="1" v-if="$ui.showBrowser">
            <PreviewVue class="h-full w-full" :token="$ui.monitorToken" />
          </SplitterPanel>
        </SplitterGroup>
        <div class="h-full w-full" v-if="$ui.showApp && $ui.appDivided === 'none'">
          <CoderVue class="h-full w-full" v-if="$ui.showCoder" />
          <PreviewVue class="h-full w-full" :token="$ui.monitorToken"
            v-if="$ui.showBrowser" />
        </div>
      </SplitterPanel>

      <SplitterResizeHandle id="splitter-group-1-resize-handle-1" class="bg-stone-800 hover:bg-slate-600 w-1"
        v-if="$ui.showApp && showCodxJunior" />

      <SplitterPanel id="splitter-group-1-panel-2" :order="1" :min-size="$ui.floatingCodxJunior ? 0 : $ui.showApp ?  20 : 100"
        :defaultSize="$ui.floatingCodxJunior ? 0 : $ui.codxJuniorWidth"
        class="flex items-center justify-center transition-all transition-discrete"
        :class="$ui.floatingCodxJunior ? 'absolute z-50 right-0 top-0 bottom-0 border-red-600 w-2 opacity-30 hover:w-2/4 hover:opacity-90' : ''"
        @resize="size => $ui.setCodxJuniorWidth(size)"
        v-if="showCodxJunior">

        <CodxJuniorVue class="w-full h-full" />
      </SplitterPanel>

      <SplitterResizeHandle id="splitter-group-1-resize-handle-2" class="bg-stone-800 hover:bg-slate-600 w-1" v-if="$ui.showLogs"/>

      <SplitterPanel id="splitter-group-1-panel-3" :order="3" :defaultSize="25" :minSize="20" class="flex items-center justify-center"
        v-if="$ui.showLogs">
        <LogViewerVue class="text-xs bg-base-300 w-full h-full" />
      </SplitterPanel>

    </SplitterGroup>
    <NavigationBar :right="true" v-if="$ui.isLandscape" />

  </div>
</template>
<script>
export default {
  data() {
    return {
    }
  },
  computed: {
    isHorizontal() {
      return this.$ui.appDivided === 'horizontal'
    },
    showCodxJunior() {
      return !!this.$ui.tabIx
    }
  },
  methods: {
    onDblclickCodxJunior() {
      console.log("onDblclickCodxJunior")
    }
  }
}
</script>