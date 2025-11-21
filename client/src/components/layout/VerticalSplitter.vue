<script setup>
import { SplitterGroup, SplitterPanel, SplitterResizeHandle } from 'radix-vue'
</script>

<template>
  <SplitterGroup class="h-full" :id="groupId" direction="horizontal">
    <SplitterPanel
      :id="`${groupId}-panel-splitter-1`"
      :min-size="panels?.left?.minSize || 10"
      :collapsible="panels?.left?.collapsible || true"
      :defaultSize="panels?.left?.defaultSize || 20"
      :order="1"
      v-if="$slots.left"
    >
      <slot name="left"></slot>
    </SplitterPanel>
    <SplitterResizeHandle
      :id="`${groupId}-panel-divider`"
      class="w-1 hover:bg-slate-600"
      v-if="$slots.right"
    />
    <SplitterPanel
      :id="`${groupId}-panel-splitter-2`"
      :min-size="panels?.right?.minSize || 10"
      :collapsible="panels?.right?.collapsible || true"
      :defaultSize="panels?.right?.defaultSize || 20"
      :order="2"
      v-if="$slots.right"
    >
      <slot name="right"></slot>
    </SplitterPanel>
  </SplitterGroup>
</template>

<script>
export default {
  props: ['panels'],
  computed: {
    groupId() {
      // Generates a unique ID for the splitter group
      const t = this.generateUID()
      return `splitter-group-${t}`
    }
  }
}
</script>