<script setup>
import AssistantChat from '@/components/codx-junior/AssistantChat.vue';
import MenuDropDown from '@/components/MenuDropDown.vue'
</script>
<template>
  <div class="w-full flex flex-col gap-2">
    <div class="w-full flex justify-between items-center">
      <div class="w-1/12"></div>
      <div class="grow text-4xl text-center">
        Wiki
      </div>
      <div class="w-1/12">
        <MenuDropDown class="dropdown-left">
          <li @click="$ui.setActiveTab('knowledge_settings')" ><a>Wiki settings</a></li>
        </MenuDropDown>
      </div>
    </div>
    <AssistantChat profile-name="wiki" />
  </div>
</template>
<script>
export default {
  data() {
    return {
      loaded: false,
      wikiError: false
    }
  },
  computed: {
    url() {
      return `/api/wiki/${this.$project.project_name}/`
    }
  },
  methods: {
    onLoaded(iframe) {
      const style = document.createElement('style')
      const refElement = document.body
      const { backgroundColor } = getComputedStyle(refElement) 
      style.innerHTML = `
        body, .VPSidebar, .curtain, .content-body, .VPLocalNav, .VPNavBar {
          background-color: ${backgroundColor} !important;
        }
      `
      iframe.contentDocument.body.appendChild(style)
      this.loaded = true
    }
  }
}
</script>