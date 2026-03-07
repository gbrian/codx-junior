<script setup>
import AIModelSettings from './AIModelSettings.vue'
</script>

<template>
  <div class="w-full h-full flex flex-col gap-2 p-4">
    <h1 class="text-2xl font-bold mb-4">AI Models</h1>
    <div class="grid grid-cols-1 @md:grid-cols-2 @xl:grid-cols-3 gap-4">
      <div
        v-for="model in aiModels"
        :key="model.name"
        class="click card border border-slate-300 bg-slate-800 text-white/80 p-4 shadow-sm flex flex-col justify-between"
        @click="editModel(model)"
      >
        <div class="overflow-hidden">
          <h2 class="font-bold text-lg text-primary flex justify-between">
            <div>
              <span>{{ model.name }}</span><span class="text-secondary" v-if="model.ai_model && model.name != model.ai_model"> / {{ model.ai_model }}</span>
            </div>
          </h2>
          <span class="badge badge-xs badge-warning" v-if="model.model_type === 'llm'">
            <i class="fa-solid fa-brain"></i> LLM
          </span>
          <span class="badge badge-xs badge-info" v-else>
            <i class="fa-solid fa-file"></i> Embeddings
          </span>
          <table class="w-full">
            <thead>
              <tr>
                <td>Provider:</td>
                <td>{{ model.ai_provider }}</td>
              </tr>
              <tr v-if="model.model_type === 'llm'">
                <td>Temperature:</td>
                <td>{{ model.settings.temperature }}</td>
              </tr>
              <tr v-if="model.model_type === 'llm'">
                <td>Context:</td>
                <td>
                  <span v-if="model.settings.context_length">
                    {{ (model.settings.context_length || 0) }} KB
                  </span>
                </td>
              </tr>
              <tr v-if="model.model_type === 'llm' && model.settings.merge_messages">
                <td>Merge messages:</td>
                <td>{{ model.settings.merge_messages || '-' }}</td>
              </tr>
              <tr v-if="model.model_type === 'embeddings'">
                <td>Vector Size:</td>
                <td>{{ model.settings.vector_size || '-' }}</td>
              </tr>
              <tr v-if="model.model_type === 'embeddings'">
                <td>Chunk Size:</td>
                <td>{{ model.settings.chunk_size || '-' }}</td>
              </tr>
            </thead>
          </table>
        </div>
        <div class="flex gap-2 mt-4">
          <button class="btn btn-xs btn-circle btn-outline text-info" @click.stop="showModelInfo = model">            
            <i class="fa-solid fa-circle-info"></i>
          </button>
          <button class="btn btn-xs btn-circle btn-outline" @click.stop="editModel(model)">
            <i class="fa-solid fa-pen-to-square"></i>
          </button>
          <div class="grow"></div>
          <button class="btn btn-xs btn-circle btn-info btn-outline tooltip" 
            :class="model.loading && 'animate.pulse btn-warning'"
            data-tip="Reload model (depends on provider)"
            @click.stop="reloadModel(model)">
            <i class="fa-solid fa-arrows-rotate"></i>
          </button>
        </div>
      </div>
      <div class="card border-2 border-dashed border-base-300 p-4 flex justify-center items-center cursor-pointer" @click="editModel(null)">
        <span class="text-gray-500">Add New Model</span>
      </div>
    </div>
    <modal class="w-2/3 h-2/3 overflow-auto" v-if="showDialog">
      <AIModelSettings
        :aiProviders="aiProviders"
        :model="currentModel" 
        @save="saveModel"
        @cancel="showDialog = false"
        @delete="confirmDelete"
        />
    </modal>

    <modal class="w-1/3 h-2/3" close="true" @close="showModelInfo = null" v-if="showModelInfo">
      <div class="text-2xl">{{ showModelInfo.name }}</div>
      <pre class="overflow-auto">{{ showModelInfo.metadata?.info }}</pre>
    </modal>

    <modal v-if="showDeleteDialog">
      <div>
        <p>Are you sure you want to delete {{ modelToDelete.name }}?</p>
        <div class="modal-action">
          <button class="btn btn-error" @click="deleteModel">
            Confirm
          </button>
          <button class="btn" @click="showDeleteDialog = false">Cancel</button>
        </div>
      </div>
    </modal>
  </div>
</template>

<script>
export default {
  props: ['settings'],
  data() {
    return {
      showDialog: false,
      showDeleteDialog: false,
      currentModel: {
        name: '',
        ai_provider: '',
        model_type: 'llm',
        settings: {
          temperature: 1,
          vector_size: 1536,
          chunk_size: 8190,
        },
      },
      modelToDelete: null,
      showModelInfo: null
    }
  },
  computed: {
    aiModels() {
      return this.settings.ai_models
    },
    aiProviders() {
      return this.settings.ai_providers
    },
    currentModelIsLLM() {
      return this.currentModel?.model_type === 'llm'
    },
  },
  methods: {
    editModel(model) {
      if (!model) {
        model = { settings: {} }
        this.aiModels.push(model)
      }
      this.currentModel = model
      this.showDialog = true
    },
    saveModel() {
      this.showDialog = false
      // Add logic to save model
    },
    confirmDelete(model) {
      this.showDialog = false
      this.modelToDelete = model
      this.showDeleteDialog = true
    },
    deleteModel() {
      const index = this.aiModels.findIndex(m => m.name === this.modelToDelete.name)
      if (index !== -1) {
        this.aiModels.splice(index, 1)
      }
      this.showDeleteDialog = false
    },
    async reloadModel(model) {
      model.loading = true
      try {
        const info = await this.$storex.api.projects.ai.models.reload(model)
        model.metadata = {
          ...model.metadata ||{},       
          info
        }
        this.showModelInfo = model
      } finally {
        model.loading = false
      }
    }
  },
}
</script>