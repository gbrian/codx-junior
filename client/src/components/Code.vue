<script setup>
import CodeEditor from 'simple-code-editor';
import MermaidViewerVue from './MermaidViewer.vue'
import MarkdownViewer from './MarkdownViewer.vue';
</script>
<template>
  <div class="rounded-md">
    <div class="flex gap-2 w-full justify-end bg-base-100 p-2 rounded-t" ref="toolbar">
      <button class="btn btn-xs tooltip" data-tip="Generate code" @click="$emit('generate-code', codeBlockInfo)">
        <i class="fa-solid fa-file-code"></i> Generate code
      </button>
      <button class="btn btn-xs tooltip" data-tip="Preview HTML"
        @click="htmlPreview = !htmlPreview" v-if="language === 'html'"
      >
        <i class="fa-brands fa-chrome"></i>
      </button>
      <button class="btn btn-xs" @click="showMermaidSource = !showMermaidSource"
        v-if="showMermaid">
        <span v-if="showMermaidSource">View diagram</span>
        <span v-else>View code</span>
      </button>
      <button class="btn btn-xs tooltip" data-tip="Copy" @click="$ui.copyTextToClipboard(code.innerText)">
        <i class="fa-solid fa-copy"></i> Copy
      </button>
    </div>
    <MermaidViewerVue :diagram="codeText" theme="dark" 
      @click="showMermaidSource = !showMermaidSource"
      v-if="showMermaid && !showMermaidSource" />
    <CodeEditor
      line-nums 
      :value="codeText"
      :languages="languages"
      font-size="0.75rem"
      width="100%"
      theme="github-dark"
      :header="false"
      v-if="showCode"
    ></CodeEditor>
    <MarkdownViewer :text="codeText" v-if="showMarkdown" />
    <div class="" v-html="codeText" v-if="htmlPreview"></div>
  </div>
</template>
<script>
const languageMapping = {
  "vue": "html",
  "markdown": "md"
}
export default {
  props: ['code'],
  data () {
    return {
      codeText: null,
      languages: null,
      htmlPreview: false,
      showMermaidSource: false
    }
  },
  created () {
    const language = languageMapping[this.codeLanguage] || this.codeLanguage
    this.languages = [[ language, language.toUpperCase() ]]
    this.codeText = this.code.innerText
    console.log("Code block created", language)
  },
  mounted () {
    this.code.parentNode.after(this.$el)
    this.code.parentNode.remove()
    this.$el.querySelector('.header.border')?.append(this.$refs.toolbar)
  },
  computed: {
    language() {
      const lang = this.code.attributes["class"].value.split("-").reverse()[0]
      return languageMapping[lang] || lang
    },
    codeLanguage () {
      return this.language.includes("mermaid") ? "markdown" : this.language
    },
    showMermaid () {
      return this.language === 'mermaid'
    },
    showCode () {
      return !this.showMarkdown && (!this.showMermaid || this.showMermaidSource) && !this.htmlPreview
    },
    showMarkdown() {
      return this.language === 'md' 
    },
    markdownText () {
      if (this.language === 'md' && false) {
        return this.codeText
      }
      return null
    },
    codeBlockInfo() {
      return {
        code: this.code.innerText,
        language: this.language
      }
    }
  }
}
</script>

