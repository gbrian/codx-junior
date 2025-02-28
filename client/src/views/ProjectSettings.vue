<script setup>
import { API } from '../api/api'
</script>

<template>
  <div class="flex flex-col gap-2 h-full">
    <div class="text-xl font-medium my-2 flex justify-between px-2">
      Settings
      <div class="grow"></div>
      <div class="flex gap-2 justify-end">
        <button type="button" @click="reloadSettings" class="btn btn-sm btn-outline btn-accent">Reload</button>
        <button type="submit" class="btn btn-sm btn-primary" @click="saveSettings">Save</button>
      </div>
    </div>

    <div class="grow px-2" v-if="settings">
      <div class="font-bold mb-2">Project</div>
      <div class="ml-4">

        <div class="flex justify-between mb-2">
          <div class="label-text">codx_path</div>
          <div class="w-1/2"><input v-model="settings.codx_path" type="text" class="input input-bordered w-full"></div>
        </div>

        <div class="flex justify-between mb-2">
          <div class="label-text">project_dependencies</div>
          <div class="w-1/2"><input v-model="settings.project_dependencies" type="text"
              class="input input-bordered w-full"></div>
        </div>
        <div class="flex justify-between mb-2">
          <div class="label-text">project_icon</div>
          <div class="w-1/2"><input v-model="settings.project_icon" type="text" class="input input-bordered w-full">
          </div>
        </div>
        <div class="flex justify-between mb-2">
          <div class="label-text">project_name</div>
          <div class="w-1/2"><input v-model="settings.project_name" type="text" class="input input-bordered w-full">
          </div>
        </div>
        <div class="flex justify-between mb-2">
          <div class="label-text">project_path</div>
          <div class="w-1/2"><input v-model="settings.project_path" type="text" class="input input-bordered w-full">
          </div>
        </div>
        <div class="flex justify-between mb-2">
          <div class="label-text">project_wiki</div>
          <div class="w-1/2"><input v-model="settings.project_wiki" type="text" class="input input-bordered w-full">
          </div>
        </div>
      </div>

      <div class="font-bold mb-2">AI</div>
      <div class="ml-4">
        <div class="flex justify-between mb-2">
          <div class="label-text">llm_model</div>
          <div class="w-1/2"><input v-model="settings.llm_model" type="text"
              class="input input-bordered w-full"></div>
        </div>
        <div class="flex justify-between mb-2">
          <div class="label-text">embeddings_model</div>
          <div class="w-1/2"><input v-model="settings.embeddings_model" type="text"
              class="input input-bordered w-full"></div>
        </div>
      </div>
      <div class="font-bold mb-2">Knowledge</div>
      <div class="ml-4 flex flex-col gap-1">
        <div class="flex justify-between mb-2">
          <div class="label-text">use_knowledge</div>
          <div class="w-1/2"><input v-model="settings.use_knowledge" type="checkbox" class="toggle"></div>
        </div>
        <div class="text-xs">Enable/Disable context enhancement with project files</div>
        <div class="flex justify-between mb-2">
          <div class="label-text">watching</div>
          <div class="w-1/2"><input v-model="settings.watching" type="checkbox" class="toggle"></div>
        </div>
        <div>Context</div>
        <div class="text-xs rounded p-2">
          RAG engine search settings for context enhacement
          Scoring knowledge helps finding the best resources to enrich AI context
          <ul class="pl-4">
            <li><strong>RAG distance (0-1):</strong> Filters after reading from RAG engine</li>
            <li><strong>AI score (0-1):</strong> Post filter using AI to return a score based on how much value will add
              this document to the context</li>
          </ul>
        </div>
        <div class="flex justify-between mb-2">
          <div class="label-text">knowledge_context_rag_distance</div>
          <div class="w-1/2"><input v-model="settings.knowledge_context_rag_distance" type="text"
              class="input input-bordered w-full"></div>
        </div>
        <div class="flex justify-between mb-2">
          <div class="label-text">knowledge_context_cutoff_relevance_score</div>
          <div class="w-1/2"><input v-model="settings.knowledge_context_cutoff_relevance_score" type="text"
              class="input input-bordered w-full"></div>
        </div>
        <div class="flex justify-between mb-2">
          <div class="label-text">knowledge_search_document_count</div>
          <div class="w-1/2"><input v-model="settings.knowledge_search_document_count" type="text"
              class="input input-bordered w-full"></div>
        </div>
        <div class="flex justify-between mb-2">
          <div class="label-text">knowledge_hnsw_M</div>
          <div class="w-1/2"><input v-model="settings.knowledge_hnsw_M" type="text" class="input input-bordered w-full">
          </div>
        </div>

        <div class="divider"></div>

        <div class="flex justify-between mb-2">
          <div class="label-text">knowledge_query_subprojects</div>
          <div class="w-1/2"><input v-model="settings.knowledge_query_subprojects" type="checkbox" class="toggle"></div>
        </div>

        <div class="flex justify-between mb-2">
          <div class="label-text">knowledge_enrich_documents</div>
          <div class="w-1/2"><input v-model="settings.knowledge_enrich_documents" type="checkbox" class="toggle"></div>
        </div>
        <div class="flex justify-between mb-2">
          <div class="label-text">knowledge_extract_document_tags</div>
          <div class="w-1/2"><input v-model="settings.knowledge_extract_document_tags" type="checkbox" class="toggle">
          </div>
        </div>
        <div class="flex justify-between mb-2">
          <div class="label-text">knowledge_external_folders</div>
          <div class="w-1/2"><input v-model="settings.knowledge_external_folders" type="text"
              class="input input-bordered w-full"></div>
        </div>

        <div class="flex justify-between mb-2">
          <div class="label-text">knowledge_file_ignore</div>
          <div class="w-1/2"><input v-model="settings.knowledge_file_ignore" type="text"
              class="input input-bordered w-full"></div>
        </div>
        <div class="flex justify-between mb-2">
          <div class="label-text">knowledge_search_type</div>
          <div class="w-1/2"><input v-model="settings.knowledge_search_type" type="text"
              class="input input-bordered w-full"></div>
        </div>
      </div>

    </div>

    <div class="flex flex-col gap-2 bg-base-200 p-2">
      <div class="text-xl text-error">Danger zone</div>
      <button class="btn btn-error" @click="deleteProject">
        <div class="flex gap-2" v-if="confirmDelete">
          Confirm delete? <span class="hover:underline">YES</span> / <span class="hover:underline"
            @click.stop="confirmDelete = false">NO</span>
        </div>
        <div v-else>
          Delete project
        </div>
      </button>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      settings: null,
      confirmDelete: false
    }
  },
  mounted() {
    this.reloadSettings()
  },
  computed: {
    project() {
      return this.$project
    }
  },
  watch: {
    project() {
      this.reloadSettings()
    }
  },
  methods: {
    async reloadSettings() {
      this.settings = { ...this.$projects.activeProject }
    },
    async saveSettings() {
      await this.$projects.saveSettings(this.settings)
      this.reloadSettings()
    },
    deleteProject() {
      if (this.confirmDelete) {
        this.$emit('delete')
      } else {
        this.confirmDelete = true
      }
    }
  }
}
</script>