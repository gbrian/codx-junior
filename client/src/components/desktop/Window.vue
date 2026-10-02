<script setup>
// import { IDockviewPanelProps } from 'dockview-vue'
</script>
<template>
  <div class="w-full h-full flex flex-col overflow-hidden">
    <div class="flex-1 overflow-auto">
      <slot />
    </div>
  </div>
</template>
<script>
export default {
  name: 'Window',
  props: {
    params: {
      type: Object,
      required: true
    }
  },
  computed: {
    title() {
      return this.params?.api?.title || ''
    },
    panelApi() {
      return this.params?.api
    }
  }
}
</script>