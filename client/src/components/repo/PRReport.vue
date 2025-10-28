
<script setup>
import PRFile from './PRFile.vue';
</script>

<template>
  <div>
    <PRFile v-for="file, ix in files" :key="file.fileFullName + ix"
        :file="file" 
        :option="showOption"
        :columns="columns"
        class="grow bg-base-200 mb-2"
        @new-chat="$emit('new-chat', $event)"
        @chat-column="$emit('chat-column', $event)"
    />
  </div>
</template>
<script>
export default {
  props: ['files', 'showOption', 'columns']
}
</script>