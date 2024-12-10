<script setup>
import { SplitterGroup, SplitterPanel, SplitterResizeHandle } from 'radix-vue'
import BrowserVue from './browser/Browser.vue'
import CoderVue from '../components/apps/Coder.vue'
import CodxJuniorVue from '../views/CodxJunior.vue'
import NavigationBar from '../components/NavigationBar.vue'
</script>

<template>
  <div class="bg-base-300 flex">
    <SplitterGroup
      id="splitter-group-1"
      direction="horizontal"
    >
      <SplitterPanel
        id="splitter-group-1-panel-1"
        :min-size="20"
        class=""
        v-if="$ui.showApp"
      >
      <SplitterGroup
        id="splitter-group-2"
        :direction="isHorizontal ? 'horizontal' : 'vertical'"
        v-if="$ui.appDivided !== 'none'"
      >
        <SplitterPanel
          id="splitter-group-2-panel-1"
          :min-size="40"
          class=""
          v-if="$ui.showCoder"
        >
          <CoderVue class="h-full w-full" />
        </SplitterPanel>
        <SplitterResizeHandle
          id="splitter-group-2-resize-handle-1"
          class="bg-stone-800"
          :style="`${isHorizontal ? 'width' : 'height'}: 2px`"
          v-if="$ui.showBrowser && $ui.showCoder"
        />   
        <SplitterPanel
          id="splitter-group-2-panel-2"
          :min-size="20"
          class=""
          v-if="$ui.showBrowser"
        >
          <BrowserVue class="h-full w-full" />
        </SplitterPanel>
      </SplitterGroup>
      <div class="h-full w-full" v-else>
        <CoderVue class="h-full w-full"
          :class="$ui.appActives[0] === 'coder' ? '': 'hidden'" />
        <BrowserVue class="h-full w-full"
          :class="$ui.appActives[0] === 'browser' ? '': 'hidden'"/>
      </div>
      </SplitterPanel>

      <SplitterResizeHandle
        id="splitter-group-1-resize-handle-1"
        class="bg-stone-800"
        style="width: 2px;"
        v-if="$ui.showApp"
      />

      <SplitterPanel
        id="splitter-group-1-panel-2"
        :min-size="$ui.showApp ? 0 : 100"
        :defaultSize="$ui.codxJuniorWidth"
        class="flex items-center justify-center"
        @resize="size => $ui.setCodxJuniorWidth(size)"
        v-if="!$ui.showApp || showCodxJunior">
        
        <CodxJuniorVue class="w-full h-full" />
      </SplitterPanel>

    </SplitterGroup>
    <NavigationBar :right="true" v-if="$ui.isLandscape" />

  </div>
</template>
<script>
export default {
  data () {
    return {
      showCodxJunior: true
    }
  },
  computed: {
    isHorizontal () {
      return this.$ui.appDivided === 'horizontal'
    }
  },
  methods: {
    onDblclickCodxJunior () {
      console.log("onDblclickCodxJunior")
      // this.showCodxJunior = !this.showCodxJunior
    }
  }
}
</script>