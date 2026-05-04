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
      <!-- Notebook sync icon: only shown for .ipynb files -->
      <span
        v-if="isNotebook(file)"
        class="ml-2 cursor-pointer text-warning"
        :title="'Sync notebook: ' + file"
        @click.stop="$emit('sync-notebook', file)"
      >
        <i class="fa-solid fa-book-open"></i>
      </span>
      <!-- Export chat to notebook icon: only shown for .ipynb files -->
      <span
        v-if="isNotebook(file)"
        class="ml-2 cursor-pointer text-success"
        :title="'Export chat to notebook: ' + file"
        @click.stop="$emit('export-notebook', file)"
      >
        <i class="fa-solid fa-file-export"></i>
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
  emits: ['remove', 'add-as-message', 'sync-notebook', 'export-notebook'],
  methods: {
    isNotebook(file) {
      return file?.endsWith('.ipynb')
    }
  }
}
</script>