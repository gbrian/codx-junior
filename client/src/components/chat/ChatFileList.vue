<script setup>
</script>

<template>
  <div class="my-2 text-xs" v-if="files.length">
    <span><i class="fa-solid fa-paperclip"></i></span>
    <a
      v-for="file in files"
      :key="file"
      :data-tip="file"
      class="group text-nowrap ml-2 hover:underline hover:bg-base-300 cursor-pointer text-accent"
      @click="$ui.openFile(file)"
    >
      <span class="click mr-1" @click.stop="$ui.copyTextToClipboard(file)">
        <i class="fa-solid fa-copy"></i>
      </span>
      <span :title="file">{{ file?.split('/').reverse()[0] || '---error---' }}</span>
      <span class="ml-2 cursor-pointer" @click.stop="$emit('add-as-message', file)">
        <i class="fa-regular fa-comment-dots"></i>
      </span>
      <span class="ml-2 cursor-pointer" @click.stop="$emit('remove', file)">
        <i class="fa-regular fa-circle-xmark"></i>
      </span>
    </a>
  </div>
</template>

<script>
export default {
  props: {
    files: { type: Array, default: () => [] }
  },
  emits: ['remove', 'add-as-message']
}
</script>