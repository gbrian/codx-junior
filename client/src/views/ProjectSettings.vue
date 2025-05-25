<script setup>
import ModelSelector from '@/components/ai_settings/ModelSelector.vue'
</script>

<template>
  <div class="flex flex-col gap-2 h-full" v-if="settings">
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
      <div class="ml-4 flex flex-col gap-2">

        <div class="flex justify-between mb-2">
          <div class="label-text">Project name</div>
          <div class="w-2/3">
            <input v-model="settings.project_name" type="text" class="input input-bordered w-full" />
            <div class="text-xs">The display name of your project.</div>
          </div>
        </div>

        <div class="flex justify-between mb-2">
          <div class="label-text">Project icon</div>
          <div class="w-2/3 flex gap-1 items-center">
            <input v-model="settings.project_icon" type="text" class="input input-bordered w-full" />
            <img :src="settings.project_icon" alt="Project Icon" class="w-8 h-8 rounded-full" />
          </div>
        </div>

        <div class="flex justify-between mb-2">
          <div class="label-text">Project path</div>
          <div class="w-2/3">
            <input v-model="settings.project_path" type="text" class="input input-bordered w-full" />
            <div class="text-xs">The exact directory path to access project files. (Default: .codx parent's folder).</div>
          </div>
        </div>

        <div class="flex justify-between mb-2">
          <div class="label-text">Project preview url</div>
          <div class="w-2/3">
            <input v-model="settings.project_preview_url" type="text" class="input input-bordered w-full" />
            <div class="text-xs">Project's preview url.</div>
          </div>
        </div>

        <div class="flex justify-between mb-2">
          <div class="label-text">Wiki path</div>
          <div class="w-2/3">
            <input v-model="settings.project_wiki" type="text" class="input input-bordered w-full" />
            <div class="text-xs">The link to the project's wiki for documentation.</div>
          </div>
        </div>

        <div class="flex justify-between mb-2">
          <div class="label-text">Dependencies</div>
          <div class="w-2/3">
            <input v-model="settings.project_dependencies" type="text" class="input input-bordered w-full" />
            <div class="text-xs">List of external libraries or modules required.</div>
          </div>
        </div>
      </div>

      <div class="font-bold mb-2">Project Branches</div>
      <div class="flex flex-col gap-2">
        <div>
          <div class="ml-4 flex flex-col gap-2">
            <div class="flex justify-between mb-2">
              <div class="label-text"></div>
              <div class="w-2/3">
                <div class="flex flex-col gap-2">
                  <div class="text-xs">Project branches are copies of the project's files to allow working in parallel</div>
                  <span @click="addBranch" class="text-primary txt-xs underline click">
                    add path
                  </span>
                  <div v-for="(branch, index) in settings.project_branches" :key="index" class="flex justify-between items-center">
                    <button @click="removeBranch(index)" class="btn btn-xs btn-error mr-2">
                      <i class="fa-solid fa-minus"></i>
                    </button>
                    <input v-model="settings.project_branches[index]" type="text" class="input input-bordered w-full input-xs" />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="font-bold mb-2">AI</div>

      <div class="ml-4 flex flex-col gap-2">
        <div class="flex justify-between mb-2">
          <div class="label-text">Wiki model</div>
          <div class="w-2/3">
            <ModelSelector v-model="settings.wiki_model" />
          </div>
        </div>
        <div class="flex justify-between mb-2">
          <div class="label-text">Embeddings model</div>
          <div class="w-2/3">
            <ModelSelector v-model="settings.embeddings_model" />
          </div>
        </div>
        <div class="flex justify-between mb-2">
          <div class="label-text">Knowledge search</div>
          <div class="w-2/3">
            <ModelSelector v-model="settings.rag_model" />
          </div>
        </div>
        <div class="flex justify-between mb-2">
          <div class="label-text">Reasoning model</div>
          <div class="w-2/3">
            <ModelSelector v-model="settings.llm_model" />
          </div>
        </div>
      </div>

      <div class="font-bold mb-2">Knowledge</div>
      <div class="ml-4 flex flex-col gap-1">
        <div class="flex justify-between mb-2">
          <div class="label-text">Use knowledge</div>
          <div class="w-2/3">
            <input v-model="settings.use_knowledge" type="checkbox" class="toggle" />
            <div class="text-xs">Enable/Disable context enhancement with project files.</div>
          </div>
        </div>
        <div class="flex justify-between mb-2">
          <div class="label-text">Watching</div>
          <div class="w-2/3">
            <input v-model="settings.watching" type="checkbox" class="toggle" />
          </div>
        </div>
        <div>Context</div>
        <div class="text-xs rounded p-2">
          RAG engine search settings for context enhancement Scoring knowledge helps finding the best resources to enrich AI context
          <ul class="pl-4">
            <li><strong>RAG distance (0-1):</strong> Filters after reading from RAG engine</li>
            <li><strong>AI score (0-1):</strong> Post filter using AI to return a score based on how much value will add this document to the context</li>
          </ul>
        </div>
        <div class="flex justify-between mb-2">
          <div class="label-text">RAG distance</div>
          <div class="w-2/3">
            <input v-model="settings.knowledge_context_rag_distance" type="text" class="input input-bordered w-full" />
          </div>
        </div>
        <div class="flex justify-between mb-2">
          <div class="label-text">Cutoff Relevance score</div>
          <div class="w-2/3">
            <input v-model="settings.knowledge_context_cutoff_relevance_score" type="text" class="input input-bordered w-full" />
          </div>
        </div>
        <div class="flex justify-between mb-2">
          <div class="label-text">Document count</div>
          <div class="w-2/3">
            <input v-model="settings.knowledge_search_document_count" type="text" class="input input-bordered w-full" />
          </div>
        </div>
        <div class="flex justify-between mb-2">
          <div class="label-text">HNSW M</div>
          <div class="w-2/3">
            <input v-model="settings.knowledge_hnsw_M" type="text" class="input input-bordered w-full" />
          </div>
        </div>

        <div class="divider"></div>

        <div class="flex justify-between mb-2">
          <div class="label-text">Query subprojects</div>
          <div class="w-2/3">
            <input v-model="settings.knowledge_query_subprojects" type="checkbox" class="toggle" />
          </div>
        </div>

        <div class="flex justify-between mb-2">
          <div class="label-text">Enrich documents</div>
          <div class="w-2/3">
            <input v-model="settings.knowledge_enrich_documents" type="checkbox" class="toggle" />
          </div>
        </div>
        <div class="flex justify-between mb-2">
          <div class="label-text">Extract document tags</div>
          <div class="w-2/3">
            <input v-model="settings.knowledge_extract_document_tags" type="checkbox" class="toggle" />
          </div>
        </div>
        <div class="flex justify-between mb-2">
          <div class="label-text">External folders</div>
          <div class="w-2/3">
            <input v-model="settings.knowledge_external_folders" type="text" class="input input-bordered w-full" />
          </div>
        </div>

        <div class="flex justify-between mb-2">
          <div class="label-text">File ignore</div>
          <div class="w-2/3">
            <input v-model="settings.knowledge_file_ignore" type="text" class="input input-bordered w-full" />
          </div>
        </div>
        <div class="flex justify-between mb-2">
          <div class="label-text">Search type</div>
          <div class="w-2/3">
            <input v-model="settings.knowledge_search_type" type="text" class="input input-bordered w-full" />
          </div>
        </div>
      </div>
    </div>

    <div class="font-bold mb-2">Miscellaneous</div>
    <div class="ml-4 flex flex-col gap-1">
      <div class="flex justify-between mb-2">
        <div class="label-text">Save file mentions as tasks</div>
        <div class="w-2/3">
          <input v-model="settings.save_mentions" type="checkbox" class="toggle" />
          <div class="text-xs">Enable/Disable saving file mentions as tasks in the "mentions" board.</div>
        </div>
      </div>
    </div>

    <div class="flex flex-col gap-2 bg-base-200 p-2">
      <div class="text-xl text-error">Danger zone</div>
      <button class="btn btn-error" @click="toggleConfirmDelete">
        <div class="flex gap-2" v-if="confirmDelete">
          Confirm delete? <span class="hover:underline">YES</span> / <span class="hover:underline" @click.stop="confirmDelete = false">NO</span>
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
    },
    models() {
      return this.$storex.api.globalSettings.ai_models
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
    },
    addBranch() {
      if (!this.settings.project_branches) {
        this.settings.project_branches = []
      }
      this.settings.project_branches.push('')
    },
    removeBranch(index) {
      this.settings.project_branches.splice(index, 1)
    }
  }
}
</script>