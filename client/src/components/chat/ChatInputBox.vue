<script setup>
import ProjectResourcesAutoCompleteVue from '../autocomplete/ProjectResourcesAutoComplete.vue'
import EmojiPicker from './EmojiPicker.vue'
import ChatInputToolbar from './ChatInputToolbar.vue'
</script>

<template>
  <div
    class="border border-primary rounded-md bg-base-300 my-2 pb-2 flex shadow indicator w-full flex-col"
    :class="{
      'border-warning': isEditing,
      'bg-warning/10': draggingOver
    }"
    @dragover.prevent="draggingOver = true"
    @dragleave.prevent="draggingOver = false"
    @drop.prevent="onDrop"
    v-if="!readOnly"
  >
    <!-- Document search autocomplete -->
    <modal close="true" @close="$emit('close-knowledge')" v-if="showDocumentSearch">
        <ProjectResourcesAutoCompleteVue
        :project="chatProject"
        @select-result="$emit('add-document', $event)"
        @close="$emit('close-search')"
        v-if="showDocumentSearch"
        />
    </modal>

    <!-- Emoji picker -->
    <EmojiPicker
      class="px-2 py-1"
      :emoji-name="cursorWord.word"
      v-if="cursorWord.word?.startsWith(':')"
      @emoji="$emit('replace-emoji', $event)"
    />

    <!-- Contenteditable editor -->
    <div
      class="editor max-h-40 w-full px-2 py-1 overflow-auto text-wrap focus-visible:outline-none"
      :contenteditable="!waiting"
      ref="editor"
      @paste="$emit('paste', $event)"
      @keydown="$emit('keydown', $event)"
    ></div>

    <ChatInputToolbar
      :waiting="waiting"
      :isEditing="isEditing"
      :isVoiceSession="isVoiceSession"
      :searching="searching"
      :hasTestScript="hasTestScript"
      :selectedUser="selectedUser"
      :usersList="usersList"
      :selectedModel="selectedModel"
      :aiModels="aiModels"
      :images="images"
      :voiceLanguageLabel="voiceLanguageLabel"
      @send="$emit('send')"
      @search-message="$emit('search-message')"
      @add-message="$emit('add-message')"
      @cancel-edit="$emit('cancel-edit')"
      @user-changed="$emit('user-changed', $event)"
      @model-changed="$emit('model-changed', $event)"
      @toggle-search="$emit('toggle-search')"
      @hide-all="$emit('hide-all')"
      @attach-files="$emit('attach-files')"
      @test-project="$emit('test-project')"
      @toggle-voice="$emit('toggle-voice')"
      @remove-image="$emit('remove-image', $event)"
      @preview-image="$emit('preview-image', $event)"
    />
  </div>
</template>

<script>
export default {
  props: {
    waiting: Boolean,
    isEditing: Boolean,
    isVoiceSession: Boolean,
    searching: Boolean,
    readOnly: Boolean,
    hasTestScript: Boolean,
    showDocumentSearch: Boolean,
    chatProject: Object,
    selectedUser: Object,
    usersList: { type: Array, default: () => [] },
    selectedModel: String,
    aiModels: { type: Array, default: () => [] },
    images: { type: Array, default: () => [] },
    cursorWord: { type: Object, default: () => ({}) },
    voiceLanguageLabel: String
  },
  emits: [
    'send', 'add-message', 'cancel-edit', 'paste', 'keydown',
    'add-document', 'close-search', 'replace-emoji',
    'user-changed', 'model-changed', 'toggle-search', 'hide-all',
    'attach-files', 'test-project', 'toggle-voice',
    'remove-image', 'preview-image', 'drop'
  ],
  data() {
    return {
      draggingOver: false
    }
  },
  methods: {
    onDrop(e) {
      this.draggingOver = false
      this.$emit('drop', e)
    },
    // Expose editor ref for parent access
    getEditor() {
      return this.$refs.editor
    }
  }
}
</script>