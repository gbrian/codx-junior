<script setup>
import { SplitterGroup, SplitterPanel, SplitterResizeHandle } from 'radix-vue'
</script>
<template>
  <SplitterGroup class="h-full" :id="groupId" direction="horizontal">
      <SplitterPanel
        :id="`${groupId}-panel-splitter-1`" 
        :min-size="10" :collapsible="true" class="" :order="0"
          v-if="$slots.left"
        >
        <slot name="left">
        </slot>
      </SplitterPanel>
      <SplitterResizeHandle :id="`${groupId}-panel-divider`" class="w-1 hover:bg-slate-600"
        v-if="$slots.right"
      />
      <SplitterPanel 
        :id="`${groupId}-panel-splitter-2`" 
        :min-size="20" :defaultSize="80" :order="1" class=""
        v-if="$slots.right"
      >
        <slot name="right">
        </slot>
      </SplitterPanel>
  </SplitterGroup>
</template>
<script>
export default {
  props: ['panels'],
  computed: {
    groupId() {
      const t = this.generateUID()
      return `splitter-group-${t}`
    }
  }
}
</script>