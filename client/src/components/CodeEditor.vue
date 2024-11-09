<script setup>
import CodeEditor from 'simple-code-editor'
import TreeViewVue from './TreeView.vue'
</script>

<template>
  <div class="flex flex-col gap-1 relative h-full">
    <div class="h-12"> 
      <div class="flex items-center gap-2">
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
      <div class="absolute top-8 left-0 bottom-0 right-0 z-50 bg-base-100/20 click" @click="openMenu = false" v-if="openMenu">
        <div class="h-full flex flex-col p-2 bg-base-200 rounded w-72" @click.stop="">
          <div class="input input-sm input-bordered flex items-center gap-2">
            <button class="click" @click="clearSearch" :class="findFile?.length > 3 ? 'block': 'hidden'">
              <i class="fa-regular fa-circle-xmark"></i>
            </button>
            <input v-model="findFile" type="text" class="grow" placeholder="Search" @keydown.enter.stop="onSearchFiles" />
            <button class="click" @click="onSearchFiles" :class="findFile?.length > 3 ? 'block': 'hidden'">
              <i class="fa-solid fa-magnifying-glass"></i>
            </button>
          </div>
          <TreeViewVue :items="treeItems" class="grow overflow-auto w-72"
            @open="onOpenItem"
          />
        </div>
      </div>
    </div>
    <div class="" v-if="aiAssistant">
      <div class="chat chat-end">
        <div class="chat-bubble w-80 p-1 flex flex-col gap-1">
          <CodeEditor v-model="aiChanges"
            width="100%"
            :header="false"
            :languages="[['markdown', 'AI']]"
          />
          <div class="flex gap-2 justify-between items-center px-1">
            <div class="flex gap-2">
              <button class="btn btn-xs" :class="useKnowledge && 'btn-info'"
                @click="useKnowledge = !useKnowledge">
                <i class="fa-solid fa-book"></i>
              </button>
            </div>
            <button class="btn btn-xs" :class="saving && 'animate-pulse bg-purple-500'" @click="applyAiChanges">
              <i class="fa-solid fa-paper-plane"></i>
            </button>
          </div>
        </div>
      </div>
    </div>
    <CodeEditor v-model="fileContent"
      class="grow"
      width="100%"
      font-size="12px"
      :header="false"
    />
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
      saving: false,
      useKnowledge: false
    }
  },
  async created () {
    const { data: { files } } = await this.$storex.api.files.list(this.$project.project_path)
    this.items = files
    if (this.$ui.openedFile) {
      this.item = {
        "name": this.$ui.openedFile.split("/").reverse()[0],
        "file_path": `${this.$project.project_path}/${this.$ui.openedFile}`,
        "is_dir": false
      }
      this.onOpenItem(this.item)
    }
  },
  computed: {
    fileName() {
      return this.item?.name
    },
    treeItems () {
      return this.searchResults ? this.searchResults : this.items
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
        const flags = []
        if (this.useKnowledge) {
          flags.push("--knowledge")
        }
        const content = "<" + `codx>${flags.join(" ")}\n${this.aiChanges}</codx>\n${this.fileContent}`
        await this.$storex.api.files.write(this.item.file_path, content)
        this.onOpenItem(this.item)
      } finally {
        this.saving = false
      }
    }
  }
}
</script>