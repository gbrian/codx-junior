<script setup>
import ProjectIcon from './ProjectIcon.vue'
</script>
<template>
    <ProjectIcon :width="width" :icon-only="iconOnly" :project="project" />
</template>
<script>
export default {
    props: ['chat', 'width', 'icon-only'],
    computed: {
      project() {
        return this.$chats.getChatWorkingProject(this.chat)
      }
    }
}
</script>