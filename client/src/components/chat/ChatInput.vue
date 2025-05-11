<script setup>
import { API } from '../../api/api'
</script>

<template>
  <div class="w-full flex flex-col gap-2">
    <div class="dropdown dropdown-top dropdown-open mb-1" v-if="showTermSearch">
      <button class="btn bg-base-300 w-fit p-2">
        <div class="flex items-center text-sky-600">
          <i class="fa-solid fa-at"></i>
          <input
            type="text"
            class="input input-xs bg-transparent"
            placeholder="search term..."
            v-model="termSearchQuery"
            ref="termSearcher"
            @keydown.down.stop="onSelNext"
            @keydown.up.stop="onSelPrev"
            @keydown.enter.stop="addSearchTerm(searchTerms[searchTermSelIx])"
            @keydown.esc="closeTermSearch"
          />
          <button
            class="btn btn-xs btn-circle btn-outline btn-error ml-2"
            v-if="termSearchQuery"
          >
            <i class="fa-solid fa-circle-xmark"></i>
          </button>
        </div>
      </button>
      <ul
        class="dropdown-content menu p-2 shadow bg-base-300 rounded-box w-fit"
        v-if="searchTerms"
      >
        <li v-for="(term, ix) in searchTerms" :key="term.key">
          <a @click="addSearchTerm(term)">
            <div :class="[searchTermSelIx === ix ? 'underline' : '']">
              <span class="text-sky-600 font-bold">@{{ term.key }}</span>
              <span class="text-xs">({{ term.file.split('/').reverse()[0] }})</span>
            </div>
          </a>
        </li>
      </ul>
    </div>
    <div
      :class="[
        'flex bg-base-300 border rounded-md shadow indicator w-full',
        multiline ? 'flex-col' : '',
        editMessage && 'border-warning',
        onDraggingOverInput ? 'bg-warning/10' : ''
      ]"
      @dragover.prevent="onDraggingOverInput = true"
      @dragleave.prevent="onDraggingOverInput = false"
      @drop.prevent="onDrop"
    >
      <div
        :class="[
          'max-h-40 w-full px-2 py-1 overflow-auto text-wrap focus-visible:outline-none'
        ]"
        :contenteditable="!waiting"
        ref="editor"
        @input="onMessageChange"
        @paste="onContentPaste"
        @keydown.esc.stop="onResetEdit"
      >
      </div>
      <div class="flex justify-between items-end px-2 py-2">
        <div class="carousel rounded-box">
          <div
            class="carousel-item relative click flex flex-col"
            v-for="(image, ix) in images"
            :key="image.src"
          >
            <div
              class="bg-contain bg-no-repeat bg-center w-10 h-10 lg:h-20 lg:w-20 bg-base-300 mr-4"
              :style="`background-image: url(${image.src})`"
              @click="imagePreview = image"
            >
            </div>
            <p class="text-xs">{{ image.alt.slice(0, 10) }}</p>
            <button
              class="btn btn-xs btn-circle btn-error absolute right-0 top-0"
              @click="removeImage(ix)"
            >
              X
            </button>
          </div>
        </div>
        <span class="loading loading-dots loading-md btn btn-sm" v-if="waiting"></span>
        <div class="flex gap-1 items-center justify-end" v-else>
          <button
            class="btn btn-sm btn-info btn-outline"
            @click="sendMessage"
            v-if="editMessage"
          >
            <i class="fa-solid fa-save"></i>
            <div class="text-xs" v-if="editMessage">Edit</div>
          </button>
          <button
            class="btn btn-sm btn-outline tooltip"
            data-tip="Save changes"
            @click="onResetEdit"
            v-if="editMessage"
          >
            <i class="fa-regular fa-circle-xmark"></i>
          </button>
          <button class="btn btn btn-sm btn-circle btn-outline tooltip"
            data-tip="Ask codx-junior"
            :class="isVoiceSession && 'btn-success animate-pulse'"
            @click="sendMessage" 
            v-if="!editMessage">
            <i class="fa-solid fa-microphone-lines" v-if="isVoiceSession"></i>
            <i :class="$projects.chatModes[chat.mode].icon" v-else></i>
          </button>
          <button
            class="btn btn-sm btn-outline tooltip btn-warning"
            data-tip="Make code changes"
            @click="improveCode"
            v-if="!editMessage && chat.mode === 'chat'"
          >
            <i class="fa-solid fa-code"></i>
          </button>
          <div class="dropdown dropdown-top dropdown-end">
            <button tabindex="0" class="btn btn-sm m-1">
              <i class="fa-solid fa-ellipsis-vertical"></i>
            </button>
            <ul
              class="dropdown-content menu bg-base-100 rounded-box z-[1] w-52 p-2 shadow gap-2"
            >
              <li
                class="btn btn-sm tooltip"
                data-tip="Attach files"
                @click="selectFile = true"
              >
                <a>
                  <i class="fa-solid fa-paperclip"></i>
                  Attach files
                </a>
              </li>
              <li
                class="btn btn-sm"
                @click="testProject"
                v-if="API.activeProject.script_test"
              >
                <a>
                  <i class="fa-solid fa-flask"></i>
                  Test
                </a>
              </li>
              <li
                class="btn btn-sm tooltip"
                :class="isVoiceSession && 'btn-success'"
                :data-tip="$ui.voiceLanguages[$ui.voiceLanguage]"
                @click="toggleVoiceSession"
                v-if="!editMessage"
              >
                <a>
                  <i class="fa-solid fa-microphone-lines"></i>
                  Voice mode
                </a>
              </li>
              <li
                class="btn btn-sm text-white btn-error tooltip"
                data-tip="Delete?"
                @click="$emit('delete')"
              >
                <a>
                  <i class="fa-solid fa-trash-can"></i>
                  Delete
                </a>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
    <modal v-if="imagePreview">
      <div class="flex flex-col gap-2">
        <div class="text-2xl">Upload image</div>
        <div
          class="bg-contain bg-no-repeat bg-base-300/20 bg-center h-60 w-full"
          :style="`background-image: url(${imagePreview.src})`"
        >
        </div>
        <div>
          Image alt:
          <span class="text-xs" v-if="imagePreview.alt?.length">
            {{ imagePreview.alt?.length }} chars.
          </span>
        </div>
        <pre
          class="alert alert-xs h-20 overflow-auto"
          v-if="imagePreview.readonly"
        >
          {{ imagePreview.alt }}
        </pre>
        <div class="textarea input-bordered" v-else>
          <textarea
            class="w-full bg-transparent"
            v-model="imagePreview.alt"
            placeholder="Image content"
          >
          </textarea>
          <div class="flex justify-end">
            <button
              class="btn btn-sm bg-purple-600 text-white tooltip"
              data-tip="Extract text"
              @click="onExtractTextImage(imagePreview)"
            >
              <i class="fa-regular fa-closed-captioning"></i>
            </button>
          </div>
        </div>
        <div class="flex justify-end gap-2">
          <button class="btn" @click="imagePreview = null">Cancel</button>
          <button class="btn btn-primary" @click="onAddImage">Ok</button>
        </div>
      </div>
    </modal>
    <modal v-if="selectFile">
      <div class="form-control w-full max-w-xs space-y-2">
        <label class="label">
          <span class="label-text">Select File(s)</span>
        </label>
        <input
          type="file"
          accept="image/*"
          multiple
          @change="handleFileChange"
          class="file-input file-input-bordered file-input-primary w-full"
        />
        <button class="btn btn-error btn-sm" @click="selectFile = false">
          Cancel
        </button>
      </div>
    </modal>
  </div>
</template>

<script>
export default {
  props: ["chat", "editMessage"],
  data() {
    return {
      termSearchQuery: null,
      imagePreview: null,
      selectFile: false,
      onDraggingOverInput: false,
      waiting: false,
      images: [],
      searchTerms: [],
      searchTermSelIx: 0,
      isVoiceSession: false,
      multiline: false
    }
  },
  computed: {
    showTermSearch() {
      return !!this.termSearchQuery
    },
    canPost() {
      return this.$refs.editor.innerText || this.images?.length
    }
  },
  methods: {
    setEditorText(text) {
      this.$refs.editor.innerText = text
      this.onMessageChange()
    },
    async improveCode() {
      this.postMyMessage()
      this.$emit('improve-code', this.chat) 
    },
    addMessage(msg) {
      this.$emit('add-message', msg)
    },
    getUserMessage() {
      const message = this.$refs.editor.innerText
      return {
        role: "user",
        content: message,
        images: this.images.map(JSON.stringify)
      }
    },
    postMyMessage() {
      if (this.canPost) {
        this.addMessage(this.getUserMessage())
        this.cleanUserInputAndWaitAnswer()
      }
    },
    cleanUserInputAndWaitAnswer() {
      this.setEditorText("")
      this.images = []
      this.scrollToBottom()
    },
    async sendMessage() {
      if (!this.canPost) {
        return      
      }
      if (this.isVoiceSession && !this.canPost) {
        return
      }
      if (this.editMessage) {
        this.$emit('update-message', { content: this.$refs.editor.innerText, images: this.images.map(JSON.stringify) })
      } else {
        this.postMyMessage()
        await this.sendChatMessage(this.chat)
      }
    },
    async sendChatMessage(chat) {
      this.waiting = true
      try {
        await this.$emit('send-message', chat)
      } finally {
        this.waiting = false
      }
    },
    resetTermSearch() {
      this.termSearchQuery = null
    },
    addSearchTerm(term) {
      let text = this.$refs.editor.innerText
      if (text[text.length - 1] === "@") {
        text = text.slice(0, text.length - 1)
      }
      text += `@${term.key} `
      this.$emit('update-editor-text', text.trim())
      this.$emit("add-file", term.file)
      this.closeTermSearch()
    },
    closeTermSearch() {
      this.searchTerms = null
      this.termSearchQuery = null
      this.showTermSearch = false
      const target = this.$refs.editor
      const range = document.createRange()
      const sel = window.getSelection()
      range.selectNodeContents(target)
      range.collapse(false)
      sel.removeAllRanges()
      sel.addRange(range)
      target.focus()
    },
    onSelNext() {
      this.searchTermSelIx++
      if (this.searchTermSelIx === this.searchTerms?.length) {
        this.searchTermSelIx = 0
      }
    },
    onSelPrev() {
      this.searchTermSelIx--
      if (this.searchTermSelIx === -1) {
        this.searchTermSelIx = this.searchTerms?.length - 1
      }
    },
    onDrop(e) {
      this.onDraggingOverInput = false
      const file = [...e.dataTransfer.files].find(f => f.type.startsWith("image"))
      if (file) {
        this.onInputImage(file)
      }
    },
    async onContentPaste(e) {
      const file = [...e.clipboardData?.items].find(f => f.type.startsWith("image"))?.getAsFile()
      if (file) {
        this.onInputImage(file)
        e.preventDefault()
        return false
      }
    },
    getFileImageUrl(file) {
      return new Promise(ok => {
        const reader = new FileReader()
        reader.onload = (event) => {
          ok(event.target.result)
        }
        reader.readAsDataURL(file)
      })
    },
    async onInputImage(file) {
      const base64URL = await this.getFileImageUrl(file)
      this.imagePreview = {
        src: base64URL,
        alt: ""
      }
    },
    onAddImage() {
      if (this.imagePreview.ix === undefined) {
        this.images.push(this.imagePreview)
        this.imagePreview.ix = this.images.length - 1
      }
      this.imagePreview = null
    },
    async onExtractTextImage(image) {
      function base64ToFile(base64Data, filename) {
        const byteString = atob(base64Data.split(',')[1])
        const mimeString = base64Data.split(',')[0].split(':')[1].split(';')[0]
        const byteArray = new Uint8Array(byteString.length)
        for (let i = 0; i < byteString.length; i++) {
          byteArray[i] = byteString.charCodeAt(i)
        }
        const blob = new Blob([byteArray], { type: mimeString })
        return new File([blob], filename, { type: mimeString })
      }
      const file = base64ToFile(image.src, "image")
      const text = await API.tools.imageToText(file)
      image.alt = text
    },
    async handleFileChange({ target: { files } }) {
      const allUrls = await Promise.all([...files].map(file => this.getFileImageUrl(file)))
      this.images = [
        ...this.images,
        ...allUrls.map((src, ix) => ({ src, alt: "", ix: this.images.length + 1 + ix }))
      ]
      this.selectFile = false
    },
    removeImage(ix) {
      this.images = this.images.filter((_, imx) => imx !== ix)
    },
    onMessageChange() {
      this.editorText = this.$refs.editor.innerText.trim() || ""
    },
    toggleVoiceSession() {
      if (this.isVoiceSession) {
        return this.stopVoiceSession()
      }
      let silents = 5
      this.isVoiceSession = true
      const recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)()
      recognition.lang = this.$ui.voiceLanguage
      recognition.interimResults = false
      recognition.onresult = event => {
        const transcript = event.results[0][0].transcript
        this.$refs.editor.innerText += transcript
        this.onMessageChange()
      }
      recognition.onend = () => {
        if (this.isVoiceSession && silents--) {
          recognition.start()
        } else {
          this.stopVoiceSession()
        }
      }
      recognition.start()
      this.recognition = recognition
    },
    stopVoiceSession() {
      this.recognition?.stop()
      this.recognition = null
    },
    scrollToBottom() {
      setTimeout(() => this.$refs.anchor?.scrollIntoView(), 200)
    }
  }
}
</script>