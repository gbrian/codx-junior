<script setup>
import { TreeItem, TreeRoot } from 'radix-vue'
</script>

<template>
  <div>
    <div class="w-full flex justify-between">
      <div class="text-2xl flex items-center">
        Wiki tree
        <div class="flex gap-1 text-xs click">
          <div class="ml-2 text-warning tooltip" data-tip="Add category"
            @click.stop="addChild()">
            <i class="fa-solid fa-plus"></i>
          </div>
        </div>
      </div>
      <div class="flex gap-2">
        <button class="btn btn-sm ml-2 text-white bg-purple-600 hover:animate-pulse tooltip" data-tip="Generate wiki tree"
          @click.stop="buildTree()">
          <i class="fa-solid fa-wand-magic-sparkles"></i>

        </button>
        <button class="btn btn-sm btn-primary" @click="saveSettings">Save</button>
        <button class="btn btn-sm btn-secondary" @click="resetWikiSettings">Discard</button>
      </div>
    </div>
    
    <div class="w-full flex gap-2">
      <div>
        <TreeRoot
          v-slot="{ flattenItems }"
          class="shrink-0 list-none select-none w-56 text-blackA11 rounded-lg p-2 text-sm font-medium"
          :items="wikiTree.categories"
          :get-key="(item) => item.title"
          :default-expanded="['components']"
          v-if="wikiTree"
        >
          <TreeItem
            v-for="item in flattenItems"
            v-slot="{ isExpanded }"
            :key="item._id"
            :style="{ 'padding-left': `${item.level - 0.5}rem` }"
            v-bind="item.bind"
            class="click flex group items-start py-1 px-2 my-0.5 rounded outline-none focus:ring-grass8 focus:ring-2 data-[selected]:bg-grass4"
          >
            <template v-if="item.value.children?.length">
              <span v-if="isExpanded"><i class="fa-solid fa-caret-down"></i></span>
              <span v-else><i class="fa-solid fa-caret-right"></i></span>
            </template>
            <div class="grow ml-2 hover:underline justify-between flex gap-1 items-end" @click.stop="editItem(item.value)">
              {{ item.value.title }} 
              <div class="grow justify-end flex items-center gap-1" v-if="item.value.wiki_files?.length">
                <div>{{ item.value.wiki_files?.length || 0 }}</div>
                <i class="fa-regular fa-file-lines"></i>
              </div>
            </div>
            <div class="ml-2 text-error opacity-0 group-hover:opacity-100 tooltip"
              data-tip="Delete"
              @click.stop="addChild(item.value)">
              <i class="fa-solid fa-trash-can"></i>
            </div>          
            <div class="ml-2 text-warning opacity-0 group-hover:opacity-100 tooltip"
              data-tip="Add child" @click.stop="addChild(item.value)">
              <i class="fa-solid fa-plus"></i>
            </div>          
          </TreeItem>
        </TreeRoot>
      </div>
      <div class="grow flex flex-col gap-2" v-if="selectedItem">
        <div class="form-control">
          <label class="label">
            <span class="label-text">Parent</span>
          </label>
          <select v-model="selectedItem.parentProject" 
            placeholder="Title" class="select select-bordered">
            <option v-for="item in allItems" :key="item.title"
              :value="item.title">{{ item.title }}</option>
          </select>
        </div>
        <div class="form-control">
          <label class="label">
            <span class="label-text">Title</span>
          </label>
          <input type="text" v-model="selectedItem.title" placeholder="Title" class="input input-bordered">
        </div>
        <div class="form-control">
          <label class="label">
            <span class="label-text">Description</span>
          </label>
          <textarea v-model="selectedItem.description" placeholder="Description" class="textarea textarea-bordered"></textarea>
        </div>
        <div class="form-control">
          <label class="label">
            <span class="label-text">Keywords</span>
          </label>
          <input type="text" v-model="selectedItem.keywords" placeholder="Keywords" class="input input-bordered">
        </div>
        <div class="text-xl">
          Children: {{ selectedItem.children?.length || 0 }}
        </div>
        <div class="text-xl">
          Files: {{ selectedItem.files?.length || 0 }}
        </div>
        <div class="flex flex-col gap-2">
          <div class="flex gap-1 group" v-for="file in selectedItem.files" :key="file">
            <div class="ml-2 text-warning opacity-0 group-hover:opacity-100 tooltip click"
              data-tip="Build wiki" @click.stop="buildWiki(file)">
              <i class="fa-solid fa-rotate-right"></i>
            </div>
            {{ file.replace($project.project_path, '') }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      selectedItem: null,
      wikiTree: null
    }
  },
  created() {
    this.resetWikiSettings()
  },
  computed: {
    allItems() {
      return this.wikiTree.categories.reduce((acc, item) => {
        const flatten = (node) => {
          acc.push(node)
          if (node.children) {
            node.children.forEach(flatten)
          }
        }
        flatten(item)
        return acc
      }, [])
    }
  },
  methods: {
    async resetWikiSettings() {
      this.wikiTree = await this.$storex.api.wiki.config()
    },
    editItem(item) {
      item.parent = this.allItems.find(p => p.children?.find(c => c.title === item.title))
      this.selectedItem = item
    },
    addChild(item) {
      const newItem = { title: "New page"}
      if (!item) {
        this.wikiTree.categories.push(newItem)
      } else {
        item.children = [...item.children||[], newItem]
      }
    },
    deleteItem() {
      const { parent, title } = this.selectedItem 
      const children = parent?.children || this.wikiTree.categories
      const ix = children.findIndex(p => p.title === title)
      children.splice(ix, 1)
    },
    async buildTree() {
      this.wikiTree = await this.$storex.api.wiki.build({ step: "create_wiki_tree" })
    },
    saveSettings() {
      this.allItems.map(c => {
        c.keywords = Array.isArray(c.keywords) ? c.keywords : 
          c.keywords?.split(",").map(k => k.trim()).filter(k => !!k)
      })
      this.$storex.api.wiki.save(this.wikiTree)
    },
    buildWiki(file_path) {
      this.$storex.api.wiki.build({ step: "create_wiki_document", file_path })
    }
  }
}
</script>
