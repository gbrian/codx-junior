<script setup>
import VueSplitter from '@rmp135/vue-splitter'
import NoVNCVue from '../components/NoVNC.vue'
import CoderVue from '../components/apps/Coder.vue'
import EmbeddedCodxJuniorVue from '@/components/EmbeddedCodxJunior.vue'
</script>

<template>
  <div class="flex w-full h-full relative">
    <div class="grow" v-if="leftPanel">
      <CoderVue class="h-full grow" v-if="$ui.showCoder" />
      <NoVNCVue class="h-full grow" v-if="$ui.showPreview" />
    </div>
    <div class="shrink-0" :class="leftPanel ? 'w-14' : 'w-full'">
      <div class="left-0 right-0 top-0 bottom-0 group bg-base-300/40 flex justify-end click"
        :class="expandCodxJunior && 'w-full absolute'"
        @click="expandCodxJunior = false"
      >
        <EmbeddedCodxJuniorVue :class="expandCodxJunior ? 'w-2/3' : 'w-full'"
          @click="openCodxJunior"  />
      </div>
    </div>
  </div>
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
      splitterPercent: 0,
      e$storex: null,
      expandCodxJunior: false
    }
  },
  created () {
  },
  computed: {
    leftPanel () {
      return this.$ui.showCoder || this.$ui.showPreview
    },
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
    leftPanel () {
      this.expandCodxJunior = false
    },
  },
  methods: {
    onCodxJuniorLoad ({ target }) {
      if (this.e$storex) {
        return
      }
      this.e$storex = target.contentWindow.$storex
      this.e$storex.setParent(this.$storex)
    },
    openCodxJunior () {
      if (this.leftPanel) {
        setTimeout(() => this.expandCodxJunior = true, 300)
      }
    }
  }
}
</script>
