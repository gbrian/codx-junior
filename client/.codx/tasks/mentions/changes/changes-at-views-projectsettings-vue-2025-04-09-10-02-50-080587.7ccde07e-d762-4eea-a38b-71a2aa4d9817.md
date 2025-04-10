# [[{"id": "7ccde07e-d762-4eea-a38b-71a2aa4d9817", "doc_id": null, "project_id": null, "parent_id": null, "status": "", "tags": ["skip_knowledge"], "file_list": [], "profiles": [], "name": "changes-at-views-projectsettings-vue-2025-04-09-10-02-50-080587", "created_at": "2025-04-09 10:00:59.199595", "updated_at": "2025-04-09T10:03:29.574956", "mode": "chat", "kanban_id": "", "column_id": "", "board": "mentions", "column": "changes", "chat_index": 0, "live_url": "", "branch": "", "file_path": "", "model": ""}]]
## [[{"doc_id": "a2345f51-3649-4d08-a02a-ada41801dde0", "role": "user", "task_item": "", "hide": false, "improvement": false, "created_at": "2025-04-09 10:00:59.198224", "updated_at": "2025-04-09 10:00:59.198250", "images": [], "files": [], "meta_data": {}, "profiles": []}]]

                      ```
                      <script setup>
import ModelSelector from '@/components/ai_settings/ModelSelector.vue';
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
      <div class="ml-4 flex flex-col gap-2">

        <div class="flex justify-between mb-2">
          <div class="label-text">Project Name</div>
          <div class="w-2/3">
            <input v-model="settings.project_name" type="text" class="input input-bordered w-full">
            <div class="text-xs">The display name of your project.</div>
          </div>
        </div>

        <div class="flex justify-between mb-2">
          <div class="label-text">Project Icon</div>
          <div class="w-2/3 flex gap-1 items-center">
            <input v-model="settings.project_icon" type="text" class="input input-bordered w-full">
            <img :src="settings.project_icon" alt="Project Icon" class="w-8 h-8 rounded-full">
          </div>
        </div>

        <div class="flex justify-between mb-2">
          <div class="label-text">Project Path</div>
          <div class="w-2/3">
            <input v-model="settings.project_path" type="text" class="input input-bordered w-full">
            <div class="text-xs">The exact directory path to access project files.</div>
          </div>
        </div>

        <div class="flex justify-between mb-2">
          <div class="label-text">Project Preview Url</div>
          <div class="w-2/3">
            <input v-model="settings.project_preview_url" type="text" class="input input-bordered w-full">
            <div class="text-xs">Project's preview url.</div>
          </div>
        </div>

        <div class="flex justify-between mb-2">
          <div class="label-text">Wiki Page</div>
          <div class="w-2/3">
            <input v-model="settings.project_wiki" type="text" class="input input-bordered w-full">
            <div class="text-xs">The link to the project's wiki for documentation.</div>
          </div>
        </div>

        <div class="flex justify-between mb-2">
          <div class="label-text">codx-junior Path</div>
          <div class="w-2/3">
            <input v-model="settings.codx_path" type="text" class="input input-bordered w-full">
            <div class="text-xs">The root directory where the project's code resides.</div>
          </div>
        </div>

        <div class="flex justify-between mb-2">
          <div class="label-text">Dependencies</div>
          <div class="w-2/3">
            <input v-model="settings.project_dependencies" type="text" class="input input-bordered w-full">
            <div class="text-xs">List of external libraries or modules required.</div>
          </div>
        </div>
      </div>

      <div class="font-bold mb-2">Branches</div>
      <div class="ml-4 flex flex-col gap-2">
        @codx-ok, please-wait...: Create a list manager allowing adding,removing entries from settings.project_branches list. User will paste the path
      </div>

      <div class="font-bold mb-2">AI</div>

      <div class="ml-4 flex flex-col gap-2">
        <div class="flex justify-between mb-2">
          <div class="label-text">Wiki Model</div>
          <div class="w-2/3">
            <ModelSelector v-model="settings.wiki_model" />
          </div>
        </div>
        <div class="flex justify-between mb-2">
          <div class="label-text">Embeddings Model</div>
          <div class="w-2/3">
            <ModelSelector v-model="settings.embeddings_model" />
          </div>
        </div>
        <div class="flex justify-between mb-2">
          <div class="label-text">Knowledge Search</div>
          <div class="w-2/3">
            <ModelSelector v-model="settings.rag_model" />
          </div>
        </div>
        <div class="flex justify-between mb-2">
          <div class="label-text">Reasoning Model</div>
          <div class="w-2/3">
            <ModelSelector v-model="settings.llm_model" />
          </div>
        </div>
      </div>

      <div class="font-bold mb-2">Knowledge</div>
      <div class="ml-4 flex flex-col gap-1">
        <div class="flex justify-between mb-2">
          <div class="label-text">Use Knowledge</div>
          <div class="w-2/3">
            <input v-model="settings.use_knowledge" type="checkbox" class="toggle">
            <div class="text-xs">Enable/Disable context enhancement with project files.</div>
          </div>
        </div>
        <div class="flex justify-between mb-2">
          <div class="label-text">Watching</div>
          <div class="w-2/3">
            <input v-model="settings.watching" type="checkbox" class="toggle">
          </div>
        </div>
        <div>Context</div>
        <div class="text-xs rounded p-2">
          RAG engine search settings for context enhancement
          Scoring knowledge helps finding the best resources to enrich AI context
          <ul class="pl-4">
            <li><strong>RAG distance (0-1):</strong> Filters after reading from RAG engine</li>
            <li><strong>AI score (0-1):</strong> Post filter using AI to return a score based on how much value will add
              this document to the context</li>
          </ul>
        </div>
        <div class="flex justify-between mb-2">
          <div class="label-text">RAG Distance</div>
          <div class="w-2/3">
            <input v-model="settings.knowledge_context_rag_distance" type="text" class="input input-bordered w-full">
          </div>
        </div>
        <div class="flex justify-between mb-2">
          <div class="label-text">Cutoff Relevance Score</div>
          <div class="w-2/3">
            <input v-model="settings.knowledge_context_cutoff_relevance_score" type="text" class="input input-bordered w-full">
          </div>
        </div>
        <div class="flex justify-between mb-2">
          <div class="label-text">Document Count</div>
          <div class="w-2/3">
            <input v-model="settings.knowledge_search_document_count" type="text" class="input input-bordered w-full">
          </div>
        </div>
        <div class="flex justify-between mb-2">
          <div class="label-text">HNSW M</div>
          <div class="w-2/3">
            <input v-model="settings.knowledge_hnsw_M" type="text" class="input input-bordered w-full">
          </div>
        </div>

        <div class="divider"></div>

        <div class="flex justify-between mb-2">
          <div class="label-text">Query Subprojects</div>
          <div class="w-2/3">
            <input v-model="settings.knowledge_query_subprojects" type="checkbox" class="toggle">
          </div>
        </div>

        <div class="flex justify-between mb-2">
          <div class="label-text">Enrich Documents</div>
          <div class="w-2/3">
            <input v-model="settings.knowledge_enrich_documents" type="checkbox" class="toggle">
          </div>
        </div>
        <div class="flex justify-between mb-2">
          <div class="label-text">Extract Document Tags</div>
          <div class="w-2/3">
            <input v-model="settings.knowledge_extract_document_tags" type="checkbox" class="toggle">
          </div>
        </div>
        <div class="flex justify-between mb-2">
          <div class="label-text">External Folders</div>
          <div class="w-2/3">
            <input v-model="settings.knowledge_external_folders" type="text" class="input input-bordered w-full">
          </div>
        </div>

        <div class="flex justify-between mb-2">
          <div class="label-text">File Ignore</div>
          <div class="w-2/3">
            <input v-model="settings.knowledge_file_ignore" type="text" class="input input-bordered w-full">
          </div>
        </div>
        <div class="flex justify-between mb-2">
          <div class="label-text">Search Type</div>
          <div class="w-2/3">
            <input v-model="settings.knowledge_search_type" type="text" class="input input-bordered w-full">
          </div>
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
    models () {
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
    }
  }
}
</script>
                      ```
                      
                      User commented in line 78: Create a list manager allowing adding,removing entries from settings.project_branches list. User will paste the path
                      
## [[{"doc_id": "4568907c-35c3-4599-bcbd-60710a36c363", "role": "user", "task_item": "", "hide": false, "improvement": false, "created_at": "2025-04-09 10:00:59.198224", "updated_at": "2025-04-09 10:00:59.198250", "images": [], "files": [], "meta_data": {}, "profiles": ["daisyui_components", "Vue files"]}]]
Best practices for this file:
                  Project uses DaisyUI for components, use them instead basic HTML elements
# Vue vuejs coding best pratices
Vue files must always follow this structure in this order.
No other elements are valid:
```example vue file
<script setup>
import Component from './component.vue'
import markdown from 'mardown'
</script>
<template>
<div class="w.full h-full flex gap-2">
</div>
</template>
<script>
export default {
props: [].
data (){
 return { myVariable: null }
},
computed: {},
watch: {},
methods: {}
}
</sctipt>
```
* export default component object
* Use component "data" method to return an object variables
* Use component "computed" to define computed properties
" Use component "methods" to define component methods 
* "script setup" section contains ONLY imports, no variables, properties bnor methods
* Use TailwindCSS classes for styling, always consider mobile styles
* Vue component definition will be exporting a default object like, without ref, nor computed imports
* Don't use ";" in the javascript or typescript code
* Avoid long functions
* Add short and concise comments for complex functions
* Don't use <style> elements, use TailWindCSS classes
                  
## [[{"doc_id": "dfaf40f5-2217-4784-8956-bb1c1c8c8e96", "role": "user", "task_item": "", "hide": false, "improvement": false, "created_at": "2025-04-09 10:00:59.198224", "updated_at": "2025-04-09 10:00:59.198250", "images": [], "files": [], "meta_data": {}, "profiles": []}]]

              Rewrite full file content replacing codx instructions with the minimum changes as possible.
              Return only the file content without any further decoration or comments.
              Do not surround response with '```' marks, just content:
              <script setup>
import ModelSelector from '@/components/ai_settings/ModelSelector.vue';
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
      <div class="ml-4 flex flex-col gap-2">

        <div class="flex justify-between mb-2">
          <div class="label-text">Project Name</div>
          <div class="w-2/3">
            <input v-model="settings.project_name" type="text" class="input input-bordered w-full">
            <div class="text-xs">The display name of your project.</div>
          </div>
        </div>

        <div class="flex justify-between mb-2">
          <div class="label-text">Project Icon</div>
          <div class="w-2/3 flex gap-1 items-center">
            <input v-model="settings.project_icon" type="text" class="input input-bordered w-full">
            <img :src="settings.project_icon" alt="Project Icon" class="w-8 h-8 rounded-full">
          </div>
        </div>

        <div class="flex justify-between mb-2">
          <div class="label-text">Project Path</div>
          <div class="w-2/3">
            <input v-model="settings.project_path" type="text" class="input input-bordered w-full">
            <div class="text-xs">The exact directory path to access project files.</div>
          </div>
        </div>

        <div class="flex justify-between mb-2">
          <div class="label-text">Project Preview Url</div>
          <div class="w-2/3">
            <input v-model="settings.project_preview_url" type="text" class="input input-bordered w-full">
            <div class="text-xs">Project's preview url.</div>
          </div>
        </div>

        <div class="flex justify-between mb-2">
          <div class="label-text">Wiki Page</div>
          <div class="w-2/3">
            <input v-model="settings.project_wiki" type="text" class="input input-bordered w-full">
            <div class="text-xs">The link to the project's wiki for documentation.</div>
          </div>
        </div>

        <div class="flex justify-between mb-2">
          <div class="label-text">codx-junior Path</div>
          <div class="w-2/3">
            <input v-model="settings.codx_path" type="text" class="input input-bordered w-full">
            <div class="text-xs">The root directory where the project's code resides.</div>
          </div>
        </div>

        <div class="flex justify-between mb-2">
          <div class="label-text">Dependencies</div>
          <div class="w-2/3">
            <input v-model="settings.project_dependencies" type="text" class="input input-bordered w-full">
            <div class="text-xs">List of external libraries or modules required.</div>
          </div>
        </div>
      </div>

      <div class="font-bold mb-2">Branches</div>
      <div class="ml-4 flex flex-col gap-2">
        @codx-ok, please-wait...: Create a list manager allowing adding,removing entries from settings.project_branches list. User will paste the path
      </div>

      <div class="font-bold mb-2">AI</div>

      <div class="ml-4 flex flex-col gap-2">
        <div class="flex justify-between mb-2">
          <div class="label-text">Wiki Model</div>
          <div class="w-2/3">
            <ModelSelector v-model="settings.wiki_model" />
          </div>
        </div>
        <div class="flex justify-between mb-2">
          <div class="label-text">Embeddings Model</div>
          <div class="w-2/3">
            <ModelSelector v-model="settings.embeddings_model" />
          </div>
        </div>
        <div class="flex justify-between mb-2">
          <div class="label-text">Knowledge Search</div>
          <div class="w-2/3">
            <ModelSelector v-model="settings.rag_model" />
          </div>
        </div>
        <div class="flex justify-between mb-2">
          <div class="label-text">Reasoning Model</div>
          <div class="w-2/3">
            <ModelSelector v-model="settings.llm_model" />
          </div>
        </div>
      </div>

      <div class="font-bold mb-2">Knowledge</div>
      <div class="ml-4 flex flex-col gap-1">
        <div class="flex justify-between mb-2">
          <div class="label-text">Use Knowledge</div>
          <div class="w-2/3">
            <input v-model="settings.use_knowledge" type="checkbox" class="toggle">
            <div class="text-xs">Enable/Disable context enhancement with project files.</div>
          </div>
        </div>
        <div class="flex justify-between mb-2">
          <div class="label-text">Watching</div>
          <div class="w-2/3">
            <input v-model="settings.watching" type="checkbox" class="toggle">
          </div>
        </div>
        <div>Context</div>
        <div class="text-xs rounded p-2">
          RAG engine search settings for context enhancement
          Scoring knowledge helps finding the best resources to enrich AI context
          <ul class="pl-4">
            <li><strong>RAG distance (0-1):</strong> Filters after reading from RAG engine</li>
            <li><strong>AI score (0-1):</strong> Post filter using AI to return a score based on how much value will add
              this document to the context</li>
          </ul>
        </div>
        <div class="flex justify-between mb-2">
          <div class="label-text">RAG Distance</div>
          <div class="w-2/3">
            <input v-model="settings.knowledge_context_rag_distance" type="text" class="input input-bordered w-full">
          </div>
        </div>
        <div class="flex justify-between mb-2">
          <div class="label-text">Cutoff Relevance Score</div>
          <div class="w-2/3">
            <input v-model="settings.knowledge_context_cutoff_relevance_score" type="text" class="input input-bordered w-full">
          </div>
        </div>
        <div class="flex justify-between mb-2">
          <div class="label-text">Document Count</div>
          <div class="w-2/3">
            <input v-model="settings.knowledge_search_document_count" type="text" class="input input-bordered w-full">
          </div>
        </div>
        <div class="flex justify-between mb-2">
          <div class="label-text">HNSW M</div>
          <div class="w-2/3">
            <input v-model="settings.knowledge_hnsw_M" type="text" class="input input-bordered w-full">
          </div>
        </div>

        <div class="divider"></div>

        <div class="flex justify-between mb-2">
          <div class="label-text">Query Subprojects</div>
          <div class="w-2/3">
            <input v-model="settings.knowledge_query_subprojects" type="checkbox" class="toggle">
          </div>
        </div>

        <div class="flex justify-between mb-2">
          <div class="label-text">Enrich Documents</div>
          <div class="w-2/3">
            <input v-model="settings.knowledge_enrich_documents" type="checkbox" class="toggle">
          </div>
        </div>
        <div class="flex justify-between mb-2">
          <div class="label-text">Extract Document Tags</div>
          <div class="w-2/3">
            <input v-model="settings.knowledge_extract_document_tags" type="checkbox" class="toggle">
          </div>
        </div>
        <div class="flex justify-between mb-2">
          <div class="label-text">External Folders</div>
          <div class="w-2/3">
            <input v-model="settings.knowledge_external_folders" type="text" class="input input-bordered w-full">
          </div>
        </div>

        <div class="flex justify-between mb-2">
          <div class="label-text">File Ignore</div>
          <div class="w-2/3">
            <input v-model="settings.knowledge_file_ignore" type="text" class="input input-bordered w-full">
          </div>
        </div>
        <div class="flex justify-between mb-2">
          <div class="label-text">Search Type</div>
          <div class="w-2/3">
            <input v-model="settings.knowledge_search_type" type="text" class="input input-bordered w-full">
          </div>
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
    models () {
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
    }
  }
}
</script>
              
## [[{"doc_id": "27b3c167-006e-4eb5-8723-b8787241826f", "role": "assistant", "task_item": "", "hide": false, "improvement": false, "created_at": "2025-04-09 10:00:59.198224", "updated_at": "2025-04-09 10:00:59.198250", "images": [], "files": [], "meta_data": {"time_taken": 39.49329376220703, "first_chunk_time_taken": 6.391007423400879, "model": "gpt-4o"}, "profiles": []}]]
<script setup>
import ModelSelector from '@/components/ai_settings/ModelSelector.vue'
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
      <div class="ml-4 flex flex-col gap-2">

        <div class="flex justify-between mb-2">
          <div class="label-text">Project Name</div>
          <div class="w-2/3">
            <input v-model="settings.project_name" type="text" class="input input-bordered w-full" />
            <div class="text-xs">The display name of your project.</div>
          </div>
        </div>

        <div class="flex justify-between mb-2">
          <div class="label-text">Project Icon</div>
          <div class="w-2/3 flex gap-1 items-center">
            <input v-model="settings.project_icon" type="text" class="input input-bordered w-full" />
            <img :src="settings.project_icon" alt="Project Icon" class="w-8 h-8 rounded-full" />
          </div>
        </div>

        <div class="flex justify-between mb-2">
          <div class="label-text">Project Path</div>
          <div class="w-2/3">
            <input v-model="settings.project_path" type="text" class="input input-bordered w-full" />
            <div class="text-xs">The exact directory path to access project files.</div>
          </div>
        </div>

        <div class="flex justify-between mb-2">
          <div class="label-text">Project Preview Url</div>
          <div class="w-2/3">
            <input v-model="settings.project_preview_url" type="text" class="input input-bordered w-full" />
            <div class="text-xs">Project's preview url.</div>
          </div>
        </div>

        <div class="flex justify-between mb-2">
          <div class="label-text">Wiki Page</div>
          <div class="w-2/3">
            <input v-model="settings.project_wiki" type="text" class="input input-bordered w-full" />
            <div class="text-xs">The link to the project's wiki for documentation.</div>
          </div>
        </div>

        <div class="flex justify-between mb-2">
          <div class="label-text">codx-junior Path</div>
          <div class="w-2/3">
            <input v-model="settings.codx_path" type="text" class="input input-bordered w-full" />
            <div class="text-xs">The root directory where the project's code resides.</div>
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

      <div class="font-bold mb-2">Branches</div>
      <div class="ml-4 flex flex-col gap-2">
        <div>
          <div class="label-text">Project Branches</div>
          <div class="flex flex-col gap-2">
            <div v-for="(branch, index) in settings.project_branches" :key="index" class="flex justify-between items-center">
              <input v-model="settings.project_branches[index]" type="text" class="input input-bordered w-full" />
              <button @click="removeBranch(index)" class="btn btn-sm btn-error ml-2">Remove</button>
            </div>
            <button @click="addBranch" class="btn btn-sm btn-accent">Add Branch</button>
          </div>
        </div>
      </div>

      <div class="font-bold mb-2">AI</div>

      <div class="ml-4 flex flex-col gap-2">
        <div class="flex justify-between mb-2">
          <div class="label-text">Wiki Model</div>
          <div class="w-2/3">
            <ModelSelector v-model="settings.wiki_model" />
          </div>
        </div>
        <div class="flex justify-between mb-2">
          <div class="label-text">Embeddings Model</div>
          <div class="w-2/3">
            <ModelSelector v-model="settings.embeddings_model" />
          </div>
        </div>
        <div class="flex justify-between mb-2">
          <div class="label-text">Knowledge Search</div>
          <div class="w-2/3">
            <ModelSelector v-model="settings.rag_model" />
          </div>
        </div>
        <div class="flex justify-between mb-2">
          <div class="label-text">Reasoning Model</div>
          <div class="w-2/3">
            <ModelSelector v-model="settings.llm_model" />
          </div>
        </div>
      </div>

      <div class="font-bold mb-2">Knowledge</div>
      <div class="ml-4 flex flex-col gap-1">
        <div class="flex justify-between mb-2">
          <div class="label-text">Use Knowledge</div>
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
          <div class="label-text">RAG Distance</div>
          <div class="w-2/3">
            <input v-model="settings.knowledge_context_rag_distance" type="text" class="input input-bordered w-full" />
          </div>
        </div>
        <div class="flex justify-between mb-2">
          <div class="label-text">Cutoff Relevance Score</div>
          <div class="w-2/3">
            <input v-model="settings.knowledge_context_cutoff_relevance_score" type="text" class="input input-bordered w-full" />
          </div>
        </div>
        <div class="flex justify-between mb-2">
          <div class="label-text">Document Count</div>
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
          <div class="label-text">Query Subprojects</div>
          <div class="w-2/3">
            <input v-model="settings.knowledge_query_subprojects" type="checkbox" class="toggle" />
          </div>
        </div>

        <div class="flex justify-between mb-2">
          <div class="label-text">Enrich Documents</div>
          <div class="w-2/3">
            <input v-model="settings.knowledge_enrich_documents" type="checkbox" class="toggle" />
          </div>
        </div>
        <div class="flex justify-between mb-2">
          <div class="label-text">Extract Document Tags</div>
          <div class="w-2/3">
            <input v-model="settings.knowledge_extract_document_tags" type="checkbox" class="toggle" />
          </div>
        </div>
        <div class="flex justify-between mb-2">
          <div class="label-text">External Folders</div>
          <div class="w-2/3">
            <input v-model="settings.knowledge_external_folders" type="text" class="input input-bordered w-full" />
          </div>
        </div>

        <div class="flex justify-between mb-2">
          <div class="label-text">File Ignore</div>
          <div class="w-2/3">
            <input v-model="settings.knowledge_file_ignore" type="text" class="input input-bordered w-full" />
          </div>
        </div>
        <div class="flex justify-between mb-2">
          <div class="label-text">Search Type</div>
          <div class="w-2/3">
            <input v-model="settings.knowledge_search_type" type="text" class="input input-bordered w-full" />
          </div>
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
      this.settings.project_branches.push('')
    },
    removeBranch(index) {
      this.settings.project_branches.splice(index, 1)
    }
  }
}
</script>