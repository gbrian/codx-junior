<script setup>
import CodxDropdownVue from './CodxDropdown.vue'
import BarButton from './BarButton.vue';
</script>
<template>
  <div class="flex flex-col items-center px-1 py-2 bg-base-100 gap-4">
    <BarButton tab="projects" @click="$ui.setActiveTab('projects')">
      <i class="fa-solid fa-cubes"></i>
    </BarButton>

    <BarButton 
      @click="$ui.showNewProject(true)">
      <i class="fa-solid fa-plus"></i>
    </BarButton>

    <BarButton tab="tasks"
      @click="$ui.setActiveTab('tasks')">
      <i class="fa-brands fa-trello"></i>
    </BarButton>

    <BarButton tab="profiles"
      @click="$ui.setActiveTab('profiles')"
      v-if="$users.isProjectAdmin"
    >
      <i class="fa-solid fa-user-group"></i>
    </BarButton>

    <BarButton tab="file-finder"
      @click="$ui.setActiveTab('file-finder')">
      <i class="fa-solid fa-folder"></i>
    </BarButton>
  
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