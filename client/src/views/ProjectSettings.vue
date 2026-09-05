<script setup>
import ModelSelector from '@/components/ai_settings/ModelSelector.vue'
import MCPServerListEditor from '@/components/project_settings/MCPServerListEditor.vue'
</script>

<template>
  <div class="w-full h-full container" v-if="settings">
    <div class="w-full h-full flex gap-0">
      <!-- Desktop Sidebar -->
      <aside class="hidden @md:flex w-64 bg-base-200 border-r border-base-300 flex-col">
        <div class="p-6 border-b border-base-300">
          <h1 class="text-lg font-bold text-base-content">{{ project.project_name }}</h1>
          <p class="text-xs text-base-content/60 mt-1">Project Settings</p>
        </div>

        <nav class="flex-1 overflow-y-auto p-4 space-y-2">
          <button
            v-for="item in navItems"
            :key="item.id"
            @click="activeTab = item.id"
            :class="[
              'w-full text-left px-4 py-3 rounded-lg transition-colors duration-200',
              'flex items-center gap-3',
              activeTab === item.id
                ? 'bg-primary text-primary-content font-medium'
                : 'text-base-content/70 hover:bg-base-300 hover:text-base-content'
            ]"
          >
            <i :class="`fa-solid ${item.icon} w-4 text-center`"></i>
            <span class="text-sm">{{ item.label }}</span>
          </button>
        </nav>

        <!-- Desktop Footer Actions -->
        <div class="p-4 border-t border-base-300 space-y-2">
          <button
            @click="reloadSettings"
            class="w-full btn btn-sm btn-ghost justify-start gap-2"
          >
            <i class="fa-solid fa-arrow-rotate-right text-xs"></i>
            <span>Reload</span>
          </button>
          <button
            @click="saveSettings"
            class="w-full btn btn-sm btn-primary justify-start gap-2"
          >
            <i class="fa-solid fa-floppy-disk text-xs"></i>
            <span>Save Changes</span>
          </button>
        </div>
      </aside>

      <!-- Mobile Drawer -->
      <div class="drawer @md:hidden w-full">
        <input id="project-settings-drawer" type="checkbox" class="drawer-toggle" v-model="drawerOpen" />
        <div class="drawer-content flex flex-col w-full h-full overflow-auto">
          <!-- Mobile Header with Menu Button -->
          <div class="border-b border-base-300 px-4 py-4 bg-base-100 flex items-center justify-between">
            <label for="project-settings-drawer" class="btn btn-ghost btn-sm btn-circle">
              <i class="fa-solid fa-bars text-lg"></i>
            </label>
            <h2 class="text-lg font-bold text-base-content flex-1 ml-4">
              {{ getActiveLabel() }}
            </h2>
          </div>

          <!-- Mobile Main Content -->
          <div class="flex-1 overflow-y-auto p-4">
            <div v-if="activeTab === 'general'">
              <div class="font-bold mb-4">Project</div>
              <div class="flex flex-col gap-4">
                <div>
                  <label class="label-text block mb-2">Project name</label>
                  <input v-model="settings.project_name" type="text" class="input input-bordered w-full" />
                  <div class="text-xs text-base-content/60 mt-1">The display name of your project.</div>
                </div>
                <div>
                  <label class="label-text block mb-2">Project icon</label>
                  <div class="flex gap-2 items-center">
                    <input v-model="settings.project_icon" type="text" class="input input-bordered flex-1" />
                    <img :src="settings.project_icon" alt="Icon" class="w-8 h-8 rounded-full" />
                  </div>
                </div>
                <div>
                  <label class="label-text block mb-2">Project path</label>
                  <input v-model="settings.project_path" type="text" class="input input-bordered w-full" />
                  <div class="text-xs text-base-content/60 mt-1">Absolute path: {{ settings.abs_project_path }}</div>
                  <div class="text-xs text-base-content/60">Project location: {{ settings.codx_path }}</div>
                </div>
                <div>
                  <label class="label-text flex items-center gap-2">
                    <input v-model="settings.project_wiki" type="checkbox" class="toggle" />
                    <span>Generate project's wiki</span>
                  </label>
                </div>
                <div>
                  <label class="label-text block mb-2">Wiki path</label>
                  <input v-model="settings.project_wiki_path" type="text" class="input input-bordered w-full" />
                  <div class="text-xs text-base-content/60 mt-1">Project's wiki folder.</div>
                </div>
                <div>
                  <label class="label-text block mb-2">Dependencies</label>
                  <input v-model="settings.project_dependencies" type="text" class="input input-bordered w-full" />
                  <div class="text-xs text-base-content/60 mt-1">List of external libraries or modules required.</div>
                </div>
              </div>

              <div class="divider"></div>

              <div class="font-bold mb-4">Project Branches</div>
              <div class="flex flex-col gap-2">
                <div class="text-xs text-base-content/60">Project branches are copies of the project's files to allow working in parallel</div>
                <button @click="addBranch" class="btn btn-sm btn-ghost justify-start">
                  <i class="fa-solid fa-plus"></i>
                  Add branch
                </button>
                <div v-for="(branch, index) in settings.project_branches" :key="index" class="flex gap-2 items-center">
                  <button @click="removeBranch(index)" class="btn btn-xs btn-error">
                    <i class="fa-solid fa-minus"></i>
                  </button>
                  <input v-model="settings.project_branches[index]" type="text" class="input input-bordered input-xs flex-1" />
                </div>
              </div>
            </div>

            <div v-if="activeTab === 'ai'">
              <div class="font-bold mb-4">AI Models</div>
              <div class="flex flex-col gap-4">
                <div>
                  <label class="label-text block mb-2">Wiki model</label>
                  <ModelSelector v-model="settings.wiki_model" />
                </div>
                <div>
                  <label class="label-text block mb-2">Embeddings model</label>
                  <ModelSelector v-model="settings.embeddings_model" />
                </div>
                <div>
                  <label class="label-text block mb-2">Knowledge search</label>
                  <ModelSelector v-model="settings.rag_model" />
                </div>
                <div>
                  <label class="label-text block mb-2">Reasoning model</label>
                  <ModelSelector v-model="settings.llm_model" />
                </div>
              </div>
            </div>

            <div v-if="activeTab === 'mcp'">
              <MCPServerListEditor v-model="settings.mcp_servers" />
            </div>

            <div v-if="activeTab === 'knowledge'">
              <div class="font-bold mb-4">Knowledge</div>
              <div class="flex flex-col gap-4">
                <div>
                  <label class="label-text flex items-center gap-2">
                    <input v-model="settings.use_knowledge" type="checkbox" class="toggle" />
                    <span>Use knowledge</span>
                  </label>
                  <div class="text-xs text-base-content/60 mt-1">Enable/Disable context enhancement with project files.</div>
                </div>
                <div>
                  <label class="label-text flex items-center gap-2">
                    <input v-model="settings.knowledge_generate_training_dataset" type="checkbox" class="toggle" />
                    <span>Training datasets</span>
                  </label>
                  <div class="text-xs text-base-content/60 mt-1">Enable/Disable generating training datasets for this project.</div>
                </div>
                <div>
                  <label class="label-text flex items-center gap-2">
                    <input v-model="settings.watching" type="checkbox" class="toggle" />
                    <span>Watching</span>
                  </label>
                </div>

                <div class="divider"></div>

                <div class="text-sm font-semibold">Context Settings</div>
                <div class="text-xs text-base-content/60 bg-base-300 p-3 rounded">
                  RAG engine search settings for context enhancement. Scoring knowledge helps finding the best resources to enrich AI context.
                  <ul class="pl-4 mt-2">
                    <li><strong>RAG distance (0-1):</strong> Filters after reading from RAG engine</li>
                    <li><strong>AI score (0-1):</strong> Post filter using AI to return a score based on how much value will add this document to the context</li>
                  </ul>
                </div>

                <div>
                  <label class="label-text block mb-2">RAG distance</label>
                  <input v-model="settings.knowledge_context_rag_distance" type="text" class="input input-bordered w-full" />
                </div>
                <div>
                  <label class="label-text block mb-2">Cutoff Relevance score</label>
                  <input v-model="settings.knowledge_context_cutoff_relevance_score" type="text" class="input input-bordered w-full" />
                </div>
                <div>
                  <label class="label-text block mb-2">Document count</label>
                  <input v-model="settings.knowledge_search_document_count" type="text" class="input input-bordered w-full" />
                </div>
                <div>
                  <label class="label-text block mb-2">HNSW M</label>
                  <input v-model="settings.knowledge_hnsw_M" type="text" class="input input-bordered w-full" />
                </div>

                <div class="divider"></div>

                <div>
                  <label class="label-text flex items-center gap-2">
                    <input v-model="settings.knowledge_query_subprojects" type="checkbox" class="toggle" />
                    <span>Query subprojects</span>
                  </label>
                </div>
                <div>
                  <label class="label-text flex items-center gap-2">
                    <input v-model="settings.knowledge_enrich_documents" type="checkbox" class="toggle" />
                    <span>Enrich documents</span>
                  </label>
                </div>
                <div>
                  <label class="label-text flex items-center gap-2">
                    <input v-model="settings.knowledge_extract_document_tags" type="checkbox" class="toggle" />
                    <span>Extract document tags</span>
                  </label>
                </div>
                <div>
                  <label class="label-text block mb-2">External folders</label>
                  <input v-model="settings.knowledge_external_folders" type="text" class="input input-bordered w-full" />
                </div>
                <div>
                  <label class="label-text block mb-2">File ignore</label>
                  <input v-model="settings.knowledge_file_ignore" type="text" class="input input-bordered w-full" />
                </div>
                <div>
                  <label class="label-text block mb-2">Search type</label>
                  <input v-model="settings.knowledge_search_type" type="text" class="input input-bordered w-full" />
                </div>
              </div>
            </div>

            <div v-if="activeTab === 'miscellaneous'">
              <div class="font-bold mb-4">Miscellaneous</div>
              <div>
                <label class="label-text flex items-center gap-2">
                  <input v-model="settings.save_mentions" type="checkbox" class="toggle" />
                  <span>Save file mentions as tasks</span>
                </label>
                <div class="text-xs text-base-content/60 mt-1">Enable/Disable saving file mentions as tasks in the "mentions" board.</div>
              </div>
            </div>

            <div v-if="activeTab === 'danger'">
              <div class="text-xl text-error font-bold mb-4">Danger Zone</div>
              <button class="btn btn-error w-full" @click="toggleConfirmDelete">
                <div class="flex gap-2" v-if="confirmDelete">
                  Confirm delete? <span class="hover:underline">YES</span> / <span class="hover:underline" @click.stop="confirmDelete = false">NO</span>
                </div>
                <div v-else>
                  <i class="fa-solid fa-trash"></i>
                  Delete project
                </div>
              </button>
            </div>
          </div>

          <!-- Mobile Footer Actions -->
          <div class="border-t border-base-300 px-4 py-3 bg-base-100 flex gap-2">
            <button
              @click="reloadSettings"
              class="btn btn-sm btn-ghost btn-circle"
              title="Reload"
            >
              <i class="fa-solid fa-arrow-rotate-right text-sm"></i>
            </button>
            <button
              @click="saveSettings"
              class="btn btn-sm btn-primary flex-1"
            >
              <i class="fa-solid fa-floppy-disk text-xs"></i>
              <span>Save</span>
            </button>
          </div>
        </div>

        <!-- Mobile Drawer Sidebar -->
        <div class="drawer-side z-40">
          <label for="project-settings-drawer" class="drawer-overlay"></label>
          <aside class="w-64 bg-base-200 border-r border-base-300 flex flex-col h-full">
            <div class="p-6 border-b border-base-300">
              <h1 class="text-lg font-bold text-base-content">{{ project.project_name }}</h1>
              <p class="text-xs text-base-content/60 mt-1">Settings</p>
            </div>

            <nav class="flex-1 overflow-y-auto p-4 space-y-2">
              <button
                v-for="item in navItems"
                :key="item.id"
                @click="selectTab(item.id)"
                :class="[
                  'w-full text-left px-4 py-3 rounded-lg transition-colors duration-200',
                  'flex items-center gap-3',
                  activeTab === item.id
                    ? 'bg-primary text-primary-content font-medium'
                    : 'text-base-content/70 hover:bg-base-300 hover:text-base-content'
                ]"
              >
                <i :class="`fa-solid ${item.icon} w-4 text-center`"></i>
                <span class="text-sm">{{ item.label }}</span>
              </button>
            </nav>
          </aside>
        </div>
      </div>

      <!-- Desktop Main Content -->
      <main class="hidden @md:flex flex-1 flex-col overflow-hidden">
        <div class="border-b border-base-300 px-8 py-4 bg-base-100">
          <h2 class="text-2xl font-bold text-base-content">
            {{ getActiveLabel() }}
          </h2>
          <p class="text-sm text-base-content/60 mt-1">{{ getActiveDescription() }}</p>
        </div>

        <div class="flex-1 overflow-y-auto p-8">
          <div v-if="activeTab === 'general'">
            <div class="font-bold mb-4 text-lg">Project</div>
            <div class="space-y-6 mb-8">
              <div class="flex justify-between items-start gap-6">
                <div class="flex-1">
                  <label class="label-text block font-semibold mb-2">Project name</label>
                  <p class="text-xs text-base-content/60">The display name of your project.</p>
                </div>
                <div class="w-96">
                  <input v-model="settings.project_name" type="text" class="input input-bordered w-full" />
                </div>
              </div>

              <div class="flex justify-between items-start gap-6">
                <div class="flex-1">
                  <label class="label-text block font-semibold mb-2">Project icon</label>
                  <p class="text-xs text-base-content/60">Icon URL for your project.</p>
                </div>
                <div class="w-96 flex gap-3 items-center">
                  <input v-model="settings.project_icon" type="text" class="input input-bordered flex-1" />
                  <img :src="settings.project_icon" alt="Icon" class="w-10 h-10 rounded-full" />
                </div>
              </div>

              <div class="flex justify-between items-start gap-6">
                <div class="flex-1">
                  <label class="label-text block font-semibold mb-2">Project path</label>
                  <p class="text-xs text-base-content/60">Absolute path: {{ settings.abs_project_path }}</p>
                  <p class="text-xs text-base-content/60">Project location: {{ settings.codx_path }}</p>
                </div>
                <div class="w-96">
                  <input v-model="settings.project_path" type="text" class="input input-bordered w-full" />
                </div>
              </div>

              <div class="flex justify-between items-start gap-6">
                <div class="flex-1">
                  <label class="label-text block font-semibold mb-2">Generate wiki</label>
                  <p class="text-xs text-base-content/60">Enable automatic wiki generation for this project.</p>
                </div>
                <div class="w-96">
                  <input v-model="settings.project_wiki" type="checkbox" class="toggle" />
                </div>
              </div>

              <div class="flex justify-between items-start gap-6">
                <div class="flex-1">
                  <label class="label-text block font-semibold mb-2">Wiki path</label>
                  <p class="text-xs text-base-content/60">Project's wiki folder.</p>
                </div>
                <div class="w-96">
                  <input v-model="settings.project_wiki_path" type="text" class="input input-bordered w-full" />
                </div>
              </div>

              <div class="flex justify-between items-start gap-6">
                <div class="flex-1">
                  <label class="label-text block font-semibold mb-2">Dependencies</label>
                  <p class="text-xs text-base-content/60">List of external libraries or modules required.</p>
                </div>
                <div class="w-96">
                  <input v-model="settings.project_dependencies" type="text" class="input input-bordered w-full" />
                </div>
              </div>
            </div>

            <div class="divider"></div>

            <div class="font-bold mb-4 text-lg">Project Branches</div>
            <div class="space-y-4">
              <p class="text-xs text-base-content/60">Project branches are copies of the project's files to allow working in parallel</p>
              <button @click="addBranch" class="btn btn-sm btn-outline">
                <i class="fa-solid fa-plus"></i>
                Add branch
              </button>
              <div v-for="(branch, index) in settings.project_branches" :key="index" class="flex gap-3 items-center">
                <button @click="removeBranch(index)" class="btn btn-sm btn-error">
                  <i class="fa-solid fa-minus"></i>
                </button>
                <input v-model="settings.project_branches[index]" type="text" class="input input-bordered flex-1" />
              </div>
            </div>
          </div>

          <div v-if="activeTab === 'ai'">
            <div class="space-y-6">
              <div class="flex justify-between items-start gap-6">
                <div class="flex-1">
                  <label class="label-text block font-semibold mb-2">Wiki model</label>
                  <p class="text-xs text-base-content/60">Model used for wiki generation.</p>
                </div>
                <div class="w-96">
                  <ModelSelector v-model="settings.wiki_model" />
                </div>
              </div>

              <div class="flex justify-between items-start gap-6">
                <div class="flex-1">
                  <label class="label-text block font-semibold mb-2">Embeddings model</label>
                  <p class="text-xs text-base-content/60">Model for generating document embeddings.</p>
                </div>
                <div class="w-96">
                  <ModelSelector v-model="settings.embeddings_model" />
                </div>
              </div>

              <div class="flex justify-between items-start gap-6">
                <div class="flex-1">
                  <label class="label-text block font-semibold mb-2">Knowledge search</label>
                  <p class="text-xs text-base-content/60">RAG model for knowledge retrieval.</p>
                </div>
                <div class="w-96">
                  <ModelSelector v-model="settings.rag_model" />
                </div>
              </div>

              <div class="flex justify-between items-start gap-6">
                <div class="flex-1">
                  <label class="label-text block font-semibold mb-2">Reasoning model</label>
                  <p class="text-xs text-base-content/60">Main LLM for reasoning and generation.</p>
                </div>
                <div class="w-96">
                  <ModelSelector v-model="settings.llm_model" />
                </div>
              </div>
            </div>
          </div>

          <div v-if="activeTab === 'mcp'">
            <MCPServerListEditor v-model="settings.mcp_servers" />
          </div>

          <div v-if="activeTab === 'knowledge'">
            <div class="space-y-6">
              <div class="flex justify-between items-start gap-6">
                <div class="flex-1">
                  <label class="label-text block font-semibold mb-2">Use knowledge</label>
                  <p class="text-xs text-base-content/60">Enable/Disable context enhancement with project files.</p>
                </div>
                <div class="w-96">
                  <input v-model="settings.use_knowledge" type="checkbox" class="toggle" />
                </div>
              </div>

              <div class="flex justify-between items-start gap-6">
                <div class="flex-1">
                  <label class="label-text block font-semibold mb-2">Training datasets</label>
                  <p class="text-xs text-base-content/60">Enable/Disable generating training datasets for this project.</p>
                </div>
                <div class="w-96">
                  <input v-model="settings.knowledge_generate_training_dataset" type="checkbox" class="toggle" />
                </div>
              </div>

              <div class="flex justify-between items-start gap-6">
                <div class="flex-1">
                  <label class="label-text block font-semibold mb-2">Watching</label>
                  <p class="text-xs text-base-content/60">Monitor project files for changes.</p>
                </div>
                <div class="w-96">
                  <input v-model="settings.watching" type="checkbox" class="toggle" />
                </div>
              </div>

              <div class="divider"></div>

              <div class="bg-base-200 p-6 rounded-lg">
                <h3 class="font-semibold mb-3">Context Settings</h3>
                <p class="text-xs text-base-content/60 mb-3">RAG engine search settings for context enhancement. Scoring knowledge helps finding the best resources to enrich AI context.</p>
                <ul class="text-xs text-base-content/60 space-y-2 pl-4">
                  <li><strong>RAG distance (0-1):</strong> Filters after reading from RAG engine</li>
                  <li><strong>AI score (0-1):</strong> Post filter using AI to return a score based on how much value will add this document to the context</li>
                </ul>
              </div>

              <div class="flex justify-between items-start gap-6">
                <div class="flex-1">
                  <label class="label-text block font-semibold mb-2">RAG distance</label>
                  <p class="text-xs text-base-content/60">Distance threshold (0-1)</p>
                </div>
                <div class="w-96">
                  <input v-model="settings.knowledge_context_rag_distance" type="text" class="input input-bordered w-full" />
                </div>
              </div>

              <div class="flex justify-between items-start gap-6">
                <div class="flex-1">
                  <label class="label-text block font-semibold mb-2">Cutoff Relevance score</label>
                  <p class="text-xs text-base-content/60">Relevance score threshold (0-1)</p>
                </div>
                <div class="w-96">
                  <input v-model="settings.knowledge_context_cutoff_relevance_score" type="text" class="input input-bordered w-full" />
                </div>
              </div>

              <div class="flex justify-between items-start gap-6">
                <div class="flex-1">
                  <label class="label-text block font-semibold mb-2">Document count</label>
                  <p class="text-xs text-base-content/60">Number of documents to retrieve</p>
                </div>
                <div class="w-96">
                  <input v-model="settings.knowledge_search_document_count" type="text" class="input input-bordered w-full" />
                </div>
              </div>

              <div class="flex justify-between items-start gap-6">
                <div class="flex-1">
                  <label class="label-text block font-semibold mb-2">HNSW M</label>
                  <p class="text-xs text-base-content/60">HNSW algorithm parameter</p>
                </div>
                <div class="w-96">
                  <input v-model="settings.knowledge_hnsw_M" type="text" class="input input-bordered w-full" />
                </div>
              </div>

              <div class="divider"></div>

              <div class="flex justify-between items-start gap-6">
                <div class="flex-1">
                  <label class="label-text block font-semibold mb-2">Query subprojects</label>
                  <p class="text-xs text-base-content/60">Include subproject knowledge in search.</p>
                </div>
                <div class="w-96">
                  <input v-model="settings.knowledge_query_subprojects" type="checkbox" class="toggle" />
                </div>
              </div>

              <div class="flex justify-between items-start gap-6">
                <div class="flex-1">
                  <label class="label-text block font-semibold mb-2">Enrich documents</label>
                  <p class="text-xs text-base-content/60">Enhance documents with additional metadata.</p>
                </div>
                <div class="w-96">
                  <input v-model="settings.knowledge_enrich_documents" type="checkbox" class="toggle" />
                </div>
              </div>

              <div class="flex justify-between items-start gap-6">
                <div class="flex-1">
                  <label class="label-text block font-semibold mb-2">Extract document tags</label>
                  <p class="text-xs text-base-content/60">Automatically extract tags from documents.</p>
                </div>
                <div class="w-96">
                  <input v-model="settings.knowledge_extract_document_tags" type="checkbox" class="toggle" />
                </div>
              </div>

              <div class="flex justify-between items-start gap-6">
                <div class="flex-1">
                  <label class="label-text block font-semibold mb-2">External folders</label>
                  <p class="text-xs text-base-content/60">Comma-separated list of external folders to index.</p>
                </div>
                <div class="w-96">
                  <input v-model="settings.knowledge_external_folders" type="text" class="input input-bordered w-full" />
                </div>
              </div>

              <div class="flex justify-between items-start gap-6">
                <div class="flex-1">
                  <label class="label-text block font-semibold mb-2">File ignore patterns</label>
                  <p class="text-xs text-base-content/60">Patterns for files to exclude from knowledge.</p>
                </div>
                <div class="w-96">
                  <input v-model="settings.knowledge_file_ignore" type="text" class="input input-bordered w-full" />
                </div>
              </div>

              <div class="flex justify-between items-start gap-6">
                <div class="flex-1">
                  <label class="label-text block font-semibold mb-2">Search type</label>
                  <p class="text-xs text-base-content/60">Knowledge search algorithm.</p>
                </div>
                <div class="w-96">
                  <input v-model="settings.knowledge_search_type" type="text" class="input input-bordered w-full" />
                </div>
              </div>
            </div>
          </div>

          <div v-if="activeTab === 'miscellaneous'">
            <div class="space-y-6">
              <div class="flex justify-between items-start gap-6">
                <div class="flex-1">
                  <label class="label-text block font-semibold mb-2">Save file mentions as tasks</label>
                  <p class="text-xs text-base-content/60">Enable/Disable saving file mentions as tasks in the "mentions" board.</p>
                </div>
                <div class="w-96">
                  <input v-model="settings.save_mentions" type="checkbox" class="toggle" />
                </div>
              </div>
            </div>
          </div>

          <div v-if="activeTab === 'danger'">
            <div class="bg-error/10 border border-error rounded-lg p-6">
              <h3 class="text-lg font-bold text-error mb-4">Delete Project</h3>
              <p class="text-sm text-base-content/70 mb-6">This action cannot be undone. Please be certain before deleting.</p>
              <button class="btn btn-error" @click="toggleConfirmDelete">
                <div class="flex gap-2" v-if="confirmDelete">
                  Confirm delete? <span class="hover:underline cursor-pointer">YES</span> / <span class="hover:underline cursor-pointer" @click.stop="confirmDelete = false">NO</span>
                </div>
                <div v-else>
                  <i class="fa-solid fa-trash"></i>
                  Delete project
                </div>
              </button>
            </div>
          </div>
        </div>
      </main>
    </div>
  </div>
</template>

<script>
export default {
  components: {
    MCPServerListEditor
  },
  data() {
    return {
      activeTab: 'general',
      settings: null,
      confirmDelete: false,
      drawerOpen: false,
      navItems: [
        { id: 'general', label: 'General', icon: 'fa-sliders' },
        { id: 'ai', label: 'AI Models', icon: 'fa-brain' },
        { id: 'mcp', label: 'MCP Servers', icon: 'fa-server' },
        { id: 'knowledge', label: 'Knowledge', icon: 'fa-lightbulb' },
        { id: 'miscellaneous', label: 'Miscellaneous', icon: 'fa-ellipsis' },
        { id: 'danger', label: 'Danger Zone', icon: 'fa-exclamation-triangle' }
      ]
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
      this.settings = await this.$project?.$api.settings.read()
      if (this.settings && !this.settings.mcp_servers) {
        this.settings.mcp_servers = []
      }
      this.confirmDelete = false
    },
    async saveSettings() {
      await this.$project.$api.settings.save(this.settings)
      await this.reloadSettings()
      this.$ui.addNotification({ text: 'Settings saved successfully' })
    },
    toggleConfirmDelete() {
      if (this.confirmDelete) {
        this.$emit('delete')
      } else {
        this.confirmDelete = true
      }
    },
    selectTab(tabId) {
      this.activeTab = tabId
      this.drawerOpen = false
    },
    getActiveLabel() {
      return this.navItems.find(item => item.id === this.activeTab)?.label || 'Settings'
    },
    getActiveDescription() {
      const descriptions = {
        general: 'Configure project name, path, wiki, and branches',
        ai: 'Select AI models for different project tasks',
        mcp: 'Configure Model Context Protocol servers',
        knowledge: 'Configure knowledge base and RAG settings',
        miscellaneous: 'Other project settings and preferences',
        danger: 'Irreversible actions for this project'
      }
      return descriptions[this.activeTab] || ''
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