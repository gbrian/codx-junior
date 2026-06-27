<script setup>
import ModelSelector from '@/components/ai_settings/ModelSelector.vue'
</script>

<template>
  <div class="flex flex-col gap-4">
    <div class="flex flex-col gap-4">
      <div class="flex flex-col gap-2 text-xs">
        <div class="text-xl font-bold">Global</div>
        <div class="ml-6 p-2 flex flex-col gap-2">
          <div class="flex items-center">
            <span class="w-1/4">codx-junior Avatar:</span>
            <input v-model="settings.codx_junior_avatar" type="text" class="input input-bordered flex-grow" />
          </div>
          <div class="flex items-center">
            <span class="w-1/4">Projects Root Path:</span>
            <input v-model="settings.projects_root_path" type="text" class="input input-bordered flex-grow" />
          </div>
        </div>
      </div>
      <div class="flex flex-col gap-2 text-xs">
        <div class="text-xl font-bold">Git</div>
        <div class="ml-6 p-2 flex flex-col gap-2">
          <div class="flex items-center">
            <span class="w-1/4">Username:</span>
            <input v-model="settings.git.username" type="text" class="input input-bordered flex-grow" />
          </div>
          <div class="flex items-center">
            <span class="w-1/4">Email:</span>
            <input v-model="settings.git.email" type="text" class="input input-bordered flex-grow" />
          </div>
        </div>
      </div>
      <div class="flex flex-col gap-2 text-xs">
        <div class="text-xl font-bold">AI</div>
        <div class="ml-6 p-2 flex flex-col gap-2">
          <div class="flex items-center">
            <span class="w-1/4">Log AI:</span>
            <input v-model="settings.log_ai" type="checkbox" class="checkbox" />
          </div>
          <div class="font-bold">Embeddings</div>
          <div class="text-xs">Converts project's documents into embeddings for knowledge search</div>
          <div class="flex flex-col gap-2">
            <div class="flex items-center">
              <span class="p-6 w-1/4">Model:</span>
              <ModelSelector v-model="settings.embeddings_model" />
            </div>
          </div>
          <div class="font-bold">Knowledge search</div>
          <div class="text-xs">Scores knowledge results based on user's request</div>
          <div class="flex flex-col gap-2">
            <div class="flex items-center">
              <span class="p-6 w-1/4">Model:</span>
              <ModelSelector v-model="settings.rag_model" />
            </div>
          </div>
          <div class="font-bold">Reasoning</div>
          <div class="text-xs">Default Reasoning model</div>
          <div class="flex flex-col gap-2">
            <div class="flex items-center">
              <span class="p-6 w-1/4">Model:</span>
              <ModelSelector v-model="settings.llm_model" />
            </div>
          </div>
          <div class="font-bold">WIKI</div>
          <div class="text-xs">Generates wiki documents from project's knowledge</div>
          <div class="flex flex-col gap-2">
            <div class="flex items-center">
              <span class="p-6 w-1/4">Model:</span>
              <ModelSelector v-model="settings.wiki_model" />
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    settings: {
      type: Object,
      required: true
    }
  }
}
</script>