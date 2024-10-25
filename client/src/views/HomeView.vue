<script setup>
import NavigationBarVue from '../components/NavigationBar.vue'
import LogoVue from '../components/Logo.vue'
import TabNavigationVue from '../components/TabNavigation.vue'
import TabViewVue from '../components/TabView.vue'
</script>
<template>
  <div class="drawer drawer-end">
    <input id="my-drawer-4" type="checkbox" class="drawer-toggle opacity-0" />
    <div class="drawer-content p-2 flex flex-col gap-2 overflow-auto" v-if="$project">
      <div class="flex justify-between">
        <div class="flex flex-col">
          <div class="font-bold">{{ $project.project_name }}</div>
          <div class="text-xs">{{ $project.project_path }}</div>
        </div>
        <label for="my-drawer-4" class="drawer-button btn btn-sm">
          <LogoVue />
        </label>
      </div>
      <TabNavigationVue />
      <TabViewVue />
    </div>
    <div v-else>
      LOADING....
    </div>
    <div class="drawer-side">
      <label for="my-drawer-4" aria-label="close sidebar" class="drawer-overlay"></label>
      <NavigationBarVue :right="true" />
    </div>
  </div>
</template>
<script>
export default {
}
</script>
