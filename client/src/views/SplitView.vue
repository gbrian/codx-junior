<script setup>
import VueSplitter from '@rmp135/vue-splitter'
</script>

<template>
    <vue-splitter
        @mousedown="splitterDragging = true"
        @mouseup="onEndSplitting"
        :initial-percent="splitterPercent"
        v-model:percent="splitterPercent"
    >
        <template #left-pane>
        <div :class="['h-full relative grow']">
            <iframe ref="iframe" :src="coderUrl" :class="[
                'h-full w-full border-0 bg-base-300'
            ]"
            @load="onCoderLoaded"
            title="coder"
            allow="camera *;microphone *;clipboard-read; clipboard-write;"
            :key="iframeKey"
            v-if="$storex.ui.showCoder"
            >
            </iframe>
            <div class="absolute top-0 left-0 right-0 bottom-0 bg-base-300 flex flex-col items-center justify-center z-50" v-if="$storex.ui.showCoder && !iframeLoaded">
            <div class="flex items-end gap-2">
                LOADING CODER <span class="loading loading-dots loading-sm"></span>
            </div>
            </div>
            <div class="h-full relative grow flex flex-col p-1" v-if="$storex.ui.showPreview">
            <label class="grow input input-sm input-bordered flex items-center gap-2">
                <input type="text" class="grow" :value="preViewUrl" placeholder="Enter url..." @keydown.enter="preViewUrl = $event.target.value" />
                <i class="fa-solid fa-magnifier"></i>
            </label>  
            <iframe ref="iframe" :src="preViewUrl" class="h-full w-full border-0 bg-base-300"
                title="preview"
                allow="camera *;microphone *;clipboard-read; clipboard-write;"
                :key="iframeKey"
                >
            </iframe>
            </div>
            <div class="absolute top-0 left-0 right-0 bottom-0 flex flex-col items-center justify-center z-50" v-if="splitterDragging">
            <div class="flex items-end gap-2">
            </div>
            </div>
        </div>
        </template>
        <template #right-pane>
        <div class="w-full h-full relative">
          <iframe :src="codxJuniorUrl" class="h-full w-full border-0 bg-base-300"
                title="codx-junior"
                allow="camera *;microphone *;clipboard-read; clipboard-write;"
                key="codx-junior"
                @load="onCodxJuniorLoad"
                >
            </iframe>
            <div class="absolute top-0 left-0 right-0 bottom-0 flex flex-col items-center justify-center z-50" v-if="splitterDragging">
            </div>
        </div>
        </template>
    </vue-splitter>
</template>
<script>
const MAX_CODER_PANEL_SIZE = 75
const MIN_CODER_PANEL_SIZE = 25
export default {
  data () {
    return {
      url: "/coder",
      preViewUrl: "_blank_",
      iframeLoaded: false,
      codxJuniorPanelWidth: 2,
      maxcodxJuniorPanelWidth: 6,
      iframeKey: 0,
      splitterDragging: false,
      splitterPercent: 75,
      e$storex: null
    }
  },
  created () {
    this.splitterPercent =
      parseFloat(localStorage.getItem("SPLITTER_PERCENT") || this.splitterPercent)
  },
  computed: {
    splitView () {
      return this.$storex.ui.splitView
    },
    coderUrl () {
      return `${window.location.origin}${this.url}`
    },
    codxJuniorUrl () {
      return "/"
    }
  },
  watch: {
    splitView (newVal) {
      if (newVal) {
        this.iframeLoaded = false
      }
    },
    splitterPercent () {
      if (this.splitterPercent > MAX_CODER_PANEL_SIZE) {
        this.splitterPercent = MAX_CODER_PANEL_SIZE
      }
      if (this.splitterPercent < MIN_CODER_PANEL_SIZE) {
        this.splitterPercent = MIN_CODER_PANEL_SIZE
      }
    }
  },
  methods: {
    onCoderLoaded () {
      const { pathname, search } = this.$refs.iframe.contentWindow.location
      if (pathname.indexOf("/coder") === -1) {
        this.url = `/coder${pathname.slice(1)}${search}`
        this.$refs.iframe.attributes.src.value = this.url
        this.iframeLoaded = false
      } else { 
        setTimeout(() => this.checkCoderLoader(), 1000)
      }
      console.log("IFRAME URL", this.url)
    },
    onEndSplitting () {
      this.splitterDragging = false
      localStorage.setItem("SPLITTER_PERCENT", this.splitterPercent.toString())
    },
    checkCoderLoader () {
      let checkCount = 30 
      let interval = setInterval(() => {
        const { contentWindow } = this.$refs.iframe
        if (!checkCount) {
          this.iframeKey = this.iframeKey + 1
        } else {
          const div = contentWindow.document.querySelector("body div")
          if (div) {
            this.iframeLoaded = true
            contentWindow.addEventListener('beforeunload', () => this.iframeLoaded = false)
          }
        }
        if (this.iframeLoaded || !checkCount) {
          clearInterval(interval)
        }
        checkCount--
      }, 1000)
    },
    onCodxJuniorLoad ({ target }) {
      if (this.e$storex) {
        return
      }
      this.e$storex = target.contentWindow.$storex
      this.e$storex.setParent(this.$storex)
    }
  }
}
</script>
<style>
  .vue-splitter.vertical>.splitter {
    width: 2px;
    background-color: #4c4c4c;
  }
  .vue-splitter.vertical>.splitter:hover {
    width: 3px;
  }
</style>