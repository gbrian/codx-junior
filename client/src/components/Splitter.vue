<script setup lang="ts">
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
        <CoderVue class="h-full grow" v-if="$ui.showCoder" />
        <NoVNCVue class="h-full grow p-1" v-if="$ui.showPreview" />
      </SplitterPanel>
      <SplitterResizeHandle
        id="splitter-group-1-resize-handle-1"
        class="w-2"
      />
      <SplitterPanel
        id="splitter-group-1-panel-2"
        :min-size="20"
        class="flex items-center justify-center"
      >
        <CodxJuniorVue class="w-full h-full" />
      </SplitterPanel>
    </SplitterGroup>
  </div>
</template>