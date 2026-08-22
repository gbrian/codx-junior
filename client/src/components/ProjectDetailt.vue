<script setup>
import ProjectSelector from './ProjectSelector.vue'
</script>

<template>
  <ProjectSelector
    :model-value="project"
    :iconify="iconify"
    :options="options"
    :disabled="disabled"
    :icon-size="iconSize"
    @select="onProjectSelected"
    @update:model-value="onProjectSelected"
  />
</template>

<script>
export default {
  props: {
    iconify: Boolean,
    options: Object,
    disabled: Boolean,
    iconSize: {
      type: Number,
      default: () => 6
    },
    modelValue: {
      type: Object,
      default: () => null
    }
  },
  emits: ['update:modelValue', 'select'],
  computed: {
    project() {
      return this.modelValue || this.$project
    }
  },
  methods: {
    onProjectSelected(project) {
      this.$emit('update:modelValue', project)
      this.$emit('select', project)
    }
  }
}
</script>