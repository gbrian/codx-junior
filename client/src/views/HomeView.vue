<script setup>
import { API } from '../api/api'
import MarkdownVue from '@/components/Markdown.vue'
</script>
<template>
  <div class="flex flex-col gap-2 h-full">
    <div class="breadcrumbs text-sm shrink-0">
      <ul>
        <li v-for="path in history" :key="path"
          @click="onBack(path)"
        >
          <a>{{ path }}</a>
        </li>
      </ul>
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
      homeContent: ""
    }
  },
  created () {
    this.navigate("/home.md")
  },
  methods: {
    navigate (path) {
      this.history.push(path)
      API.wiki.read(path)
      .then(({ data }) => this.homeContent = data)
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
    }
  }
}
</script>
