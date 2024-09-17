<script setup>
import ChatEntry from '@/components/ChatEntry.vue'
</script>
<template>
  <div class="flex flex-col gap-2 grow">
    <div class="flex flex-col grow">
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
              @image="previewImage = $event"
            />
          </div>
          <div class="anchor" ref="anchor"></div>
        </div>
      </div>
      <div class="absolute top-0 left-0 right-0 bottom-0 z-50" v-if="previewImage">
        <div class="flex justify-center bg-base-300 p-4">
          <img :src="previewImage" class="click rounded-md" @click="previewImage = null"/>
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
      <div class="carousel rounded-box">
        <div class="carousel-item relative" v-for="url, ix in images" :key="url">
          <img class="w-40 h-40 click" :src="url" @click="previewImage = url" />
          <button class="btn btn-xs btn-circle btn-error absolute right-2 top-2"
            @click="removeImage(ix)"
          >
            X
          </button>
        </div>
      </div>
    </div>
    <div :class="['flex gap-2 p-2 bg-base-300 border rounded-md shadow', multiline ? 'flex-col' : '']">
      <div :class="['max-h-40 grow px-2 py-1 overflow-auto text-wrap focus-visible:outline-none',
        editMessageId !== null ? 'border-error': '',
        editMessageId !== null ? 'border-warning': '',
      ]" contenteditable="true"
        ref="editor" @input="onMessageChange"
        @paste="onContentPaste"
        @keydown.esc.stop="onResetEdit"
      >
      </div>
      <div class="flex gap-2 items-center justify-end mt-1">
        <button class="btn btn btn-sm btn-circle mb-1 btn-outline" @click="sendMessage">
          <i class="fa-solid fa-comment"></i>
        </button>
        <button class="btn btn-info btn-sm btn-circle mb-1 btn-outline" @click="askKnowledge">
          <i class="fa-solid fa-file-circle-plus"></i>
        </button>
        <button class="btn btn-warning btn-sm mb-1 btn-outline" @click="improveCode">
          <i class="fa-solid fa-code"></i> Code
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
  </div>
</template>
<script>
import { API } from '@/api/api'
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
      editorText: ""
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
      this.images = message.images || []
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
    improveCode () {
      this.postMyMessage()
      this.sendApiRequest(
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
      if (message) {
        this.addMessage({
          role: 'user',
          content: message,
          images: this.images
        })
        this.setEditorText("")
        this.images = []
        this.$refs.anchor.scrollIntoView()
      }
    },
    async sendMessage () {
      if (this.editMessageId !== null) {
        this.onUpdateMessage()
        return
      }
      this.postMyMessage()
      this.sendApiRequest(
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
      this.$emit('save')
    },
    async onContentPaste(pasteEvent) {
      var items = pasteEvent.clipboardData?.items;
      if (!items) {
        return
      }
      for (var i = 0; i < items.length; i++) {
        if (items[i].type.indexOf("image") == -1) continue;
        var file = items[i].getAsFile();
        if (file.type.match('image.*')) {
          pasteEvent.preventDefault();
          const reader = new FileReader();
          reader.onload = (event) => {
            const base64URL = event.target.result;
            this.images.push(base64URL);
          };
          reader.readAsDataURL(file);
        }
      }
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
    }
  }
}
</script>