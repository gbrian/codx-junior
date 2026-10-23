<script setup>
import WallAvatar from './WallAvatar.vue'
import ProjectDetailt from '../ProjectDetailt.vue'
import ChatProfileSelector from '@/components/chat/ChatProfileSelector.vue'
import ChatAttachmentPreview from '@/components/chat/ChatAttachmentPreview.vue'
import ChatIntelliSense from '@/components/chat/ChatIntelliSense.vue'
</script>

<template>
  <div class="flex gap-3 px-4 py-3" data-wall-composer>
    <WallAvatar :account="me" :size="10" />

    <div class="flex-1 min-w-0">
      <!-- Reply banner -->
      <div v-if="replyTo" class="text-sm text-base-content/50 mb-1 flex items-center gap-2">
        Reply to
        <span class="text-info">@{{ replyHandle }}</span>
        <button class="btn btn-ghost btn-xs" @click="$emit('cancel-reply')">Cancel</button>
      </div>

      <!-- Mention IntelliSense — floats above the input while typing "@" -->
      <div class="relative z-50">
        <ChatIntelliSense
          v-if="showIntelliSense"
          :suggestions="intelliSenseSuggestions"
          :active-index="intelliSenseIndex"
          :query="intelliSenseQuery"
          :search-controller="searchController"
          :progress="intelliSenseProgress"
          @select="onIntelliSenseSelect"
          @hover="intelliSenseIndex = $event"
          @accept-multi="onIntelliSenseAcceptMulti"
          @cancel="cancelIntelliSense"
        />
      </div>

      <!-- Text -->
      <textarea
        ref="input"
        v-model="text"
        rows="2"
        :placeholder="replyTo ? 'Write your reply…' : 'Share an update with your project…'"
        class="textarea textarea-ghost w-full text-base leading-relaxed resize-none px-0 focus:outline-none"
        aria-label="Compose update"
        @input="onInput"
        @keyup="onCaretMove"
        @click="onCaretMove"
        @keydown="onKeyDown"
        @paste="onPaste"
      ></textarea>

      <!-- Pasted / uploaded images and recorded audio notes -->
      <ChatAttachmentPreview
        v-if="attachments.length"
        :attachments="attachments"
        class="mt-2"
        @remove-attachment="removeAttachment"
        @update-attachment="onAttachmentUpdated"
      />

      <!-- Files referenced through @mentions -->
      <div v-if="files.length" class="flex flex-wrap gap-1 mt-2">
        <span v-for="file in files" :key="file" class="badge badge-ghost gap-1 max-w-full">
          <i class="fa-solid fa-file-code text-[10px]"></i>
          <span class="truncate max-w-[12rem]">{{ shortName(file) }}</span>
          <button type="button" class="hover:text-error" aria-label="Remove file" @click="removeFile(file)">
            <i class="fa-solid fa-xmark text-[10px]"></i>
          </button>
        </span>
      </div>

      <!-- Recording indicator -->
      <div v-if="recording" class="flex items-center gap-2 mt-2 text-sm text-error" role="status" aria-live="polite">
        <span class="w-2 h-2 rounded-full bg-error animate-pulse" aria-hidden="true"></span>
        <span>Recording audio… <span class="tabular-nums">{{ recordLabel }}</span></span>
        <button type="button" class="btn btn-ghost btn-xs" @click="stopRecording">Stop</button>
      </div>

      <!-- Toolbar -->
      <div class="flex items-center justify-between gap-3 mt-1 pt-2 border-t border-base-content/10">
        <div class="flex items-center gap-1 -ml-2">
          <button
            type="button"
            class="btn btn-ghost btn-sm btn-circle"
            title="Upload images or audio"
            aria-label="Upload images or audio"
            @click="$refs.fileInput.click()"
          >
            <i class="fa-regular fa-image"></i>
          </button>

          <!-- Audio note: record a voice message and attach it as base64 audio -->
          <button
            type="button"
            class="btn btn-sm btn-circle"
            :class="recording ? 'btn-error' : 'btn-ghost'"
            :title="recording ? 'Stop recording' : 'Record audio note'"
            :aria-label="recording ? 'Stop recording' : 'Record audio note'"
            :aria-pressed="recording"
            @click="toggleRecording"
          >
            <i :class="recording ? 'fa-solid fa-stop' : 'fa-solid fa-microphone'"></i>
          </button>

          <!-- Target project: the chat is created in whichever project is picked
               here (icon-only ProjectDetailt picker). -->
          <ProjectDetailt
            v-model="selectedProject"
            iconify
            :display-limit="4"
            class="!w-auto shrink-0"
          />

          <ChatProfileSelector
            v-if="selectedProject"
            :project="selectedProject"
            :selected-profiles="profiles"
            @profiles-changed="onProfilesChanged"
          />
        </div>

        <div class="flex items-center gap-3">
          <span class="text-xs tabular-nums" :class="overLimit ? 'text-error' : 'text-base-content/50'">
            {{ text.length }}/{{ max }}
          </span>
          <button class="btn btn-primary btn-sm rounded-full" :disabled="!canSubmit || submitting" @click="submit">
            <span v-if="submitting" class="loading loading-spinner loading-xs"></span>
            {{ replyTo ? 'Reply' : 'Post' }}
          </button>
        </div>
      </div>

      <!-- Hidden file input used to upload images / audio from the device.
           `accept` includes audio so the OS opens the file browser (albums /
           Downloads) instead of jumping straight to the camera, and NO `capture`
           attribute is set (that is what would force the camera). -->
      <input
        ref="fileInput"
        type="file"
        accept="image/*,audio/*"
        multiple
        class="hidden"
        @change="onFilesSelected"
      />
    </div>
  </div>
</template>

<script>
import ChatAttachment from '@/api/model/ChatAttachment.js'

export default {
  props: {
    me: { type: Object, required: true },
    replyTo: { type: Object, default: null },
    // Resolved author account of the post being replied to (posts only carry
    // `authorId`, so the parent resolves the handle and passes it in).
    replyAuthor: { type: Object, default: null },
    submitting: { type: Boolean, default: false },
    // Active project — used to seed the target project and the mention index.
    project: { type: Object, default: null }
  },
  emits: ['submit', 'cancel-reply'],
  data() {
    return {
      text: '',
      // Posts now drive an AI prompt, so the cap is generous (counter only).
      max: 2000,
      // Selected profiles ({ name, … }) kept for display + their names.
      profiles: [],
      profileNames: [],
      // Project the new chat will be created in (chosen with ProjectDetailt).
      selectedProject: null,
      // Project files referenced through @mentions.
      files: [],
      // ChatAttachment instances (pasted / uploaded images, recorded audio).
      attachments: [],
      cursorWord: {},
      intelliSenseSuggestions: [],
      intelliSenseIndex: 0,
      intelliSenseQuery: '',
      intelliSenseProgress: '',
      intelliSenseDebounce: null,
      intelliSenseDismissed: false,
      searchController: null,
      previousQuery: null,
      // ── Audio notes (MediaRecorder) ──────────────────────────
      recording: false,
      recordSeconds: 0,
      recordTimer: null,
      mediaRecorder: null,
      mediaStream: null,
      audioChunks: []
    }
  },
  computed: {
    overLimit() {
      return this.text.length > this.max
    },
    canSubmit() {
      return (this.text.trim().length > 0 || this.attachments.length > 0) && !this.overLimit
    },
    replyHandle() {
      return this.replyAuthor?.handle || this.replyTo?.author?.handle || 'unknown'
    },
    showIntelliSense() {
      return !!this.cursorWord.word?.startsWith('@') &&
        (this.intelliSenseSuggestions.length > 0 || !!this.searchController?.isSearching)
    },
    // mm:ss counter shown while recording.
    recordLabel() {
      const s = this.recordSeconds || 0
      const mm = String(Math.floor(s / 60)).padStart(2, '0')
      const ss = String(s % 60).padStart(2, '0')
      return `${mm}:${ss}`
    }
  },
  watch: {
    // Seed the target project from the active one, then keep the user's choice.
    project: {
      handler(newProject) {
        if (!this.selectedProject) this.selectedProject = newProject
      },
      immediate: true
    },
    // Profiles belong to a project — clear them when the target project changes.
    selectedProject() {
      this.profiles = []
      this.profileNames = []
    }
  },
  unmounted() {
    clearTimeout(this.intelliSenseDebounce)
    this.cancelIntelliSense()
    this.cleanupRecording()
  },
  methods: {
    // ── Profiles ──────────────────────────────────────────────
    onProfilesChanged(items) {
      this.profiles = Array.isArray(items) ? items : []
      this.profileNames = this.profiles.map(p => p.name || p)
    },

    // ── Images / audio files (paste + upload) ─────────────────
    async onFilesSelected(event) {
      const files = Array.from(event.target.files || [])
      await this.addMediaFiles(files)
      event.target.value = ''
    },
    async addMediaFiles(files) {
      for (const file of files) {
        const type = file?.type || ''
        if (!type.startsWith('image/') && !type.startsWith('audio/')) continue
        try {
          const attachment = await ChatAttachment.fromFile(file)
          this.attachments = [...this.attachments, attachment]
        } catch (error) {
          console.error('[WallComposer] Failed to read file', error)
          this.$ui?.addNotification?.({ text: 'Could not read file', type: 'error' })
        }
      }
    },
    async onPaste(event) {
      const items = event.clipboardData?.items || []
      const imageItems = [...items].filter(i => i.type?.startsWith('image/'))
      // Only intercept the paste when it actually carries images so pasting
      // text keeps working normally.
      if (!imageItems.length) return
      event.preventDefault()
      const files = imageItems.map(i => i.getAsFile()).filter(Boolean)
      await this.addMediaFiles(files)
    },
    removeAttachment(index) {
      this.attachments = this.attachments.filter((_, i) => i !== index)
    },
    onAttachmentUpdated({ index, attachment }) {
      this.attachments.splice(index, 1, attachment)
      this.attachments = [...this.attachments]
    },
    removeFile(file) {
      this.files = this.files.filter(f => f !== file)
    },
    shortName(file) {
      return file?.split('/').pop()
    },

    // ── Audio notes (record → base64 audio attachment) ────────
    async toggleRecording() {
      if (this.recording) this.stopRecording()
      else await this.startRecording()
    },
    async startRecording() {
      const Recorder = window.MediaRecorder
      if (!navigator.mediaDevices?.getUserMedia || !Recorder) {
        this.$ui?.addNotification?.({ text: 'Audio recording is not supported', type: 'error' })
        return
      }
      try {
        this.mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true })
        // Prefer a widely supported container; fall back to the browser default.
        const preferred = ['audio/webm', 'audio/mp4', 'audio/ogg']
          .find(t => Recorder.isTypeSupported?.(t))
        this.mediaRecorder = new Recorder(this.mediaStream, preferred ? { mimeType: preferred } : undefined)
        this.audioChunks = []
        this.mediaRecorder.ondataavailable = (e) => { if (e.data?.size) this.audioChunks.push(e.data) }
        this.mediaRecorder.onstop = () => this.finalizeRecording()
        this.mediaRecorder.start()
        this.recording = true
        this.recordSeconds = 0
        this.recordTimer = setInterval(() => { this.recordSeconds += 1 }, 1000)
      } catch (error) {
        console.error('[WallComposer] Failed to start recording', error)
        this.$ui?.addNotification?.({ text: 'Microphone access was denied', type: 'error' })
        this.cleanupRecording()
      }
    },
    stopRecording() {
      this.recording = false
      if (this.recordTimer) { clearInterval(this.recordTimer); this.recordTimer = null }
      // Stopping the recorder triggers `onstop` → `finalizeRecording`.
      if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
        this.mediaRecorder.stop()
      } else {
        this.cleanupRecording()
      }
    },
    async finalizeRecording() {
      const mimeType = this.mediaRecorder?.mimeType || 'audio/webm'
      const blob = new Blob(this.audioChunks, { type: mimeType })
      this.cleanupRecording()
      if (!blob.size) return
      const ext = mimeType.includes('mp4') ? 'm4a' : mimeType.includes('ogg') ? 'ogg' : 'webm'
      const stamp = new Date().toISOString().replace(/[:.]/g, '-')
      const file = new File([blob], `audio-note-${stamp}.${ext}`, { type: mimeType })
      try {
        const attachment = await ChatAttachment.fromFile(file)
        this.attachments = [...this.attachments, attachment]
      } catch (error) {
        console.error('[WallComposer] Failed to attach audio note', error)
        this.$ui?.addNotification?.({ text: 'Could not attach the audio note', type: 'error' })
      }
    },
    cleanupRecording() {
      if (this.recordTimer) { clearInterval(this.recordTimer); this.recordTimer = null }
      if (this.mediaStream) {
        this.mediaStream.getTracks().forEach(track => track.stop())
        this.mediaStream = null
      }
      this.mediaRecorder = null
      this.audioChunks = []
    },

    // ── Mention IntelliSense (mirrors the chat composer) ──────
    onInput() {
      this.updateCursorWord()
      this.scheduleIntelliSense()
    },
    onCaretMove() {
      this.updateCursorWord()
    },
    updateCursorWord() {
      const el = this.$refs.input
      if (!el) return
      const caretIndex = el.selectionStart
      const value = el.value
      let start = caretIndex
      while (start > 0 && /\S/.test(value[start - 1])) start--
      this.cursorWord = { word: value.slice(start, caretIndex), caretIndex }
    },
    scheduleIntelliSense() {
      if (this.intelliSenseDismissed) {
        const word = this.cursorWord.word
        if (word !== this.intelliSenseQuery) this.intelliSenseDismissed = false
      }
      clearTimeout(this.intelliSenseDebounce)
      this.intelliSenseDebounce = setTimeout(() => this.runIntelliSense(), 220)
    },
    async runIntelliSense() {
      if (this.intelliSenseDismissed) return
      const word = this.cursorWord.word
      if (!word?.startsWith('@')) { this.cancelIntelliSense(); return }
      const rawQuery = word.slice(1)
      if (!rawQuery || rawQuery.trim().length < 3) { this.cancelIntelliSense(); return }
      if (this.previousQuery !== rawQuery && this.searchController) this.cancelIntelliSense()
      this.previousQuery = rawQuery
      this.searchController = await this.$storex.projects.createSearchController()
      this.intelliSenseQuery = rawQuery
      this.intelliSenseIndex = 0
      this.searchController.onProgress = ({ stage, project }) => {
        this.intelliSenseProgress = `${stage}: ${project}`
      }
      try {
        await this.selectedProject?.$state?.searchMentions?.({
          query: rawQuery,
          limit: 10,
          controller: this.searchController,
          onResults: (results) => {
            if (!this.searchController?.isCancelled) {
              if (results.length === 1 && results[0].name === rawQuery) {
                this.onIntelliSenseSelect(results[0])
              } else {
                this.intelliSenseSuggestions = results
                this.intelliSenseIndex = 0
              }
            }
          }
        })
      } catch (error) {
        if (error.message !== 'Search cancelled') console.error('[WallComposer] Search error:', error)
      }
      this.intelliSenseProgress = ''
    },
    cancelIntelliSense() {
      if (this.searchController) { this.searchController.cancel(); this.searchController = null }
      this.intelliSenseSuggestions = []
      this.intelliSenseQuery = ''
      this.previousQuery = null
    },
    dismissIntelliSense() {
      this.intelliSenseDismissed = true
      this.intelliSenseSuggestions = []
    },
    insertMention(name) {
      const el = this.$refs.input
      const value = this.text
      const { caretIndex, word } = this.cursorWord
      const left = value.slice(0, caretIndex - word.length)
      const right = value.slice(caretIndex)
      const insert = '@' + name + ' '
      this.text = left + insert + right
      this.$nextTick(() => {
        if (!el) return
        const pos = (left + insert).length
        el.focus()
        el.setSelectionRange(pos, pos)
        this.cursorWord = { word: '', caretIndex: pos }
      })
    },
    onIntelliSenseSelect(suggestion) {
      // A file suggestion is attached to the post rather than inserted inline.
      if (suggestion?.file) {
        if (!this.files.includes(suggestion.file)) this.files = [...this.files, suggestion.file]
        const value = this.text
        const { caretIndex, word } = this.cursorWord
        this.text = value.slice(0, caretIndex - word.length) + value.slice(caretIndex)
        this.dismissIntelliSense()
        this.$refs.input?.focus()
        return
      }
      this.insertMention(suggestion.name)
      this.dismissIntelliSense()
    },
    onIntelliSenseAcceptMulti(items) {
      items.forEach(item => {
        if (item.file && !this.files.includes(item.file)) this.files = [...this.files, item.file]
      })
      const names = items.filter(i => !i.file).map(i => i.name)
      if (names.length) {
        const value = this.text
        const { caretIndex, word } = this.cursorWord
        const left = value.slice(0, caretIndex - word.length)
        const right = value.slice(caretIndex)
        this.text = left + names.map(n => '@' + n).join(' ') + ' ' + right
        this.$nextTick(() => this.$refs.input?.focus())
      }
      this.dismissIntelliSense()
    },
    onKeyDown(event) {
      if (!this.intelliSenseSuggestions.length) return
      if (event.key === 'Tab') {
        event.preventDefault()
        this.onIntelliSenseSelect(this.intelliSenseSuggestions[this.intelliSenseIndex])
        return
      }
      if (event.key === 'Escape') { this.dismissIntelliSense(); return }
      if (event.key === 'ArrowUp') {
        event.preventDefault()
        this.intelliSenseIndex = Math.max(0, this.intelliSenseIndex - 1)
        return
      }
      if (event.key === 'ArrowDown') {
        event.preventDefault()
        this.intelliSenseIndex = Math.min(this.intelliSenseSuggestions.length - 1, this.intelliSenseIndex + 1)
      }
    },

    // ── Submit ────────────────────────────────────────────────
    submit() {
      if (!this.canSubmit || this.submitting) return
      this.$emit('submit', {
        text: this.text.trim(),
        profiles: [...this.profileNames],
        files: [...this.files],
        attachments: this.attachments.map(a => (a.toJSON ? a.toJSON() : a)),
        // The project the chat must be created in.
        project: this.selectedProject
      })
      this.reset()
    },
    reset() {
      this.text = ''
      this.attachments = []
      this.files = []
      this.profiles = []
      this.profileNames = []
      this.cursorWord = {}
      this.cancelIntelliSense()
    }
  }
}
</script>