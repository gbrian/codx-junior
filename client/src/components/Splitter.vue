<script setup>
import { SplitterGroup, SplitterPanel, SplitterResizeHandle } from 'radix-vue'
import BrowserVue from './browser/Browser.vue'
import CoderVue from '../components/apps/Coder.vue'
import CodxJuniorVue from '../views/CodxJunior.vue'
</script>

<template>
  <div class="bg-base-300">
    <SplitterGroup
      id="splitter-group-1"
      direction="horizontal"
    >
      <SplitterPanel
        id="splitter-group-1-panel-1"
        :min-size="20"
        class=""
      >
      <SplitterGroup
        id="splitter-group-2"
        :direction="isHorizontal ? 'horizontal' : 'vertical'"
        v-if="$ui.appDivided !== 'none'"
      >
        <SplitterPanel
          id="splitter-group-2-panel-1"
          :min-size="20"
          class=""
          v-if="$ui.showCoder"
        >
          <CoderVue class="h-full w-full" />
        </SplitterPanel>
        <SplitterResizeHandle
          id="splitter-group-2-resize-handle-1"
          class="bg-slate-600" :class="isHorizontal ? 'w-1' : 'h-1'"
          v-if="$ui.showBrowser && $ui.showCoder"
        />   
        <SplitterPanel
          id="splitter-group-2-panel-2"
          :min-size="20"
          class=""
          v-if="$ui.showBrowser"
        >
          <BrowserVue class="h-full w-full p-1" />
        </SplitterPanel>
      </SplitterGroup>
      <div class="h-full w-full" v-else>
        <CoderVue class="h-full w-full"
          :class="$ui.appActives[0] === 'coder' ? '': 'hidden'" />
        <BrowserVue class="h-full w-full p-1"
          :class="$ui.appActives[0] === 'browser' ? '': 'hidden'"/>
      </div>
      </SplitterPanel>
      <SplitterResizeHandle
        id="splitter-group-1-resize-handle-1"
        class="bg-slate-600 w-1"
      />
      <SplitterPanel
        id="splitter-group-1-panel-2"
        :min-size="3"
        :defaultSize="$ui.codxJuniorWidth"
        class="flex items-center justify-center"
        @resize="size => $ui.setCodxJuniorWidth(size)"
      >
        <CodxJuniorVue class="w-full h-full" />
      </SplitterPanel>
    </SplitterGroup>
  </div>
</template>
<script>
export default {
  data () {
    return {
    }
  },
  computed: {
    isHorizontal () {
      return this.$ui.appDivided === 'horizontal'
    }
  }
}
</script>