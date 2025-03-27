<script setup>
</script>

<template>
  <div class="w-full h-full flex flex-col gap-2 p-4">
    <h1 class="text-2xl font-bold mb-4">AI Models</h1>
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <div
        v-for="model in aiModels"
        :key="model.name"
        class="click card border border-slate-300 bg-slate-800 text-white/80 p-4 shadow-sm flex flex-col justify-between"
        @click="editModel(model)"
      >
        <div class="overflow-hidden">
          <h2 class="font-bold text-lg text-primary">{{ model.name }}</h2>
          <span class="badge badge-xs badge-warning" v-if="model.model_type === 'llm'">
            <i class="fa-solid fa-brain"></i> LLM
          </span>
          <span class="badge badge-xs badge-info" v-else>
            <i class="fa-solid fa-file"></i> Embeddings
          </span>
          <table class="w-full">
            <tr>
              <td>Provider:</td>
              <td>{{ model.ai_provider }}</td>
            </tr>
            <tr v-if="model.model_type === 'llm'">
              <td>Temperature:</td>
              <td>{{ model.settings.temperature || '-' }}</td>
            </tr>
            <tr v-if="model.model_type === 'embeddings'">
              <td>Vector Size:</td>
              <td>{{ model.settings.vector_size || '-' }}</td>
            </tr>
            <tr v-if="model.model_type === 'embeddings'">
              <td>Chunk Size:</td>
              <td>{{ model.settings.chunk_size || '-' }}</td>
            </tr>
          </table>
        </div>
        <div class="flex gap-2 mt-4">
          <button class="btn btn-xs btn-circle btn-outline text-info" @click.stop="">
            <a :href="model.url" target="_blank" v-if="model.url"><i class="fa-solid fa-circle-info"></i></a>
          </button>
          <button class="btn btn-xs btn-circle btn-outline" @click.stop="editModel(model)">
            <i class="fa-solid fa-pen-to-square"></i>
          </button>
          <button class="btn btn-xs btn-circle btn-outline text-error" @click.stop="confirmDelete(model)">
            <i class="fa-solid fa-trash-can"></i>
          </button>
        </div>
      </div>
      <div class="card border-2 border-dashed border-base-300 p-4 flex justify-center items-center cursor-pointer" @click="editModel(null)">
        <span class="text-gray-500">Add New Model</span>
      </div>
    </div>
    <modal v-if="showDialog">
      <form class="flex flex-col gap-2" @submit.prevent="saveModel">
        <div class="form-control">
          <span class="label">Model Type</span>
          <select class="select select-bordered" v-model="currentModel.model_type">
            <option value="llm">LLM</option>
            <option value="embeddings">Embeddings</option>
          </select>
        </div>
        <div class="form-control">
          <span class="label">AI Provider</span>
          <select class="select select-bordered" v-model="currentModel.ai_provider">
            <option v-for="provider in aiProviders" :key="provider.name" :value="provider.name">
              {{ provider.name }}
            </option>
          </select>
        </div>
        <div class="divider"></div>
        <div class="form-control">
          <span class="label">Model Name</span>
          <input
            class="input input-bordered"
            v-model="currentModel.name"
            placeholder="Model Name"
          />
        </div>
        <div class="form-control">
          <span class="label">AI Provider Model's Name</span>
          <input
            class="input input-bordered"
            v-model="currentModel.ai_model"
            :placeholder="currentModel.name"
          />
        </div>
        <div class="form-control">
          <span class="label">Model url</span>
          <input
            class="input input-bordered"
            v-model="currentModel.url"
            placeholder="Url"
          />
        </div>
        <div class="form-control" v-if="currentModelIsLLM">
          <span class="label">Temperature</span>
          <input
            type="number"
            class="input input-bordered"
            v-model.number="currentModel.settings.temperature"
            placeholder="Temperature"
            step="0.1"
          />
        </div>
        <div class="form-control" v-if="!currentModelIsLLM">
          <span class="label">Vector Size</span>
          <input
            type="number"
            class="input input-bordered"
            v-model.number="currentModel.settings.vector_size"
            placeholder="Vector Size"
          />
        </div>
        <div class="form-control" v-if="!currentModelIsLLM">
          <span class="label">Chunk Size</span>
          <input
            type="number"
            class="input input-bordered"
            v-model.number="currentModel.settings.chunk_size"
            placeholder="Chunk Size"
          />
        </div>
        <div class="flex gap-2 justify-end">
          <button class="btn btn-primary" type="submit">Save</button>
          <button class="btn" @click="showDialog = false">Cancel</button>
        </div>
      </form>
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
          chunk_size: 8190
        }
      },
      modelToDelete: null
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
    }
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
      this.modelToDelete = model
      this.showDeleteDialog = true
    },
    deleteModel() {
      const index = this.aiModels.findIndex(m => m.name === this.modelToDelete.name)
      if (index !== -1) {
        this.aiModels.splice(index, 1)
      }
      this.showDeleteDialog = false
    }
  }
}
</script>