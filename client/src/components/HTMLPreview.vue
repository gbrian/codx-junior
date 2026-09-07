<script setup>
  import VueDraggableResizable from 'vue-draggable-resizable'
  import 'vue-draggable-resizable/style.css'
</script>

<template>
  <div class="h-full flex flex-col">
    <div class="flex gap-2 p-2 border-b border-slate-500 flex-wrap items-center">
      <div class="flex gap-2 items-center">
        <span class="text-xs font-medium opacity-60">Screen:</span>
        <select 
          v-model="selectedSize" 
          class="select select-xs select-bordered max-w-xs"
          title="Select screen size"
        >
          <option value="custom">Custom</option>
          <option value="mobile-sm">Mobile (375px)</option>
          <option value="mobile-md">Mobile (425px)</option>
          <option value="tablet">Tablet (768px)</option>
          <option value="laptop">Laptop (1024px)</option>
          <option value="desktop">Desktop (1440px)</option>
        </select>
      </div>

      <div v-if="selectedSize === 'custom'" class="flex gap-1 items-center">
        <input 
          v-model.number="customWidth" 
          type="number" 
          min="200" 
          max="2560"
          placeholder="Width"
          class="input input-xs input-bordered max-w-[80px]"
          title="Width in pixels"
        />
        <span class="text-xs opacity-60">×</span>
        <input 
          v-model.number="customHeight" 
          type="number" 
          min="200" 
          max="2560"
          placeholder="Height"
          class="input input-xs input-bordered max-w-[80px]"
          title="Height in pixels"
        />
        <span class="text-xs opacity-60">px</span>
      </div>

      <div class="flex gap-2 ml-auto">
        <button 
          class="btn btn-xs btn-outline"
          @click="refreshPreview"
          title="Refresh preview"
        >
          <i class="fa-solid fa-arrows-rotate"></i>
          <span class="hidden sm:inline">Refresh</span>
        </button>
        <button 
          class="btn btn-xs btn-outline"
          @click="openPopup"
          title="Open in popup"
        >
          <i class="fa-solid fa-window-restore"></i>
          <span class="hidden sm:inline">Popup</span>
        </button>
      </div>
    </div>
    
    <div class="flex-1 overflow-auto flex items-center justify-center p-4 bg-base-200" ref="previewContainer">
      <div 
        class="border border-slate-400 bg-white overflow-auto transition-all duration-200"
        :style="{ width: displayWidth + 'px', height: displayHeight + 'px' }"
      >
        <iframe
          ref="previewFrame"
          class="w-full h-full border-0"
          :key="refreshCounter"
          sandbox="allow-scripts allow-same-origin allow-forms"
          title="HTML Preview"
        ></iframe>
      </div>
    </div>
  </div>

  <!-- Popup Modal -->
  <div 
    v-if="isPopupOpen"
    class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50"
  >
    <vue-draggable-resizable
      v-model:w="popupWidth"
      v-model:h="popupHeight"
      :parent="true"
      :resizable="true"
      class-name-active="active"
      class-name-dragging="dragging"
    >
      <div 
        class="bg-white rounded-lg shadow-2xl flex flex-col w-full h-full"
      >
        <!-- Popup Header -->
        <div class="flex gap-2 p-3 border-b border-slate-300 bg-base-100 items-center rounded-t-lg flex-wrap">
          <span class="text-sm font-semibold">HTML Preview</span>
          
          <div class="flex gap-2 items-center flex-wrap">
            <select 
              v-model="popupSelectedSize" 
              class="select select-xs select-bordered"
              title="Select screen size"
            >
              <option value="custom">Custom</option>
              <option value="mobile-sm">Mobile (375px)</option>
              <option value="mobile-md">Mobile (425px)</option>
              <option value="tablet">Tablet (768px)</option>
              <option value="laptop">Laptop (1024px)</option>
              <option value="desktop">Desktop (1440px)</option>
            </select>

            <div v-if="popupSelectedSize === 'custom'" class="flex gap-1 items-center">
              <input 
                v-model.number="popupWidth" 
                type="number" 
                min="300"
                placeholder="Width"
                class="input input-xs input-bordered max-w-[60px]"
                title="Popup width in pixels"
              />
              <span class="text-xs opacity-60">×</span>
              <input 
                v-model.number="popupHeight" 
                type="number" 
                min="300"
                placeholder="Height"
                class="input input-xs input-bordered max-w-[60px]"
                title="Popup height in pixels"
              />
              <span class="text-xs opacity-60">px</span>
            </div>
          </div>

          <div class="flex gap-1 ml-auto">
            <button 
              class="btn btn-xs btn-ghost"
              @click="refreshPopupPreview"
              title="Refresh preview"
            >
              <i class="fa-solid fa-arrows-rotate"></i>
            </button>

            <button 
              class="btn btn-xs btn-ghost"
              @click="closePopup"
              title="Close popup"
            >
              <i class="fa-solid fa-xmark"></i>
            </button>
          </div>
        </div>

        <!-- Popup Content -->
        <div class="flex-1 overflow-auto bg-base-200">
          <iframe
            ref="popupFrame"
            class="w-full h-full border-0"
            :key="popupRefreshCounter"
            sandbox="allow-scripts allow-same-origin allow-forms"
            title="HTML Preview Popup"
          ></iframe>
        </div>
      </div>
    </vue-draggable-resizable>
  </div>
</template>

<script>
const screenSizes = {
  'mobile-sm': { width: 375, height: 667 },
  'mobile-md': { width: 425, height: 812 },
  'tablet': { width: 768, height: 1024 },
  'laptop': { width: 1024, height: 768 },
  'desktop': { width: 1440, height: 900 }
}

export default {
  props: ['html'],
  data() {
    return {
      refreshCounter: 0,
      popupRefreshCounter: 0,
      selectedSize: 'laptop',
      customWidth: 1024,
      customHeight: 768,
      displayWidth: 1024,
      displayHeight: 768,
      isPopupOpen: false,
      popupWidth: 1200,
      popupHeight: 800,
      popupSelectedSize: 'custom'
    }
  },
  watch: {
    html(newHtml) {
      this.$nextTick(() => {
        this.renderHTML(newHtml)
        if (this.isPopupOpen) {
          this.renderPopupHTML(newHtml)
        }
      })
    },
    selectedSize(newSize) {
      this.applySize(newSize)
    },
    customWidth(newVal) {
      if (this.selectedSize === 'custom') {
        this.displayWidth = newVal
      }
    },
    customHeight(newVal) {
      if (this.selectedSize === 'custom') {
        this.displayHeight = newVal
      }
    },
    popupSelectedSize(newSize) {
      this.applyPopupSize(newSize)
    }
  },
  mounted() {
    this.applySize(this.selectedSize)
    this.renderHTML(this.html)
  },
  methods: {
    renderHTML(htmlContent) {
      const iframe = this.$refs.previewFrame
      if (!iframe) return
      
      try {
        const doc = iframe.contentDocument || iframe.contentWindow.document
        doc.open()
        doc.write(`
          <!DOCTYPE html>
          <html>
          <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
              body {
                margin: 0
                padding: 1rem
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif
                background-color: #0f172a
                color: #e2e8f0
              }
            </style>
          </head>
          <body>
            ${htmlContent}
          </body>
          </html>
        `)
        doc.close()
      } catch (error) {
        console.error('Error rendering HTML preview:', error)
      }
    },

    renderPopupHTML(htmlContent) {
      const iframe = this.$refs.popupFrame
      if (!iframe) return
      
      try {
        const doc = iframe.contentDocument || iframe.contentWindow.document
        doc.open()
        doc.write(`
          <!DOCTYPE html>
          <html>
          <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
              body {
                margin: 0
                padding: 1rem
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif
                background-color: #0f172a
                color: #e2e8f0
              }
            </style>
          </head>
          <body>
            ${htmlContent}
          </body>
          </html>
        `)
        doc.close()
      } catch (error) {
        console.error('Error rendering popup preview:', error)
      }
    },

    applySize(sizeKey) {
      const size = screenSizes[sizeKey]
      if (size) {
        this.displayWidth = size.width
        this.displayHeight = size.height
      }
    },

    applyPopupSize(sizeKey) {
      const size = screenSizes[sizeKey]
      if (size) {
        this.popupWidth = size.width
        this.popupHeight = size.height
      }
    },

    refreshPreview() {
      this.refreshCounter++
      this.$nextTick(() => {
        this.renderHTML(this.html)
      })
    },

    refreshPopupPreview() {
      this.popupRefreshCounter++
      this.$nextTick(() => {
        this.renderPopupHTML(this.html)
      })
    },

    openPopup() {
      this.isPopupOpen = true
      this.popupSelectedSize = 'custom'
      this.$nextTick(() => {
        this.renderPopupHTML(this.html)
      })
    },

    closePopup() {
      this.isPopupOpen = false
    }
  }
}
</script>