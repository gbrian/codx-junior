<script setup>
import MermaidViewerVue from './MermaidViewer.vue'
import MarkdownViewer from './MarkdownViewer.vue'
import CodeViewer from './CodeViewer.vue'
import HTMLPreview from './HTMLPreview.vue'
import BlockEditor from './BlockEditor.vue'
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

      <div class="flex gap-2 w-full justify-end rounded-t" ref="toolbar" v-if="(showMermaid || showHTMLPreview) && !isEditing">
        <button class="btn btn-xs" @click="showMermaidSource = !showMermaidSource" v-if="showMermaid">
          <span v-if="showMermaidSource">View diagram</span>
          <span v-else>View code</span>
        </button>
        <button class="btn btn-sm bg-info/60 my-2 flex gap-2" @click="htmlPreview = !htmlPreview" v-if="showHTMLPreview">
          <span v-if="htmlPreview">View code</span>
          <span v-else><i class="fa-solid fa-tablet-screen-button"></i> View preview</span>
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
      return extension === 'html' && !this.isVibeCoding
    },
    showCode() {
      return !this.showMarkdown && (!this.showMermaid || this.showMermaidSource) && (!this.showHTMLPreview || !this.htmlPreview)
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