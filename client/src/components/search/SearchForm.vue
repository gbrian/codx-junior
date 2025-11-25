<script setup>
</script>

<template>
  <div class="">
    <div class="flex gap-2 items-center">
      <div class="flex gap-2 items-center shrink-0">
        <div class="avatar">
          <div class="w-8 rounded-full">
            <img :src="$project?.project_icon" />
          </div>
        </div>
        <span class="text-xs mr-4">{{ $project?.project_name }}</span>
      </div>
      <div class="input w-full flex input-bordered items-center">
        <input type="text" placeholder="Search in knowledge" class="grow" v-model="searchTerm" @keypress.enter="onKnowledgeSearch" />
        <div class="click" @click="onKnowledgeSearch">
          <i class="fa-solid fa-magnifying-glass"></i>
        </div>
      </div>
    </div>
    
    <div class="flex flex-col gap-2" v-if="searchResults">
      <div class="chat chat-start" v-if="searchResults.response">
        <div class="chat-bubble chat-bubble-accent">
          {{ searchResults.response }}
        </div>
      </div>
      <span class="alert alert-error alert-sm" v-if="noResults">
        No documents associated...
      </span>
      <div class="grid grid-cols-2 gap-2">
        <div
          class="border p-2 border-info cursor-pointer rounded-md bg-base-300 flex flex-col justify-between gap-2 text-xs"
          v-for="doc, key in searchResults" :key="key">
          {{ key }}
        </div>
      </div>
    </div>
    
    <div v-if="loading" class="w-full">
      <progress class="progress w-full"></progress>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      searchTerm: '', // Reactive data for search input
      loading: false, // Reactive data for loading state
      searchResults: null,
      noResults: false
    }
  },
  methods: {
    async onKnowledgeSearch() {
      this.searchResults = null
      const { searchTerm } = this
      if (!searchTerm) {
        return
      }
      // Show progress bar
      this.loading = true
      try {
        const data = await this.$storex.api.knowledge.search({
          searchTerm,
          searchType: 'default', // Default search type
          documentSearchType: 'default', // Default document search type
          cutoffScore: 0,
          cutoffRag: 0,
          documentCount: 10 // Default document count
        })
        data.documents = data.documents.reduce((acc, doc) => {
          if (!acc[doc.metadata.source]) {
            acc[doc.metadata.source] = {
              distance: doc.distance ? (1 / parseInt(doc.distance)) : null,
              page_content: doc.page_content.slice(0, 250),
              metadata: doc.metadata,
              docs: []
            }
          }
          acc[doc.metadata.source].docs.push(doc)
          return acc
        }, {})
        this.searchResults = data
        this.noResults = Object.keys(data.documents).length === 0
      } finally {
        // Hide progress bar after search completes
        this.loading = false
      }
    }
  }
}
</script>