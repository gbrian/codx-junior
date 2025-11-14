<script setup>
import { API } from '../../api/api'
import MarkdownVue from '@/components/Markdown.vue'
</script>

<template>
  <div class="search flex flex-col gap-2 justify-between h-full">
    <div class="flex flex-col gap-2">
      <div class="hidden flex gap-2 text-xs">
        <label class="label" v-for="type in searchTypes" :key="type.name">
          <input type="checkbox" v-model="type.selected" 
            :checked="type.selected" class="checkbox mr-2" />
          {{  type.name }}
        </label>
      </div>
      <div class="flex gap-2 items-center">
        <label class="input input-sm input-bordered flex items-center gap-2 grow">
          <input type="text" class="flex-grow" placeholder="Search in knowledge" @keypress.enter="onKnowledgeSearch"
            :disabled="searching"
            v-model="searchTerm" />
          <i :class="searching && 'animate-pulse'" class="fa-solid fa-magnifying-glass click" @click="onKnowledgeSearch"></i>
        </label>
        <div class="btn btn-sm btn-error btn-outline" @click="$emit('close')">
          <i class="fa-solid fa-circle-xmark"></i>
        </div>
      </div>
      <progress class="progress" v-if="searching"/>
    </div>
    <div class="flex flex-col gap-2 grow overflow-auto" v-if="searchResults">
      <div class="chat chat-start" v-if="searchResults.response">
        <div class="chat-bubble chat-bubble-accent">
          {{ searchResults.response }}
        </div>
      </div>
      <span class="alert alert-error alert-sm" v-if="noResults">
        No documents associated...
      </span>
      <div class="grid grid-cols-2 gap-2 max-h-60 overflow-auto">
        <div
          class="border p-2 border cursor-pointer rounded-md bg-base-300 flex flex-col justify-between gap-2 text-xs"
            :class="doc.selected && 'border-info border-2'"
          v-for="doc, key in searchResults.documents" :key="key" 
            @click="$emit('select', doc)">
          <div class="p-1 rounded font-bold flex flex-col gap-2" :title="doc.metadata.source"
            :class="doc.metadata.relevance_score >= cutoffScore ? 'text-primary' : 'text-error'">
            <div class="click underline" >
              <span @click.stop="$ui.openFile(doc.metadata.source)">
                <i class="fa-solid fa-up-right-from-square"></i> {{ doc.metadata.source.split('/').reverse()[0] }}
              </span>
            </div>
          </div>
          <markdown-vue :text="doc.page_content" class="hidden prose-xs text-xs overflow-auto"></markdown-vue>
          <div class="alert alert-sm alert-error" v-if="doc.metadata.score_error">
            {{ doc.metadata.score_error }}
          </div>
          <div class="flex gap-2 items-center">
            <i class="fa-solid fa-scale-unbalanced"></i>
            {{ `${doc.distance || doc.metadata.db_distance || ''}`.slice(0, 4) }}
            <i class="fa-solid fa-brain"></i>
            {{ doc.metadata.relevance_score }} - {{ doc.metadata.language }}
            <i class="fa-solid fa-file-lines"></i>
            x {{ doc.docs.length }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  props: ['project', 'close'],
  data() {
    return {
      searching: false,
      searchTerm: null,
      searchResults: null,
      selectedFiles: {},
      documentCount: this.project.knowledge_search_document_count,
      cutoffRag: this.project.knowledge_context_rag_distance,
      cutoffScore: this.project.knowledge_context_cutoff_relevance_score,
      enableKeywords: this.project.knowledge_extract_document_tags,
      searchTypes: [
        { name: 'Full Text', value: 'fulltext', selected: true },
        { name: 'Smart', value: 'embeddings' },
        { name: 'Path', value: 'source' },
      ]
    }
  },
  computed: {
    noResults() {
      return this.searchResults &&
        !Object.keys(this.searchResults.documents).length &&
        this.searchResults.response
    },
    searchTypeSelected() {
      return this.searchTypes.filter(st => st.selected)
    }
  },
  methods: {
    async onKnowledgeSearch() {      
      if (!this.searchTerm || !this.searchTypeSelected.length) {
        return
      }
      try {
        this.searching = true
        this.searchResults = null
        const results = await Promise.all(
          this.searchTypeSelected.map(searchType =>
              this.project.$api.knowledge.search({
                searchTerm: this.searchTerm,
                searchType: searchType.value,
                documentSearchType: this.documentSearchType,
                cutoffScore: this.project.knowledge_context_cutoff_relevance_score,
                cutoffRag: this.project.knowledge_context_rag_distance,
                documentCount: this.documentCount
              }).then(this.mergeResults.bind(this)))
            )
        const documents  = results.reduce((a, b) => ({ ...a, ...b }), {})
        this.searchResults = { documents }
      } finally {
        this.searching = false
      }
    },
    mergeResults(data) {
      return data.documents.reduce((acc, doc) => {
        if (!acc[doc.metadata.source]) {
          acc[doc.metadata.source] = {
            distance: doc.distance,
            page_content: doc.page_content.slice(0, 250),
            metadata: doc.metadata,
            docs: []
          }
        }
        acc[doc.metadata.source].docs.push(doc)
        return acc
      }, {})
    }
  }
}
</script>