<script setup>
import VueMermaidString from 'vue-mermaid-string'
import mermaid from 'mermaid'
import { ref } from 'vue'
</script>

<template>
  <div class="w-full h-full flex gap-2 bg-base-300 p-2 rounded-lg relative">
    <pre v-if="error">{{ error }}</pre>
    <div class="w-full h-full flex gap-2 overflow-auto relative" 
      v-else
      ref="diagramContainer">
      <vue-mermaid-string 
        class="w-full h-full flex gap-2" 
        :value="diagram" 
        :options="{ theme: 'dark' }"
      />
    </div>

    <!-- Zoom Controls -->
    <div class="absolute bottom-4 right-4 flex gap-2 bg-base-200 rounded-lg p-2 shadow-lg">
      <button 
        @click.stop="zoomOut" 
        :disabled="zoomLevel <= minZoom"
        class="btn btn-sm btn-ghost"
        title="Zoom Out"
      >
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM13 10H7" />
        </svg>
      </button>

      <button 
        @click.stop="resetZoom" 
        class="btn btn-sm btn-ghost"
        title="Reset Zoom"
      >
        <span class="text-xs">{{ zoomLevel }}%</span>
      </button>

      <button 
        @click.stop="zoomIn" 
        :disabled="zoomLevel >= maxZoom"
        class="btn btn-sm btn-ghost"
        title="Zoom In"
      >
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM10 7v6m3-3H7" />
        </svg>
      </button>
    </div>
  </div>
</template>

<script>
export default {
  props: ['diagram'],
  data() {
    return {
      error: '',
      zoomLevel: 100,
      minZoom: 50,
      maxZoom: 200,
      zoomStep: 10
    }
  },
  created() {
    this.validateDiagram()  
  },
  watch: {
    diagram() {
      this.validateDiagram()
    }
  },
  methods: {
    async validateDiagram() {
      try {
        await mermaid.parse(this.diagram)
        this.error = null
        // Apply zoom after diagram renders
        this.$nextTick(() => {
          this.applyZoomToSvg()
        })
      } catch (ex) {
        this.error = ex
      }
    },
    getSvgElement() {
      // Query SVG inside the diagram container
      const container = this.$refs.diagramContainer
      return container ? container.querySelector('svg') : null
    },
    applyZoomToSvg() {
      const svg = this.getSvgElement()
      if (svg) {
        const scale = this.zoomLevel / 100
        svg.style.transform = `scale(${scale})`
        svg.style.transformOrigin = 'top left'
      }
    },
    zoomIn() {
      if (this.zoomLevel < this.maxZoom) {
        this.zoomLevel += this.zoomStep
        this.applyZoomToSvg()
      }
    },
    zoomOut() {
      if (this.zoomLevel > this.minZoom) {
        this.zoomLevel -= this.zoomStep
        this.applyZoomToSvg()
      }
    },
    resetZoom() {
      this.zoomLevel = 100
      this.applyZoomToSvg()
    }
  }
}
</script>