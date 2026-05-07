<script setup>
import BarButton from './BarButton.vue'
</script>
<template>
  <div class="flex items-center px-1 py-2 bg-base-100 gap-4">


    <BarButton tab="home" @click="onNewQuickChat">
      <i class="fa-solid fa-comments"></i>
    </BarButton>

    <BarButton tab="home" @click="$ui.setActiveTab('home')">
      <i class="fa-solid fa-home"></i>
    </BarButton>

    <BarButton 
      @click="$ui.showNewProject(true)">
      <i class="fa-solid fa-plus"></i>
    </BarButton>

    <BarButton tab="wiki" @click="$ui.setActiveTab('wiki')">
      <i class="fa-solid fa-graduation-cap"></i>
    </BarButton>

    <BarButton tab="tasks"
      @click="$ui.setActiveTab('tasks')">
      <i class="fa-brands fa-trello"></i>
    </BarButton>

    <BarButton tab="profiles"
      @click="$ui.setActiveTab('profiles')"
      v-if="$users.isProjectAdmin"
    >
      <i class="fa-solid fa-user-group"></i>
    </BarButton>

    <BarButton tab="knowledge"
      @click="$ui.setActiveTab('knowledge')"
      v-if="$users.isProjectAdmin"
    >
      <i class="fa-solid fa-magnifying-glass"></i>
    </BarButton>

    <BarButton tab="file-finder"
      @click="$ui.setActiveTab('file-finder')" v-if="false">
      <i class="fa-solid fa-folder"></i>
    </BarButton>      
  </div>
</template>
<script>
export default {
  data () {
    return {
      showMobileMenu: false
    }
  },
  methods: {
    async onNewQuickChat() {
      const chat = await this.$service.chat.newQuickChat()
      this.$ui.openChat(chat)
    }
  }
}
</script>