<script setup>
import { SplitterGroup, SplitterPanel, SplitterResizeHandle } from 'radix-vue'
import NoVNCVue from '../components/NoVNC.vue'
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
        class="flex items-center justify-center"
      >
        <div class="flex flex-col justify-start w-full h-full">
          <div role="tablist" class="tabs tabs-lifted">
            <a role="tab" class="tab" @click="appActiveTab = 0"
              :class="appActiveTab === 0 ? 'tab-active' : '' " 
              v-if="$ui.showCoder"
            >
              Coder</a>
            <a role="tab" class="tab" @click="appActiveTab = 1"
              :class="appActiveTab === 1 ? 'tab-active' : '' " 
              v-if="$ui.showBrowser"
            >
              Browser</a>
          </div>
          <CoderVue class="h-full w-full"
            :class="appActiveTab === 0 ? '' : 'hidden' " 
            v-if="$ui.showCoder" />
          <NoVNCVue class="h-full w-full p-1"
            :class="appActiveTab === 1 ? '' : 'hidden' "
            v-if="$ui.showBrowser" />
        </div>
      </SplitterPanel>
      <SplitterResizeHandle
        id="splitter-group-1-resize-handle-1"
        class="w-2"
      />
      <SplitterPanel
        id="splitter-group-1-panel-2"
        :min-size="3"
        :defaultSize="$ui.codxJuniorWidth"
        class="flex items-center justify-center border-l border-sky-500/40"
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
      appActiveTab: 0
    }
  }
}
</script>