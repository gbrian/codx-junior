<script setup>
import { API } from '../api/api'
import MarkdownVue from '@/components/Markdown.vue'
</script>
<template>
  <div class="flex flex-col gap-2 h-full mb-4">
    <div class="badge badge-warning flex gap-1" v-if="!settings.project_wiki">Set <span><strong>project_wiki path</strong></span> to enable.</div>
    <div class="flex items-center gap-2">
      <div class="breadcrumbs text-xs shrink-0">
        <ul>
          <li class="badge badge-outline" v-for="path in history" :key="path"
            @click="onBack(path)"
          >
            <a>{{ path }}</a>
          </li>
        </ul>
      </div>
      <button class="hidden btn btn-xs btn-ghost" @click="editDocument">
        <span v-if="isEditing"><i class="fa-solid fa-floppy-disk"></i></span>
        <span v-else><i class="fa-solid fa-file-pen"></i></span>
      </button>
    </div>
    <MarkdownVue
      class="grow w-full overflow-auto" :text="homeContent"
      @link="onLink"
    ></MarkdownVue>
  </div>
</template>
<script>
export default {
  props: ['showEditor'],
  data () {
    return {
      history: [],
      homeContent: "",
      isEditing: false
    }
  },
  created () {
    this.navigate("/home.md")
  },
  computed: {
    settings () {
      return API.activeProject
    }
  },
  methods: {
    navigate (path) {
      this.history.push(path)
      API.wiki.read(path)
      .then(data => this.homeContent = data)
      .catch(() => this.homeContent = "## No project wiki yet!" )
    },
    onBack (path) {
      const ix = this.history.indexOf(path)
      this.history.splice(ix)
      this.navigate(path)
    },
    onLink (link) {
      console.log("On markdown link", link)
      let { url } = link
      if (!url.startsWith("/")) {
        url = "/" + url
      } 
      this.navigate(url)
    },
    editDocument () {
      if (this.isEditing) {
        this.saveDocument()
      } else {
        this.isEditing = true
      }
    },
    saveDocument () {
      this.isEditing = false
    }
  }
}
</script>
