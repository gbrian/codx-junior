<template>
  <div role="tablist" class="tabs tabs-bordered">
    <a role="tab" :class="['tab flex items-center gap-2', (tabIx === 'tasks') ? 'tab-active font-bold' : '']" @click="setActiveTab('tasks')">
      <i class="fa-brands fa-trello"></i> <span class="hidden lg:inline">Tasks</span>
    </a>
    <a role="tab" :class="['tab flex items-center gap-2', (tabIx === 'knowledge') ? 'tab-active font-bold' : '']" @click="setActiveTab('knowledge')">
      <i class="fa-solid fa-book"></i> <span class="hidden lg:inline">Knowledge</span>
    </a>
    <a role="tab" :class="['tab flex items-center gap-2', (tabIx === 'wiki') ? 'tab-active font-bold' : '']" @click="setActiveTab('wiki')">
      <i class="fa-brands fa-wikipedia-w"></i> <span class="hidden lg:inline">Docs</span>
    </a>
    <a role="tab" :class="['tab flex items-center gap-2', (tabIx === 'editor') ? 'tab-active font-bold' : '']" @click="setActiveTab('editor')">
      <i class="fa-solid fa-pen"></i> <span class="hidden lg:inline">Editor</span>
    </a>
  </div>
</template>
<script>
export default {
  props: ['tabIx'],
  methods: {
    setActiveTab(tabName) {
      this.$emit('tab', tabName);
    }
  }
}
</script>