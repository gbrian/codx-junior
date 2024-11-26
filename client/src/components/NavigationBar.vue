<script setup>
import ProjectIconVue from './ProjectIcon.vue'
</script>
<template>
  <div class="flex flex-col items-center shadow h-full"
    :class="$ui.showApp && 'click'">

    <ProjectIconVue
      :right="right"
      @click.stop="setActiveTab('home')"
    />
		
    <div class="grow overflow-auto border-b border-slate-700 py-1 text-center">
        <div class="over">
          <div class="h-full overflow-auto flex flex-col gap-2">
            <!-- button class="btn btn-ghost" @click="$projects.loadAllProjects()">
              <i class="fa-solid fa-arrows-rotate"></i>
            </button>
            <ProjectIconVue 
              :project="project"
              :right="right"
              v-for="project in $projects.allProjects" :key="project.codx_path"
              class="opacity-50 hover:opacity-100"
              @click.stop="setActiveProject(project)"
            /-->
          </div>
        </div>
      </div>

    <div class="flex flex-col mt-4 hidden md:flex">
      <div :class="['hover:bg-base-100 click relative', $ui.appActives[0] === 'coder' ? 'bg-base-100 text-primary': '',]">
				<a class="h-16 px-6 flex justify-center items-center w-full focus:text-orange-500 tooltip" :class="right ? 'tooltip-left' : 'tooltip-right'" data-tip="Show coder"
					 @click.stop="$ui.setShowCoder(true)">
           <div class="flex flex-col gap-4">
            <i class="fa-solid fa-code"></i>
            <span class="text-xs text-error hover:underline opacity-50 hover:opacity-100 absolute top-2 right-2 tooltip" data-tip="close" 
              @click.stop="$ui.setShowCoder(false)" v-if="$ui.showCoder">
              <i class="fa-solid fa-power-off"></i>
            </span>
          </div>
				</a>
			</div>
      <div :class="['hover:bg-base-100 click', $ui.appActives[0] === 'browser' ? 'bg-base-100 text-primary': '']">
				<a class="h-16 px-6 flex justify-center items-center w-full focus:text-orange-500 tooltip" :class="right ? 'tooltip-left' : 'tooltip-right'" data-tip="Show preview"
					 @click.stop="$ui.setShowBrowser(true)">
           <div class="flex flex-col gap-4">
            <i class="fa-solid fa-display"></i>
            <span class="text-xs text-error hover:underline opacity-50 hover:opacity-100 absolute top-2 right-2 tooltip" data-tip="close" 
              @click.stop="$ui.setShowBrowser(false)" v-if="$ui.showBrowser">
              <i class="fa-solid fa-power-off"></i>
            </span>
          </div>
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
          <li><a @click.stop="setActiveTab('profiles')">Profiles</a></li>
          <li><a @click.stop="setActiveTab('settings')">Project settings</a></li>
          <li><a @click.stop="setActiveTab('global-settings')">Global settings</a></li>
          <li><a @click.stop="$ui.toggleLogs()">Logs</a></li>
          <li class="border"></li>
          <li>
            <a>
              <i class="fa-solid fa-table-columns"></i>
              <select class="select select-sm overflow-auto" @change="$ui.setAppDivided($event.target.value)">
                <option v-for="divider in ['none', 'horizontal', 'vertical']" :key="divider" :value="divider">
                  {{ divider }}
                </option>
              </select>
            </a>
          </li>
          <li>
            <a>
              <span class="click" @click="$storex.api.screen.getScreenResolution()"><i class="fa-solid fa-display"></i></span>
              <select class="select select-sm overflow-auto" @change="$storex.api.screen.setScreenResolution($event.target.value)">
                <option disabled selected>Select Resolution</option>
                <option v-for="resolution in $storex.api.screen.display?.resolutions" :key="resolution" :value="resolution"
                  :selected="$storex.api.screen.display?.resolution === resolution"
                >
                  {{ resolution }}
                </option>
              </select>
            </a>
          </li>
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
  created () {
    this.$storex.api.screen.getScreenResolution()
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
    setActiveProject(project) {
      this.$projects.setActiveProject(project)
    }
  }
};
</script>