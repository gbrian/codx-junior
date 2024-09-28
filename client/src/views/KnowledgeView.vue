<script setup>
import { API } from '../api/api'
import MarkdownVue from '@/components/Markdown.vue'
</script>
<template>
  <div class="gap-2 h-full justify-between">
    <div class="text-xl font-medium flex justify-between items-center gap-2">
      Knowledge: {{ settings.project_path}}
      <div class="grow">
        <div class="text-error text-xs" v-if="!settings?.use_knowledge">Knowledge search is disabled!</div>
      </div>
      <button class="btn btn-sm" @click="settings.watching = !settings?.watching">
        <span class="label-text mr-2">Watch changes</span> 
        <input type="checkbox" class="toggle toggle-sm toggle-primary" :checked="settings?.watching"
          @change="toggleWatch" :disabled="!settings" />
      </button>
      
      <div class="stat-desc flex gap-2 items-center btn btn-sm" @click="reloadStatus">
        <i class="fa-solid fa-rotate-right"></i> Update
      </div>
    </div>
    <div class="text-xs flex gap-2" v-if="subProjects?.length">
      Linked projects:
      <span class="badge badge-xs badge-warning" v-for="sp in subProjects" :key="sp">
        {{ sp }}
      </span>
    </div>
    <div class="flex flex-col gap-2" v-if="settings?.use_knowledge">
      <div class="text-xs flex gap-2 items-center">
        <i class="fa-solid fa-sliders"></i>
        <div class="flex gap-2 items-center">Search type: 
          <select v-model="documentSearchType" class="w-20 select-bordered select select-xs">
            <option value="similarity">similarity</option>
          </select>
        </div>
        <div class="flex gap-2 items-center">Document count:
          <input type="text" v-model="documentCount" class="w-20 input-bordered input input-xs  max-w-xs" />
        </div>
        <div class="flex gap-2 items-center">Document score (0-1):
          <input type="text" v-model="cutoffScore" class="w-20 input-bordered input input-xs  max-w-xs" />
        </div>
        <div class="flex gap-2 items-center">Keywords:
          <input type="checkbox" v-model="enableKeywords" class="w-20 checkbox checkbox-xs" />
        </div>
        <button class="btn btn-sm" @click="saveKnowledgeSettings">
          <i class="fa-solid fa-floppy-disk"></i>
        </button>
      </div>
      <label class="input input-bordered flex items-center gap-2">
        <select class="select select-xs" v-model="searchType">
          <option value="embeddings">Embeddings</option>
          <option value="source">Source</option>
        </select>
        <input type="text" class="grow" placeholder="Search in knowledge"
          @keypress.enter="onKnowledgeSearch"
          v-model="searchTerm" />
        <i class="fa-solid fa-magnifying-glass" @click="onKnowledgeSearch"></i>
      </label>
      <div class="text-xs">{{ { ...searchResults.settings } }}</div>
      <span class="alert alert-error alert-sm" v-if="!searchResults?.documents?.length">
        No results
      </span>
      <div class="grid grid-cols-3 gap-2">
        <span class="border p-2 border-info cursor-pointer rounded-md bg-base-300 indicator"
            v-for="doc,ix in searchResults?.documents" :key="ix"
            @click="showDoc = { ...doc, docSelected: 0 }"
        >
          <span class="indicator-item badge badge-primary flex gap-2">
            <i class="fa-solid fa-gauge"></i>
            {{ doc.metadata.relevance_score }} - {{ doc.metadata.language  }}
          </span>
          {{ doc.metadata.source.split("/").reverse().slice(0, 2).join(" ") }}
        </span>
      </div>
    </div>
    <div class="stats">
      <div class="stat click" @click="setTab(0)">
        <div class="stat-figure mt-6">
          <i class="fa-2xl fa-solid fa-file"></i>
        </div>
        <div class="stat-title">Pending</div>
        <div class="stat-value">{{ status?.pending_files?.length }}</div>
        <div class="stat-desc"></div>
      </div>
      
      <div class="stat click" @click="setTab(1)">
        <div class="stat-figure mt-6 text-success">
          <i class="fa-2xl fa-solid fa-puzzle-piece"></i>
        </div>
        <div class="stat-title">Indexed</div>
        <div class="stat-value">{{ status?.file_count }}</div>
        <div class="stat-desc"></div>
      </div>

      <div class="stat click" @click="setTab(2)">
        <div class="stat-figure mt-6 text-warning">
          <i class="fa-2xl fa-solid fa-file"></i>
        </div>
        <div class="stat-title">Ignored</div>
        <div class="stat-value">{{ ignoredFolders?.length }}</div>
        <div class="stat-desc"></div>
      </div>

      <div class="stat">
        <div class="stat-figure mt-6 text-info">
          <i class="fa-2xl fa-solid fa-book"></i>
        </div>
        <div class="stat-title">Keywords</div>
        <div class="stat-value">{{ status?.keyword_count }}</div>
        <div class="stat-desc"></div>
      </div>

      <div class="stat">
        <div class="stat-figure mt-6 text-secondary">
          <i class="fa-2xl fa-solid fa-clock"></i>
        </div>
        <div class="stat-title">Last refresh</div>
        <div class="stat-value text-wrap text-sm">{{ lastRefresh }}</div>
      </div>
    </div>

    <div class="p-4 flex flex-col gap-2 grow">
      <div>
        <div class="flex gap-2 my-2">
          <button class="btn btn-sm" @click="toggleAllNoneSelection">
            Select all/none
          </button>
          <label class="input input-sm input-bordered flex items-center gap-2">
            <input type="text" class="grow" placeholder="Search" v-model="fileFilter" />
            <i class="fa-solid fa-magnifying-glass"></i>
            <span class="-mt-1" v-if="fileFilter">({{ showFiles.length }})</span>
          </label>
        </div>
        <div class="flex my-2">
            <div class="badge click" v-for="count, extension in extensions" :key="extension"
                @click="fileFilter = '.' + extension"
            >
                {{ extension }} ({{ count }})
            </div>
        </div>
        <div class="max-h-60 overflow-auto" v-if="showFiles?.length">
          <div class="text-xs" v-for="file in showFiles" :key="file">
            <div class="flex gap-2">
              <input type="checkbox" v-model="selectedFiles[file]" class="checkbox" />
              {{ file.replace(projectPath, "") }}
            </div>
          </div>
        </div>
        <div class="flex gap-2">
          <button class="btn btn-primary btn-sm" @click="reloadKnowledge" v-if="selectedFileCount">
            <i class="fa-solid fa-circle-info"></i> Index ({{ selectedFileCount }}) files now
          </button>
          <button class="btn btn-primary btn-sm btn-error text-white"
            @click="ignoreSelectedFiles(true)" v-if="selectedFileCount && showIndexFiles !== 2">
            <i class="fa-solid fa-folder"></i> Ignore ({{ selectedFileCount }}) folder
          </button>
          <button class="btn btn-primary btn-sm btn-error text-white"
            @click="ignoreSelectedFiles(false)" v-if="selectedFileCount && showIndexFiles !== 2">
            <i class="fa-solid fa-file"></i> Ignore ({{ selectedFileCount }}) files
          </button>
          <button class="btn btn-primary btn-sm btn-success text-white"
            @click="ignoreSelectedFiles(false)" v-if="selectedFileCount && showIndexFiles === 2">
            <i class="fa-solid fa-plus"></i> Add ({{ selectedFileCount }}) files
          </button>
          <button class="btn btn-primary btn-sm btn-warning text-white" @click="dropSelectedFiles" v-if="selectedFileCount">
            <i class="fa-solid fa-trash-can"></i> Drop ({{ selectedFileCount }}) files
          </button>
        </div>
      </div>
      <div class="text-xl flex gap-2 items-center mt-2">
        <i class="fa-solid fa-hand"></i> Manual folder indexing
      </div>
      <div class="text-xs">Allows to index new floders or re-index existing ones</div>
      <label class="input input-bordered flex items-center gap-2">
        <input type="text" class="grow" :placeholder="projectPath" v-model="folderFilter" />
        <span v-if="folderFilter" @click="reloadFolder(folderFilter)">
          <i class="fa-solid fa-rotate-right"></i>
        </span>
        <span v-else>
          <i class="fa-solid fa-magnifying-glass"></i>
        </span>
      </label>
      <div class="dropdown dropdown-open" v-if="folderResulst">
        <div class="dropdown-content z-[1] menu p-2 shadow bg-base-100 rounded-box w-fit">
          <ul>
            <li class="" v-for="folder in folderResulst" :key="folder"
              @click="folderFilter = folder"
            >
              <a>{{ folder }}</a></li>
          </ul>
        </div>
      </div>
    </div>
    <div class="text-xs font-bold py-2 flex flex-col gap-2">
      <div class="text-xl">Ignored patterns:</div>
      <div class="flex input input-sm input-bordered gap-2 max-w-xs items-center">
        <input type="text" class="grow" v-model="addToIgnore" @keydown.enter="addEntriesToIgnore([addToIgnore])">
        <div class="btn btn-xs btn-circle btn-warning" @click="addEntriesToIgnore([addToIgnore])">
          <i class="fa-solid fa-plus"></i>
        </div>
      </div>
      <div class="grid grid-cols-4 gap-2">
        <span class="px-2 flex gap-2 items-center w-fit rounded-full text-warning-content bg-warning" v-for="folder, ix in ignoredFolders" :key="ix">
          {{ folder }}
          <div class="btn btn-xs btn-circle" @click="removeEntriesFromIgnore([folder])">
            <i class="fa-solid fa-minus"></i>
          </div>
        </span>
      </div>
    </div>
    <dialog class="modal modal-bottom sm:modal-middle modal-open" v-if="showDoc" @click="showDoc = null">
      <div class="modal-box flex flex-col gap-2 w-full max-w-full">
        <div class="font-bold text-wrap">
          {{ showDoc.metadata.source.split("/").reverse()[0] }}
        </div>
        <div class="flex flex-col gap-2 grow">
          <div class="flex gap-2 items-center">
            <button class="btn btn-xs btn-info" @click.stop="showDoc.docSelected--"
              :disabled="!showDoc.docSelected">
              <i class="fa-solid fa-backward"></i>
            </button>
            Doc: {{ showDoc.docSelected||0 }} / {{ showDoc.docs.length - 1 }}
            <button class="btn btn-xs btn-warning" @click.stop="showDoc.docSelected++"
              :disabled="!((showDoc.docSelected||0) < (showDoc.docs.length-1))">
              <i class="fa-solid fa-forward"></i>
            </button>
          </div>    
          <MarkdownVue class="prose h-60 overflow-auto"
            :text="'```json\n' + showDoc.docs[showDoc.docSelected||0].page_content + '\n```'" />
        </div>
        <div class="text-xs">
          <pre>{{ showDoc.metadata }}</pre>
        </div>
        <div>
          <form class="flex gap-2" method="dialog">
            <button class="btn btn-info text-white" @click="reIndexFile(showDoc)">
              Re-index
            </button>
            <button class="btn btn-info text-white" @click="extractKeywords(showDoc)">
              Keywords
            </button>
            <button class="btn btn-error text-white" @click="unIndexFile(showDoc)">
              Drop file
            </button>
            <div class="grow"></div>
            <button class="btn" @click="showDoc = null">
              Close
            </button>
          </form>
        </div>
      </div>
    </dialog>
  </div>
</template>
<script>
import moment from 'moment'

export default {
  data() {
    return {
      documents: 0,
      embeddings: 0,
      status: null,
      loading: false,
      folderFilter: null,
      searchTerm: null,
      searchResults: null,
      showDoc: null,
      searchType: "embeddings",
      documentSearchType: API.lastSettings.knowledge_search_type,
      cutoffScore: API.lastSettings.knowledge_context_cutoff_relevance_score,
      documentCount: API.lastSettings.knowledge_search_document_count,
      enableKeywords: API.lastSettings.knowledge_extract_document_tags,
      selectedFiles: {},
      showIndexFiles: 0,
      fileFilter: null,
      addToIgnore: null,
      settings: API.lastSettings
    }
  },
  async created() {
    this.reloadStatus()
  },
  computed: {
    projectPath () {
      return this.settings.project_path
    },
    lastRefresh() {
      if (this.status?.last_update) {
        const ts = parseInt(this.status.last_update, 10) * 1000
        return moment(new Date(ts)).fromNow()
      }
      return null
    },
    folderResulst () {
      if ((this.folderFilter?.length || 0) < 3) {
        return []
      }
      const query = this.folderFilter.toLowerCase()

      const allFolders = [...this.status?.pending_files||[], ...this.status?.folders||[]]
      return allFolders.filter((f, ix, arr) => arr.findIndex(e => e === f) === ix && f.toLowerCase().indexOf(query) !== -1)
        .slice(0, 20)
    },
    showDocPreview () {
      const codePreview = this.showDoc.docs.sort((a, b) => a.metadata.index < b.metadata.index ? -1 : 1)
                              .map(doc => `#### ${doc.metadata.index}: ${doc.metadata.keywords}\n${doc.page_content}\n`)
                              .join("\n")
      return codePreview
    },
    selectedFileCount () {
      return this.selectedFilePaths.filter(k => !!this.selectedFiles[k]).length
    },
    selectedFilePaths () {
      return Object.keys(this.selectedFiles)
    },
    ignoredFolders () {
      const files = this.settings?.knowledge_file_ignore?.trim()
      return files?.split(',').filter(e => e.trim().length)
    },
    showFilesSelected () {
      switch(this.showIndexFiles) {
        case 0:
          return this.status?.pending_files
        case 1:
          return this.status?.files
        default:
          return this.ignoredFolders
      }
    },
    showFiles () {
      const { fileFilter } = this
      return this.showFilesSelected?.filter(f => !fileFilter || f.indexOf(fileFilter) !== -1)
    },
    extensions () {
        return this.showFiles?.filter(f => f.indexOf(".") !== -1).reduce((acc, v) => {
            const extension = v.split(".").reverse()[0]
            acc[extension] = (acc[extension]||0) + 1
            return acc
        } , {})
    },
    subProjects () {
      const {sub_projects } = this.settings
      if (Array.isArray(sub_projects)) {
        return sub_projects
      }
      return sub_projects?.split(",")
    }
  },
  watch: {
  },
  methods: {
    async reloadStatus() {
      const { data } = await API.knowledge.status()
      this.settings = { ...API.lastSettings }
      this.status = data
    },
    async reloadFolder (folderToReload) {
      this.reloadPath(folderToReload)
    },
    async reloadPath(path) {
      this.loading = true
      try {
        await API.knowledge.reloadFolder(path)
        await this.reloadStatus()
        this.folderFilter = null
      } catch{}
      this.loading = false
    },
    async reloadKnowledge () {
      this.loading = true
      try {
        this.selectedFilePaths.forEach(async filePath => {
          await this.reloadPath(filePath)
          delete this.selectedFiles[filePath]
        })
      } catch{}
      this.reloadStatus()
      this.loading = false
    },
    async ignoreSelectedFiles (ignoreFolder) {
      const ignoreFiles = this.selectedFilePaths.map(file => file.replace(this.projectPath, ""))
      const ignoreFolders = ignoreFiles.map(file => file.split("/").reverse()[1])
      const newIgnore = ignoreFolder ? ignoreFolders : ignoreFiles
      this.addEntriesToIgnore(newIgnore)
    },
    async addEntriesToIgnore(entries) {
      const currIgnore = this.settings?.knowledge_file_ignore?.split(',') || []
      const newIgnore = new Set([...currIgnore, ...entries])
      API.lastSettings.knowledge_file_ignore = [...newIgnore].join(",")
      await API.settings.write(API.lastSettings)
      await this.reloadStatus()
      this.selectedFiles = {}
      this.addToIgnore = null
    },
    async removeEntriesFromIgnore(entries) {
      const currIgnore = API.lastSettings?.knowledge_file_ignore?.split(',') || []
      const newIgnore = currIgnore.filter(e => !entries.includes(e))
      API.lastSettings.knowledge_file_ignore = newIgnore.join(",")
      await API.settings.write(API.lastSettings)
      await this.reloadStatus()
      this.selectedFiles = {}
      this.addToIgnore = null
    },
    async dropSelectedFiles () {
      await API.knowledge.delete(this.selectedFilePaths)
      this.selectedFiles = {}
      await this.reloadStatus()
    },
    async onKnowledgeSearch () {
      const { searchTerm,
              searchType,
              documentSearchType,
              cutoffScore,
              documentCount
      } = this
      const { data } = await API.knowledge.search({ searchTerm,
                                                    searchType,
                                                    documentSearchType,
                                                    cutoffScore,
                                                    documentCount
                                                  })
      data.documents = data.documents.reduce((acc, doc) => {
        if (!acc[doc.metadata.source]) {
          acc[doc.metadata.source] = { metadata: doc.metadata, docs: [] }
        }
        acc[doc.metadata.source].docs.push(doc)
        return acc
      }, {})
      this.searchResults = data 
    },
    async unIndexFile(doc) {
      await API.knowledge.delete([doc.metadata.source])
      this.showDoc = null
      this.onKnowledgeSearch()
    },
    async reIndexFile(doc) {
      await API.knowledge.reloadFolder(doc.metadata.source)
      this.onKnowledgeSearch()
    },
    async extractKeywords(doc) {
      const { data } = await API.knowledge.keywords(doc)
      this.showDoc = data
    },
    async saveKnowledgeSettings () {
      await API.settings.read()
      API.settings.write({
        ...API.lastSettings,
        knowledge_search_type: this.documentSearchType,
        knowledge_context_cutoff_relevance_score: this.cutoffScore,
        knowledge_search_document_count: this.documentCount,
        knowledge_extract_document_tags: this.enableKeywords
      })
      this.reloadStatus()
    },
    async toggleWatch () {
      if (!API.lastSettings) {
        return
      }
      if (API.lastSettings.watching) {
        await API.project.watch()
      } else {
        await API.project.unwatch()
      }
      API.settings.read()
      this.reloadStatus()
    },
    setTab (ix) {
      this.showIndexFiles = ix
      this.selectedFiles = {}
    },
    toggleAllNoneSelection () {
      if (this.selectedFileCount) {
        this.selectedFiles = {}
      } else {
        this.selectedFiles = this.showFiles.reduce((acc, f) => ({
          ...acc,
          [f]: true
        }), {})
      }
    }
  }
}
</script>