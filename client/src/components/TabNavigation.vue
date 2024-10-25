<template>
  <div role="tablist" class="tabs tabs-bordered">
    <a role="tab" :class="['tab flex items-center gap-2', ($ui.tabIx === 'home') ? 'tab-active font-bold' : '']" @click="setActiveTab('home')">
      <i class="fa-solid fa-house"></i>
      <span class="hidden lg:inline">Projects</span>
    </a>
    <a role="tab" :class="['tab flex items-center gap-2', ($ui.tabIx === 'tasks') ? 'tab-active font-bold' : '']" @click="setActiveTab('tasks')">
      <i class="fa-brands fa-trello"></i> <span class="hidden lg:inline">Tasks</span>
    </a>
    <a role="tab" :class="['tab flex items-center gap-2', ($ui.tabIx === 'knowledge') ? 'tab-active font-bold' : '']" @click="setActiveTab('knowledge')">
      <i class="fa-solid fa-book"></i> <span class="hidden lg:inline">Knowledge</span>
    </a>
    <a role="tab" :class="['tab flex items-center gap-2', ($ui.tabIx === 'wiki') ? 'tab-active font-bold' : '']" @click="setActiveTab('wiki')">
      <i class="fa-brands fa-wikipedia-w"></i> <span class="hidden lg:inline">Docs</span>
    </a>
    <a role="tab" :class="['tab flex items-center gap-2', ($ui.tabIx === 'editor') ? 'tab-active font-bold' : '']">
      <div class="dropdown dropdown-end">
        <div tabindex="0" role="button" class="">
          <i class="fa-solid fa-ellipsis"></i><span class="hidden lg:inline">App</span>
        </div>
        <ul tabindex="0" class="dropdown-content menu bg-base-100 rounded-box z-[1] w-52 p-2 shadow">
          <li @click="setActiveApp('coder')">
            <a><i class="fa-solid fa-code"></i> Coder</a></li>
          <li @click="setActiveApp('preview')">
            <a><i class="fa-solid fa-display"></i> Prefiew</a>
          </li>
        </ul>
      </div>
    </a>
  </div>
</template>
<script>
export default {
  methods: {
    setActiveTab(tabName) {
      this.$ui.setActiveTab(tabName);
      this.$ui.setActiveApp()
    },
    setActiveApp(appName) {
      this.$ui.setActiveTab(appName);
      this.$ui.setActiveApp(appName)
    }
  }
}
</script>