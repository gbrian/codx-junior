<script setup>
import ProjectIconVue from './ProjectIcon.vue'
</script>
<template>
  <aside
		class="flex flex-col items-center shadow h-full">
		<ProjectIconVue 
      :class="tabIx == 'home' && 'bg-base-100'"
      :project="$project.activeProject"
      :right="right"
      @click="setActiveTab('home')"
    />
		
    <div class="grow overflow-auto border-b border-slate-700 py-1 text-center">
        <div class="over">
          <div class="h-full overflow-auto flex flex-col gap-2">
            <ProjectIconVue 
              :project="project"
              :right="right"
              v-for="project in $project.allProjects" :key="project.codx_path"
              class="opacity-50 hover:opacity-100"
              @click="setActiveProject(project)"
            />
          </div>
        </div>
      </div>

    <div class="flex flex-col mt-4">
      <div :class="['hover:bg-base-100 click', showCoder ? 'bg-base-100': '']">
				<a class="h-16 px-6 flex justify-center items-center w-full focus:text-orange-500 tooltip" :class="right ? 'tooltip-left' : 'tooltip-right'" data-tip="Show coder"
					 @click="$storex.ui.toggleCoder()">
           <i class="fa-solid fa-code"></i>
				</a>
			</div>
      <div :class="['hover:bg-base-100 click', $global.ui.showPreview ? 'bg-base-100': '']">
				<a class="h-16 px-6 flex justify-center items-center w-full focus:text-orange-500 tooltip" :class="right ? 'tooltip-left' : 'tooltip-right'" data-tip="Show preview"
					 @click="$storex.ui.togglePreview()">
           <i class="fa-solid fa-display"></i>
				</a>
			</div>
    </div>
    
    <div>
      <div :class="['hover:bg-base-100 dropdown dropdown-end click',
        right ? 'dropdown-left' : 'dropdown-right',
        isSettings ? 'bg-base-100': '']">
				<a tabindex="0" class="h-16 px-6 flex justify-center items-center w-full focus:text-orange-500 tooltip" :class="right ? 'tooltip-left' : 'tooltip-right'" data-tip="Projects">
           <i class="fa-solid fa-gear"></i>
				</a>
        <ul tabindex="0" class="dropdown-content menu bg-base-200 rounded-box z-[1] w-52 p-2 shadow-xl">
          <li><a @click="setActiveTab('profiles')">Profiles</a></li>
          <li><a @click="setActiveTab('settings')">Project settings</a></li>
          <li><a @click="setActiveTab('global-settings')">Gobal settings</a></li>
        </ul>
			</div>
    </div>

  </aside>
</template>

<script>
export default {
  props: ['tabIx', 'right'],
  data() {
    return {
      isCollapsed: false,
      tabActive: 'text-info bg-base-100',
      tabInactive: 'text-warning bg-base-300 opacity-50 hover:opacity-100'
    };
  },
  computed: {
    isSettings () {
      return ['settings', 'profiles', 'global-settings'].includes(this.tabIx)
    },
    showCoder () {
      const $storex = this.$storex.$parent || this.$storex
      return $storex.ui.showCoder

    }
  },
  methods: {
    setActiveTab (tab) {
      this.$emit('set-active', tab)
    },
    async setActiveProject(project) {
      await this.$project.setActiveProject(project)
      this.setActiveTab(this.tabIx)
    }
  }
};
</script>