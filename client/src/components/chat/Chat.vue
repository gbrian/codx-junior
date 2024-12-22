<script setup>
import { API } from '../../api/api'
import ChatEntry from '@/components/ChatEntry.vue'
import Browser from '@/components/browser/Browser.vue'
import Markdown from '@/components/Markdown.vue'
</script>
<template>
  <div class="flex flex-col gap-1 grow">
    <div class="w-full overflow-auto">
      <div class="my-2 text-xs" v-if="chat.file_list?.length">
        <a v-for="file in chat.file_list" :key="file" :data-tip="file"
          class="group text-nowrap mr-2 hover:underline hover:bg-base-300 click text-accent"
          @click="$ui.openFile(file)"
        >
          <span>{{ file.split('/').reverse()[0] }}</span>
          <span class="ml-2 click" @click.stop="$emit('remove-file', file)">
            <i class="fa-regular fa-circle-xmark"></i>
          </span>
        </a>
      </div>
    </div>
    <div class="grow relative">
      <div class="absolute top-0 left-0 right-0 bottom-0 scroller overflow-y-auto overflow-x-hidden">
        <Browser v-if="isBrowser" :token="$ui.monitors['preview']" />
        <div class="flex flex-col gap-2" 
          v-for="message in messages" :key="message.id">
          <ChatEntry :class="['mb-4 rounded-md',
            editMessage ? editMessage === message ? 'border border-warning' : 'opacity-40' : '',
            message.hide ? 'opacity-60' : '']"
            :chat="chat"
            :message="message"
            @edit="onEditMessage(message)"
            @remove="removeMessage(message)"
            @remove-file="removeFileFromMessage(message, $event)"
            @hide="toggleHide(message)"
            @run-edit="runEdit"
            @copy="onCopy(message)"
            @generate-code="onGenerateCode(message, $event)"
            @add-file-to-chat="$emit('add-file', $event)"
            @image="imagePreview = { ...$event, readonly: true }"
          />
        </div>
        <div class="anchor" ref="anchor"></div>
      </div>
    </div>
    <div class="badge text-info my-2 animate-pulse" v-if="waiting">typing ...</div>
    <div class="chat chat-end" v-if="isBrowser">
      <div class="chat-image avatar">
        <div class="w-10 rounded-full">
          <img
            src="/only_icon.png" />
        </div>
      </div>
      <div class="chat-bubble">
        <Markdown class="max-h-40 overflow-auto" :text="lastAIMessage.content" v-if="lastAIMessage" />
        <div v-else>
          <span class="font-bold">Let's navigate together:</span>
          Use browser to navigate any web or try:
          <span class="italic text-info">Find top 5 results for ....</span>
        </div>
      </div>
    </div>
    
    <div class="dropdown dropdown-top dropdown-open mb-1" v-if="showTermSearch">
      <div tabindex="0" role="button" class="rounded-md bg-base-300 w-fit p-2">
        <div class="flex p-1 items-center text-sky-600">
          <i class="fa-solid fa-at"></i>
          <input type="text" v-model="termSearchQuery"
            ref="termSearcher"
            class="-ml-1 input input-xs text-lg bg-transparent" placeholder="search term..."
            @keydown.down.stop="onSelNext"
            @keydown.up.stop="onSelPrev"
            @keydown.enter.stop="addSerchTerm(searchTerms[searchTermSelIx])"
            @keydown.esc="closeTermSearch"
          />
          <button class="btn btn-xs btn-circle btn-outline btn-error"
            @click="termSearchQuery = null"            
            v-if="termSearchQuery">
            <i class="fa-solid fa-circle-xmark"></i>
          </button>
        </div>
      </div>
      <ul tabindex="0" class="dropdown-content z-[1] menu p-2 shadow bg-base-300 rounded-box w-fit" v-if="searchTerms">
        <li v-for="term, ix in searchTerms" :key="term.key">
          <a @click="addSerchTerm(term)">
            <div :class="[searchTermSelIx === ix ? 'underline':'']">
              <span class="text-sky-600 font-bold">@{{ term.key }}</span> <span class="text-xs">({{ term.file.split('/').reverse()[0] }})</span>
            </div>
          </a>
        </li>
      </ul>
    </div>
    <div :class="['flex bg-base-300 border rounded-md shadow', 
          multiline ? 'flex-col' : '',
          editMessage && 'border-warning',
          onDraggingOverInput ? 'bg-warning/10': '']"
        @dragover.prevent="onDraggingOverInput = true"
        @dragleave.prevent="onDraggingOverInput = false"
        @drop.prevent="onDrop"
    >
      <div :class="['max-h-40 w-full px-2 py-1 overflow-auto text-wrap focus-visible:outline-none']" contenteditable="true"
        ref="editor" @input="onMessageChange"
        @paste="onContentPaste"
        @keydown.esc.stop="onResetEdit"
      >
      </div>
      <div class="flex justify-between items-end px-2">
        <div class="carousel rounded-box">
          <div class="carousel-item relative click flex flex-col" v-for="image, ix in allImages" :key="image.src">
            <div class="bg-contain bg-no-repeat bg-center w-10 h-10 lg:h-20 lg:w-20 bg-base-300 mr-4"
              :style="`background-image: url(${image.src})`" @click="imagePreview = image">
            </div>
            <p class="text-xs">{{ image.alt.slice(0, 10) }}</p>
            <button class="btn btn-xs btn-circle btn-error absolute right-0 top-0"
              @click="removeImage(ix)"
            >
              X
            </button>
          </div>
        </div>
        <div class="flex gap-1 items-center justify-end py-2">
          <button class="btn btn btn-sm btn-info btn-outline" @click="sendMessage" v-if="editMessage">
            <i class="fa-solid fa-save"></i>
            <div class="text-xs" v-if="editMessage">Edit</div>
          </button>
          <button class="btn btn btn-sm btn-outline tooltip" data-tip="Save changes" @click="onResetEdit" v-if="editMessage">
            <i class="fa-regular fa-circle-xmark"></i>
          </button>
          <button class="btn btn btn-sm btn-circle btn-outline tooltip" data-tip="Ask codx-junior" @click="sendMessage" v-if="!editMessage && !isBrowser">
            <i class="fa-solid fa-comment"></i>
          </button>
          <button class="btn btn btn-sm btn-circle btn-outline tooltip"
            :class="isBrowser && 'btn-warning'"
            data-tip="Ask codx-browser" @click="navigate"
            v-if="!editMessage">
            <i class="fa-brands fa-chrome"></i>
          </button>
          <button class="btn btn btn-sm btn-outline tooltip" 
            :class="isVoiceSession && 'btn-info animate-pulse'"
            :data-tip="$ui.voiceLanguages[$ui.voiceLanguage]" @click="toggleVoiceSession" v-if="!editMessage">
            <i class="fa-solid fa-microphone-lines"></i>
          </button>
          <div class="dropdown dropdown-top dropdown-end">
            <div tabindex="0" role="button" class="btn btn-sm m-1">
              <i class="fa-solid fa-ellipsis-vertical"></i>
            </div>
            <ul tabindex="0" class="dropdown-content menu bg-base-100 rounded-box z-[1] w-52 p-2 shadow gap-2">
              <li class="btn btn-sm btn-warning" @click="improveCode()" v-if="!editMessage">
                <a>
                  <i class="fa-solid fa-code"></i>
                  Code
                </a>
              </li>
              <li class="btn btn-sm" @click="selectFile = true">
                <a><i class="fa-solid fa-paperclip"></i> Attach files</a>
              </li>
              <li class="btn btn-sm" @click="testProject" v-if="API.lastSettings.script_test">
                <a>
                  <i class="fa-solid fa-flask"></i>
                  Test
                </a>
              </li>
              <li>
                <a> 
                  <i class="fa-solid fa-microphone-lines"></i>
                  <select class="select select-sm" @change="setVoiceLanguage($event.target.value)">
                    <option v-for="key, lang in $ui.voiceLanguages"
                      :key="lang"
                      :selected="$ui.voiceLanguage === lang" :value="lang">{{ key }}</option>
                  </select>
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
        <div class="bg-contain bg-no-repeat bg-base-300/20 bg-center h-60 w-full" :style="`background-image: url(${imagePreview.src})`"></div>
        <div>
            Image alt: <span class="text-xs" v-if="imagePreview.alt?.length">{{ imagePreview.alt?.length }} chars.</span>
        </div>
        <pre class="alert alert-xs h-20 overflow-auto" v-if="imagePreview.readonly">{{ imagePreview.alt }}</pre>
        <div class="textarea input-bordered" v-else>
          <textarea class="w-full bg-transparent" v-model="imagePreview.alt" placeholder="Image content">
          </textarea>
          <div class="flex justify-end">
            <button class="btn btn-sm bg-purple-600 text-white tooltip"
              data-tip="Extract text"
              @click="onExtractTextImage(imagePreview)">
              <i class="fa-regular fa-closed-captioning"></i>
            </button>
          </div>
        </div>
        <div class="flex justify-end gap-2">
          <button class="btn" @click="imagePreview = null">
            Cancel
          </button>
          <button class="btn btn-primary" @click="onAddImage">
            Ok
          </button>
        </div>
      </div>
    </modal>
    <modal v-if="selectFile">
      <label class="file-select">
      <div class="select-button">
        <span>Select File(s)</span>
      </div>
      <input type="file" accept="image/*" multiple @change="handleFileChange"/>
      <button class="btn btn-sm btn-error" @click="selectFile = false">
        Cancel
      </button>
    </label>
    </modal>
  </div>
</template>
<script>
const defFormater = d => JSON.stringify(d, null, 2)

export default {
  props: ['chat', 'showHidden'],
  data () {
    return {
      waiting: false,
      editMessage: null,
      editMessageId: null,
      termSearchQuery: null,
      searchTerms: null,
      searchTermSelIx: -1,
      showTermSearch: false,
      files: [],
      images: [],
      previewImage: null,
      editorText: "",
      imagePreview: null,
      onDraggingOverInput: false,
      testError: null,
      previewStyle: {
        zoom: 0.6
      },
      selectFile: false,
      isVoiceSession: false,
      recognition: null,
      isBrowser: false
    }
  },
  created () {
  },
  computed: {
     messages () {
      if (this.isBrowser) {
        return []
      }
      if (this.isTask) {
        const msgs = [...this.chat?.messages ||[]].filter(m => !m.hide).reverse()
        return [msgs.find(m => m.role === 'user'),
                msgs.find(m => m.role === 'assistant')].filter(m => !!m)
      }
      return this.chat?.messages?.filter(m => !m.hide || this.showHidden)
    },
    multiline () {
      return this.editorText?.split("\n").length > 1 || this.images?.length
    },
    allImages () {
      return this.images
    },
    messageText () {
      return this.editorText
    },
    canPost () {
      return this.messageText || this.images?.length
    },
    isTask () {
      return this.chat.mode === 'task'
    },
    lastAIMessage() {
      if (this.chat) {
        const { messages } = this.chat
        for(var c = messages.length - 1; c >= 0; --c) {
          const m = messages[c]
          if (!m.hide 
                && m.role === 'assistant'
                && m.task_item === 'browser') {
            return m
          }
        }
      }
      return null
    }
  },
  watch: {
    termSearchQuery (newVal) {
      if (newVal?.length > 2) {
        this.searchKeywords()
      } else {
        this.searchTerms = null
      }
    },
  },
  methods: {
    zoomIn() {
      this.previewStyle.zoom += 0.1;
    },
    zoomOut() {
      this.previewStyle.zoom -= 0.1;
    },
    setEditorText (text) {
      this.$refs.editor.innerText = text
      this.onMessageChange()
    },
    onEditMessage (message) {
      console.log("onEditMessage", message)
      this.editMessage = message
      this.editMessageId = this.chat.messages.findIndex(m => m === message)
      try {
        this.images = message.images.map(JSON.parse)
      } catch {}
      this.setEditorText(this.editMessage.content)
    },
    toggleHide(message) {
      message.hide = !message.hide 
      this.saveChat()
    },
    onCopy (message) {
      navigator.permissions.query({name: "clipboard-read"}).then(result => {
          if (result.state == "granted" || result.state == "prompt") {
            navigator.clipboard.writeText(message.content)
          }
      })
      .catch(console.error);
    },
    async improveCode () {
      this.postMyMessage()
      await this.sendApiRequest(
        () => API.run.improve(this.chat),
        data => ['### Changes done',
                  data.messages.reverse()[0].content,
                  '### Edits done',
                  data.edits.map(edit => "```json\n"
                      + JSON.stringify(edit, 2, null) + 
                    "\n```"),
                  "### Error",
                  JSON.stringify(data.errors, 2, null)
                ].join("\n")
      )
      this.testProject()
    },
    runEdit (codeSnipped) {
      this.sendApiRequest(
        () => API.run.edit({ id: "", messages: [{ role: 'user', content: codeSnipped }] }),
        data => [
                  data.messages.reverse()[0].content,
                  "\n\n",
                  ...data.errors.map(e => ` * ${e}\n`)
                ].join("\n")
      )
    },
    addMessage (msg) {
      this.chat.messages = [
        ...this.chat.messages||[],
        msg
      ]
    },
    getUserMessage() {
      const message = this.$refs.editor.innerText
      return {
        role: 'user',
        content: message,
        images: this.images.map(JSON.stringify)
      }
    },
    postMyMessage () {
      if (this.canPost) {      
        this.addMessage(this.getUserMessage())
        this.cleanUserInputAndWaitAnswer()
      }
    },
    cleanUserInputAndWaitAnswer() {
      this.setEditorText("")
      this.images = []
      this.$refs.anchor?.scrollIntoView()

    },
    async sendMessage () {
      if (this.editMessage !== null) {
        this.updateMessage()
      } else {
        this.postMyMessage()
        const { data } = await this.sendChatMessage(this.chat)
        this.chat.messages = data.messages
      }
      this.saveChat()
    },
    async navigate () {
      if (!this.editorText) {
        if (this.isBrowser = !this.isBrowser) {
          if (this.lastAIMessage) {
            this.lastAIMessage.hide
          }
        }
        return
      }
      const message = this.getUserMessage()
      const { data } = await this.sendChatMessage({ mode: 'browser', messages: [
        ...this.chat.messages,
        message
      ] })
      this.chat.messages = data.messages
      this.saveChat()
      this.cleanUserInputAndWaitAnswer()
    },
    getSendMessage() {
      return this.editMessage ||
                this.chat.messages[this.chat.messages.length - 1].content
    },
    async askKnowledge () {
      const searchTerm = this.$refs.editor.innerText 
      const knowledgeSearch = {
          searchTerm,
          searchType: 'embeddings',
          documentSearchType: API.lastSettings.knowledge_search_type,
          cutoffScore: API.lastSettings.knowledge_context_cutoff_relevance_score,
          documentCount: API.lastSettings.knowledge_search_document_count
      }
      // this.postMyMessage()
      const { data: { documents } } = await API.knowledge.search(knowledgeSearch)
      const docs = documents.map(doc => `#### File: ${doc.metadata.source.split("/").reverse()[0]}\n>${doc.metadata.source}\n\`\`\`${doc.metadata.language}\n${doc.page_content}\`\`\``) 
      this.$refs.editor.innerText = docs.join("\n")
    },
    async sendApiRequest (apiCall, formater = defFormater) {
      try {
        this.waiting = true
        await apiCall()
        this.$emit('refresh-chat')
        this.$refs.anchor.scrollIntoView()
      } catch (ex) {
        this.addMessage({
          role: 'assistant',
          content: ex.message
        }) 
      }
      this.waiting = false
    },
    async sendChatMessage(chat) {
      this.waiting = true
      try {
        return await API.chats.message(chat)
      } finally {
        this.waiting = false
      }
    },
    async updateMessage () {
      const { innerText } = this.$refs.editor
      const images = this.images.map(JSON.stringify)
      this.editMessage.content = innerText
      this.editMessage.images = images
      this.editMessage.updated_at = new Date().toISOString()
      this.onResetEdit()
    },
    onResetEdit() {
      if (this.editMessageId !== null) {
        this.editMessage = null
        this.setEditorText("")
        this.editMessageId = null
        this.images = []
      }
    },
    removeMessage(message) {
      this.$emit("delete-message", message)
    },
    async searchKeywords () {
      const { data } = await API.knowledge.searchKeywords(this.termSearchQuery)
      this.searchTerms = Object.keys(data).map(k => data[k].reduce((acc, term) => {
        acc.push({
          key: term,
          file: k
        })
        return acc
      }, []))
      .reduce((a, b) => a.concat(b), [])
      this.searchTermSelIx = 0
    },
    addSerchTerm(term) {
      let text = this.$refs.editor.innerText
      if (text[text.length-1] === '@') {
        text = text.slice(0, text.length-1)
      }
      text += `@${term.key} `
      this.editMessage = text.trim()
      this.setEditorText(this.editMessage)
      
      this.$emit('add-file', term.file)
      this.closeTermSearch ();
    },
    closeTermSearch () {
      this.searchTerms = null
      this.termSearchQuery = null
      this.showTermSearch = false
      const target = this.$refs.editor

      const range = document.createRange();
      const sel = window.getSelection();
      range.selectNodeContents(target);
      range.collapse(false);
      sel.removeAllRanges();
      sel.addRange(range);
      target.focus();
      range.detach();
    },
    onSelNext () {
      this.searchTermSelIx++
      if (this.searchTermSelIx === this.searchTerms?.length) {
        this.searchTermSelIx = 0
      }
    },
    onSelPrev () {
      this.searchTermSelIx--
      if (this.searchTermSelIx === -1) {
        this.searchTermSelIx = this.searchTerms?.length - 1
      }
    },
    saveChat () {
      return API.chats.save(this.chat)
    },
    onDrop(e) {
      this.onDraggingOverInput = false
      if (!e.dataTransfer.files) {
        return
      }
      var file = [...e.dataTransfer.files].filter(f => f.type.indexOf("image") !== -1)[0]
      if (file) {
        this.onInputImage(file)
      }
    },
    async onContentPaste(e) {
      if (!e.clipboardData?.items) {
        return
      }
      var file = [...e.clipboardData?.items].filter(f => f.type.indexOf("image") !== -1)[0]?.getAsFile()
      if (file) {
        this.onInputImage(file)
        e.preventDefault()
        return false
      }
    },
    getFileImageUrl(file) {
      return new Promise(ok => {
        const reader = new FileReader();
        reader.onload = (event) => {
          const base64URL = event.target.result;
          ok(base64URL)
        };
        reader.readAsDataURL(file);
      })
    },
    async onInputImage(file) {
      const base64URL = await this.getFileImageUrl(file)
      this.imagePreview = {
            src: base64URL,
            alt: ""
          }
    },
    onAddImage () {
      if (this.imagePreview.ix === undefined) {
        this.images.push(this.imagePreview)
        this.imagePreview.ix = this.images.length -1
      }
      this.imagePreview = null
    },
    async onExtractTextImage(image) {
      function base64ToFile(base64Data, filename) {
        const byteString = atob(base64Data.split(',')[1]);
        const mimeString = base64Data.split(',')[0].split(':')[1].split(';')[0];
        const byteArray = new Uint8Array(byteString.length);
        for (let i = 0; i < byteString.length; i++) {
          byteArray[i] = byteString.charCodeAt(i);
        }
        const blob = new Blob([byteArray], { type: mimeString });
        return new File([blob], filename, { type: mimeString });
      }

      const file = base64ToFile(image.src, "image")
      const text = await API.tools.imageToText(file)
      image.alt = text
    },
    async handleFileChange ({ target: { files }}) {
      const allUrls = await Promise.all([...files].map(file => this.getFileImageUrl(file)))
      console.log("handleFileChange", allUrls)
      this.images = [
        ...this.images, 
        ...allUrls.map((src, ix) => ({ src, alt: "", ix: this.images.length + 1 + ix }))]
      this.selectFile = false
    },
    onGenerateCode(message, code) {
      this.setEditorText(`Generate code only for this piece of code:
      \`\`\`
      ${code}
      \`\`\``)
    },
    removeImage(ix) {
      this.images = this.images.filter((i, imx) => imx !== ix)
    },
    onMessageChange () {
      this.editorText = this.$refs.editor.innerText.trim() || ""
    },
    async testProject () {
      const { data } = await API.project.test()
      this.testError = data
      if (this.testError) {
        this.editMessage = this.testError
        this.setEditorText(this.editMessage)
      }
    },
    removeFileFromMessage(message, file) {
      message.files = message.files.filter(f => f !== file)
      this.saveChat()
    },
    toggleVoiceSession () {
      if (this.isVoiceSession) {
        return this.stopVoiceSession()
      }
      let silents = 5
      this.isVoiceSession = true;

      const recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
      recognition.lang = this.$ui.voiceLanguage;
      recognition.interimResults = false;

      recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        this.$refs.editor.innerText += transcript
        this.onMessageChange()
      };

      recognition.onend = () => {
        if (this.isVoiceSession && silents--) {
          recognition.start();
        } else {
          this.stopVoiceSession()
        }
      };

      recognition.start();
      this.recognition = recognition
    },
    stopVoiceSession() {
      this.isVoiceSession = false
      this.recognition?.stop()
    },
    setVoiceLanguage(language) {
      this.$ui.setVoiceLanguage(language)
    }
  }
}
</script>