<template>
  <span v-if="chat.mode === 'task'"><i class="fa-regular fa-file-lines"></i></span>
  <span v-if="chat.mode === 'chat'"><i class="fa-regular fa-comments"></i></span>
  <span v-if="chat.mode === 'browser'"><i class="fa-brands fa-chrome"></i></span>
</template>

<script>
export default {
  props: {
    chat: {
      type: Object,
      required: true
    }
  }
}
</script>