<template>
  <div class="linked-projects flex flex-col gap-2">
    <div v-for="project in linkedProjects" :key="project.name" class="linked-project flex items-center gap-2">
      <img :src="project.icon" alt="Project Icon" class="w-8 h-8" />
      <span class="text-lg">{{ project.name }}</span>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      linkedProjects: [
        { name: 'Project 1', icon: 'path/to/project1-icon.jpg' },
        { name: 'Project 2', icon: 'path/to/project2-icon.jpg' }
      ]
    }
  }
}
</script>