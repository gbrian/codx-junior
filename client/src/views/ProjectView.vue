<script setup>
import { ref, onMounted } from 'vue';
import { API } from '../api/api';

const allProjects = ref([]);

const getAllProjects = async () => {
  const { data } = await API.project.list();
  allProjects.value = data;
};

onMounted(() => {
  getAllProjects();
});
</script>
<template>
  <div class="flex flex-col gap-2">
    <div class="text-xl">Projects</div>
    <ul>
      <li v-for="project in allProjects" :key="project.project_name">
        <div class="rounded-full font-bold flex gap-2 items-center">
          <div class="w-8 h-8 bg-cover bg-center rounded-full bg-primary"
              :style="`background-image:url('${project.project_icon}')`"></div>
          <div>{{ project.project_name }}</div>
        </div>
      </li>
    </ul>
  </div>
</template>