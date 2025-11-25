<script setup>
import "@git-diff-view/vue/styles/diff-view.css";
import { DiffView, DiffModeEnum } from "@git-diff-view/vue";
import { DiffFile, generateDiffFile } from "@git-diff-view/file";
</script>
<template>
  <div>
    <div class="flex items-center gap-2 px-2 py-1 text-xs">
      <div class="flex gap-2 items-center">
        Split / Unified
        <input type="checkbox" v-model="diffSplit" class="toggle toggle-sm" />
      </div>
      <div class="flex gap-2 items-center">
        Text wrap
        <input type="checkbox" v-model="diffWrap" class="toggle toggle-sm" />
      </div>
  </div>

  <DiffView
    :diff-file="diffFile"
    :diff-view-font-size="14"
    :diff-view-highlight="true"
    :diff-view-add-widget="false"
    :diff-view-theme="'dark'"
    :diff-view-wrap="diffWrap"
    :diffViewMode="diffSplit ? DiffModeEnum.Split : DiffModeEnum.Unified"          
    v-if="data"
  />
</div>
</template>
<script>
export default {
  props: ['orgContent', 'newContent', 'file', 'language', 'diff'],
  data() {
    return {
      data: null,
      diffFile: null,
      diffWrap: true,
      diffSplit: false
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
