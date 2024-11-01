<script setup>
import CodxJuniorVue from './CodxJunior.vue'
import SplitterVue from '../components/Splitter.vue'
</script>

<template>
  <SplitterVue class="w-full h-full" v-if="$ui.showApp" />
  <CodxJuniorVue class="w-full h-full" v-else />
</template>
<script>
export default {
}
</script>
