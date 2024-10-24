<script setup>
import NoVNCVue from '../components/NoVNC.vue'
import CoderVue from '../components/apps/Coder.vue'
import CodxJuniorVue from './CodxJunior.vue'
</script>

<template>
  <div class="w-full h-full relative flex">
    <CoderVue class="h-full grow" v-if="$ui.showCoder" />
    <NoVNCVue class="h-full grow" v-if="$ui.showPreview" />
    <div class="h-full w-1 hover:w-fit group cursor-ew-resize bg-slate-600 flex flex-col justify-center"
      v-if="leftPanel && !$ui.floatingCodxJunior">
      <span class="click hidden group-hover:block" @click="$ui.incrementCodxJuniorWidth()"><i class="fa-solid fa-angle-left"></i></span>
      <span class="click hidden group-hover:block" @click="$ui.decrementCodxJuniorWidth()"><i class="fa-solid fa-angle-right"></i></span>
    </div>
    <div class="right-side shrink-0 w-16" v-if="leftPanel && $ui.floatingCodxJunior">
      <div class="absolute top-0 right-0 bottom-0 bg-base-300/30 flex justify-end z-50 click"
        :class="$ui.expandCodxJunior && 'w-full'"
        @click.stop="$ui.toggleCodxJunior()">
        <CodxJuniorVue class="h-full bg-base-300"
          @click.stop=""
          :class="$ui.expandCodxJunior ? 'w-2/3' : 'w-16'"
        />
      </div>
    </div>
    <CodxJuniorVue class="right-side h-full" :class="leftPanel ? $ui.codxJuniorWidth : 'w-full'" v-else />
  </div>
</template>
<script>
export default {
  computed: {
    leftPanel () {
      return !!this.$ui.showApp
    },
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
