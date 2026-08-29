<script setup>
import Editor from '@/components/monaco/Editor.vue'
import ChatProfileSelector from './ChatProfileSelector.vue'
import ChatLLMModelSelector from './ChatLLMModelSelector.vue'
</script>

<template>
  <div class="h-full flex flex-col gap-2 p-4 bg-base-100">
    
    <!-- Message info -->
    <div class="flex gap-4 text-xs text-base-content/60">
      <div class="flex items-center gap-2">
        <span class="font-semibold">Author:</span>
        <span>{{ message.user }}</span>
      </div>
      <div class="flex items-center gap-2">
        <span class="font-semibold">Updated:</span>
        <span>{{ formatDate(message.updated_at) }}</span>
      </div>
    </div>

    <!-- Profiles and Model Selector -->
    <div class="flex gap-2 items-center flex-wrap">
      <div class="flex-1 min-w-48">
        <ChatProfileSelector
          :project="chatProject"
          :selected-profiles="selectedProfiles"
          :use-modal="false"
          @profiles-changed="onProfilesChanged"
        />
      </div>
      <div class="w-48">
        <ChatLLMModelSelector
          :selected-model="selectedModel"
          @model-changed="onModelChanged"
        />
      </div>
    </div>

    <!-- Markdown editor -->
    <div class="flex-1 min-h-0 rounded-md border border-base-300 overflow-hidden">
      <Editor
        ref="editor"
        v-model="editorContent"
        language="markdown"
        :fileName="message.doc_id + '.md'"
        class="h-full"
        @save="onSave"
      />
    </div>

    <!-- Footer actions -->
    <div class="flex justify-between items-center gap-2">
      <div class="text-xs text-base-content/60">
        <span class="badge badge-sm">{{ characterCount }} characters</span>
      </div>
      <div class="flex gap-2">
        <button 
          class="btn btn-sm btn-outline" 
          @click="onDiscard"
        >
          Cancel
        </button>
        <button 
          class="btn btn-sm btn-primary" 
          @click="onSave"
          :disabled="!hasChanges && !hasProfileChanges && !hasModelChanges"
        >
          <i class="fa-solid fa-floppy-disk"></i>
          Save
        </button>
      </div>
    </div>
  </div>
</template>

<script>
import moment from 'moment'

export default {
  props: ['message'],
  emits: ['save', 'discard'],
  data() {
    return {
      editorContent: this.message?.content || '',
      originalContent: this.message?.content || '',
      selectedProfiles: this.message?.profiles || [],
      originalProfiles: [...(this.message?.profiles || [])],
      selectedModel: this.message?.llm_model || null,
      originalModel: this.message?.llm_model || null
    }
  },
  computed: {
    chatProject() {
      return this.$projects.allProjectsById[this.message.project_id]
        || this.$project
    },
    hasChanges() {
      return this.editorContent !== this.originalContent
    },
    hasProfileChanges() {
      return this.selectedProfiles.join(',') !== this.originalProfiles.join(',')
    },
    hasModelChanges() {
      return this.selectedModel !== this.originalModel
    },
    characterCount() {
      return this.editorContent.length
    }
  },
  methods: {
    formatDate(date) {
      return moment(date).format('DD/MMM HH:mm:ss')
    },
    onProfilesChanged(profiles) {
      this.selectedProfiles = profiles.map(p => p.name || p)
    },
    onModelChanged(modelName) {
      this.selectedModel = modelName
    },
    onSave() {
      if (!this.hasChanges && !this.hasProfileChanges && !this.hasModelChanges) return
      this.$emit('save', {
        doc_id: this.message.doc_id,
        content: this.editorContent,
        profiles: this.selectedProfiles,
        llm_model: this.selectedModel
      })
    },
    onDiscard() {
      this.$emit('discard')
    }
  },
  watch: {
    message(newMessage) {
      if (newMessage) {
        this.editorContent = newMessage.content || ''
        this.originalContent = newMessage.content || ''
        this.selectedProfiles = newMessage.profiles || []
        this.originalProfiles = [...(newMessage.profiles || [])]
        this.selectedModel = newMessage.llm_model || null
        this.originalModel = newMessage.llm_model || null
      }
    }
  }
}
</script>