<script setup>
import ProjectDetailt from './ProjectDetailt.vue';
</script>
<template>
<div class="dropdown flex flex-col h-full" v-if="$project">
    <ProjectDetailt />
    <ul tabindex="0" class="dropdown-content menu bg-base-100 rounded-box z-[1] w-52 p-2 shadow">
    <li v-for="project in $projects.allProjects" :key="project.codx_path" @click.stop="$projects.setActiveProject(project)">
        <a class="flex gap-2">
        <div class="avatar">
            <div class="w-6 h-6 rounded-full">
            <img :src="project.project_icon" alt="Project Icon" />
            </div>
        </div>
        {{ project.project_name }}
        </a>
    </li>
    </ul>
</div>
</template>
<script>
export default {}
</script>