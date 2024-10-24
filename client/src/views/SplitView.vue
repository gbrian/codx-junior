<script setup>
import NoVNCVue from '../components/NoVNC.vue'
import CoderVue from '../components/apps/Coder.vue'
import CodxJuniorVue from './CodxJunior.vue'
</script>

<template>
  <div class="w-full h-full relative flex">
    <CoderVue class="h-full grow" v-if="$ui.showCoder" />
    <NoVNCVue class="h-full grow" v-if="$ui.showPreview" />
    <div class="splitter h-full w-3" v-if="leftPanel && !$ui.floatingCodxJunior"
    >
    @codx-processing: Add dragging loggic to "splitter" to modify right-side when not floating using w-1/6, w-2/6,... and read and store it in $ui.setRightPanelWidth and $ui.rightPanelWidth
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
    <CodxJuniorVue class="right-side h-full" :class="leftPanel ? 'w-1/3' : 'w-full'" v-else />
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
