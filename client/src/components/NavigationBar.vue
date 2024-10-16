<template>
  <aside
		class="flex flex-col items-center shadow h-full">
		<div :class="['h-16 w-full shrink-0 flex flex-col gap-1 items-center items-center hover:bg-base-100 click',
      tabIx == 'home' && 'bg-base-100'
    ]" @click="setActiveTab('home')">
			<a class="h-6 w-6 mt-4 tooltip tooltip-right" data-tip="Projects">
        <div class="avatar">
          <div class="w-6 rounded-full">
            <img :src="$project.activeProject?.project_icon || '/only_icon.png'" />
          </div>
        </div>
      </a>
      <div class="text-xs w-16 text-center overflow-hidden text-nowrap px-1 font-bold">
        {{ $project.activeProject?.project_name  }}
      </div>
		</div>
		<ul>
			<li :class="['hover:bg-base-100 click', (tabIx == 'tasks') ? 'bg-base-100': '']">
				<a class="h-16 px-6 flex flex justify-center items-center w-full focus:text-orange-500 tooltip tooltip-right" data-tip="Kanban board"
          @click="setActiveTab('tasks')">
          <i class="fa-solid fa-list-check"></i>
				</a>
			</li>
			<li :class="['hover:bg-base-100 click', (tabIx == 'knowledge') ? 'bg-base-100': '']">
				<a class="h-16 px-6 flex justify-center items-center w-full focus:text-orange-500 tooltip tooltip-right" data-tip="Knowledge"
					 @click="setActiveTab('knowledge')">
					<i class="fa-solid fa-book"></i>
				</a>
			</li>
      <li :class="['hover:bg-base-100 click', (tabIx == 'wiki') ? 'bg-base-100': '']">
				<a class="h-16 px-6 flex justify-center items-center w-full focus:text-orange-500 tooltip tooltip-right" data-tip="Docs"
					 @click="setActiveTab('wiki')">
           <i class="fa-brands fa-wikipedia-w"></i>
				</a>
			</li>
      <li class="flex justify-center">
        <div class="h-1 border-t-2 w-2/3 opacity-40"></div>
      </li>
      <li :class="['hover:bg-base-100 click', $storex.ui.showCoder ? 'bg-base-100': '']">
				<a class="h-16 px-6 flex justify-center items-center w-full focus:text-orange-500 tooltip tooltip-right" data-tip="Show coder"
					 @click="$storex.ui.toggleCoder()">
           <i class="fa-solid fa-code"></i>
				</a>
			</li>
      <li :class="['hover:bg-base-100 click', $storex.ui.showPreview ? 'bg-base-100': '']">
				<a class="h-16 px-6 flex justify-center items-center w-full focus:text-orange-500 tooltip tooltip-right" data-tip="Show preview"
					 @click="$storex.ui.togglePreview()">
           <i class="fa-solid fa-display"></i>
				</a>
			</li>
    </ul>
    <div class="grow"></div>
    <ul>
      <li :class="['hover:bg-base-100 dropdown dropdown-right dropdown-end click', isSettings ? 'bg-base-100': '']">
				<a tabindex="0" class="h-16 px-6 flex justify-center items-center w-full focus:text-orange-500 tooltip tooltip-right" data-tip="Projects">
           <i class="fa-solid fa-gear"></i>
				</a>
        <ul tabindex="0" class="dropdown-content menu bg-base-200 rounded-box z-[1] w-52 p-2 shadow-xl">
          <li><a @click="setActiveTab('profiles')">Profiles</a></li>
          <li><a @click="setActiveTab('settings')">Project settings</a></li>
          <li><a @click="setActiveTab('global-settings')">Gobal settings</a></li>
        </ul>
			</li>
    </ul>
  </aside>
</template>

<script>
export default {
  props: ['tabIx'],
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
    }
  },
  methods: {
    setActiveTab (tab) {
      this.$emit('set-active', tab)
    }
  }
};
</script>