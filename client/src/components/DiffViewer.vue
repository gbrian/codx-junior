<script setup>
import Editor from './monaco/Editor.vue'
import "@git-diff-view/vue/styles/diff-view.css"
import { DiffView, DiffModeEnum } from "@git-diff-view/vue"
import { generateDiffFile } from "@git-diff-view/file"
</script>

<template>
  <div class="flex flex-col h-full">
    <!-- Toolbar -->
    <div class="flex items-center gap-2 px-2 py-1 text-xs bg-base-200/50 border-b border-base-content/10">
      <!-- View mode toggles (for lightweight viewer) -->
      <div class="flex gap-2 items-center" v-if="!editMode">
        <div class="flex gap-2 items-center">
          <span class="text-xs font-medium opacity-70">Split</span>
          <input type="checkbox" v-model="diffSplit" class="toggle toggle-sm" />
        </div>
        <div class="flex gap-2 items-center">
          <span class="text-xs font-medium opacity-70">Wrap</span>
          <input type="checkbox" v-model="diffWrap" class="toggle toggle-sm" />
        </div>
      </div>

      <!-- Spacer -->
      <div class="flex-1"></div>

      <!-- Edit mode toggle (only when both versions are available) -->
      <button
        v-if="!rawDiff"
        class="btn btn-xs gap-1"
        :class="editMode ? 'btn-warning' : 'btn-ghost'"
        @click="toggleEditMode"
        :title="editMode ? 'Exit edit mode' : 'Enable diff editing with Monaco'"
      >
        <i class="fa-solid fa-edit"></i>
        <span class="hidden sm:inline text-[10px]">{{ editMode ? 'Editing' : 'Edit' }}</span>
      </button>
    </div>

    <!-- Content area -->
    <div class="flex-1 overflow-auto">
      <!-- Edit mode: Monaco DiffEditor -->
      <Editor
        v-if="editMode && orgContent !== null"
        :diff="true"
        :model-value="newContent"
        :original-code="orgContent"
        :language="language"
        :file-name="file"
        :render-side-by-side="true"
        :hide-unchanged="true"
        class="h-full"
        @update:modelValue="onMonacoDiffChange"
      />

      <!-- View mode: Lightweight DiffViewer -->
      <DiffView
        v-else-if="!editMode && (diffFile || diffData)"
        v-bind="diffViewData"
        :diff-view-font-size="14"
        :diff-view-highlight="true"
        :diff-view-add-widget="addWidget"
        :diff-view-theme="'dark'"
        :diff-view-wrap="diffWrap"
        :diffViewMode="diffSplit ? DiffModeEnum.Split : DiffModeEnum.Unified"
        :extend-data="extendData"
      >
        <!-- Pass-through so callers can render per-line widgets (e.g. comments) -->
        <template #widget="widgetProps">
          <slot name="widget" v-bind="widgetProps" />
        </template>
      </DiffView>

      <!-- Empty state -->
      <div v-else class="flex flex-col items-center justify-center h-full gap-2 text-base-content/40 text-sm">
        <i class="fa-solid fa-code-compare text-2xl"></i>
        <span>No diff to display</span>
        <span class="text-xs opacity-60" v-if="contentSameWarning">Both versions appear identical</span>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  components: {
    DiffView,
    Editor
  },
  props: {
    orgContent: { type: String, default: null },
    newContent: { type: String, default: null },
    file: { type: String, default: '' },
    language: { type: String, default: '' },
    // Raw unified diff: used when there are no file contents available
    // (PR review payloads only carry the patch)
    diff: { type: String, default: null },
    // git-diff-view widget button (per line) and per-line data (e.g. comments)
    addWidget: { type: Boolean, default: false },
    extendData: { type: Object, default: () => ({ oldFile: {}, newFile: {} }) }
  },
  emits: ['update:newContent'],
  data() {
    return {
      DiffModeEnum,
      diffFile: null,
      diffData: null,
      diffWrap: false,
      diffSplit: false,
      contentSameWarning: false,
      editMode: false
    }
  },
  computed: {
    /** Only a raw diff was given: render the patch instead of comparing contents */
    rawDiff() {
      return !!this.diff && !this.orgContent && !this.newContent
    },

    /** DiffView accepts either a pre-built DiffFile or raw diff data */
    diffViewData() {
      return this.diffFile ? { diffFile: this.diffFile } : { data: this.diffData }
    }
  },
  watch: {
    orgContent() {
      this.buildDiff()
    },
    newContent() {
      this.buildDiff()
    },
    diff() {
      this.buildDiff()
    }
  },
  created() {
    this.buildDiff()
  },
  methods: {
    buildDiff() {
      const lang = this.language || this.file?.split('.').reverse()[0] || ''
      const fileName = this.file || ''

      this.contentSameWarning = false
      this.diffFile = null
      this.diffData = null

      // Raw git diff mode: no contents to compare, render the hunks directly
      if (this.rawDiff) {
        this.diffData = {
          oldFile: { fileName, fileLang: lang, content: '' },
          newFile: { fileName, fileLang: lang, content: '' },
          hunks: [this.diff]
        }
        return
      }

      const oldContent = this.orgContent || ''
      const newContent = this.newContent || ''

      if (oldContent === newContent) {
        this.contentSameWarning = true
        return
      }

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
    },

    toggleEditMode() {
      this.editMode = !this.editMode
      // Rebuild diff when exiting edit mode to show updated changes
      if (!this.editMode) {
        this.buildDiff()
      }
    },

    onMonacoDiffChange(newValue) {
      this.$emit('update:newContent', newValue)
    }
  }
}
</script>