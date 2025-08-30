<template>
  <div class="p-4 flex flex-col gap-2">
    <div class="flex flex-col gap-2" v-if="selectedCategory">
      <div class="text-2xl flex gap-2">
        <span @click="back()" >
        <i class="fa-solid fa-circle-arrow-left"></i></span>
        {{ selectedCategory.title }}
      </div>
      <div class="text-sm">{{ selectedCategory.description }}</div>
    </div>
    <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4"
      v-if="showSubCategories"
    >
      <div v-for="category in selectedSection" :key="category.title" 
        class="card bg-base-100 shadow-xl"
        @click="selectCategory(category)"
      >
        <div class="card-body">
          <h2 class="text-xl">{{ category.title }}</h2>
          <p class="text-xs h-40 overflow-auto">
            {{ category.description }}</p>
          <div class="flex justify-end">
            <div>
              <i class="fa-regular fa-file-lines"></i>
              {{ categoryFileCount(category) }}
            </div>
          </div>
        </div>
      </div>
    </div>
    <div class="flex flex-col gap-2" v-if="selectedCategory?.wiki_files?.length">
      <div class="badge badge-xs badge-outline badge-info gap-2" v-if="selectedFile">
        {{  selectedFile.split("/").reverse()[0] }}
        <span class="hover:underline click" @click="showFile(null)" >
          <i class="fa-solid fa-xmark"></i>
        </span>
      </div>
      <div class="text-2xl" v-else>Files</div>
      
      <markdown class="" :text="fileContent" v-if="fileContent" />

      <div class="shrink-0 grid grid-cols-1 sm:grid-cols-2 gap-4 md:grid-cols-3" v-else>
        <div class="badge badge-xs badge-outline click"
          v-for="file in selectedCategory.wiki_files" :key="file"
          @click="showFile(file)"
        >
          {{  file.split("/").reverse()[0] }}
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import Markdown from '../Markdown.vue'
export default {
  components: { Markdown },
  data() {
    return {
      selectedFile: null,
      selectedCategory: null,
      fileContent: null,
      wikiTree: null
    }
  },
  async created() {
    await this.resetWikiSettings()
  },
  computed: {
    showSubCategories() {
      return !this.selectedCategory || this.selectedCategory?.children
    },
    selectedSection() {
      return this.selectedCategory?.children || this.wikiTree?.categories
    },
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
  methods: {
    categoryFileCount(category) {
      return this.allItems.filter(({ path }) => path.startsWith(category.path))
                .map(c => c.wiki_files?.length || 0)
                .reduce((acc, v) => acc + v, 0)
    },
    async resetWikiSettings() {
      this.wikiTree = await this.$storex.api.wiki.config()
    },
    selectCategory(category) {
      if (category) {
        const parent = category?.parent || this.selectedCategory 
        this.selectedCategory = { ...category, parent }
      } else {
        this.selectedCategory = null
      }
    },
    back() {
      this.selectedCategory = this.selectedCategory.parent
      this.showFile(null)
    },
    async showFile(file) {
      this.selectedFile = file
      this.fileContent = file ? await this.$storex.api.files.read(file) : null
    }
  }
}
</script>