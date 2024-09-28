<script setup>
import { API } from '../../api/api'
import ChatEntry from '@/components/ChatEntry.vue'
</script>
<template>
  <div class="flex flex-col gap-2 grow">
    <div class="flex flex-col grow" v-if="livePreview">
      <div class="flex flex-col w-full grow">
        <input type="text" class="input input-bordered input-xs w-full" placeholder="http://..." v-model="chat.live_url" />
        <iframe ref="iframe" :src="chat.live_url" class="w-full h-full bg-base-200"></iframe>
      </div>
    </div>
    <div class="flex flex-col grow" v-else>
      <div class="grow overflow-auto relative">
        <div class="absolute top-0 left-0 w-full h-full scroller">
          <div v-for="message in messages" :key="message.id">
            <ChatEntry :message="message"
              @edit="onEditMessage(message)"
              @remove="removeMessage(message)"
              @hide="toggleHide(message)"
              @run-edit="runEdit"
              @copy="onCopy(message)"
              @generate-code="onGenerateCode(message, $event)"
              @image="imagePreview = $event"
            />
          </div>
          <div class="anchor" ref="anchor"></div>
        </div>
      </div>
      <div class="badge my-2 animate-pulse" v-if="waiting">typing ...</div>
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
                <span class="text-sky-600 font-bold">@{{ term.key }}</span> <span class="text-xs">({{ term.file.split("/").reverse()[0] }})</span>
              </div>
            </a>
          </li>
        </ul>
      </div>
    </div>
    <div class="carousel rounded-box">
      <div class="carousel-item relative click flex flex-col" v-for="image, ix in allImages" :key="image.src">
        <div class="bg-auto bg-no-repeat bg-center h-28 w-28 bg-base-300 mr-4"
          :style="`background-image: url(${image.src})`" @click="imagePreview = image">
        </div>
        <p class="text-xs">{{ image.alt }}</p>
        <button class="btn btn-xs btn-circle btn-error absolute right-2 top-2"
          @click="removeImage(ix)"
        >
          X
        </button>
      </div>
    </div>
    <div :class="['flex gap-2 p-2 bg-base-300 border rounded-md shadow', multiline ? 'flex-col' : '']">
      <div :class="['max-h-40 w-full max-w-full px-2 py-1 overflow-auto text-wrap focus-visible:outline-none',
        editMessageId !== null ? 'border-error': '',
        editMessageId !== null ? 'border-warning': '',
        onDraggingOverInput ? 'bg-warning/10': ''
      ]" contenteditable="true"
        ref="editor" @input="onMessageChange"
        @paste.prevent="onContentPaste"
        @dragover.prevent="onDraggingOverInput = true"
        @dragleave.prevent="onDraggingOverInput = false"
        @drop.prevent="onDrop"
        @keydown.esc.stop="onResetEdit"
      >
      </div>
      <div class="flex gap-2 items-center justify-end mt-1">
        <button class="btn btn btn-sm btn-circle mb-1 btn-outline" @click="sendMessage" v-if="!livePreview">
          <i class="fa-solid fa-comment"></i>
        </button>
        <button class="btn btn-warning btn-sm mb-1 btn-outline" @click="livePreview ? liveEdit() : improveCode()">
          <i class="fa-solid fa-code"></i> Code
        </button>
        <button :class="['btn btn-sm mb-1 btn-outline',
            testError ? 'btn-error' : 'btn-info'
          ]" @click="testProject" v-if="API.lastSettings.script_test">
          <i class="fa-solid fa-flask"></i> Test
        </button>
      </div>
    </div>
    <div class="flex mt-2 w-full p-1 rounded-md bg-warning text-neutral" v-if="editMessageId != null">
      <div class="font-bold">
        <span v-if="editMessage.role === 'user'">Edit message: </span>
        <span v-else>Request corrections: </span>
      </div>
      <span class="italic">
        {{ chat.messages[editMessageId].content.slice(0, 50)  }}...
      </span>
      <div class="grow"></div>
      <button class="click hover:shadow" @click="editMessageId = null">
        <i class="fa-regular fa-circle-xmark"></i>
      </button>
    </div>
    <modal v-if="imagePreview">
      <div class="flex flex-col gap-2">
        <div class="text-2xl">Upload image</div>
        <img class="h-30 max-w-full" :src="imagePreview.src" />
        <input class="input input-bordered" v-model="imagePreview.alt" placeholder="Add image info" />
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
      testError: null
    }
  },
  computed: {
    editor () {
      return this.$refs.editor
    },
    messages () {
      return this.chat?.messages?.filter(m => !m.hide || this.showHidden)
    },
    multiline () {
      return this.editorText.indexOf("\n") !== -1
    },
    allImages () {
      return this.images
    },
    livePreview () {
      return this.chat?.mode === 'live'
    }
  },
  watch: {
    termSearchQuery (newVal) {
      if (newVal?.length > 2) {
        this.searchKeywords()
      } else {
        this.searchTerms = null
      }
    }
  },
  methods: {
    setEditorText (text) {
      this.editor.innerText = text
      this.onMessageChange()
    },
    onEditMessage (message) {
      this.editMessage = message
      this.editMessageId = this.chat.messages.findIndex(m => m === message)

      if (this.editMessage.role == 'user') {
        this.setEditorText(this.editMessage.content)
      } else {
        this.setEditorText("Please apply this corrections to your message:\n- ")
      }
      this.images = (message.images || []).map(i => {
        try {
          JSON.parse(i)
        } catch {
          return { src: i }
        }
      })
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
    async liveEdit () {
      await this.sendMessage()
      this.improveCode()
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
    postMyMessage () {
      const message = this.editor.innerText
      if (message || this.images?.length) {
        this.addMessage({
          role: 'user',
          content: message,
          images: this.images.map(JSON.stringify)
        })
        this.setEditorText("")
        this.images = []
        this.$refs.anchor?.scrollIntoView()
      }
    },
    async sendMessage () {
      if (this.editMessageId !== null) {
        this.onUpdateMessage()
        return
      }
      this.postMyMessage()
      return this.sendApiRequest(
        () => API.chats.message(this.chat),
        ({ content } = {}) => {
          return `${ content }`
        }
      )
    },
    getSendMessage() {
      return this.editMessage ||
                this.chat.messages[this.chat.messages.length - 1].content
    },
    async askKnowledge () {
      const searchTerm = this.editor.innerText 
      const knowledgeSearch = {
          searchTerm,
          searchType: 'embeddings',
          documentSearchType: API.lastSettings.knowledge_search_type,
          cutoffScore: API.lastSettings.knowledge_context_cutoff_relevance_score,
          documentCount: API.lastSettings.knowledge_search_document_count
      }
      // this.postMyMessage()
      const { data: { documents } } = await API.knowledge.search(knowledgeSearch)
      documents.map(doc => this.addMessage({
          role: 'assistant',
          content: `#### File: ${doc.metadata.source.split("/").reverse()[0]}\n>${doc.metadata.source}\n\`\`\`${doc.metadata.language}\n${doc.page_content}\`\`\``
        }) 
      )
      this.saveChat()
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
    onUpdateMessage () {
      if (this.editMessage.role === 'user') {
        this.editMessage.content = this.editor.innerText
      }
      this.onResetEdit()
      this.saveChat()
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
      const ix = this.chat.messages.findIndex(m => m === message)
      this.$emit("delete-message", ix)
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
      }
    },
    onInputImage(file) {
      const reader = new FileReader();
      reader.onload = (event) => {
        const base64URL = event.target.result;
        this.imagePreview = {
          src: base64URL,
          alt: ""
        }
      };
      reader.readAsDataURL(file);
    },
    onAddImage () {
      if (this.imagePreview.ix === undefined) {
        this.images.push(this.imagePreview)
        this.imagePreview.ix = this.images.length -1
      }
      this.imagePreview = null
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
      this.editorText = this.editor.innerText.trim() || ""
    },
    async testProject () {
      const { data } = await API.project.test()
      this.testError = data
      if (this.testError) {
        this.editMessage = this.testError
        this.setEditorText(this.editMessage)
      }
    }
  }
}
</script>