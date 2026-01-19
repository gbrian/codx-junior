<script setup>
import MobileMenuVue from '../MobileMenu.vue'
import ProjectIconVue from '../ProjectIcon.vue'
import CodxDropdownVue from './CodxDropdown.vue'

</script>
<template>
  <div class="flex flex-col items-center px-1 py-2 bg-base-100 gap-4">

    <div class="flex gap-2 items-center click" @click="showMobileMenu = !showMobileMenu">
      <div class="flex flex-col">
        <MobileMenuVue class="" v-if="showMobileMenu" @click.stop="" @close="showMobileMenu = false" />
        <span class="animate-pulse text-xs text-center" v-if="!$storex.session.connected">...offline</span>
      </div>
      <ProjectIconVue
        :icon-only="true"
        :project="$project" 
      /> 
    </div>


    <div class="click " 
      :class="$ui.activeTab === 'projects' ? 'text-primary': ''"
      @click="$ui.setActiveTab('projects')">
      <i class="fa-xl fa-solid fa-cubes"></i>
    </div>

    <div class="click "
      @click="$ui.showNewProject(true)">
      <i class="fa-xl fa-solid fa-plus"></i>
    </div>

    <div class="click "
      :class="!$project ? 'text-slate-400' : ($ui.activeTab === 'tasks' ? 'text-primary': '')"
      @click="$ui.setActiveTab('tasks')">
      <i class="fa-xl fa-brands fa-trello"></i>
    </div>

    <div class="click "
      v-if="$users.isProjectAdmin"
      :class="!$project ? 'text-slate-400' : ($ui.activeTab === 'profiles' ? 'text-primary': '')"
      @click="$ui.setActiveTab('profiles')">
      <i class="fa-xl fa-solid fa-user-group"></i>
    </div>

    <div class="click "
      :class="!$project ? 'text-slate-400' : ($ui.activeTab === 'file-finder' ? 'text-primary': '')"
      @click="$ui.setActiveTab('file-finder')">
      <i class="fa-xl fa-solid fa-folder"></i>
    </div>
  
    <div class="grow"></div>
  
    <CodxDropdownVue class="z-50" />      
  </div>
</template>
<script>
export default {
  data () {
    return {
      showMobileMenu: false
    }
  }
}
</script>