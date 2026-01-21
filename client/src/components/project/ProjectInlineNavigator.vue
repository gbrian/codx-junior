<script setup>
</script>
<template>
  <div class="flex gap-1 overflow-auto max-w-full pb-3 text-xs" v-if="$project">
    <div class="carousel carousel-center bg-neutral max-w-full space-x-2">
      <div class="carousel-item flex gap-2 items-center border border-slate-600 click rounded-md px-1"
        @click="$projects.setActiveProject($projects.parentProject)"
        v-if="$projects.parentProject"
      >
        <img class="w-4 h-4 rounded-full" :src="$projects.parentProject.project_icon" />
        {{  $projects.parentProject.project_name }}
      </div>
      
      <div class="carousel-item flex gap-2 items-center border border-slate-600 click rounded-md px-1"
        v-for="project in $projects.childProjects" :key="project.project_id"
        @click="$projects.setActiveProject(project)"
      >
        <img class="w-4 h-4 rounded-full" :src="project.project_icon" />
        {{  project.project_name }}
      </div>
    </div>
  </div>
</template>
<script>
export default {
}
</script>