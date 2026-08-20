<script setup>
import ChapterBlock from './ChapterBlock.vue'
import parser from '@/utils/markdownParser'
</script>

<template>
  <div class="flex flex-col @container/document">
    <!-- CHANGED: Use chapter.hash as stable key to preserve chapter instances during streaming -->
    <ChapterBlock
      v-for="(chapter, index) in chapters"
      :key="chapter.hash || ('chapter-' + chapter.level + '-' + index)"
      :chapter="chapter"
      :blocks="getChapterBlocks(chapter)"
      :files="files"
      :documentId="documentId"
      :docProject="docProject"
      :chat="chat"
      :message="message"
      :loading="loading"
      @add-file="$emit('add-file', $event)"
      @copy-chapter="handleCopyChapter"
      @create-task="handleCreateTask"
      @generate-code="$emit('generate-code', $event)"
      @reload-file="$emit('reload-file', { file: $event, message })"
      @open-file="$emit('open-file', $event)"
      @save-file="$emit('save-file', $event)"
      @edit-message="$emit('edit-message', $event)"
      @sub-task="$emit('sub-task', $event)"
    >
      <template #chapter-actions="{ chapter, fullContent }">
        <slot 
          name="chapter-actions" 
          :chapter="chapter"
          :full-content="fullContent"
        />
      </template>
    </ChapterBlock>
  </div>
</template>

<script>
export default {
  props: {
    content: { type: String, default: '' },
    files: { type: Array, default: null },
    project: { type: Object, default: null },
    chat: { type: Object, default: null },
    loading: { type: Boolean, default: false },
    documentId: { type: String, default: '' },
    message: { type: Object, default: null }
  },
  emits: [
    'generate-code',
    'reload-file',
    'open-file',
    'save-file',
    'add-file',
    'edit-message',
    'sub-task',
    'copy-chapter',
    'create-task'
  ],
  data() {
    return {
      cachedChapters: [],
      lastContentHash: null
    }
  },
  computed: {
    chapters() {
      // CHANGED: During streaming, always reparse to get new content updates,
      // but chapters with stable hashes won't unmount/remount
      const contentHash = this.loading
        ? this.content
        : this.getContentStructureHash()

      if (this.lastContentHash != null && contentHash === this.lastContentHash) {
        return this.cachedChapters
      }

      this.lastContentHash = contentHash
      this.cachedChapters = parser.parseChapters(this.content || '', this.loading)
      return this.cachedChapters
    },
    docProject() {
      return this.project || this.$project
    }
  },
  methods: {
    getContentStructureHash() {
      const lines = (this.content || '').split('\n')
      let hash = ''
      for (let i = 0; i < lines.length; i++) {
        const line = lines[i]
        if (/^#{1,6}\s+/.test(line) || /^( {0,3})(`{3,}|~{3,})/.test(line)) {
          hash += i + ':' + line + '|'
        }
      }
      return hash
    },
    getChapterBlocks(chapter) {
      const contentWithoutHeader = parser.stripHeaderFromContent(chapter.content || '')
      return parser.parseBlocks(contentWithoutHeader, parser.getRenderer)
    },
    handleCopyChapter(chapterData) {
      this.$emit('copy-chapter', chapterData)
    },
    handleCreateTask(taskData) {
      this.$emit('create-task', taskData)
    }
  }
}
</script>