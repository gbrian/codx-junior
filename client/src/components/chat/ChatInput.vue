<script setup>
</script>
<template>
  <div class="flex flex-col gap-1 grow">
    <div class="badge text-info my-2 animate-pulse" v-if="waiting">typing ...</div>
    <div :class="['flex bg-base-300 border rounded-md shadow', multiline ? 'flex-col' : '']"
         @dragover.prevent="onDraggingOverInput = true"
         @dragleave.prevent="onDraggingOverInput = false"
         @drop.prevent="onDrop">
      <div :class="['max-h-40 w-full px-2 py-1 overflow-auto text-wrap focus-visible:outline-none']"
           contenteditable="true"
           ref="editor" @input="onMessageChange" @paste="onPaste">
      </div>
      <div class="flex justify-between items-end px-2">
        <div class="flex gap-1 items-center justify-end py-2">
          <button class="btn btn btn-sm btn-circle btn-outline" @click="sendMessage">
            <i class="fa-solid fa-comment"></i>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
<script>
export default {
  props: ['message'],
  data () {
    return {
      waiting: false,
      editorText: "",
      onDraggingOverInput: false,
      editMessage: this.$props.message
    }
  },
  computed: {
    multiline () {
      return this.editorText?.split("\n").length > 1;
    },
  },
  watch: {
    message () {
      this.editMessage = this.message
    }
  },
  methods: {
    onMessageChange() {
      this.editorText = this.$refs.editor.innerText.trim() || "";
    },
    async sendMessage() {
      const message = this.editorText;
      if (message) {
        this.$emit('message', { role: 'user', content: message });
        this.editorText = "";
        this.$refs.editor.innerText = "";
      }
    },
    onDrop(e) {
      this.onDraggingOverInput = false;
      const files = e.dataTransfer.files;

      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        if (file.type.startsWith('image/')) {
          this.$emit('image', file);
        } else {
          this.$emit('file', file);
        }
      }
    },
    async onPaste(e) {
      const items = e.clipboardData.items;
      for (let i = 0; i < items.length; i++) {
        if (items[i].type.startsWith('image/')) {
          const file = items[i].getAsFile();
          this.$emit('image', file);
        }
      }
    }
  }
}
</script>