<script setup>
import WikiSections from '@/components/wiki/WikiSections.vue'
import Document from '@/components/document/Document.vue';
import VerticalSplitter from '@/components/layout/VerticalSplitter.vue';
</script>

<template>
  <div class="flex flex-col h-full gap-2 p-1 @md:p-2">
    <div class="text-2xl font-bold">
      <span class="click" @click="viewReadme = false">Wiki</span>
      <span v-if="viewReadme">/ README</span>
    </div>
    <VerticalSplitter class="grow overflow-hidden" 
      :panels="{ 
        left: { defaultSize: 30 }, 
        right: { defaultSize: 70 }}
      ">
      
      <template v-slot:left>
        <div  v-if="wikiTree">
          <ul class="menu">
            <li
              @click="selectedCategory = null"
            >
              <a>README</a>
            </li>
            <li v-for="category in wikiTree.categories" :key="category"
              @click="selectedCategory = category"
            >
              <a>{{ category.title }}</a>
            </li>
          </ul>
        </div>
        <span v-else>Loading...</span>
      </template>
      <template v-slot:right>
        <div class="">
          <div class="flex flex-col gap-2" v-if="selectedCategory">
            <div class="text-2xl flex gap-2 click" @click="back()">
              <span >
              <i class="fa-solid fa-circle-arrow-left"></i></span>
              {{ selectedCategory.title }}
            </div>
            <div class="text-sm">{{ selectedCategory.description }}</div>
          </div>
          <Document :content="readme || ''" v-else />
        </div>
      </template>
    </VerticalSplitter>
  </div>
</template>

<script>
export default {
  data() {
    return {
      viewReadme: false,
      readme: null,
      wikiTree: null,
      selectedCategory: null
    }
  },
  created() {
    this.loadreadme()
  },
  computed: {
    allItems() {
      return this.wikiTree.categories.reduce((acc, item) => {
        const flatten = (node, parent) => {
          node.parent = parent
          acc.push(node)
          if (node.children) {
            node.children.forEach(n => flatten(n, node))
          }
        }
        flatten(item)
        return acc
      }, [])
    }
  },
  watch: {},
  methods: {
    async loadreadme() {
      this.readme = await this.$project.$api.projects.readme()
      this.wikiTree = await this.$storex.api.wiki.config()
    }
  }
}
</script>