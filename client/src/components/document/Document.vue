<script setup>
import ChapterBlock from './ChapterBlock.vue'
import parser from '@/utils/markdownParser'
</script>

<template>
  <div class="flex flex-col @container/document">
    <ChapterBlock
      v-for="(chapter, index) in chapters"
      :key="chapter.hash || ('chapter-' + chapter.level + '-' + index)"
      :chapter="chapter"
      :chapter-path="[index]"
      :blocks="getChapterBlocks(chapter)"
      :files="files"
      :documentId="documentId"
      :docProject="docProject"
      :chat="chat"
      :message="message"
      :loading="loading"
      :editable="editable"
      @add-file="$emit('add-file', $event)"
      @copy-chapter="handleCopyChapter"
      @create-task="handleCreateTask"
      @generate-code="$emit('generate-code', $event)"
      @reload-file="$emit('reload-file', { file: $event, message })"
      @open-file="$emit('open-file', $event)"
      @save-file="$emit('save-file', $event)"
      @edit-message="$emit('edit-message', $event)"
      @sub-task="$emit('sub-task', $event)"
      @block-edited="onBlockEdited"
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
    message: { type: Object, default: null },
    // In-place block editing is only offered where a save target exists (chat
    // messages). Read-only document views keep the plain renderer.
    editable: { type: Boolean, default: false }
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
    'create-task',
    'block-edited'
  ],
  data() {
    return {
      cachedChapters: [],
      lastContentHash: null
    }
  },
  computed: {
    chapters() {
      const contentHash = this.getContentHash()

      if (this.lastContentHash !== null && contentHash === this.lastContentHash && !this.loading) {
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
    getContentHash() {
      const content = this.content || ''
      let hash = 0
      for (let i = 0; i < content.length; i++) {
        const char = content.charCodeAt(i)
        hash = ((hash << 5) - hash) + char
        hash = hash & hash
      }
      return hash.toString()
    },
    getChapterBlocks(chapter) {
      return parser.parseBlocks(parser.getChapterBody(chapter.content || ''), parser.getRenderer)
    },
    handleCopyChapter(chapterData) {
      this.$emit('copy-chapter', chapterData)
    },
    handleCreateTask(taskData) {
      this.$emit('create-task', taskData)
    },
    onBlockEdited(editData) {
      // Preferred path: a chapter emitted its own new source plus its position
      // in the tree. Serializing the parsed tree lets us replace exactly that
      // section (and only that one), so identical blocks in another section are
      // left untouched.
      let fullContent = editData.fullContent
      if (!fullContent && Array.isArray(editData.chapterPath)) {
        fullContent = parser.serializeChapters(this.chapters, {
          path: editData.chapterPath,
          content: editData.newContent,
          replaceChildren: editData.replaceChildren === true
        })
      }

      // Backwards compatible fallback for callers that only send the block.
      if (!fullContent) {
        const { originalContent, newContent } = editData
        fullContent = (this.content || '').replace(originalContent, newContent)
      }

      if (fullContent === this.content) return
      this.$emit('block-edited', {
        ...editData,
        fullContent
      })
    }
  }
}
</script>