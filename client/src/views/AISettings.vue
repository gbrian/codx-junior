<script setup>
import AIProvidersAndModels from '@/components/ai_settings/AIProvidersAndModels.vue'
</script>

<template lang="pug">
    AIProvidersAndModels(:settings="settings")
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