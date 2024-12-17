<script setup>
import NavigationBarVue from '../components/NavigationBar.vue';
import LogoVue from '../components/Logo.vue';
import TabNavigationVue from '../components/TabNavigation.vue';
import TabViewVue from '../components/TabView.vue';
import ProjectDropdown from '@/components/ProjectDropdown.vue';
</script>
<template>
  <div class="drawer drawer-end">
    <input id="my-drawer-4" type="checkbox" class="drawer-toggle opacity-0" />
    <div class="w-full h-full flex flex-col justify-center items-center bg-base-100/30" v-if="$projects.allProjects === null">
      <div class="text-2xl">LOADING <span class="loading loading-dots loading-xs"></span></div>
    </div>
    <div ref="contentRef" class="drawer-content p-2 flex flex-col gap-2 overflow-auto bg-base-100">
      <div class="flex justify-between">
        <ProjectDropdown class="flex flex-col" />
        <label for="my-drawer-4" class="drawer-button btn btn-sm">
          <LogoVue />
        </label>
      </div>
      <TabNavigationVue />
      <TabViewVue class="grow" />
    </div>
    <div class="drawer-side">
      <label for="my-drawer-4" aria-label="close sidebar" class="drawer-overlay"></label>
      <NavigationBarVue class="bg-base-300" :right="true" />
    </div>
  </div>
</template>
<script>
export default {
  methods: {
    scrollToTop() {
      this.$refs.content.scrollTo({ top: 0, behavior: 'smooth' });
    }
  }
}
</script>