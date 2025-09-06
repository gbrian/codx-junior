<script setup>
import "@git-diff-view/vue/styles/diff-view.css";
import { DiffView, DiffModeEnum } from "@git-diff-view/vue";
import { DiffFile, generateDiffFile } from "@git-diff-view/file";
</script>
<template>
  <DiffView
    :diff-file="diffFile"
    :diff-view-font-size="14"
    :diff-view-mode="DiffModeEnum.Split"
    :diff-view-highlight="true"
    :diff-view-add-widget="false"
    :diff-view-wrap="false"
    :diff-view-theme="'dark'"
    v-if="data"
  />
</template>
<script>
export default {
  props: ['orgContent', 'newContent', 'file', 'language', 'diff'],
  data() {
    return {
      data: null,
      diffFile: null
    }
  },
  async created() {
    const language = this.language || this.file.split(".").reverse()[0]
    this.diffFile = generateDiffFile(
                  this.file, 
                  this.orgContent,
                  this.file,
                  this.newContent, 
                  language,
                  language)
    this.diffFile.initRaw()

    this.data = {
      oldFile: {
        fileName: this.file,
        fileLang: this.language,
        content: this.orgContent
      },
      newFile: {
        fileName: this.file,
        fileLang: this.language,
        content: this.newContent
      },
      hunks: this.diff ? [this.diff]: []
    }
  }
}
</script>
