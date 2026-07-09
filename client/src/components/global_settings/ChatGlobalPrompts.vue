<script setup>
import CodeViewer from '../CodeViewer.vue'
</script>

<template>
  <div class="w-full h-full flex flex-col gap-6">
    <!-- Chat Global Instructions Section -->
    <div class="card bg-base-100 border border-base-300">
      <div class="card-body">
        <h3 class="card-title text-lg flex items-center gap-2">
          <i class="fa-solid fa-comments text-primary"></i>
          Global Chat Prompt
        </h3>
        
        <div class="divider my-2"></div>

        <!-- Hint Section -->
        <div class="alert alert-info gap-3 mb-4">
          <i class="fa-solid fa-circle-info text-lg"></i>
          <div>
            <p class="font-semibold">A global prompt for all chat interactions</p>
            <p class="text-sm opacity-80">For more specific instructions, use Profiles to customize behavior per agent or workspace</p>
          </div>
        </div>

        <!-- CodeViewer for Prompt Editing -->
        <div class="form-control w-full">
          <label class="label">
            <span class="label-text font-semibold">Prompt Template</span>
            <span class="label-text-alt text-base-content/50">
              {{ characterCount }}/{{ maxCharacters }} characters
            </span>
          </label>
          
          <div class="border border-base-300 rounded-lg overflow-hidden h-80">
            <CodeViewer
              v-model="promptContent"
              :code="promptContent"
              language="markdown"
              file="prompt.md"
              :finished="true"
              :show-code-opened="true"
              @save-file="onCodeChange"
            />
          </div>

          <label class="label">
            <span class="label-text-alt text-base-content/60">
              Tip: Use variables like {user}, {context}, {date} for dynamic content
            </span>
          </label>
        </div>
      </div>
    </div>

    <!-- Reset to Default Button -->
    <div class="flex gap-2">
      <button
        @click="resetToDefault"
        class="btn btn-outline btn-sm gap-2"
      >
        <i class="fa-solid fa-rotate-left"></i>
        Reset to Default
      </button>
      <div class="flex-1"></div>
      <span class="text-xs text-base-content/50 self-center">
        Changes are saved automatically
      </span>
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
  },
  data() {
    return {
      maxCharacters: 5000,
      defaultPrompt: 'You are a helpful assistant. Provide clear and concise responses.',
      promptContent: ''
    }
  },
  computed: {
    characterCount() {
      return this.promptContent?.length || 0
    }
  },
  watch: {
    'settings.chat_global_instructions': {
      handler(newVal) {
        this.promptContent = newVal || ''
      },
      immediate: true
    }
  },
  methods: {
    onCodeChange({ content }) {
      this.promptContent = content
      this.settings.chat_global_instructions = content
      this.$emit('update:settings', this.settings)
    },
    resetToDefault() {
      this.promptContent = this.defaultPrompt
      this.settings.chat_global_instructions = this.defaultPrompt
      this.$emit('update:settings', this.settings)
      this.$ui.addNotification({ text: 'Reset to default prompt' })
    }
  }
}
</script>