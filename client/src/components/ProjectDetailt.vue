<script setup>
</script>

<template>
  <div v-if="project">
    <div tabindex="0" role="button" class="flex flex-col gap-2 text-xl md:text-2xl"
      :title="project.project_name"
    >
      <div class="flex gap-2 items-center text-nowrap">
        <!-- Dropdown Component -->
        <div class="dropdown dropdown-start">
          <div tabindex="0" role="button" class="flex gap-1 click items-center">
            <div class="avatar" v-if="options?.showIcon">
              <div class="w-7 rounded-md">
                <img :src="project.project_icon" />
              </div>
            </div>
            <span class="-mt-1" v-if="iconify !== true">{{ project.project_name }}</span>
            
          </div>
          <ul tabindex="0" class="dropdown-content menu bg-base-100 rounded-box z-[1000] shadow-sm min-w-60 border p-2 mt-2"
            v-if="options?.showSelector !== false"
          >
            <li>
              <!-- Search Input for Projects -->
              <div class="flex items-center mb-2 input input-sm">
                <span class="click" @click="$projects.loadAllProjects()">
                  <i class="fa-solid fa-arrows-rotate"></i>
                </span>
                <input 
                  type="text" 
                  placeholder="Search projects..." 
                  class=""
                  v-model="searchQuery"
                  @input="filterProjects"
                />
                <i class="fa-solid fa-magnifying-glass ml-2"></i>
                <i class="fa-solid fa-xmark ml-2 cursor-pointer" @click="clearSearch"></i>
              </div>
            </li>
            <li clss="group" v-for="matchedProject in matchedProjects" :key="matchedProject.project_name">
              <a @click.prevent.stop="onProjectSelected(matchedProject)">
                <img class="w-6 h-6 rounded bg-base-300" :src="matchedProject.project_icon"/>
                {{ matchedProject.project_name }}
                <span class="click tooltip" data-tip="Open folder"
                  v-if="showFolders" @click.stop="$ui.coderOpenPath(matchedProject)"
                >
                  <i class="fa-regular fa-folder"></i>
                </span>
              </a>
            </li>
            <li>
              <a @click.prevent.stop="onProjectSelected(project)">
                <img class="w-6 h-6 rounded bg-base-300" :src="project.project_icon"/>
                {{ project.project_name }}
                <span class="click tooltip" data-tip="Open folder"
                  v-if="showFolders" @click.stop="$ui.coderOpenPath(project)">
                  <i class="fa-regular fa-folder"></i>
                </span>
              </a>
            </li>
            
            <!-- Parent Project Section -->
            <li v-if="project.parentProject">
              <a @click.prevent.stop="onProjectSelected(project.parentProject)">
                <img class="w-6 h-6 rounded bg-base-300" :src="project.parentProject.project_icon"/>
                {{ project.parentProject.project_name }}
                <span class="click tooltip" data-tip="Open folder"
                  v-if="showFolders" @click.stop="$ui.coderOpenPath(project.parentProject)">
                  <i class="fa-regular fa-folder"></i>
                </span>
              </a>
            </li>

            <!-- Top Level Projects Section -->
            <li>
              <details>
                <div>Top Level Projects</div>
                <ul>
                  <li v-for="child in $projects.allParentProjects" :key="child.project_name">
                    <a @click.prevent.stop="onProjectSelected(child)">
                      <img class="w-6 h-6 rounded bg-base-300" :src="child.project_icon"/>
                      {{ child.project_name }}
                      <span class="click tooltip" data-tip="Open folder"
                        v-if="showFolders" @click.stop="$ui.coderOpenPath(child)">
                        <i class="fa-regular fa-folder"></i>
                      </span>
                    </a>
                  </li>
                </ul>
              </details>
            </li>

            <!-- Child Projects Section -->
            <li v-if="$projects.childProjects?.length">
              <details open>
                <div>Child Projects</div>
                <ul>
                  <li v-for="child in $projects.childProjects" :key="child.project_name">
                    <a @click.prevent.stop="onProjectSelected(child)">
                      <img class="w-6 h-6 rounded bg-base-300" :src="child.project_icon"/>
                      {{ child.project_name }}
                      <span class="click tooltip" data-tip="Open folder"
                        v-if="showFolders" @click.stop="$ui.coderOpenPath(child)">
                        <i class="fa-regular fa-folder"></i>
                      </span>
                    </a>
                  </li>
                  <li v-for="child in $projects.projectDependencies" :key="child.project_name">
                    <a @click.prevent.stop="onProjectSelected(child)">
                      <img class="w-6 h-6 rounded bg-base-300" :src="child.project_icon"/>
                      {{ child.project_name }}
                      <span class="click tooltip" data-tip="Open folder"
                        v-if="showFolders" @click.stop="$ui.coderOpenPath(child)">
                        <i class="fa-regular fa-folder"></i>
                      </span>
                    </a>
                  </li>
                </ul>
              </details>
            </li>
            
          </ul>
        </div>        
      </div>
    </div>
  </div>
</template>

<script>
export default {
  props: ['project', 'iconify', 'options'],
  data() {
    return {
      searchQuery: '',
      matchedProjects: []
    }
  },
  computed: {
    showFolders() {
      return this.options?.showFolders
    }
  },
  methods: {
    filterProjects() {
      // Filters projects based on the search query
      this.matchedProjects = this.$projects.allProjects.filter((proj) => 
        proj.project_name.toLowerCase().includes(this.searchQuery.toLowerCase())
      )
    },
    clearSearch() {
      // Clears the search input
      this.searchQuery = ''
      this.matchedProjects = []
    },
    onProjectSelected(project) {
      this.$emit('select', project)
    }
  }
}
</script>