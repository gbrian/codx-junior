<script setup>
</script>

<template>
  <div class="w-full h-full flex flex-col gap-2">
    <div class="w-full h-full flex gap-2">
      <!-- Column for existing settings -->
      <div class="flex flex-col gap-2 w-1/2">
        <div class="form-control">
          <span class="label">Model Type</span>
          <select class="select select-bordered" v-model="model.model_type">
            <option value="llm">LLM</option>
            <option value="embeddings">Embeddings</option>
          </select>
        </div>
        <div class="form-control">
          <span class="label">AI Provider</span>
          <select class="select select-bordered" v-model="model.ai_provider">
            <option v-for="provider in aiProviders" :key="provider.name" :value="provider.name">
              {{ provider.name }}
            </option>
          </select>
        </div>
        <div class="divider"></div>
        <div class="form-control">
          <span class="label">Model Name</span>
          <input class="input input-bordered" v-model="model.name" placeholder="Model Name" />
        </div>
        <div class="form-control">
          <span class="label">AI Provider Model's Name</span>
          <input class="input input-bordered" v-model="model.ai_model" :placeholder="model.name" />
        </div>
        <div class="form-control">
          <span class="label">Model url</span>
          <input class="input input-bordered" v-model="model.url" placeholder="Url" />
        </div>
        <div class="form-control" v-if="currentModelIsLLM">
          <span class="label">Merge messages</span>
          <input type="checkbox" class="toggle" v-model.number="model.settings.merge_messages" />
        </div>
        <div class="form-control" v-if="currentModelIsLLM">
          <span class="label">Temperature</span>
          <input type="number" class="input input-bordered" v-model.number="model.settings.temperature" placeholder="Temperature" step="0.1" />
        </div>
        <div class="form-control" v-if="currentModelIsLLM">
          <span class="label">Context length (KB)</span>
          <input type="number" class="input input-bordered" v-model.number="model.settings.context_length" placeholder="Context length" step="1" />
        </div>
        <div class="form-control" v-if="!currentModelIsLLM">
          <span class="label">Vector Size</span>
          <input type="number" class="input input-bordered" v-model.number="model.settings.vector_size" placeholder="Vector Size" />
        </div>
        <div class="form-control" v-if="!currentModelIsLLM">
          <span class="label">Chunk Size</span>
          <input type="number" class="input input-bordered" v-model.number="model.settings.chunk_size" placeholder="Chunk Size" />
        </div>
      </div>
      <!-- Column for prompt_template -->
      <div class="flex flex-col gap-2 w-1/2">
        <div class="form-control h-full flex flex-col">
          <span class="label">System</span>
          <textarea class="h-20 textarea textarea-bordered" v-model="model.system" placeholder="Edit model system instructions"></textarea>
          <span class="label">Prompt Template</span>
          <textarea class="grow textarea textarea-bordered" v-model="model.prompt_template" placeholder="Edit prompt template"></textarea>
          
          <div class="text-xs text-gray-500 mt-2">
            Available variables:
            <ul class="list-disc list-inside pl-4">
              <li><strong>MESSAGE</strong>: Mandatory. Represents the user's message or action.</li>
              <li><strong>PROJECT_NAME</strong>: Optional. The name of the current project.</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
    <div class="flex gap-2">
      <button class="btn btn-error" @click="$emit('delete', model)">Delete</button>
      <div class="grow"></div>
      <button class="btn btn-primary" @click="$emit('save', model)">Save</button>
      <button class="btn" @click="$emit('cancel')">Cancel</button>
    </div>
  </div>  
</template>

<script>
export default {
  props: ['model', 'aiProviders'],
  computed: {
    currentModelIsLLM() {
      return this.model?.model_type === 'llm'
    }
  },
}
</script>