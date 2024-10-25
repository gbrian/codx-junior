<script setup>
import ProjectIconVue from './ProjectIcon.vue'
</script>
<template>
  <div class="flex flex-col items-center shadow h-full"
    :class="$ui.showApp && 'click'"
    @click="$ui.showApp && $ui.toggleCodxJunior()"
  >

    <ProjectIconVue
      :right="right"
      @click.stop="$ui.sideBarMode ? setActiveTab('home') : $ui.toggleCodxJunior()"
    />
		
    <div class="grow overflow-auto border-b border-slate-700 py-1 text-center">
        <div class="over">
          <div class="h-full overflow-auto flex flex-col gap-2">
            <ProjectIconVue 
              :project="project"
              :right="right"
              v-for="project in $projects.allProjects" :key="project.codx_path"
              class="opacity-50 hover:opacity-100"
              @click.stop="setActiveProject(project)"
            />
          </div>
        </div>
      </div>

    <div class="flex flex-col mt-4 hidden md:flex">
      <div class="hover:bg-base-100 click" v-if="$ui.showApp">
				<a class="h-16 px-6 flex justify-center items-center w-full focus:text-orange-500 tooltip"
            :class="right ? 'tooltip-left' : 'tooltip-right'" data-tip="Toggle floating"
					  @click.stop="$ui.toggleFloating()">
            <span v-if="$ui.floatingCodxJunior"><i class="fa-solid fa-window-maximize"></i></span>
            <span v-else><i class="fa-solid fa-window-restore"></i></span>
				</a>
			</div>
      <div :class="['hover:bg-base-100 click', $ui.showCoder ? 'bg-base-100': '']">
				<a class="h-16 px-6 flex justify-center items-center w-full focus:text-orange-500 tooltip" :class="right ? 'tooltip-left' : 'tooltip-right'" data-tip="Show coder"
					 @click.stop="$ui.toggleApp('coder')">
           <i class="fa-solid fa-code"></i>
				</a>
			</div>
      <div :class="['hover:bg-base-100 click', $ui.showPreview ? 'bg-base-100': '']">
				<a class="h-16 px-6 flex justify-center items-center w-full focus:text-orange-500 tooltip" :class="right ? 'tooltip-left' : 'tooltip-right'" data-tip="Show preview"
					 @click.stop="$ui.toggleApp('preview')">
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
          <li>
            <div class="flex justify-between">
              <button class="btn btn-sm" @click="$ui.incrementCodxJuniorWidth()">
                <i class="fa-solid fa-chevron-left"></i>
              </button>
              <i class="fa-regular fa-window-maximize"></i>
              <button class="btn btn-sm" @click="$ui.decrementCodxJuniorWidth()">
                <i class="fa-solid fa-chevron-right"></i>
              </button>
            </div>
          </li>
          <li><a @click.stop="setActiveTab('profiles')">Profiles</a></li>
          <li><a @click.stop="setActiveTab('settings')">Project settings</a></li>
          <li><a @click.stop="setActiveTab('global-settings')">Gobal settings</a></li>
        </ul>
			</div>
    </div>

  </div>
</template>

<script>
export default {
  props: ['right'],
  data() {
    return {
      isCollapsed: false,
      tabActive: 'text-info bg-base-100',
      tabInactive: 'text-warning bg-base-300 opacity-50 hover:opacity-100'
    };
  },
  computed: {
    isSettings () {
      return ['settings', 'profiles', 'global-settings'].includes(this.$ui.tabIx)
    }
  },
  methods: {
    setActiveTab (tab) {
      this.$ui.setActiveTab(tab)
    },
    async setActiveProject(project) {
      if (this.$ui.showApp && !this.$ui.expandCodxJunior) {
        this.$ui.toggleCodxJunior()
      }
      await this.$projects.setActiveProject(project)
    }
  }
};
</script>