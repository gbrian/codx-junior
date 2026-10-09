<script setup>
import MermaidViewerVue from './MermaidViewer.vue'
import MarkdownViewer from './MarkdownViewer.vue'
import CodeViewer from './CodeViewer.vue'
import HTMLPreview from './HTMLPreview.vue'
import BlockEditor from './BlockEditor.vue'
import CanvaViewer from './canva/CanvaViewer.vue'
</script>

<template>
  <BlockEditor
    :originalContent="codeText"
    :isCodeBlock="!showMarkdown"
    :language="language"
    ref="blockEditor"
    @edit-start="onEditStart"
    @edit-cancel="onEditCancel"
    @edit-save="onEditSave"
  >
    <div class="rounded-md py-2">
      <!-- Edit button (shown on hover) -->
      <div
        class="absolute -left-10 top-0 opacity-0 hover:opacity-100 transition-opacity"
        v-if="!isEditing"
      >
        <button
          class="btn btn-xs btn-ghost tooltip tooltip-right"
          data-tip="Edit block"
          @click="startEdit"
        >
          <i class="fa-solid fa-pen"></i>
        </button>
      </div>

      <div class="flex gap-2 w-full justify-end rounded-t" ref="toolbar" v-if="(showMermaid || showHTMLPreview || showCanva) && !isEditing">
        <button class="btn btn-xs" @click="showMermaidSource = !showMermaidSource" v-if="showMermaid">
          <span v-if="showMermaidSource">View diagram</span>
          <span v-else>View code</span>
        </button>
        <button class="btn btn-sm bg-info/60 my-2 flex gap-2" @click="htmlPreview = !htmlPreview" v-if="showHTMLPreview">
          <span v-if="htmlPreview">View code</span>
          <span v-else><i class="fa-solid fa-tablet-screen-button"></i> View preview</span>
        </button>
        <button class="btn btn-sm bg-info/60 my-2 flex gap-2" @click="showCanvaSource = !showCanvaSource" v-if="showCanva && canvaEditorAvailable">
          <span v-if="showCanvaSource"><i class="fa-solid fa-palette"></i> View canvas</span>
          <span v-else><i class="fa-solid fa-code"></i> View source</span>
        </button>
        <button class="btn btn-sm bg-info/60 my-2 flex gap-2" @click="canvaModalOpen = true" v-if="showCanvaEditor">
          <i class="fa-solid fa-expand"></i>
          <span>Expand</span>
        </button>
      </div>

      <MermaidViewerVue
        :diagram="codeText"
        theme="dark"
        @click="showMermaidSource = !showMermaidSource"
        v-if="showMermaid && !showMermaidSource && !isEditing"
      />

      <HTMLPreview
        :html="codeText"
        v-if="showHTMLPreview && htmlPreview && !isEditing"
      />

      <CanvaViewer
        :text="codeText"
        @change="onCanvaChange"
        v-if="showCanvaInlineEditor"
      />

      <!-- Expanded editor: reuses CanvaViewer (and its Save/Discard flow) inside
           a large modal so the canvas has room to breathe. The inline editor is
           hidden while this is open so only one WovenCanvas runs at a time. -->
      <modal v-if="canvaModalOpen" close size="full" @close="canvaModalOpen = false">
        <template #header>
          <span class="flex items-center gap-2 text-base font-semibold">
            <i class="fa-solid fa-palette text-info"></i>
            Canva editor
          </span>
        </template>
        <div class="w-[80vw] max-w-6xl h-[70vh] min-h-[360px]">
          <CanvaViewer full-height :text="codeText" @change="onCanvaChange" />
        </div>
      </modal>

      <CodeViewer
        :code="codeText"
        :language="language"
        :file="file"
        :files="files"
        :project="project"
        :finished="finished"
        :chat="chat"
        :message="message"
        :key="blockHash"
        v-if="showCode && !isEditing"
        @reload-file="$emit('reload-file', $event)"
        @open-file="$emit('open-file', $event)"
        @save-file="$emit('save-file', $event)"
        @add-file="$emit('add-file', $event)"
        @sub-task="$emit('sub-task', $event)"
        @message-change="onMessageChange"
      />

      <MarkdownViewer :text="codeText" v-if="showMarkdown && !isEditing" />
    </div>
  </BlockEditor>
</template>

<script>
const languageMapping = {
  "vue": "html",
  "markdown": "md",
  "html": "html"
}

export default {
  props: ['chat', 'finished', 'code', 'text', 'text-language', 'file-name', 'files', 'project', 'message', 'block-hash'],
  emits: ['reload-file', 'open-file', 'save-file', 'add-file', 'sub-task', 'edit-message', 'generate-code', 'text-changed', 'block-edited'],
  data() {
    return {
      codeText: null,
      languages: null,
      htmlPreview: false,
      showMermaidSource: false,
      showCanvaSource: false,
      canvaModalOpen: false,
      file: null,
      previousText: null,
      isEditing: false
    }
  },
  created() {
    const language = languageMapping[this.codeLanguage] || this.codeLanguage
    this.languages = [[language, language.toUpperCase()]]
    this.codeText = this.text || this.code?.innerText
    this.file = this.fileName || this.code?.attributes["data-file"]?.value
    this.previousText = this.codeText
  },
  mounted() {
    if (this.code) {
      this.code?.parentNode.after(this.$el)
      this.code?.parentNode.remove()
      this.$bubble('code-file-shown', { somedata: true })
    }
  },
  computed: {
    isVibeCoding() {
      return this.chat?.mode === 'vibe'
    },
    language() {
      const lang = this.textLanguage ||
        this.code?.attributes["class"]?.value.split("-").reverse()[0]
      return languageMapping[lang] || lang
    },
    codeLanguage() {
      return this.language?.includes("mermaid") ? "markdown" : this.language
    },
    showMermaid() {
      return this.language === 'mermaid' && !this.isVibeCoding
    },
    showHTMLPreview() {
      const extension = this.fileName?.split(".")[1] || this.codeLanguage
      return ['html'].includes(extension) && !this.isVibeCoding
    },
    showCanva() {
      return this.language === 'canva' && !this.isVibeCoding
    },
    // The block carries actual content (blank/whitespace blocks start empty)
    canvaHasContent() {
      return !!(this.codeText && this.codeText.trim())
    },
    isValidCanva() {
      if (!this.codeText) return false
      try {
        const parsed = JSON.parse(this.codeText)
        if (Array.isArray(parsed)) return true
        return !!(parsed && Array.isArray(parsed.nodes))
      } catch (ex) {
        return false
      }
    },
    // The canvas can be opened when there is a valid definition to load OR the
    // block is empty (in which case the editor starts blank so it can be drawn
    // from scratch). A block with broken JSON is NOT openable, so its source is
    // shown instead and can be fixed.
    canvaEditorAvailable() {
      return this.isValidCanva || !this.canvaHasContent
    },
    showCanvaEditor() {
      return this.showCanva && !this.showCanvaSource && this.canvaEditorAvailable
    },
    // The inline editor is hidden while the "Expand" modal owns the canvas so
    // two heavy WovenCanvas instances never run at the same time.
    showCanvaInlineEditor() {
      return this.showCanvaEditor && !this.isEditing && !this.canvaModalOpen
    },
    showCode() {
      return !this.showMarkdown && (!this.showMermaid || this.showMermaidSource) && (!this.showHTMLPreview || !this.htmlPreview) && !this.showCanvaEditor
    },
    showMarkdown() {
      return this.language === 'md' && !this.fileName
    },
    codeBlockInfo() {
      return {
        code: this.text || this.code?.innerText,
        language: this.language
      }
    }
  },
  watch: {
    text(newVal) {
      if (newVal !== undefined && newVal !== this.codeText) {
        this.previousText = this.codeText
        this.codeText = newVal
      }
    },
    code(newCode) {
      if (newCode?.innerText !== undefined) {
        const innerText = newCode.innerText
        if (innerText !== this.codeText) {
          this.previousText = this.codeText
          this.codeText = innerText
        }
      }
    },
    isEditing(value) {
      // Editing the raw source replaces the canvas, so drop the modal with it.
      if (value) this.canvaModalOpen = false
    }
  },
  methods: {
    startEdit() {
      this.isEditing = true
      this.$refs.blockEditor.startEdit()
    },
    onEditStart() {
      this.isEditing = true
    },
    onEditCancel() {
      this.isEditing = false
    },
    onEditSave({ originalContent, newContent }) {
      this.isEditing = false
      this.codeText = newContent
      this.$emit('block-edited', {
        originalContent,
        newContent,
        blockHash: this.blockHash,
        language: this.language
      })
      this.rebuildMarkdownText()
    },
    onMessageChange({ orgContent, newContent }) {
      this.codeText = newContent
      this.rebuildMarkdownText()
    },
    onCanvaChange(newContent) {
      const previousContent = this.previousText
      this.codeText = newContent
      this.previousText = newContent
      // When the block belongs to a chat message, persist the change on that
      // message (replacing only this canva block). Otherwise keep the markdown
      // editor flow (Markdown.vue listens to `text-changed`).
      if (this.message && this.chat) {
        this.saveCanvaToMessage(previousContent, newContent)
      } else {
        this.rebuildMarkdownText()
      }
    },
    // Update the chat message that owns this canva block. Only the matching
    // fenced canva block is replaced; every other part of the message is kept.
    async saveCanvaToMessage(previousContent, newContent) {
      const message = this.message
      const docId = message?.doc_id || message?.id
      const fullContent = message?.content
      if (!docId || !fullContent) {
        this.rebuildMarkdownText()
        return
      }

      const updatedContent = this.replaceCanvaBlock(fullContent, previousContent, newContent)
      if (!updatedContent || updatedContent === fullContent) {
        return
      }

      // Update the message in place so the view refreshes immediately, then
      // persist through the chat store.
      message.content = updatedContent
      message.updated_at = new Date().toISOString()

      await this.$storex.chats.updateMessageContent({
        chat: this.chat,
        doc_id: docId,
        content: updatedContent
      })
    },
    // Replace the fenced canva block whose body matches `oldContent`. Falls back
    // to a plain body replacement when no matching fence is found.
    replaceCanvaBlock(fullContent, oldContent, newContent) {
      const lang = this.language || 'canva'
      const lines = fullContent.split('\n')
      const openFence = /^ {0,3}(?:`{3,}|~{3,})\s*([^\s`~]+)/
      const closeFence = /^ {0,3}(?:`{3,}|~{3,})\s*$/

      for (let i = 0; i < lines.length; i++) {
        const open = lines[i].match(openFence)
        if (!open || open[1] !== lang) continue

        let j = i + 1
        while (j < lines.length && !closeFence.test(lines[j])) j++
        if (j >= lines.length) break

        const body = lines.slice(i + 1, j).join('\n')
        if (body === oldContent) {
          return [
            ...lines.slice(0, i + 1),
            ...newContent.split('\n'),
            ...lines.slice(j)
          ].join('\n')
        }
        i = j
      }

      if (oldContent && fullContent.includes(oldContent)) {
        return fullContent.replace(oldContent, newContent)
      }
      return fullContent
    },
    rebuildMarkdownText() {
      const siblings = this.$parent?.$children?.filter(c => c.$options?.name === undefined
        ? false
        : c.codeText !== undefined) || []

      if (!siblings.length) {
        this.$emit('text-changed', this.buildFence(this.codeText))
        return
      }

      this.$emit('text-changed', { block: this, newContent: this.codeText })
    },
    buildFence(content) {
      const lang = this.language || ''
      const fileHint = this.file ? ` ${this.file}` : ''
      return `\`\`\`${lang}${fileHint}\n${content}\n\`\`\``
    }
  }
}
</script>