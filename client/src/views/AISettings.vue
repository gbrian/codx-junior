<script setup>
import AIProviders from '@/components/ai_settings/AIProviders.vue'
import AIModels from '@/components/ai_settings/AIModels.vue';
</script>

<template lang="pug">
  .flex.flex-col.gap-2
    .text-2xl Providers
    AIProviders(:settings="settings")
    .text-2xl Models
    AIModels(:settings="settings")
</template>

<script>
export default {
  props: ['settings'],
  data() {
    return {
    }
  },
  methods: {
  }
}
</script>