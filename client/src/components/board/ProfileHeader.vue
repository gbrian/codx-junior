<template>
  <div class="profile-header flex flex-col items-center text-center">
    <img :src="projectIcon" alt="Project Icon" class="rounded-full w-36 h-36" />
    <h1 class="text-2xl font-bold mt-4">{{ projectName }}</h1>
    <button @click="editProjectSettings" class="btn btn-primary mt-2">Edit Project Settings</button>
  </div>
</template>

<script>
export default {
  data() {
    return {
      projectIcon: 'path/to/project-icon.jpg',
      projectName: 'Project Name'
    }
  },
  methods: {
    editProjectSettings() {
      // Logic to edit project settings
    }
  }
}
</script>