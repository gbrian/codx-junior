<script setup>
import UserSelector from './UserSelector.vue'
import LLMModelSelector from './LLMModelSelector.vue'
import ChatImageCarousel from './ChatImageCarousel.vue'
</script>

<template>
  <div class="flex justify-between items-end px-2 rounded-b-md">
    <ChatImageCarousel
      :images="images"
      @remove="$emit('remove-image', $event)"
      @preview="$emit('preview-image', $event)"
    />

    <!-- Loading state -->
    <span class="loading loading-dots loading-md btn btn-sm" v-if="waiting"></span>

    <div class="grow flex gap-2 items-end" v-else>
      <UserSelector
        class="dropdown-top"
        :selectedUser="selectedUser"
        :profiles="usersList"
        @user-changed="$emit('user-changed', $event)"
      />
      <LLMModelSelector
        class="dropdown-top"
        :selectedModel="selectedModel"
        :models="aiModels"
        @model-changed="$emit('model-changed', $event)"
      />

      <div class="grow"></div>

      <!-- Action buttons -->
      <div class="flex gap-2 items-center justify-end" v-if="!searching">
        <!-- Edit mode buttons -->
        <template v-if="isEditing">
          <button class="btn btn-sm btn-info btn-outline" @click="$emit('send')">
            <i class="fa-solid fa-save"></i>
            <div class="text-xs">Edit</div>
          </button>
          <button class="btn btn-sm btn-outline tooltip" data-tip="Cancel edit" @click="$emit('cancel-edit')">
            <i class="fa-regular fa-circle-xmark"></i>
          </button>
        </template>

        <!-- Normal mode buttons -->
        <template v-else>
          <button class="btn btn-sm btn-circle tooltip" data-tip="Search" @click="$emit('search-message')">
            <i class="fa-solid fa-magnifying-glass"></i>
          </button>     
          <button class="btn btn-sm btn-circle tooltip" data-tip="Add message" @click="$emit('add-message')">
            <i class="fa-solid fa-plus"></i>
          </button>
          <button
            class="btn btn-sm btn-circle tooltip"
            data-tip="Ask codx-junior"
            :class="isVoiceSession && 'btn-success animate-pulse'"
            @click="$emit('send')"
          >
            <i class="fa-solid fa-microphone-lines" v-if="isVoiceSession"></i>
            <i class="fa-solid fa-paper-plane" v-else></i>
          </button>
        </template>

        <!-- Extra options dropdown -->
        <div class="dropdown dropdown-top dropdown-end">
          <div tabindex="1" role="button" class="btn btn-sm m-1">
            <i class="fa-solid fa-ellipsis-vertical"></i>
          </div>
          <ul tabindex="1" class="dropdown-content menu bg-base-200 rounded-box z-[1] w-52 p-2 shadow gap-2">
            <li class="btn btn-sm tooltip" data-tip="Attach files" @click="$emit('attach-files')">
              <a><i class="fa-solid fa-paperclip"></i> Attach files</a>
            </li>
            <li class="btn btn-sm" @click="$emit('test-project')" v-if="hasTestScript">
              <a><i class="fa-solid fa-flask"></i> Test</a>
            </li>
            <li
              class="btn btn-sm tooltip"
              :class="isVoiceSession && 'btn-success'"
              :data-tip="voiceLanguageLabel"
              @click="$emit('toggle-voice')"
            >
              <a><i class="fa-solid fa-microphone-lines"></i> Voice mode</a>
            </li>
          </ul>
        </div>
      </div>

      <!-- Searching state -->
      <div class="flex gap-2 items-center justify-end py-2 animate-pulse" v-else>
        Searching...
      </div>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    waiting: Boolean,
    isEditing: Boolean,
    isVoiceSession: Boolean,
    searching: Boolean,
    hasTestScript: Boolean,
    selectedUser: Object,
    usersList: { type: Array, default: () => [] },
    selectedModel: String,
    aiModels: { type: Array, default: () => [] },
    images: { type: Array, default: () => [] },
    voiceLanguageLabel: String
  },
  emits: [
    'send', 'add-message', 'cancel-edit', 'user-changed', 'model-changed',
    'toggle-search', 'hide-all', 'attach-files', 'test-project',
    'toggle-voice', 'remove-image', 'preview-image'
  ]
}
</script>