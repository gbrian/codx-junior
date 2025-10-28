<script setup>
import AssistantChat from '../codx-junior/AssistantChat.vue';
import WikiSections from '../wiki/WikiSections.vue';
</script>
<template>
  <div class="h-full flex flex-col">
    Hello!
    <AssistantChat :profile-name="$project.project_name" />
    <wiki-sections />
  </div>
</template>
<script>
export default {
  components: { WikiSections },
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