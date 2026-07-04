<script setup>
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

        <!-- Textarea -->
        <div class="form-control w-full">
          <label class="label">
            <span class="label-text font-semibold">Prompt Template</span>
            <span class="label-text-alt text-base-content/50">
              {{ characterCount }}/{{ maxCharacters }} characters
            </span>
          </label>
          <textarea
            v-model="settings.chat_global_instructions"
            @input="onPromptChange"
            :maxlength="maxCharacters"
            placeholder="Enter global chat prompt template..."
            class="textarea textarea-bordered h-64 font-mono text-sm resize-none focus:textarea-primary"
          ></textarea>
          <label class="label">
            <span class="label-text-alt text-base-content/60">
              Tip: Use variables like {user}, {context}, {date} for dynamic content
            </span>
          </label>
        </div>

        <!-- Preview Section -->
        <div class="divider my-2"></div>
        <details class="collapse border border-base-300 bg-base-200">
          <summary class="collapse-title font-semibold flex items-center gap-2">
            <i class="fa-solid fa-eye"></i>
            Preview
          </summary>
          <div class="collapse-content">
            <div class="bg-base-100 p-4 rounded-lg border border-base-300 font-mono text-sm whitespace-pre-wrap break-words">
              {{ settings.chat_global_instructions || 'No prompt configured' }}
            </div>
          </div>
        </details>
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
        Changes will be saved with global settings
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
      defaultPrompt: 'You are a helpful assistant. Provide clear and concise responses.'
    }
  },
  computed: {
    characterCount() {
      return this.settings.chat_global_instructions?.length || 0
    }
  },
  methods: {
    onPromptChange() {
      this.$emit('update:settings', this.settings)
    },
    resetToDefault() {
      this.settings.chat_global_instructions = this.defaultPrompt
      this.$ui.addNotification({ text: 'Reset to default prompt' })
    }
  }
}
</script>