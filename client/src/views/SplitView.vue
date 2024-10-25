<script setup>
import NoVNCVue from '../components/NoVNC.vue'
import CoderVue from '../components/apps/Coder.vue'
import CodxJuniorVue from './CodxJunior.vue'
</script>

<template>
  <div class="w-full h-full relative"> 
    <CodxJuniorVue class="right-side h-full" v-if="$ui.isMobile" />
    <div class="w-full h-full flex" v-else>
      <CoderVue class="h-full grow" v-if="$ui.showCoder" />
      <NoVNCVue class="h-full grow p-1" v-if="$ui.showPreview" />
      <div class="right-side shrink-0 w-16" v-if="$ui.isSplitView && $ui.floatingCodxJunior">
        <div class="absolute top-0 right-0 bottom-0 bg-base-300/30 flex justify-end z-50 click"
          :class="$ui.expandCodxJunior && 'w-full'"
          @click.stop="$ui.toggleCodxJunior()">
          <CodxJuniorVue class="h-full bg-base-300"
            @click.stop=""
            :class="$ui.expandCodxJunior ? 'w-2/3' : 'w-16'"
          />
        </div>
      </div>
      <CodxJuniorVue class="h-full" :class="$ui.showApp ? 'w-3/6' : 'w-full'" v-else />
    </div>
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
