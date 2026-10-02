<script setup>
</script>

<template>
  <div class="search flex flex-col gap-2">
    <div class="text-xs font-bold">Fine tune codx-junior knowledge search</div>
    <div class="text-xs flex gap-2 items-center">
      <button class="btn btn-sm" @click="$emit('toggle-watch')">
        <span class="label-text mr-2">Watch changes</span>
        <input type="checkbox" class="toggle toggle-sm toggle-primary" :checked="settings.watching" />
      </button>
      <div class="grow"></div>
      <div class="flex gap-1 items-center">
        <i class="fa-solid fa-sliders"></i>
        <div class="flex gap-2 items-center tooltip" data-tip="Limit results">
          Limit:
          <input type="text" v-model="documentCount" class="w-10 input input-bordered input-xs max-w-xs" />
        </div>
        <div class="flex gap-2 items-center tooltip" data-tip="Rag distance (0-1)">
          Rag (0-1):
          <input type="text" v-model="cutoffRag" class="w-10 input input-bordered input-xs max-w-xs" />
        </div>
        <div class="flex gap-2 items-center tooltip" data-tip="Content score (0-1)">
          Score:
          <input type="text" v-model="cutoffScore" class="w-10 input input-bordered input-xs max-w-xs" />
        </div>
        <div class="flex gap-2 items-center tooltip" data-tip="Use keywords in search">
          Keywords:
          <input type="checkbox" v-model="enableKeywords" class="w-10 checkbox checkbox-xs" />
        </div>
        <button class="btn btn-sm tooltip hover:text-info" data-tip="Save these settings" @click="saveKnowledgeSettings">
          <i class="fa-solid fa-floppy-disk"></i>
        </button>
      </div>
    </div>
    <div class="input input-bordered flex items-center gap-2 w-full">
      <select class="select select-xs" v-model="searchType">
        <option value="fulltext">Full text</option>
        <option value="raw">Query</option>
      </select>
      <input
        type="text"
        class="flex-grow"
        placeholder="Search in knowledge"
        @keypress.enter="onKnowledgeSearch"
        v-model="searchTerm"
      />
      <i class="fa-solid fa-magnifying-glass" @click="onKnowledgeSearch"></i>
    </div>
    <div class="flex flex-col gap-2" v-if="searchResults">
      <div class="text-xs">{{ { ...searchResults.settings } }}</div>
      <div class="chat chat-start" v-if="searchResults.response">
        <div class="chat-bubble chat-bubble-accent">{{ searchResults.response }}</div>
      </div>
      <span class="alert alert-error alert-sm" v-if="noResults">No documents associated...</span>
      <div class="grid grid-cols-2 gap-2">
        <div
          class="border p-2 border-info cursor-pointer rounded-md bg-base-300 flex flex-col justify-between gap-2 text-xs"
          v-for="(doc, ix) in searchResultsDocuments"
          :key="ix"
        >
          <div
            class="p-1 rounded font-bold flex flex-col gap-2"
            :title="doc.metadata.source"
            :class="doc.metadata.relevance_score >= cutoffScore ? 'text-primary' : 'text-error'"
          >
            <div>{{ doc.metadata.source.split('/').reverse()[0] }}</div>
          </div>
          <markdown :text="doc.metadata.score_analysis || doc.page_content" class="grow"></markdown>
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
  emits: ['toggle-watch'],
  props: ['settings', 'project'],
  data() {
    return {
      searchTerm: null,
      searchResults: null,
      searchType: 'fulltext',
      documentSearchType: null,
      cutoffRag: null,
      cutoffScore: null,
      documentCount: null,
      enableKeywords: null
    }
  },
  created() {
    this.documentSearchType = this.$project.knowledge_search_type
    this.cutoffRag = this.$project.knowledge_context_rag_distance
    this.cutoffScore = this.$project.knowledge_context_cutoff_relevance_score
    this.documentCount = this.$project.knowledge_search_document_count
    this.enableKeywords = this.$project.knowledge_extract_document_tags
  },
  computed: {
    noResults() {
      return (
        this.searchResults &&
        !Object.keys(this.searchResults.documents).length &&
        this.searchResults.response
      )
    },
    searchResultsDocuments() {
      return Object.values(this.searchResults?.documents || {}).sort((a, b) =>
        a.metadata.relevance_score > b.metadata.relevance_score ? -1 : 1
      )
    }
  },
  methods: {
    async onKnowledgeSearch() {
      this.searchResults = null
      const { searchTerm, searchType, documentSearchType, documentCount } = this
      if (!searchTerm) return
      const data = await this.project.$api.knowledge.search({
        searchTerm,
        searchType,
        documentSearchType,
        cutoffScore: 0,
        cutoffRag: 0,
        documentCount
      })
      // Group documents by source file
      data.documents = data.documents.reduce((acc, doc) => {
        if (!acc[doc.metadata.source]) {
          acc[doc.metadata.source] = {
            distance: doc.distance ? 1 / parseInt(doc.distance) : null,
            page_content: doc.page_content.slice(0, 250),
            metadata: doc.metadata,
            docs: []
          }
        }
        acc[doc.metadata.source].docs.push(doc)
        return acc
      }, {})
      this.searchResults = data
    },
    async saveKnowledgeSettings() {
      await this.project.$api.settings.read()
      await this.project.$api.settings.save({
        ...this.settings,
        knowledge_search_type: this.documentSearchType,
        knowledge_context_cutoff_relevance_score: this.cutoffScore,
        knowledge_search_document_count: this.documentCount,
        knowledge_extract_document_tags: this.enableKeywords
      })
    }
  }
}
</script>