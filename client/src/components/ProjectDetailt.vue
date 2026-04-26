<script setup>
import { v4 as uuidv4 } from 'uuid'
</script>

<template>
  <div v-if="project">
    <button class="flex gap-1 click items-center"
      :popovertarget="`project-detail-popover-${uid}`" 
      :style="`anchor-name:--project-detail-anchor-${uid}`"
    >
      <div class="avatar tooltip tooltip-right" :data-tip="project.project_name" v-if="options?.showIcon !== false">
        <div class="rounded-full" :class="['w-'+ iconSize]">
          <img :src="project.project_icon" />
        </div>
      </div>
      <span class="" v-if="iconify !== true">{{ project.project_name }}</span>
    </button>
    <div class="dropdown menu w-52 border border-white/40 rounded-lg bg-base-100 shadow-sm"
      :class="[position]"
      popover :id="`project-detail-popover-${uid}`" 
      :style="`position-anchor:--project-detail-anchor-${uid}`"
      v-if="!disabled"
    >

      <!-- Search Input for Projects -->
      <div class="flex items-center p-2 input input-sm">
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
      <div class="max-h-60 overflow-auto">
        <ul class="menu">
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
</template>

<script>
export default {
  props: {
    iconify: Boolean,
    options: Object,
    position: String,
    disabled: Boolean,
    iconSize: {
      type: Number,
      default: () => (6)
    },
    modelValue: {
      type: Object,
      default: () => (null)
    }
  },
  data() {
    return {
      uid: uuidv4(),
      searchQuery: '',
      matchedProjects: []
    }
  },
  computed: {
    project() {
      return this.modelValue || this.$project
    },
    showFolders() {
      return this.options?.showFolders
    }
  },
  methods: {
    filterProjects() {
      this.matchedProjects = this.$projects.allProjects.filter((proj) => 
        proj.project_name.toLowerCase().includes(this.searchQuery.toLowerCase())
      )
    },
    clearSearch() {
      this.searchQuery = ''
      this.matchedProjects = []
    },
    onProjectSelected(project) {
      this.$emit('update:modelValue', project)
      this.$emit('select', project)
    }
  }
}
</script>