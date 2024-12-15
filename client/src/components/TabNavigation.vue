<template>
  <div role="tablist" class="tabs tabs-bordered">
    <a role="tab" :class="['tab flex items-center gap-2', ($ui.tabIx === 'home') ? 'tab-active font-bold' : '']" @click="setActiveTab('home')">
      <i class="fa-solid fa-house"></i>
      <span class="hidden lg:inline">Project</span>
    </a>
    <a role="tab" :class="['tab flex items-center gap-2', 
      disableProjectTabs && 'tab-disabled',
      ($ui.tabIx === 'tasks') ? 'tab-active font-bold' : '']"
      @click="setActiveTab('tasks')">
      <i class="fa-brands fa-trello"></i> <span class="hidden lg:inline">Tasks</span>
    </a>
    <a role="tab" :class="['hidden tab flex items-center gap-2', 
      disableProjectTabs && 'tab-disabled',
      ($ui.tabIx === 'wiki') ? 'tab-active font-bold' : '']" 
      @click="setActiveTab('wiki')">
      <i class="fa-brands fa-wikipedia-w"></i> <span class="hidden lg:inline">Docs</span>
    </a>
    <a role="tab" :class="['tab flex items-center gap-2', 
      disableProjectTabs && 'tab-disabled',
      ($ui.tabIx === 'files') ? 'tab-active font-bold' : '']" 
      @click="setActiveTab('files')">
      <i class="fa-solid fa-folder"></i> 
      <span class="hidden lg:inline">Files</span>
    </a>
    <a role="tab" :class="['tab flex items-center gap-2', 
      disableProjectTabs && 'tab-disabled',
      ($ui.tabIx === 'knowledge') ? 'tab-active font-bold' : '']" 
      @click="setActiveTab('knowledge')">
      <i class="fa-solid fa-book"></i> <span class="hidden lg:inline">Knowledge</span>
    </a>
    
    <a role="tab" :class="['tab flex items-center gap-2', 
      disableProjectTabs && 'tab-disabled',
      ($ui.tabIx === 'app') ? 'tab-active font-bold' : '']" 
      v-if="$ui.isMobile">
      <div class="dropdown dropdown-end">
        <div tabindex="0" role="button" class="flex items-center gap-2">
          <i class="fa-solid fa-ellipsis"></i>
          <span class="hidden lg:inline">App</span>
        </div>
        <ul tabindex="0" class="dropdown-content menu bg-base-100 rounded-box z-[1] w-52 p-2 shadow">
          <li @click="showCoder()">
            <a><i class="fa-solid fa-code"></i> Coder</a></li>
          <li @click="showBrowser()">
            <a><i class="fa-solid fa-display"></i> Prefiew</a>
          </li>
        </ul>
      </div>
    </a>
  </div>
</template>
<script>
export default {
  computed: {
    disableProjectTabs () {
      return !this.$project?.codx_path
    }
  },
  methods: {
    setActiveTab(tabName) {
      if (!this.disableProjectTabs || tabName === 'home') {
        this.$ui.setActiveTab(tabName);
      }
    },
    showCoder() {
      this.$ui.setActiveTab('app');
      this.$ui.setShowCoder(true)
    },
    showBrowser() {
      this.$ui.setActiveTab('app');
      this.$ui.setShowBrowser(true)
    }
  }
}
</script>