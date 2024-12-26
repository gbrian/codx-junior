<template>
  <div v-if="$project">
    <div tabindex="0" role="button" class="flex flex-col gap-2 text-2xl">
      <div class="flex gap-2 items-center">
        <div class="avatar">
          <div class="w-6 h-6 rounded-full">
            <img :src="$projects.activeProject.project_icon" />
          </div>
        </div>
        <span class="mr-2">{{ $project.project_name }}</span>
        <i class="fa-solid fa-caret-down"></i>
      </div>
    </div>
    <div class="text-xs flex gap-2 items-center">
      <div class="text-xs hidden md:flex gap-1 items-center click hover:underline hover:text-warning tooltip"
        :class="$ui.coderPath == $project.project_path && 'text-warning'"
        data-tip="Open in coder" @click="$ui.coderOpenPath($project.project_path)">
        <span v-if="$ui.coderPath == $project.project_path"><i class="fa-solid fa-folder-open"></i></span>
        <span v-else><i class="fa-solid fa-folder"></i></span>
        
        {{ $project.project_path }}
      </div>
      <span v-if="$projects.childProjects?.length"><i class="fa-solid fa-folder-tree"></i></span>
      <div class="badge badge-xs badge-secondary click hover:underline" v-for="child in $projects.childProjects"
        :key="child.project_name" @click.stop="$projects.setActiveProject(child)">
        {{ child.project_name }}
      </div>
      <span v-if="$projects.projectDependencies?.length">
        <i class="fa-solid fa-link"></i>
      </span>
      <div class="badge badge-xs badge-primary click hover:underline" v-for="child in $projects.projectDependencies"
        :key="child.project_name" @click.stop="$projects.setActiveProject(child)">
        {{ child.project_name }}
      </div>
    </div>
  </div>
</template>
<script>
export default {
  props: ['project']
}
</script>