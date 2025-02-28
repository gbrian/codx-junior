<script setup>
</script>

<template>
  <div class="w-full h-full flex flex-col gap-2 p-4">
    <h1 class="text-2xl font-bold mb-4">AI Models</h1>
    <div class="overflow-x-auto">
      <table class="table w-full">
        <thead>
          <tr>
            <th>Name</th>
            <th>Provider</th>
            <th>Type</th>
            <th>Temperature</th>
            <th>Vector Size</th>
            <th>Chunk Size</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="model in aiModels" :key="model.name" class="click" @click="editModel(model)">
            <td class="font-bold">
              {{ model.name }}
            </td>
            <td>{{ model.ai_provider }}</td>
            <td :title="model.model_type">
              <span class="text-warning" v-if="model.model_type === 'llm'"><i class="fa-solid fa-brain"></i></span>
              <span class="text-info" v-else><i class="fa-solid fa-file"></i></span>
            </td>
            <td>{{ model.settings.temperature || '-' }}</td>
            <td>{{ model.settings.vector_size || '-' }}</td>
            <td>{{ model.settings.chunk_size || '-' }}</td>
            <td class="flex gap-2">
              <button class="btn btn-xs btn-circle btn-ghost text-info" @click.stop="">
                <a :href="model.url" target="_blank" v-if="model.url"><i class="fa-solid fa-circle-info"></i></a>
              </button>
              <button class="btn btn-xs btn-circle btn-ghost" @click.stop="editModel(model)">
                <i class="fa-solid fa-pen-to-square"></i>
              </button>
              <button class="btn btn-xs btn-circle btn-ghost text-error" @click.stop="confirmDelete(model)">
                <i class="fa-solid fa-trash-can"></i>
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <div class="flex justify-end">
      <button class="btn btn-sm mt-2" @click="editModel()">
        Add New
      </button>
    </div>

    <modal v-if="showDialog">
      <form @submit.prevent="saveModel">
        <div class="form-control">
          <label class="label">Model Name</label>
          <input
            class="input input-bordered"
            v-model="currentModel.name"
            placeholder="Model Name"
          />
        </div>
        <div class="form-control">
          <label class="label">AI Provider</label>
          <input
            class="input input-bordered"
            v-model="currentModel.ai_provider"
            placeholder="AI Provider"
          />
        </div>
        <div class="form-control">
          <label class="label">Model url</label>
          <input
            class="input input-bordered"
            v-model="currentModel.url"
            placeholder="Url"
          />
        </div>
        <div class="form-control">
          <label class="label">Model Type</label>
          <select class="select select-bordered" v-model="currentModel.model_type">
            <option value="llm">LLM</option>
            <option value="embeddings">Embeddings</option>
          </select>
        </div>
        <div class="form-control" v-if="currentModelIsLLM">
          <label class="label">Temperature</label>
          <input
            type="number"
            class="input input-bordered"
            v-model.number="currentModel.settings.temperature"
            placeholder="Temperature"
            step="0.1"
          />
        </div>
        <div class="form-control" v-if="!currentModelIsLLM">
          <label class="label">Vector Size</label>
          <input
            type="number"
            class="input input-bordered"
            v-model.number="currentModel.settings.vector_size"
            placeholder="Vector Size"
          />
        </div>
        <div class="form-control" v-if="!currentModelIsLLM">
          <label class="label">Chunk Size</label>
          <input
            type="number"
            class="input input-bordered"
            v-model.number="currentModel.settings.chunk_size"
            placeholder="Chunk Size"
          />
        </div>
        <div class="flex gap-2">
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
    }
  },
  computed: {
    aiModels() {
      return this.$storex.api.globalSettings?.ai_models
    },
    currentModelIsLLM () {
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
    },
  },
}
</script>