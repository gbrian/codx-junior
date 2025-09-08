<script setup>
import { TreeItem, TreeRoot } from 'radix-vue'
</script>

<template>
  <div v-if="wikiTree">
    <div class="w-full flex justify-between">
      <div class="text-2xl flex items-center">
        Wiki tree
        <div class="flex gap-1 items-center text-xs click">
          <div class="ml-2 text-warning tooltip"
            data-tip="Add category"
            @click.stop="addChild()">
            <i class="fa-solid fa-plus"></i>
          </div>
        </div>
      </div>
      <div class="flex gap-2">
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
              <div class="grow justify-end flex items-center gap-1" v-if="item.value.files?.length">
                <div>{{ item.value.files?.length || 0 }}</div>
                <i class="fa-regular fa-file-lines"></i>
              </div>
            </div>
            <div class="ml-2 text-error opacity-0 group-hover:opacity-100 tooltip"
              data-tip="Delete"
              @click.stop="deleteItem(item.value)">
              <i class="fa-solid fa-trash-can"></i>
            </div>          
            <div class="ml-2 text-warning opacity-0 group-hover:opacity-100 tooltip"
              data-tip="Add child" @click.stop="addChild(item.value)">
              <i class="fa-solid fa-plus"></i>
            </div>          
          </TreeItem>
        </TreeRoot>
      </div>

      <div class="grow flex flex-col gap-2">
        <div class="grow flex flex-col gap-2" v-if="selectedItem">
          <div class="form-control">
            <label class="label flex justify-between">
              <span class="label-text">Parent</span>
              <button class="btn btn-xs btn-circle btn-ghost btn-error" @click="selectedItem = null">
                <i class="fa-solid fa-circle-xmark"></i>
              </button>
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
            Files: {{ selectedItem.files?.length || 0 }}
            <div class="ml-2 text-warning tooltip click"
              data-tip="Build wiki category" @click.stop="buildWikiCategory(selectedItem.path)">
              <i class="fa-solid fa-rotate-right"></i>
            </div>
          </div>
          <div class="flex flex-col gap-2">
            <div class="flex gap-1 group" v-for="file in selectedItem.files" :key="file">
              <div class="ml-2 text-error opacity-0 group-hover:opacity-100 tooltip click"
                data-tip="Delete file" @click.stop="deleteFile(file)">
                <i class="fa-solid fa-trash-can"></i>
              </div>
              <div class="ml-2 text-warning opacity-0 group-hover:opacity-100 tooltip click"
                data-tip="Build wiki" @click.stop="buildWiki(file)">
                <i class="fa-solid fa-rotate-right"></i>
              </div>
              {{ file.replace($project.project_path, '') }}
            </div>
          </div>
        </div>
        <div class="flex flex-col gap-2" v-else>
          <div class="text-xl">Global settings</div>
          <div class="form-control">
            <label class="label">
              <span class="label-text">Project's wiki path</span>
            </label>
            <input type="text" v-model="$project.project_wiki" placeholder="Path" class="input input-bordered">
          </div>  
          <div class="flex justify-between gap-2">
            <div class="form-control">
              <label class="label">
                <span class="label-text">Mode</span>
              </label>
              <select v-model="wikiTree.mode" 
                placeholder="Title" class="select select-sm select-bordered">
                <option value="codx-junior" :selected="!wikiTree.mode || wikiTree.mode === 'codx-junior'">
                  default
                </option>
                <option value="mkdocs" :selected="wikiTree.mode === 'mkdocs'">
                  MkDocs
                </option>
              </select>
            </div>
            <div class="form-control">
              <label class="label">
                <span class="label-text">Language</span>
              </label>
              <select v-model="wikiTree.language" class="select select-sm select-bordered">
                <option v-for="language in languages" :key="language" :value="language">{{ language }}</option>
              </select>
            </div>
          </div>
          <div class="form-control">
            <label class="label">
              <span class="label-text">Wiki instructions</span>
            </label>
            <textarea v-model="wikiTree.prompt" placeholder="Wiki instructions" 
              class="textarea textarea-bordered h-96"></textarea>
          </div>
          <div class="text-xl">Tools</div>
          <div class="flex justify-end gap-2">
            <button class="btn btn-xs ml-2 text-white bg-purple-600 hover:animate-pulse tooltip"
              data-tip="Automagically wiki tree"
              @click.stop="buildTree()">
              Build tree <i class="fa-solid fa-wand-magic-sparkles"></i>
            </button>
            <button class="btn btn-xs ml-2 text-white tooltip"
              data-tip="Compile wiki"
              @click.stop="compileWiki()">
              Compile
            </button>
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
      wikiTree: null,
      languages: ['English', 'Spanish', 'French', 'German']
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
      const newItem = { title: "New page" }
      if (!item) {
        this.wikiTree.categories.push(newItem)
      } else {
        item.children = [...item.children || [], newItem]
      }
    },
    deleteItem(item) {
      const { parent, title } = item || this.selectedItem 
      const children = parent?.children || this.wikiTree.categories
      const ix = children.findIndex(p => p.title === title)
      children.splice(ix, 1)
    },
    async buildTree() {
      await this.saveSettings()
      this.wikiTree = await this.$storex.api.wiki.build({ step: "create_wiki_tree" })
    },
    async compileWiki() {
      await this.$storex.api.wiki.build({ step: "compile_wiki"})
    },
    async saveSettings() {
      this.allItems.map(c => {
        c.keywords = Array.isArray(c.keywords) ? c.keywords : 
          c.keywords?.split(",").map(k => k.trim()).filter(k => !!k)
      })
      await this.$storex.api.wiki.save(this.wikiTree)
    },
    async buildWiki(file_path) {
      await this.saveSettings()
      this.$storex.api.wiki.build({ step: "create_wiki_document", file_path })
    },
    async buildWikiCategory(path) {
      this.$storex.api.wiki.build({ step: "build_wiki_category", path })
    },
    deleteFile(file) {
      const index = this.selectedItem.files.indexOf(file)
      if (index > -1) {
        this.selectedItem.files.splice(index, 1)
        this.saveSettings()
      }
    }
  }
}
</script>