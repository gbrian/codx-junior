<script setup>
import MarkdownViewer from '../MarkdownViewer.vue'
import Code from '../Code.vue'
import ChapterBlock from './ChapterBlock.vue'
import parser from '@/utils/markdownParser'
</script>

<template>
  <div 
    class="chapter-block transition-all duration-200 mb-4"
    @mouseenter="isHovered = true"
    @mouseleave="isHovered = false"
  >
    <!-- Chapter header with copy button -->
    <div v-if="chapter.level > 0">
      <div class="flex items-center justify-between group/header">
        <div :class="'heading-' + chapter.level">
          <h1 v-if="chapter.level === 1" class="text-3xl font-bold">{{ chapter.title }}</h1>
          <h2 v-else-if="chapter.level === 2" class="text-2xl font-bold">{{ chapter.title }}</h2>
          <h3 v-else-if="chapter.level === 3" class="text-xl font-bold">{{ chapter.title }}</h3>
          <h4 v-else-if="chapter.level === 4" class="text-lg font-bold">{{ chapter.title }}</h4>
          <h5 v-else-if="chapter.level === 5" class="font-bold">{{ chapter.title }}</h5>
          <h6 v-else class="font-bold text-sm">{{ chapter.title }}</h6>
        </div>
        <div class="hidden group-hover/header:flex gap-2 items-center">
          <slot 
            name="chapter-actions" 
            :chapter="chapter"
            :full-content="fullChapterContent"
          >
            <button
              class="btn btn-sm btn-ghost gap-2"
              @click="copyChapterMarkdown"
              :title="'Copy chapter: ' + chapter.title"
            >
              <i class="fa-solid fa-copy"></i>
              Copy
            </button>
          </slot>
        </div>
      </div>
    </div>

    <!-- Render blocks within chapter -->
    <div class="space-y-4">
      <!-- CHANGED: Use block.hash as stable key to prevent unmounting during streaming -->
      <div v-for="block in blocks" 
        :key="block.hash">
        <!-- Code block: has fileName or has type with synthetic fileName -->
        <Code
          v-if="isCodeBlock(block)"
          :text="block.content"
          :text-language="block.type"
          :fileName="block.fileName"
          :files="files"
          :project="docProject"
          :finished="block.finished"
          :loading="loading"
          :chat="chat"
          :message="message"
          :block-hash="block.hash"
          @generate-code="$emit('generate-code', $event)"
          @reload-file="$emit('reload-file', $event)"
          @open-file="$emit('open-file', $event)"
          @save-file="$emit('save-file', $event)"
          @add-file="$emit('add-file', $event)"
          @edit-message="$emit('edit-message', $event)"
          @sub-task="$emit('sub-task', $event)"
        />
        <!-- Markdown block: no fileName and markdown/md type -->
        <MarkdownViewer
          v-else
          :files="files"
          :documentId="documentId"
          :text="block.content"
          @add-file="$emit('add-file', $event)"
          @copy-chapter="$emit('copy-chapter', $event)"
          @create-task="$emit('create-task', $event)"
        />        
      </div>
    </div>

    <!-- Render child chapters -->
    <div v-if="chapter.children && chapter.children.length">
      <ChapterBlock
        v-for="childChapter in chapter.children"
        :key="childChapter.hash"
        :chapter="childChapter"
        :blocks="getChildChapterBlocks(childChapter)"
        :files="files"
        :documentId="documentId"
        :docProject="docProject"
        :loading="loading"
        :chat="chat"
        :message="message"
        @add-file="$emit('add-file', $event)"
        @copy-chapter="handleChildCopy"
        @create-task="$emit('create-task', $event)"
        @generate-code="$emit('generate-code', $event)"
        @reload-file="$emit('reload-file', $event)"
        @open-file="$emit('open-file', $event)"
        @save-file="$emit('save-file', $event)"
        @edit-message="$emit('edit-message', $event)"
        @sub-task="$emit('sub-task', $event)"
      >
        <template #chapter-actions="{ chapter: childChapter, fullContent }">
          <slot 
            name="chapter-actions" 
            :chapter="childChapter"
            :full-content="fullContent"
          />
        </template>
      </ChapterBlock>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    chapter: { type: Object, required: true },
    blocks: { type: Array, required: true },
    files: { type: Array, default: null },
    documentId: { type: String, default: '' },
    docProject: { type: Object, default: null },
    loading: { type: Boolean, default: false },
    chat: { type: Object, default: null },
    message: { type: Object, default: null }
  },
  emits: [
    'add-file',
    'copy-chapter',
    'create-task',
    'generate-code',
    'reload-file',
    'open-file',
    'save-file',
    'edit-message',
    'sub-task'
  ],
  data() {
    return {
      isHovered: false
    }
  },
  computed: {
    fullChapterContent() {
      return parser.collectAllChildContent(this.chapter)
    }
  },
  methods: {
    getChildChapterBlocks(childChapter) {
      const contentWithoutHeader = parser.stripHeaderFromContent(childChapter.content || '')
      return parser.parseChildBlocks(contentWithoutHeader, parser.getRenderer)
    },
    isCodeBlock(block) {
      return !!block.fileName
    },
    copyChapterMarkdown() {
      const fullContent = this.fullChapterContent
      navigator.clipboard.writeText(fullContent).then(() => {
        this.$emit('copy-chapter', {
          title: this.chapter.title,
          content: fullContent,
          level: this.chapter.level
        })
      }).catch(err => {
        console.error('Failed to copy chapter markdown', err)
      })
    },
    handleChildCopy(chapterData) {
      this.$emit('copy-chapter', chapterData)
    }
  }
}
</script>