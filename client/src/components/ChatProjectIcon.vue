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
        const { project_id, owner_project_id } = this.chat
        return this.$projects.allProjects.find(p => p.project_id === (project_id || owner_project_id))
      }
    }
}
</script>