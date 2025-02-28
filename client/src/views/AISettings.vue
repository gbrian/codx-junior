<script setup>
import AIProviders from '@/components/ai_settings/AIProviders.vue'
import AIModels from '@/components/ai_settings/AIModels.vue';
</script>

<template lang="pug">
  .flex.flex-col.gap-2
    .text-2xl Providers
    AIProviders
    .text-2xl Models
    AIModels
</template>

<script>
export default {
  data() {
    return {
    }
  },
  methods: {
  }
}
</script>