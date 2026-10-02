<script setup>

import { Editor } from '@snowdreamtech/vue-tui-editor';
</script>
<template>
  <Editor
    :initialValue="modelValue"
    initialEditType="wysiwyg"
    @update:modelValue="onUpdate"
  />
</template>
<script>
export default {
  props: {
    modelValue: {
      type: String,
      default: ''
    }
  },
  emits: ['update:modelValue'],
  methods: {
    onUpdate(value) {
      this.$emit('update:modelValue', value)
    }
  }
}
</script>
<style>
@import '/tui-editor-style.css';

</style>