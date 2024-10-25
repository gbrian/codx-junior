<script setup>
import NoVNCVue from '../components/NoVNC.vue'
import CoderVue from '../components/apps/Coder.vue'
import CodxJuniorVue from './CodxJunior.vue'
import SplitterVue from '../components/Splitter.vue'
</script>

<template>
  <div class="w-full h-full relative"> 
    <CodxJuniorVue class="right-side h-full" v-if="$ui.isMobile" />
    <SplitterVue class="w-full h-full" v-if="$ui.isSplitView">
      <template #left>
        <CoderVue class="h-full grow" v-if="$ui.showCoder" />
        <NoVNCVue class="h-full grow p-1" v-if="$ui.showPreview" />
      </template>
      <template #right>
        <CodxJuniorVue class="w-full h-full" />
      </template>
    </SplitterVue>
    <CodxJuniorVue class="w-full h-full" v-else />
  </div>
</template>
<script>
export default {
  computed: {
  },
  watch: {
  },
  methods: {
    openCodxJunior () {
      if (this.leftPanel) {
        setTimeout(() => this.$ui.toggleCodxJunior(), 300)
      }
    }
  }
}
</script>
