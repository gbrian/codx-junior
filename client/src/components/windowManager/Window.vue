<script setup>
import  vueWindowManager from 'vue-window-manager';
import "vue-window-manager/windows10.css"
</script>
<template>
  <vueWindowManager
        :isActive=true
        :top="0"
        :left="0"
        :width="500"
        :height="500"
        :minWidth="10"
        :minHeight="10"
        :isResizing="['r', 'rb', 'b', 'lb', 'l', 'lt', 't', 'rt']"
        :isButtonMaximized="true"
        :isButtonMinimized="true"
        :isMaximized="false"
        :windowId="wId"
        :title="windowTitle"
        :titleIcon="icon"
        @clickWindow="$emit('activate', wId)"
        @clickDestroy="$emit('close', wId)"
        @clickMin="$emit('min', wId)"
        class="absolute"
        style="position: absolute;"
        >
        <div class="w-full h-full overflow-auto p-1" :title="wId">
          <slot></slot>
        </div>
  </vueWindowManager>
</template>>
<script>
export default {
  props: ['window-id', 'window-title', 'icon'],
  data() {
    return {
      wId: this.windowId || Math.random().toString()
    }
  },
  mounted() {
    this.$emit('acrtive', this.wId)
  }
}
</script>