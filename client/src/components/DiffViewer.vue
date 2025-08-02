<script setup>
import "@git-diff-view/vue/styles/diff-view.css";
import { DiffView, DiffModeEnum } from "@git-diff-view/vue";
import { DiffFile, generateDiffFile } from "@git-diff-view/file";
</script>
<template>
  <DiffView
    :data="data"
    :diff-view-font-size="14"
    :diff-view-mode="DiffModeEnum.Split"
    :diff-view-highlight="true"
    :diff-view-add-widget="false"
    :diff-view-wrap="false"
    :diff-view-theme="'dark'"
    :extend-data="{oldFile: {10: {data: 'foo'}}, newFile: {20: {data: 'bar'}}}"
    v-if="data"
  />
</template>
<script>
export default {
  props: ['orgContent', 'newContent', 'file', 'language', 'diff'],
  data() {
    return {
      data: null
    }
  },
  async created() {
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
      hunks: [this.diff]
    }
  }
}
</script>
