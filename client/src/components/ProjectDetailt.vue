<script setup>
import ProjectChip from './ProjectChip.vue';
</script>
<template>
  <div v-if="$project">
    <div tabindex="0" role="button" class="flex flex-col gap-2 text-2xl">
      <div class="flex gap-2 items-center">
        <div class="avatar">
          <div class="w-6 h-6 rounded-full bg-white">
            <img :src="$projects.activeProject.project_icon" />
          </div>
        </div>
        <span class="mr-2">{{ $project.project_name }}</span>
        <i class="fa-solid fa-caret-down"></i>
      </div>
    </div>
    <div class="text-xs flex gap-2 items-center">
      <div class="text-xs hidden md:flex gap-1 items-center click hover:underline hover:text-warning tooltip"
        :class="$ui.coderProjectCodxPath == $project.codx_path && 'text-warning'"
        data-tip="Open in coder" @click="$ui.coderOpenPath($project)">
        <span v-if="$ui.coderPath == $project.project_path"><i class="fa-solid fa-folder-open"></i></span>
        <span v-else><i class="fa-solid fa-folder"></i></span>
        <div class="max-w-40 overflow-hidden text-nowrap text-right text-ellipsis" :title="$project.project_path">
          {{ $project.project_path }}
        </div>
      </div>
      <ProjectChip :project="$projects.parentProject" class="text-info"
          :data-tip="`Go to ${$projects.parentProject.project_name}`" 
          v-if="$projects.parentProject"
          @click.prevent.stop="$projects.setActiveProject($projects.parentProject)">
          <img class="w-4 rounded-full bg-base-300" :src="$projects.parentProject.project_icon"/>
          {{ $projects.parentProject.project_name }}
      </ProjectChip>
      <ProjectChip :project="child" class="text-secondary"
          :data-tip="`Go to ${child.project_name}`" 
          v-for="child in $projects.childProjects"
        :key="child.project_name" @click.prevent.stop="$projects.setActiveProject(child)">
        <img class="w-4 rounded-full bg-base-300" :src="child.project_icon"/>
        {{ child.project_name }}
      </ProjectChip>
      <ProjectChip :project="child" class="text-info"
        :data-tip="`Go to ${child.project_name}`"
        v-for="child in $projects.projectDependencies"
        :key="child.project_name" @click.stop="$projects.setActiveProject(child)">
        <img class="w-4 rounded-full bg-base-300" :src="child.project_icon"/>
        {{ child.project_name }}
      </ProjectChip>
    </div>
  </div>
</template>
<script>
export default {
  props: ['project']
}
</script>