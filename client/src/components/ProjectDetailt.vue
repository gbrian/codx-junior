<script setup>
</script>

<template>
  <div @click.stop="" v-if="project">
    <div tabindex="0" role="button" class="flex flex-col gap-2 text-xl md:text-2xl"
      :title="project.project_name"
    >
      <div class="flex gap-2 items-center py-1 px-2">
        <div class="avatar" v-if="iconify">
          <div class="w-6 h-6 rounded-full bg-white">
            <img :src="project.project_icon" />
          </div>
        </div>
        <span class="mr-2" v-if="iconify !== true">{{ project.project_name }}</span>
        
        <!-- Dropdown Component -->
        <div class="dropdown dropdown-start" @click.stop="">
          <div tabindex="0" role="button" class="btn m-1"><i class="fa-solid fa-caret-right"></i></div>
          <ul tabindex="0" class="dropdown-content menu bg-base-100 rounded-box z-50 p-2 shadow-sm">
            <li>
              <!-- Search Input for Projects -->
              <div class="flex items-center mb-2 input input-bordered">
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
              <ul>
                <li v-for="matchedProject in matchedProjects" :key="matchedProject.project_name">
                  <a @click.prevent.stop="onProjectSelected(matchedProject)">
                    <img class="w-4 h-4 rounded-full bg-base-300" :src="matchedProject.project_icon"/>
                    {{ matchedProject.project_name }}
                    <span class="click tooltip" data-tip="Open folder"
                      v-if="showFolders" @click.stop="$ui.coderOpenPath(matchedProject)"
                    >
                      <i class="fa-regular fa-folder"></i>
                    </span>
                  </a>
                </li>
              </ul>
            </li>
            <li>
              <a @click.prevent.stop="onProjectSelected(project)">
                <img class="w-4 h-4 rounded-full bg-base-300" :src="project.project_icon"/>
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
                <img class="w-4 h-4 rounded-full bg-base-300" :src="project.parentProject.project_icon"/>
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
                <summary>Top Level Projects</summary>
                <ul>
                  <li v-for="child in $projects.allParentProjects" :key="child.project_name">
                    <a @click.prevent.stop="onProjectSelected(child)">
                      <img class="w-4 h-4 rounded-full bg-base-300" :src="child.project_icon"/>
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
                <summary>Child Projects</summary>
                <ul>
                  <li v-for="child in $projects.childProjects" :key="child.project_name">
                    <a @click.prevent.stop="onProjectSelected(child)">
                      <img class="w-4 h-4 rounded-full bg-base-300" :src="child.project_icon"/>
                      {{ child.project_name }}
                      <span class="click tooltip" data-tip="Open folder"
                        v-if="showFolders" @click.stop="$ui.coderOpenPath(child)">
                        <i class="fa-regular fa-folder"></i>
                      </span>
                    </a>
                  </li>
                  <li v-for="child in $projects.projectDependencies" :key="child.project_name">
                    <a @click.prevent.stop="onProjectSelected(child)">
                      <img class="w-4 h-4 rounded-full bg-base-300" :src="child.project_icon"/>
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
      return this.options?.folders
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