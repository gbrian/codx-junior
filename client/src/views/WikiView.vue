<script setup>
import Iframe from '../components/Iframe.vue'
</script>
<template>
  <div class="w-full h-full" v-if="$project?.project_wiki && !wikiError">
    <div class="animate-pulse bg-primary h-1 w-full rounded-full" v-if="!loaded"></div>
    <Iframe class="w-full h-full" :url="url" 
      @loaded="onLoaded"      
    />
  </div>
  <div class="hero bg-base-200 w-full h-full" v-else>
    <div class="hero-content text-center">
      <div class="max-w-md">
        <h1 class="text-5xl font-bold">Wiki</h1>
        <p class="py-6">
          Wiki is not ready. Go to project settings and define a wiki folder to start generating your wiki!
        </p>
        <button class="btn btn-primary" @click="$ui.setActiveTab('wiki_settings')" >Settings</button>
      </div>
    </div>
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
  created() {
    fetch(this.url).then(res => { this.wikiError = !res.ok })
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