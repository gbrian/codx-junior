<script setup>
import Chat from '../chat/Chat.vue'
import Editor from '../monaco/Editor.vue'
</script>

<template>
  <div class="w-full h-full flex flex-col gap-4">
    <!-- Header banner -->
    <div class="flex items-center gap-3 bg-gradient-to-r from-primary/20 to-transparent rounded-xl px-4 py-3">
      <div class="avatar placeholder">
        <div class="bg-primary text-primary-content rounded-full w-10 h-10 flex items-center justify-center">
          <i class="fa-solid fa-brain text-lg"></i>
        </div>
      </div>
      <div>
        <div class="font-bold text-base">{{ model.name || 'New Model' }}</div>
        <div class="text-xs text-base-content/50">{{ model.ai_provider || 'provider not set' }}</div>
      </div>
      <div class="ml-auto flex gap-2">
        <span :class="model.model_type === 'llm' ? 'badge badge-warning' : 'badge badge-info'" class="text-xs">
          <i :class="model.model_type === 'llm' ? 'fa-solid fa-brain' : 'fa-solid fa-file'" class="mr-1"></i>
          {{ model.model_type === 'llm' ? 'LLM' : 'Embeddings' }}
        </span>
      </div>
    </div>

    <!-- Tabs -->
    <div role="tablist" class="tabs tabs-border">
      <a role="tab" class="tab" :class="tabIx === 0 && 'tab-active'" @click="tabIx = 0">
        <i class="fa-solid fa-sliders mr-1"></i> Settings
      </a>
      <a role="tab" class="tab" :class="tabIx === 1 && 'tab-active'" @click="tabIx = 1">
        <i class="fa-solid fa-file-code mr-1"></i> Modelfile
      </a>
      <a role="tab" class="tab" :class="[tabIx === 2 && 'tab-active', model.model_type !== 'llm' && 'tab-disabled opacity-40']" @click="newChat">
        <i class="fa-solid fa-comment mr-1"></i> Test chat
      </a>
    </div>

    <!-- Settings tab -->
    <div class="w-full grow flex gap-4" v-if="tabIx === 0">
      <!-- Left column -->
      <div class="flex flex-col gap-3 w-1/2">
        <!-- Type & Provider -->
        <div class="flex flex-col gap-3 p-3 bg-base-200 rounded-lg">
          <div class="text-xs font-bold uppercase tracking-widest text-primary flex items-center gap-1">
            <i class="fa-solid fa-circle-nodes"></i> Classification
          </div>
          <div class="grid grid-cols-2 gap-3">
            <div class="form-control">
              <label class="label py-1">
                <span class="label-text text-xs">Model Type</span>
              </label>
              <select class="select select-bordered select-sm" v-model="model.model_type">
                <option value="llm">LLM</option>
                <option value="embeddings">Embeddings</option>
              </select>
            </div>
            <div class="form-control">
              <label class="label py-1">
                <span class="label-text text-xs">AI Provider</span>
              </label>
              <select class="select select-bordered select-sm" v-model="model.ai_provider" @change="onProviderChange">
                <option v-for="provider in aiProviders" :key="provider.name" :value="provider.name">
                  {{ provider.name }}
                </option>
              </select>
            </div>
          </div>
        </div>

        <!-- Identity -->
        <div class="flex flex-col gap-3 p-3 bg-base-200 rounded-lg">
          <div class="text-xs font-bold uppercase tracking-widest text-secondary flex items-center gap-1">
            <i class="fa-solid fa-tag"></i> Identity
          </div>

          <!-- Model Name (friendly) -->
          <div class="form-control">
            <label class="label py-1">
              <span class="label-text text-xs">Model Name (friendly name)</span>
            </label>
            <input class="input input-bordered input-sm" v-model="model.name" placeholder="Friendly display name" />
          </div>

          <!-- Provider model list dropdown -->
          <div class="form-control" v-if="currentProviderPriceList.length">
            <label class="label py-1">
              <span class="label-text text-xs">
                <i class="fa-solid fa-list mr-1 text-secondary"></i> Select Model from Provider List
              </span>
            </label>
            <select class="select select-bordered select-sm font-mono text-xs" v-model="selectedIdentityEntry" @change="applyIdentityEntry">
              <option :value="null">— choose a model —</option>
              <option v-for="entry in currentProviderPriceList" :key="entry.model_name" :value="entry">
                {{ entry.model_name }}
              </option>
            </select>
          </div>

          <!-- Manual override toggle -->
          <div class="form-control" v-if="currentProviderPriceList.length">
            <label class="label py-1 cursor-pointer justify-start gap-2">
              <input type="checkbox" class="toggle toggle-sm toggle-secondary" v-model="manualOverride" />
              <span class="label-text text-xs">Manually override AI provider's model name</span>
            </label>
          </div>

          <!-- AI Provider Model's Name input -->
          <div class="form-control">
            <label class="label py-1">
              <span class="label-text text-xs">AI Provider Model's Name (ai_model)</span>
            </label>
            <div v-if="manualOverride || !currentProviderPriceList.length">
              <input class="input input-bordered input-sm font-mono text-xs w-full" v-model="model.ai_model" placeholder="e.g. gpt-4o" />
            </div>
            <div v-else class="px-3 py-2 bg-base-300 rounded text-xs font-mono select-none">
              {{ model.ai_model || '— select from dropdown above —' }}
            </div>
          </div>

          <!-- Model URL -->
          <div class="form-control">
            <label class="label py-1">
              <span class="label-text text-xs"><i class="fa-solid fa-network-wired mr-1 text-info"></i> Model URL</span>
            </label>
            <input class="input input-bordered input-sm font-mono text-xs" v-model="model.url" placeholder="https://..." />
          </div>
        </div>

        <!-- Billing -->
        <div class="flex flex-col gap-3 p-3 bg-base-200 rounded-lg">
          <div class="text-xs font-bold uppercase tracking-widest text-warning flex items-center gap-1">
            <i class="fa-solid fa-coins"></i> Billing
          </div>

          <!-- Pricing preview -->
          <div v-if="selectedIdentityEntry" class="flex gap-3 px-2 py-1 bg-base-300 rounded text-xs">
            <span class="text-green-500">
              <i class="fa-solid fa-arrow-right-to-bracket mr-1"></i>
              Original: ${{ selectedIdentityEntry.input_price_per_1k_tokens }} / 1K in
            </span>
            <span class="text-blue-500">
              <i class="fa-solid fa-arrow-right-from-bracket mr-1"></i>
              Original: ${{ selectedIdentityEntry.output_price_per_1k_tokens }} / 1K out
            </span>
          </div>

          <!-- Price inputs -->
          <div class="grid grid-cols-2 gap-3">
            <div class="form-control">
              <label class="label py-1">
                <span class="label-text text-xs">
                  <i class="fa-solid fa-arrow-right-to-bracket mr-1 text-green-500"></i> Input / 1K tokens
                </span>
              </label>
              <div class="flex items-center gap-1">
                <input class="input input-bordered input-sm w-full" type="number" step="0.0001" v-model.number="model.input_k_tokens_cxjcoins" placeholder="0.0000" />
                <span class="text-xs text-base-content/50 shrink-0">cxj</span>
              </div>
            </div>
            <div class="form-control">
              <label class="label py-1">
                <span class="label-text text-xs">
                  <i class="fa-solid fa-arrow-right-from-bracket mr-1 text-blue-500"></i> Output / 1K tokens
                </span>
              </label>
              <div class="flex items-center gap-1">
                <input class="input input-bordered input-sm w-full" type="number" step="0.0001" v-model.number="model.output_k_tokens_cxjcoins" placeholder="0.0000" />
                <span class="text-xs text-base-content/50 shrink-0">cxj</span>
              </div>
            </div>
          </div>
        </div>

        <!-- LLM Parameters -->
        <div class="flex flex-col gap-3 p-3 bg-base-200 rounded-lg" v-if="currentModelIsLLM">
          <div class="text-xs font-bold uppercase tracking-widest text-info flex items-center gap-1">
            <i class="fa-solid fa-sliders"></i> LLM Parameters
          </div>
          <div class="grid grid-cols-2 gap-3">
            <div class="form-control">
              <label class="label py-1">
                <span class="label-text text-xs">Temperature</span>
              </label>
              <input type="number" class="input input-bordered input-sm" v-model.number="model.settings.temperature" placeholder="1.0" step="0.1" />
            </div>
            <div class="form-control">
              <label class="label py-1">
                <span class="label-text text-xs">Context length (KB)</span>
              </label>
              <input type="number" class="input input-bordered input-sm" v-model.number="model.settings.context_length" placeholder="Context length" step="1" />
            </div>
          </div>
          <div class="form-control">
            <label class="label py-1 cursor-pointer justify-start gap-3">
              <input type="checkbox" class="toggle toggle-sm toggle-primary" v-model="model.settings.merge_messages" />
              <span class="label-text text-xs">Merge messages</span>
            </label>
          </div>
        </div>

        <!-- Embeddings Parameters -->
        <div class="flex flex-col gap-3 p-3 bg-base-200 rounded-lg" v-if="!currentModelIsLLM">
          <div class="text-xs font-bold uppercase tracking-widest text-info flex items-center gap-1">
            <i class="fa-solid fa-sliders"></i> Embeddings Parameters
          </div>
          <div class="grid grid-cols-2 gap-3">
            <div class="form-control">
              <label class="label py-1">
                <span class="label-text text-xs">Vector Size</span>
              </label>
              <input type="number" class="input input-bordered input-sm" v-model.number="model.settings.vector_size" placeholder="1536" />
            </div>
            <div class="form-control">
              <label class="label py-1">
                <span class="label-text text-xs">Chunk Size</span>
              </label>
              <input type="number" class="input input-bordered input-sm" v-model.number="model.settings.chunk_size" placeholder="8190" />
            </div>
          </div>
        </div>
      </div>

      <!-- Right column: prompt template -->
      <div class="flex flex-col gap-3 w-1/2">
        <div class="flex flex-col gap-3 p-3 bg-base-200 rounded-lg h-full">
          <div class="text-xs font-bold uppercase tracking-widest text-accent flex items-center gap-1">
            <i class="fa-solid fa-scroll"></i> Prompt Configuration
          </div>
          <div class="form-control">
            <label class="label py-1">
              <span class="label-text text-xs">System Instructions</span>
            </label>
            <textarea class="textarea textarea-bordered text-xs h-24" v-model="model.system" placeholder="System instructions..."></textarea>
          </div>
          <div class="form-control grow flex flex-col">
            <label class="label py-1">
              <span class="label-text text-xs">Prompt Template</span>
            </label>
            <textarea class="textarea textarea-bordered text-xs grow" v-model="model.prompt_template" placeholder="Edit prompt template..."></textarea>
          </div>
          <div class="text-xs text-base-content/50 p-2 bg-base-300 rounded-lg">
            <div class="font-semibold mb-1">Available variables:</div>
            <ul class="list-disc list-inside pl-2 space-y-1">
              <li><strong class="text-primary">MESSAGE</strong> — Mandatory. The user's message or action.</li>
              <li><strong class="text-secondary">PROJECT_NAME</strong> — Optional. Current project name.</li>
            </ul>
          </div>
        </div>
      </div>
    </div>

    <!-- Modelfile tab -->
    <div class="w-full grow flex flex-col min-h-0" v-if="tabIx === 1">
      <div class="flex-1 min-h-0 overflow-hidden rounded-lg border border-base-300">
        <Editor
          v-model="model.model_file"
          language="dockerfile"
          :file-name="'Modelfile'"
          :render-side-by-side="false"
        />
      </div>
    </div>

    <!-- Test chat tab -->
    <div class="w-full grow flex flex-col min-h-0" v-if="tabIx === 2">
      <div v-if="!currentModelIsLLM" class="flex items-center gap-2 p-4 bg-warning/10 rounded-lg text-warning text-sm">
        <i class="fa-solid fa-triangle-exclamation"></i>
        Test chat is only available for LLM models
      </div>
      <div v-else-if="testChatError" class="flex items-center gap-2 p-4 bg-error/10 rounded-lg text-error text-sm">
        <i class="fa-solid fa-circle-exclamation"></i>
        {{ testChatError }}
      </div>
      <Chat v-else-if="testChat" class="w-full grow min-h-0" :chat="testChat" />
      <div v-else class="flex items-center justify-center gap-2 p-8 text-base-content/40">
        <span class="loading loading-spinner loading-sm"></span>
        Creating test chat...
      </div>
    </div>

    <!-- Actions -->
    <div class="flex justify-between items-center pt-1">
      <button class="btn btn-ghost btn-sm text-error" @click="$emit('delete', model)">
        <i class="fa-solid fa-trash-can mr-1"></i> Delete
      </button>
      <div class="flex gap-2">
        <button class="btn btn-primary btn-sm" @click="$emit('save', model)">
          <i class="fa-solid fa-floppy-disk mr-1"></i> Save
        </button>
        <button class="btn btn-ghost btn-sm" @click="$emit('cancel')">
          Cancel
        </button>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  props: ['model', 'aiProviders'],
  data() {
    return {
      tabIx: 0,
      testChat: null,
      testChatError: null,
      selectedIdentityEntry: null,
      manualOverride: false
    }
  },
  computed: {
    currentModelIsLLM() {
      return this.model?.model_type === 'llm'
    },
    currentProviderPriceList() {
      if (!this.model?.ai_provider || !this.aiProviders?.length) return []
      const provider = this.aiProviders.find(p => p.name === this.model.ai_provider)
      return provider?.price_list || []
    }
  },
  watch: {
    'model.ai_provider'() {
      this.selectedIdentityEntry = null
      this.manualOverride = false
      this.syncSelectedIdentity()
    },
    'model.name'(newName) {
      if (this.testChat && newName) {
        this.testChat.llm_model = newName
      }
    },
    currentProviderPriceList: {
      handler() {
        this.syncSelectedIdentity()
      },
      immediate: true
    }
  },
  mounted() {
    this.syncSelectedIdentity()
    this.initializeModelFile()
  },
  methods: {
    async newChat() {
      if (!this.currentModelIsLLM) return
      this.tabIx = 2
      if (this.testChat) return
      this.testChatError = null
      try {
        this.testChat = await this.$chats.createNewChat({
          name: `Test: ${this.model.name || 'model'}`,
          llm_model: this.model.name,
          temp: true,
          test: true
        })
        if (this.testChat) {
          this.testChat.llm_model = this.model.name
        }
      } catch (err) {
        this.testChatError = `Failed to create test chat: ${err.message}`
      }
    },
    onProviderChange() {
      this.selectedIdentityEntry = null
      this.manualOverride = false
    },
    applyIdentityEntry() {
      if (!this.selectedIdentityEntry) return
      const entry = this.selectedIdentityEntry

      if (!this.model.name) {
        this.model.name = entry.model_name
      }

      this.model.ai_model = entry.model_name
      this.model.input_k_tokens_cxjcoins = entry.input_price_per_1k_tokens
      this.model.output_k_tokens_cxjcoins = entry.output_price_per_1k_tokens
    },
    syncSelectedIdentity() {
      if (this.model?.ai_model && this.currentProviderPriceList.length) {
        const found = this.currentProviderPriceList.find(e => e.model_name === this.model.ai_model)
        if (found) {
          this.selectedIdentityEntry = found
        } else {
          this.manualOverride = true
        }
      }
    },
    initializeModelFile() {
      if (!this.model.model_file) {
        this.model.model_file = this.getDefaultModelfile()
      }
    },
    getDefaultModelfile() {
      return `# Modelfile for ${this.model.name || 'AI Model'}
FROM base

PARAMETER temperature ${this.model.settings?.temperature || 0.7}
PARAMETER context_length ${this.model.settings?.context_length || 2048}

SYSTEM ${this.model.system || 'You are a helpful assistant.'}`
    }
  }
}
</script>