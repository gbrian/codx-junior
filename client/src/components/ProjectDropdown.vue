<script setup>
import ProjectDetailt from './ProjectDetailt.vue';
</script>
<template>
<div class="dropdown dropdown-bottom flex flex-col h-full"
    :class="isOpen ? 'dropdown-open': ''" 
    v-if="$project">
    <ProjectDetailt @click="isOpen = !isOpen" />
    <ul class="dropdown-content menu bg-base-300 rounded-box z-50 w-52 p-2 shadow"
      @mouseleave="isOpen = false"
      @blur="isOpen = false"
      v-if="isOpen">
        <div class="mb-2 flex justify-between px-1">
          <span class="click text-xl" @click="isOpen = false">
            <i class="fa-solid fa-caret-up"></i>
          </span>
          <input 
              type="text" 
              class="p-2 bg-base-100 input input-xs w-2/3 items-center" 
              placeholder="Filter projects..." 
              v-model="filterValue" 
          />
          <span class="click" @click="$projects.loadAllProjects()">
            <i class="fa-solid fa-arrows-rotate"></i>
          </span>
        </div>
        <div class="h-96 overflow-auto">
            <li 
                v-for="project in filteredProjects" 
                :key="project.codx_path" 
                @click.prevent.stop="setActiveProject(project)"
            >
                <a class="flex gap-2 items-center">
                    <div class="avatar indicator">
                        <span class="indicator-item w-2 h-2 rounded-full bg-secondary" v-if="project.watching"></span>
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
      isOpen: false,
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
      ).sort((a, b) => a.project_name < b.project_name ? -1: 1);
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
    },
    setActiveProject(project) {
      this.isOpen = false
      this.$projects.setActiveProject(project)
    }
  }
}
</script>