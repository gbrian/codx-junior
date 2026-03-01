<script setup>
import Document from '@/components/document/Document.vue'
import VerticalSplitter from '@/components/layout/VerticalSplitter.vue'
import WikiTree from '@/components/wiki/WikiTree.vue'
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
        right: { defaultSize: 70 }
      }">
      
      <template v-slot:left>
        <div v-if="wikiTree">
          <ul class="menu">
            <li @click="selectedCategory = null">
              <a>README</a>
            </li>
            <WikiTree 
              :wikiTree="wikiTree"
              :viewOnly="true"
              @select-item="onSelectItem" />
          </ul>
        </div>
        <span v-else>Loading...</span>
      </template>
      
      <template v-slot:right>
        <div class="pl-2">
          <div v-if="selectedCategory" class="flex flex-col gap-2">
            <div class="text-2xl flex gap-2 click" @click="back()">
              {{ selectedCategory.title }}
            </div>
            <div class="text-sm">{{ selectedCategory.description }}</div>
            <div v-if="selectedCategory.files" class="file-list mt-4">
              <div v-for="file in sortedFiles" :key="file.slug" class="mb-4">
                <Document :content="file.content || ''" />
              </div>
            </div>
          </div>
          <Document v-else :content="readme || ''" />
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
    },
    sortedFiles() {
      // Sort files in descending order by the slug (or another comparison criteria)
      const files = (this.selectedCategory?.files || []) 
      files.forEach(f => this.readFileContent(f))
      return files.slice().sort((a, b) => b.slug.localeCompare(a.slug))
    }
  },
  methods: {
    async readFileContent(file) {
      try {
        if (!file.content) {
          file.content = await this.$storex.api.files.read(file.wiki_file)
        }
      } catch {
        file.content = "> Not found"
      }
    },
    async loadreadme() {
      this.readme = await this.$project.$api.projects.readme()
      this.wikiTree = await this.$storex.api.wiki.config()
    },
    onSelectItem(item) {
      this.selectedCategory = item
    },
    back() {
      this.selectedCategory = null
    }
  }
}
</script>