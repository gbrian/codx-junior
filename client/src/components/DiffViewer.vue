<template>
  <div class="flex flex-col h-full">
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

    <div class="flex-1 overflow-auto">
      <DiffView
        :diff-view-font-size="14"
        :diff-view-highlight="true"
        :diff-view-add-widget="false"
        :diff-view-theme="'dark'"
        :diff-view-wrap="diffWrap"
        :diffViewMode="diffSplit ? DiffModeEnum.Split : DiffModeEnum.Unified"
        :diffFile="diffFile"
        v-if="diffFile"
      />
      <div v-else class="flex flex-col items-center justify-center h-full gap-2 text-base-content/40 text-sm">
        <i class="fa-solid fa-code-compare text-2xl"></i>
        <span>No diff to display</span>
        <span class="text-xs opacity-60" v-if="contentSameWarning">Both versions appear identical</span>
      </div>
    </div>
  </div>
</template>

<script>
import "@git-diff-view/vue/styles/diff-view.css"
import { DiffView, DiffModeEnum } from "@git-diff-view/vue"
import { generateDiffFile } from "@git-diff-view/file"

export default {
  components: {
    DiffView
  },
  props: ['orgContent', 'newContent', 'file', 'language', 'diff'],
  data() {
    return {
      DiffModeEnum, // Expose enum to template
      diffFile: null,
      diffWrap: false,
      diffSplit: false,
      contentSameWarning: false
    }
  },
  watch: {
    orgContent() { this.buildDiff() },
    newContent() { this.buildDiff() },
    diff()       { this.buildDiff() }
  },
  created() {
    this.buildDiff()
  },
  methods: {
    buildDiff() {
      const oldContent = this.orgContent || ''
      const newContent = this.newContent || ''
      const lang = this.language || this.file?.split('.').reverse()[0] || ''
      const fileName = this.file || ''

      // Warn and bail early when content is identical — nothing to diff
      if (oldContent === newContent) {
        this.contentSameWarning = true
        this.diffFile = null
        console.warn('[DiffViewer] orgContent and newContent are identical, no diff to render')
        return
      }

      this.contentSameWarning = false

      try {
        const diffFile = generateDiffFile(
          fileName, oldContent,
          fileName, newContent,
          lang, lang
        )
        diffFile.init()
        diffFile.buildSplitDiffLines()
        diffFile.buildUnifiedDiffLines()
        this.diffFile = diffFile
      } catch (err) {
        console.error('[DiffViewer] generateDiffFile failed:', err)
        this.diffFile = null
      }
    }
  }
}
</script>
