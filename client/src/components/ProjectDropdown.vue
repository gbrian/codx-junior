<script setup>
import ProjectDetailt from './ProjectDetailt.vue';
</script>
<template>
<div class="dropdown dropdown-bottom flex flex-col h-full" v-if="$project">
    <ProjectDetailt tabindex="0" />
    <ul tabindex="0" class="dropdown-content menu bg-base-300 rounded-box z-[1] w-52 p-2 shadow">
        <div v-if="showFilter" class="mb-2">
            <input 
                type="text" 
                class="p-2 bg-base-100 input input-xs" 
                placeholder="Filter projects..." 
                v-model="filterValue" 
            />
        </div>
        <div class="h-96 overflow-auto">
            <li 
                v-for="project in filteredProjects" 
                :key="project.codx_path" 
                @click.stop="$projects.setActiveProject(project)"
            >
                <a class="flex gap-2">
                    <div class="avatar">
                        <div class="w-6 h-6 rounded-full">
                            <img :src="project.project_icon" alt="Project Icon" />
                        </div>
                    </div>
                    {{ project.project_name }}
                </a>
            </li>
        </div>
    </ul>
</div>
</template>
<script>
export default {
  props: {},
  data () {
    return {
      filterValue: ""
    }
  },
  computed: {
    projects () {
      return this.$projects.allProjects;
    },
    showFilter () {
      return this.projects?.length > 10;
    },
    filteredProjects() {
      return this.projects.filter(project => 
        project.project_name.toLowerCase().includes(this.filterValue?.toLowerCase())
      );
    }
  },
  watch: {
    filterValue(newValue) {
      // You can add any required logic here
    }
  },
  methods: {
    resetFilterValue() {
      this.filterValue = null;
    }
  }
}
</script>