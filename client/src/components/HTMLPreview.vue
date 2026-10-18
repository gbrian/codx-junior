<script setup>
  import VueDraggableResizable from 'vue-draggable-resizable'
  import 'vue-draggable-resizable/style.css'
</script>

<template>
  <div class="h-full flex flex-col">
    <div class="flex gap-2 p-2 border-b border-base-100 flex-wrap items-center">
      <div class="flex gap-2 items-center">
        <span class="text-xs font-medium opacity-60">Screen:</span>
        <select 
          v-model="selectedSize" 
          class="select select-xs select-bordered max-w-xs"
          title="Select screen size"
        >
          <option value="device">Device (auto)</option>
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
        class="border border-base-100 bg-white overflow-auto transition-all duration-200"
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
    class="fixed inset-0 bg-base-100 bg-opacity-50 flex items-center justify-center p-4 z-50"
  >
    <vue-draggable-resizable
      v-model:w="popupWidth"
      v-model:h="popupHeight"
      :parent="true"
      :draggable="!isMobile"
      :resizable="!isMobile"
      class-name-active="active"
      class-name-dragging="dragging"
    >
      <div 
        class="bg-white rounded-lg shadow-2xl flex flex-col w-full h-full"
      >
        <!-- Popup Header -->
        <div class="flex gap-2 p-3 border-b border-base-100 bg-base-100 items-center rounded-t-lg flex-wrap">
          <span class="text-sm font-semibold">HTML Preview</span>
          
          <div v-if="!isMobile" class="flex gap-2 items-center flex-wrap">
            <select 
              v-model="popupSelectedSize" 
              class="select select-xs select-bordered"
              title="Select screen size"
            >
              <option value="device">Device (auto)</option>
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

// Presets resolved dynamically from the device viewport + orientation
const deviceSizes = {
  phonePortrait: { width: 375, height: 667 },
  phoneLandscape: { width: 667, height: 375 },
  tabletPortrait: { width: 768, height: 1024 },
  tabletLandscape: { width: 1024, height: 768 },
  desktopPortrait: { width: 1024, height: 768 },
  desktopLandscape: { width: 1440, height: 900 }
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
      popupSelectedSize: 'custom',
      viewportWidth: 1024,
      viewportHeight: 768,
      isMobile: false
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
    this.updateViewport()

    window.addEventListener('resize', this.handleViewportChange)
    window.addEventListener('orientationchange', this.handleViewportChange)

    // On mobile devices open with a device-sized frame instead of a desktop preset
    if (this.isMobile) {
      this.selectedSize = 'device'
      this.popupSelectedSize = 'device'
    }

    this.applySize(this.selectedSize)
    this.$nextTick(() => {
      this.renderHTML(this.html)
    })
  },
  beforeUnmount() {
    window.removeEventListener('resize', this.handleViewportChange)
    window.removeEventListener('orientationchange', this.handleViewportChange)
  },
  methods: {
    buildDocument(htmlContent) {
      return `<!DOCTYPE html>
          <html>
          <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
              html {
                -webkit-text-size-adjust: 100%;
              }
              body {
                margin: 0;
                padding: 1rem;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
                background-color: #111111;
                color: #e5e7eb;
                overflow-wrap: break-word;
              }
              img, video, iframe, table {
                max-width: 100%;
              }
            </style>
          </head>
          <body>
            ${htmlContent}
          </body>
          </html>`
    },

    writeFrame(refName, htmlContent, label) {
      const iframe = this.$refs[refName]
      if (!iframe) return

      try {
        const doc = iframe.contentDocument || iframe.contentWindow.document
        doc.open()
        doc.write(this.buildDocument(htmlContent))
        doc.close()
      } catch (error) {
        console.error(`Error rendering ${label}:`, error)
      }
    },

    renderHTML(htmlContent) {
      this.writeFrame('previewFrame', htmlContent, 'HTML preview')
    },

    renderPopupHTML(htmlContent) {
      this.writeFrame('popupFrame', htmlContent, 'popup preview')
    },

    updateViewport() {
      this.viewportWidth = window.innerWidth || 1024
      this.viewportHeight = window.innerHeight || 768
      this.isMobile = this.viewportWidth < 768
    },

    getDeviceSize() {
      const isPortrait = this.viewportHeight >= this.viewportWidth

      if (this.viewportWidth < 768) {
        return isPortrait ? deviceSizes.phonePortrait : deviceSizes.phoneLandscape
      }
      if (this.viewportWidth < 1024) {
        return isPortrait ? deviceSizes.tabletPortrait : deviceSizes.tabletLandscape
      }
      return isPortrait ? deviceSizes.desktopPortrait : deviceSizes.desktopLandscape
    },

    getAvailableSpace() {
      // p-4 on the scroll container: 16px on each side
      const container = this.$refs.previewContainer
      const width = container && container.clientWidth
        ? container.clientWidth - 32
        : this.viewportWidth - 32
      const height = container && container.clientHeight
        ? container.clientHeight - 32
        : this.viewportHeight - 160

      return {
        width: Math.max(240, width),
        height: Math.max(240, height)
      }
    },

    applySize(sizeKey) {
      if (sizeKey === 'device') {
        const size = this.getDeviceSize()
        const available = this.getAvailableSpace()
        this.displayWidth = Math.min(size.width, available.width)
        this.displayHeight = Math.min(size.height, available.height)
        return
      }

      const size = screenSizes[sizeKey]
      if (size) {
        this.displayWidth = size.width
        this.displayHeight = size.height
      }
    },

    applyPopupSize(sizeKey) {
      if (sizeKey === 'device') {
        const size = this.getDeviceSize()
        const margin = this.isMobile ? 0 : 32
        this.popupWidth = Math.max(280, Math.min(size.width, this.viewportWidth - margin))
        this.popupHeight = Math.max(280, Math.min(size.height, this.viewportHeight - margin))
        return
      }

      const size = screenSizes[sizeKey]
      if (size) {
        this.popupWidth = size.width
        this.popupHeight = size.height
      }
    },

    handleViewportChange() {
      this.updateViewport()

      if (this.selectedSize === 'device') {
        this.applySize('device')
      }

      if (!this.isPopupOpen) {
        return
      }

      if (this.popupSelectedSize === 'device') {
        this.applyPopupSize('device')
      } else if (this.popupSelectedSize === 'custom') {
        // Keep a custom popup inside the (possibly rotated) viewport
        this.popupWidth = Math.min(this.popupWidth, this.viewportWidth)
        this.popupHeight = Math.min(this.popupHeight, this.viewportHeight)
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
      this.updateViewport()
      this.isPopupOpen = true

      if (this.isMobile) {
        // Mobile: open at device size / current orientation, no draggable frame
        this.popupSelectedSize = 'device'
        this.applyPopupSize('device')
      }

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