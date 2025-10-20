
<script setup>
import PRFile from './PRFile.vue';
</script>

<template>
  <div>
    <PRFile v-for="file in files" :key="file.fullName"
        :file="file" 
        :option="showOption"
        class="grow bg-base-200 mb-2"
        @new-chat="$emit('new-chat', $event)"
    />
  </div>
</template>
<script>
export default {
  props: ['files', 'showOption']
}
</script>