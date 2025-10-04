<template>
  <div class="p-4 flex flex-col gap-2">
    <div class="flex flex-col gap-2" v-if="selectedCategory">
      <div class="text-2xl flex gap-2 click" @click="back()">
        <span >
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
    <div class="flex flex-col gap-2" v-if="selectedCategory?.files?.length">
      
      <div role="tablist" class="tabs tabs-border overflow-auto gap-2">
        <a role="tab" class="tab text-nowrap border rounded-md"
          :class="selectedFile == file && 'text-info'"
          v-for="file in selectedCategory.files" :key="file"
          @click="showFile(file)"
        >
          {{  file.slug }}
        </a>
      </div>

      <markdown class="" :text="fileContent" v-if="fileContent" />

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
                .map(c => c.files?.length || 0)
                .reduce((acc, v) => acc + v, 0)
    },
    async resetWikiSettings() {
      this.wikiTree = await this.$storex.api.wiki.config()
    },
    selectCategory(category) {
      if (category) {
        const parent = category?.parent || this.selectedCategory 
        this.selectedCategory = { ...category, parent }
        if (this.selectedCategory.wiki_files) {
          this.showFile(this.selectedCategory.wiki_files[0])
        }
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
      this.fileContent = file ? await this.$storex.api.files.read(file.wiki_file) : null
    }
  }
}
</script>