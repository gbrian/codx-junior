<script setup>
import ChatView from './ChatView.vue';
</script>
<template>
  <ChatView :chatMode="false" class="chat-view w-full h-full" :openChat="chat" /> 
</template>
<script>
export default {
  data () {
    return {
      chat: null
    }
  },
  mounted () {
    this.newChat()
  },
  methods: {
    newChat () {
      this.chat = this.$projects.createNewChat({
        board: "Knowledge",
        column: "General",
        name: "New chat",
        mode: 'chat',
        profiles: [],
        messages: []
      })
    }
  }
}
</script>