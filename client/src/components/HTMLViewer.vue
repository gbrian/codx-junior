<script setup>
import Code from './Code.vue'
</script>
<template>
  <div class="html-viewer-container h-[600px]">
    <div class="flex gap-1 bg-base-100 px-2 py-1 rounded-md">
      <div class="btn btn-sm" @click="zoomOut">
        <i class="fa-solid fa-magnifying-glass-minus"></i>
      </div>
      <div class="btn btn-sm" @click="zoomIn">
        <i class="fa-solid fa-magnifying-glass-plus"></i> <!-- Font Awesome Icon for zoom in -->
      </div>
      <div class="btn btn-sm" :class="showCode && 'btn-warning'" @click="toggleCode">
        <i class="fa-solid fa-code"></i> <!-- Font Awesome Icon for zoom in -->
      </div>
    </div>
    <Code :text="htmlContent" text-language="html" v-if="showCode" />
    <iframe
      :srcdoc="htmlContent"
      sandbox="allow-popups allow-forms"
      frameborder="0"
      class="w-full h-full"
      :style="{ zoom: zoom }"
      v-else
    ></iframe>
  </div>
</template>

<script>
export default {
  props: {
    htmlContent: {
      type: String,
      required: true,
      default: '<html><body><p>No content provided</p></body></html>'
    }
  },
  data() {
    return {
      zoom: 1,
      showCode: false
    }
  },
  methods: {
    toggleCode() {
      this.showCode = !this.showCode
    },
    zoomOut() {
      // Ensure zoom level doesn't go below 0.2
      if (this.zoom > 0.2) {
        this.zoom -= 0.1
      }
    },
    zoomIn() {
      // Ensure zoom level doesn't exceed 1.5
      if (this.zoom < 1.5) {
        this.zoom += 0.1
      }
    }
  }
}
</script>