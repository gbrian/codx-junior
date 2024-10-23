<script setup>
import NoVNCVue from '../components/NoVNC.vue'
import CoderVue from '../components/apps/Coder.vue'
import CodxJuniorVue from './CodxJunior.vue'
</script>

<template>
  <div class="w-full h-full relative flex">
    <CoderVue class="h-full grow" v-if="$ui.showCoder" />
    <NoVNCVue class="h-full grow" v-if="$ui.showPreview" />
    <div class="shrink-0" :class="leftPanel ? 'w-14' : 'grow'">
      <div class="absolute top-0 right-0 bottom-0 bg-base-300/30 flex justify-end z-50 click"
        :class="leftPanel ? $ui.expandCodxJunior && 'w-full' : 'w-full'"
        @click.stop="$ui.toggleCodxJunior()">
        <CodxJuniorVue class="h-full bg-base-300"
          @click.stop=""
          :class="$ui.expandCodxJunior ? leftPanel ? 'w-2/3' : 'w-full' : 'w-14'"
        />
      </div>
    </div>
  </div>
</template>
<script>
export default {
  computed: {
    leftPanel () {
      return this.$ui.showCoder || this.$ui.showPreview
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
