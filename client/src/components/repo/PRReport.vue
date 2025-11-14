<script setup>
import PRFile from './PRFile.vue'
</script>

<template>
  <div class="h-full overflow-auto">
    <PRFile v-for="file, ix in files" :key="file.fileFullName + ix"
        :file="file" 
        :option="showOption"
        :columns="columns"
        ref="prFiles"
        class="grow bg-base-200 mb-2"
        @new-chat="$emit('new-chat', $event)"
        @chat-column="$emit('chat-column', $event)"
        @scroll-to="scrollToFile"
    />
  </div>
</template>

<script>
export default {
  props: ['files', 'showOption', 'columns'],
  methods: {
    scrollToFile(fileName) {
      const fileComponent = this.$refs.prFiles.find(file => file.file.fileFullName === fileName)
      if (fileComponent) {
        fileComponent.$el.scrollIntoView({ behavior: 'smooth', block: 'start' })
      }
    }
  },
  expose: ['scrollToFile']
}
</script>