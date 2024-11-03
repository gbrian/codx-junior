<script setup>
import CodeEditor from 'simple-code-editor'
import TreeViewVue from './TreeView.vue'
</script>

<template>
  <div class="flex flex-col relative h-full">
    <div class="h-12"> 
      <div class="flex items-center">
        <summary class="btn btn-sm" @click="openMenu = !openMenu">
          <i class="fa-solid fa-bars"></i>
        </summary>
        <div class="grow text-xs">{{ fileName }}</div>
        <div class="flex gap-1 justify-end" v-if="item">
          <button class="btn btn-sm" :class="aiAssistant && 'text-purple-600'"
            @click="aiAssistant = !aiAssistant">
            <i class="fa-solid fa-wand-magic-sparkles"></i>
          </button>
          <button class="btn btn-sm" @click="onSaveChanges">
            <i class="fa-solid fa-floppy-disk"></i>
          </button>
          <button class="btn btn-sm" @click="onOpenItem(item)">
            <i class="fa-solid fa-rotate"></i>
          </button>
        </div>
      </div>
      <div class="absolute top-10 left-0 bottom-0 right-0 z-50 bg-base-100/20 click" @click="openMenu = false" v-if="openMenu">
        <div class="w-56 h-full flex flex-col p-2 bg-base-200 rounded" @click.stop="">
          <div class="input input-sm input-bordered flex items-center gap-2 w-full">
            <button class="click" @click="clearSearch" :class="findFile?.length > 3 ? 'block': 'hidden'">
              <i class="fa-regular fa-circle-xmark"></i>
            </button>
            <input v-model="findFile" type="text" class="grow" placeholder="Search" @keydown.enter.stop="onSearchFiles" />
          </div>
          <TreeViewVue :items="treeItems" class="grow overflow-auto"
            @open="onOpenItem"
          />
        </div>
      </div>
    </div>
    <CodeEditor v-model="fileContent"
      class="grow"
      width="100%"
      :header="false"
    />
    <div class="absolute bottom-20 right-0 z-50" v-if="aiAssistant">
      <div class="chat chat-end">
        <div class="chat-bubble w-80 p-1 flex flex-col gap-1">
          <CodeEditor v-model="aiChanges"
            width="100%"
            :header="false"
            :languages="[['markdown', 'AI']]"
          />
          <div class="flex gap-2 justify-end">
            <button class="btn btn-xs" @click="applyAiChanges">
              <i class="fa-solid fa-paper-plane"></i>
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  data () {
    return {
      openMenu: false,
      item: null,
      items: [],
      fileContent: "",
      findFile: null,
      searchResults: null,
      aiAssistant: false,
      aiChanges: null,
      saving: false
    }
  },
  async created () {
    const { data: { files } } = await this.$storex.api.files.list(this.$project.project_path)
    this.items = files
  },
  computed: {
    fileName() {
      return this.item?.name
    },
    treeItems () {
      return this.searchResults?.length ? this.searchResults : this.items
    }
  },
  watch: {
    aiAssistant (newVal) {
      if (newVal) {
        this.aiChanges = "> How can I help?"
      }
    }
  },
  methods: {
    async onOpenItem(item) {
      if (item.is_dir && !item.children?.length) {
        const { data: { files } } = await this.$storex.api.files.list(item.file_path)
        item.children = files
      } else {
        const { data } = await this.$storex.api.files.read(item.file_path)
        this.item = item
        this.fileContent = data
      }
    },
    async onSearchFiles () {
      const { data } = await this.$storex.api.files.search(this.findFile)
      this.searchResults = data
    },
    clearSearch() {
      this.findFile = null
      this.searchResults = null
    },
    async onSaveChanges() {
      this.saving = true
      await this.$storex.api.files.write(this.item.file_path, this.fileContent)
      this.onOpenItem(this.item)
    },
    async applyAiChanges () {
      this.saving = true
      try {
        const content = "<" + `codx>\n${this.aiChanges}</codx>\n${this.fileContent}`
        await this.$storex.api.files.write(this.item.file_path, content)
        this.onOpenItem(this.item)
      } finally {
        this.saving = false
      }
    }
  }
}
</script>