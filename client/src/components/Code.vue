<script setup>
import hljs from 'highlight.js';
import CodeEditor from 'simple-code-editor';
import MermaidViewerVue from './MermaidViewer.vue'
</script>
<template>
  <div>
    <div class="flex gap-2 w-full justify-center" ref="toolbar">
      <button class="btn btn-xs tooltip" data-tip="Generate code" @click="$emit('generate-code', code.innerText)">
        <i class="fa-solid fa-file-code"></i>
      </button>
      <button class="btn btn-xs tooltip" data-tip="Preview HTML"
        @click="htmlPreview = !htmlPreview" v-if="language === 'html'"
      >
        <i class="fa-brands fa-chrome"></i>
      </button>
    </div>
    <MermaidViewerVue :diagram="codeText" v-if="showMermaid" />
    <CodeEditor
      line-nums 
      :value="codeText"
      :languages="languages"
      width="100%"
      theme="github-dark"
      v-if="showCode"
    ></CodeEditor>
    <div class="" v-html="this.codeText" v-if="htmlPreview"></div>
  </div>
</template>
<script>
export default {
  props: ['code'],
  data () {
    return {
      codeText: null,
      languages: null,
      htmlPreview: false
    }
  },
  created () {
    const language = this.language
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
      return this.code.attributes["class"].value.split("-").reverse()[0]
    },
    showMermaid () {
      return this.language === 'mermaid'
    },
    showCode () {
      return !this.showMermaid && ! this.htmlPreview
    }
  }
}
</script>

