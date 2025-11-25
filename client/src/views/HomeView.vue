<script setup>
import MenuBar from '@/components/mobile/MenuBar.vue';
</script>
<template>
  <div class="px-4 py-1">
    <MenuBar />
  </div>
</template>
<script>
export default {
  methods: {
    scrollToTop() {
      this.$refs.content.scrollTo({ top: 0, behavior: 'smooth' });
    }
  }
}
</script>