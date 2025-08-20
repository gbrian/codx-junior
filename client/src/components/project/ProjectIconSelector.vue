<script setup>
import ProjectIconSquare from './ProjectIconSquare.vue';
</script>

<template>
  <div class="dropdown" :class="filter?.length && 'dropdown-open'">
    <ProjectIconSquare tabindex="0" role="button" :project="$project" 
    @click="filter = ''"
    @keydown.stop="handleKeydown"
    v-if="$project" />
    <div class="spin spin-dots" v-else></div>
    <ul tabindex="0" class="dropdown-content bg-base-100 ml-2 rounded-box z-[150] p-2 max-h-60 overflow-auto shadow-sm">
      <li><div class="text-xs text-center mb-2" :key="filter">{{ filter }}</div></li>
      <li v-for="project in projects" :key="project.project_id">
        <ProjectIconSquare :project="project" @click="selectProject(project)" />
      </li>
      <li>
        <a>
          <div class="w-12 h-12 rounded-md flex flex-col justify-center items-center border border-white/80">
            <div class="m-auto text-center m-auto click" @click="showSearch = !showSearch">
              <i class="fa-solid fa-magnifying-glass"></i>
            </div>
            <modal close="true" @close="showSearch = false" v-if="showSearch">
              <div class="p-2">
                <input type="text" class="input input-bordered absolute right-2 w-40 z-150" v-model="filter" v-if="showSearch">
              </div>
            </modal>
          </div>
        </a>
      </li>
    </ul>
  </div>
</template>

<script>
export default {
  data() {
    return {
      showSearch: false,
      filter: ""
    };
  },
  computed: {
    projects() {
      return this.$projects.allProjects
        .filter(p => p !== this.$project && (
          !this.filter || p.project_name.toLowerCase().includes(this.filter.toLowerCase())
        ));
    }
  },
  methods: {
    handleKeydown(event) {
      if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
        // Handle arrow keys for navigation
        // This is a placeholder for actual navigation logic
      } else if (event.key === 'Escape') {
        this.filter = ""
      } else if (event.key === 'Backspace') {
        this.filter = this.filter?.slice(0, this.filter?.length - 1)
      } else {
        this.filter += event.key;
      }
      console.log("Project icon handleKeydown", event, this.filter)
    },
    selectProject(project) {
      this.filter = ""
      this.$projects.setActiveProject(project);
      this.$el.parentNode.focus();
    }
  }
};
</script>
