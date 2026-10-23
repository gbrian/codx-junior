<script setup>
import ChatLLMModelSelector from './ChatLLMModelSelector.vue'
import ChatProfileSelector from './ChatProfileSelector.vue'
import FileExplorerPanel from '../filebrowser/FileExplorerPanel.vue'
import ProjectDetailt from '../ProjectDetailt.vue'
</script>

<template>
  <div class="flex justify-between items-end px-2 rounded-b-md gap-2">
    <ChatImageCarousel
      :images="images"
      @remove="$emit('remove-image', $event)"
      @preview="$emit('preview-image', $event)"
    />

    <!-- Loading state -->
    <span class="loading loading-dots loading-md btn btn-sm" v-if="waiting"></span>

    <div class="grow flex gap-2 items-end" v-else>
      <!-- Selectors on the left -->
      <div class="flex gap-2 items-center flex-wrap" v-if="!readOnly">
        <!-- Project the message is addressed to.
             Messages can define their own project_id: the picker defaults to the
             chat's project and only overrides it when another project is chosen. -->
        <div class="shrink-0" :class="isMobile ? 'w-14' : 'w-36'" v-if="activeProject">
          <ProjectDetailt
            :model-value="activeProject"
            :iconify="isMobile"
            @select="onProjectSelected"
          />
        </div>

        <!-- Shown only when the message targets a project other than the chat's -->
        <button
          class="btn btn-sm btn-ghost btn-circle tooltip text-warning"
          data-tip="Back to the chat's project"
          aria-label="Back to the chat's project"
          v-if="isProjectOverridden"
          @click="onProjectSelected(chatProject)"
        >
          <i class="fa-solid fa-rotate-left text-xs"></i>
        </button>

        <ChatLLMModelSelector
          :selected-model="selectedModel"
          :models="aiModels"
          @model-changed="$emit('model-changed', $event)"
          v-if="aiModels?.length"
        />
        
        <ChatProfileSelector
          :profiles="profiles"
          :selected-profiles="selectedProfiles"
          @update:selected-profiles="$emit('profiles-selected', $event)"
          v-if="profiles?.length"
        />
      </div>

      <div class="grow"></div>

      <!-- Action buttons -->
      <div class="flex gap-2 items-center justify-end" v-if="!searching">
        <!-- Voice note recorder.
             Kept outside the edit/normal branches so an ongoing recording is
             always visible and cancellable. The recording itself is owned by
             ChatInputBox, which emits the resulting audio file as an attachment. -->
        <template v-if="isRecording">
          <span
            class="inline-flex items-center gap-1.5 px-2 py-1 rounded-full bg-error/10 text-error text-xs font-medium tabular-nums"
            role="status"
            aria-live="polite"
          >
            <span class="w-1.5 h-1.5 rounded-full bg-error animate-pulse"></span>
            {{ recordingLabel }}
          </span>
          <button
            class="btn btn-sm btn-circle btn-primary tooltip"
            data-tip="Attach voice note"
            aria-label="Attach voice note"
            @click="$emit('stop-voice-note')"
          >
            <i class="fa-solid fa-paperclip"></i>
          </button>
          <button
            class="btn btn-sm btn-circle btn-ghost tooltip text-error"
            data-tip="Cancel recording"
            aria-label="Cancel recording"
            @click="$emit('cancel-voice-note')"
          >
            <i class="fa-solid fa-xmark"></i>
          </button>
        </template>

        <!-- Start recording.
             Lives outside the edit/normal branches: an audio note can be recorded
             both when composing a new message and when editing an existing one. -->
        <button
          class="btn btn-sm btn-circle tooltip"
          data-tip="Record a voice note"
          aria-label="Record a voice note"
          :disabled="waiting || readOnly"
          v-if="!isRecording"
          @click="$emit('start-voice-note')"
        >
          <i class="fa-solid fa-microphone"></i>
        </button>

        <!-- Edit mode buttons -->
        <template v-if="isEditing">
          <!-- Disabled while recording: saving now would drop the audio note that
               is still being captured. -->
          <button
            class="btn btn-sm btn-info btn-outline"
            :disabled="isRecording"
            @click="$emit('send')"
          >
            <i class="fa-solid fa-save"></i>
            <div class="text-xs">Edit</div>
          </button>
          <button class="btn btn-sm btn-outline tooltip" data-tip="Cancel edit" @click="$emit('cancel-edit')">
            <i class="fa-regular fa-circle-xmark"></i>
          </button>
        </template>

        <!-- Normal mode buttons -->
        <template v-else>
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
          <ul tabindex="1" class="dropdown-content bg-base-100 menu bg-base-200 rounded-box z-[1] w-52 p-2 shadow gap-2">
            <li class="btn btn-sm tooltip" data-tip="Attach files" @click="openFileModal">
              <a><i class="fa-solid fa-paperclip"></i> Attach files</a>
            </li>
            <li
              class="btn btn-sm tooltip"
              data-tip="Upload files from your computer"
              @click="$refs.fileInput.click()"
            >
              <a><i class="fa-solid fa-cloud-arrow-up"></i> Upload files</a>
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

  <!-- Hidden input used to upload local files as message attachments -->
  <input
    ref="fileInput"
    type="file"
    multiple
    class="hidden"
    @change="onUploadFilesSelected"
  />

  <!-- File Explorer Modal.
       Rendered with Vue's built-in <Teleport> so the overlay is placed at the end
       of <body> (outside the composer's [data-chat-composer] region) while still
       being mounted/unmounted by v-if.

       The shared <modal> component moves its own DOM with a manual
       `$root.$el.appendChild(this.$el)` inside mounted(). Combined with v-if that
       leaks the moved node, leaving the dialog visible after it is closed. Teleport
       is Vue's supported way to relocate content and unmounts it cleanly.

       `@click.stop` on the overlay keeps the mobile composer's click-outside
       listener from collapsing it (which would unmount this toolbar + dialog
       mid-browse). `@close` is a Vue emit, not a DOM event, so stopping the DOM
       propagation does not prevent the dialog from closing.

       Sizing is scoped to `md:` — on mobile the dialog is a full-width bottom
       sheet, matching the rest of the app. -->
  <Teleport to="body">
    <div
      v-if="showFileModal"
      class="fixed inset-0 z-50 flex items-end justify-center p-0 md:items-center md:p-4"
      @click.stop
    >
      <!-- Backdrop -->
      <div
        class="absolute inset-0 bg-base-100/60 backdrop-blur-sm animate-in fade-in duration-200"
        @click="closeFileModal"
      ></div>

      <!-- Dialog -->
      <div
        class="relative z-10 bg-base-300 border border-base-content/10 flex flex-col w-full h-[85%] rounded-t-2xl pb-[env(safe-area-inset-bottom)] md:h-5/6 md:w-5/6 md:max-h-[90vh] md:pb-0 md:rounded-lg shadow-2xl animate-in fade-in zoom-in-95 duration-300"
        role="dialog"
        aria-modal="true"
      >
        <!-- Header -->
        <div class="flex items-center justify-between px-6 py-4 border-b border-base-content/5 shrink-0">
          <h2 class="font-bold text-lg flex items-center gap-2">
            <i class="fa-solid fa-folder-open text-primary"></i>
            Select Files to Attach
          </h2>
          <button
            class="btn btn-sm btn-ghost btn-circle"
            @click="closeFileModal"
            aria-label="Close modal"
          >
            <i class="fa-solid fa-xmark text-lg"></i>
          </button>
        </div>

        <!-- Body -->
        <div class="flex-1 min-h-0 overflow-hidden p-2">
          <FileExplorerPanel
            :root-path="projectRootPath"
            @open="onFileSelected"
          />
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script>
import ChatImageCarousel from './ChatImageCarousel.vue'

export default {
  components: {
    ChatImageCarousel,
    ChatLLMModelSelector,
    ChatProfileSelector,
    FileExplorerPanel,
    ProjectDetailt
  },
  props: {
    waiting: Boolean,
    isEditing: Boolean,
    isVoiceSession: Boolean,
    searching: Boolean,
    readOnly: Boolean,
    selectedModel: String,
    aiModels: { type: Array, default: () => [] },
    images: { type: Array, default: () => [] },
    voiceLanguageLabel: String,
    profiles: { type: Array, default: () => [] },
    selectedProfiles: { type: Array, default: () => [] },
    // ── Project the message is addressed to (message.project_id) ──
    // `project` is the effective target, `chatProject` the default one used to
    // detect when the message overrides the chat's project.
    project: { type: Object, default: null },
    chatProject: { type: Object, default: null },
    // ── Voice note recorder (state owned by ChatInputBox) ──
    isRecording: { type: Boolean, default: false },
    recordingLabel: { type: String, default: '' }
  },
  emits: [
    'send', 'cancel-edit', 'model-changed',
    'toggle-voice', 'remove-image', 'preview-image', 'profiles-selected',
    'file-selected', 'upload-files', 'project-changed',
    'start-voice-note', 'stop-voice-note', 'cancel-voice-note'
  ],
  data() {
    return {
      showFileModal: false
    }
  },
  computed: {
    isMobile() {
      return this.$ui.isMobile
    },
    // Message project when present, chat project otherwise: everything this
    // toolbar resolves (picker, file browsing) must follow the same target.
    activeProject() {
      return this.project || this.chatProject
    },
    projectRootPath() {
      return this.activeProject?.abs_project_path || '/'
    },
    // The composer defaults to the chat's project: only a real override is worth
    // showing the "back to the chat's project" reset action.
    isProjectOverridden() {
      const projectId = this.activeProject?.project_id
      const chatProjectId = this.chatProject?.project_id
      return !!projectId && !!chatProjectId && projectId !== chatProjectId
    }
  },
  beforeUnmount() {
    // Never leak the Escape listener if the composer unmounts while open
    // (e.g. the mobile composer collapses and unmounts this toolbar).
    document.removeEventListener('keydown', this.onModalKeydown)
  },
  methods: {
    onProjectSelected(project) {
      this.$emit('project-changed', project)
    },
    openFileModal() {
      this.showFileModal = true
      document.addEventListener('keydown', this.onModalKeydown)
    },
    closeFileModal() {
      this.showFileModal = false
      document.removeEventListener('keydown', this.onModalKeydown)
    },
    onModalKeydown(event) {
      if (event.key === 'Escape') this.closeFileModal()
    },
    onFileSelected(fileData) {
      this.$emit('file-selected', fileData.path)
      this.closeFileModal()
    },
    onUploadFilesSelected(event) {
      const files = Array.from(event.target.files || [])
      if (files.length) this.$emit('upload-files', files)
      event.target.value = ''
    }
  }
}
</script>