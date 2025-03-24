<script setup>
</script>

<template>
  <select class="select select-bordered" v-model="value">
    <option value="">-- default --</option>
    <option v-for="model in models" :key="model.name" :value="model.name">
      {{ model.name }}
    </option>
  </select>
</template>

<script>
export default {
  props: ['modelValue'],
  emits: ['update:modelValue'],
  computed: {
    value: {
      get() {
        return this.modelValue
      },
      set(value) {
        this.$emit('update:modelValue', value)
      }
    },
    models() {
      return this.$storex.api.globalSettings.ai_models
    }
  }
}
</script>