<script setup>
import MarkdownViewer from '../MarkdownViewer.vue'
import Code from '../Code.vue'
import ChapterBlock from './ChapterBlock.vue'
import EditableBlock from './EditableBlock.vue'
import BlockEditor from '../BlockEditor.vue'
import ChapterMenu from './ChapterMenu.vue'
import parser from '@/utils/markdownParser'
</script>

<template>
  <div 
    class="chapter-block transition-all duration-200 mb-4"
    @mouseenter="isHovered = true"
    @mouseleave="isHovered = false"
  >
    <!-- Chapter header with menu -->
    <div v-if="chapter.level > 0">
      <div class="flex items-center justify-between group/header relative">
        <div :class="'heading-' + chapter.level">
          <h1 v-if="chapter.level === 1" class="text-3xl font-bold">{{ chapter.title }}</h1>
          <h2 v-else-if="chapter.level === 2" class="text-2xl font-bold">{{ chapter.title }}</h2>
          <h3 v-else-if="chapter.level === 3" class="text-xl font-bold">{{ chapter.title }}</h3>
          <h4 v-else-if="chapter.level === 4" class="text-lg font-bold">{{ chapter.title }}</h4>
          <h5 v-else-if="chapter.level === 5" class="font-bold">{{ chapter.title }}</h5>
          <h6 v-else class="font-bold text-sm">{{ chapter.title }}</h6>
        </div>
        
        <!-- Menu: CSS reveals it on hover/focus and keeps it reachable on
             touch devices (where there is no hover). -->
        <ChapterMenu
          v-if="!isEditing"
          :editable="editable"
          @edit="startEditing"
          @copy="copyChapterMarkdown"
          @create-task="createTaskFromChapter"
        >
          <template #chapter-actions>
            <slot 
              name="chapter-actions" 
              :chapter="chapter"
              :full-content="fullChapterContent"
            />
          </template>
        </ChapterMenu>
      </div>
    </div>

    <!-- Edit mode: BlockEditor with all chapter content -->
    <BlockEditor
      v-if="isEditing"
      ref="blockEditor"
      :original-content="fullChapterContent"
      :is-code-block="false"
      @edit-start="onEditStart"
      @edit-cancel="cancelEdit"
      @edit-save="onEditSave"
    >
      <div class="hidden"></div>
    </BlockEditor>

    <!-- View mode: Render blocks within chapter -->
    <div v-else class="space-y-4">
      <div
        v-for="(block, blockIndex) in blocks"
        :key="block.hash + '-' + blockIndex"
        class="group/editable-block relative"
      >
        <!-- Code block: has fileName or comes from CODX file syntax -->
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
          :block-index="blockIndex"
          :editable="editable"
          @generate-code="$emit('generate-code', $event)"
          @reload-file="$emit('reload-file', $event)"
          @open-file="$emit('open-file', $event)"
          @save-file="$emit('save-file', $event)"
          @add-file="$emit('add-file', $event)"
          @edit-message="$emit('edit-message', $event)"
          @block-edited="onBlockEdited"
          @sub-task="onCodeSubTask"
        />
        <!-- Markdown block: rendered as prose, editable as source in place -->
        <EditableBlock
          v-else
          :content="block.content"
          :block-index="blockIndex"
          :editable="editable"
          @save="onBlockEdited"
        >
          <MarkdownViewer
            :files="files"
            :documentId="documentId"
            :text="block.content"
            @add-file="$emit('add-file', $event)"
            @copy-chapter="$emit('copy-chapter', $event)"
            @create-task="onCreateTask"
          />
        </EditableBlock>
      </div>
    </div>

    <!-- Render child chapters -->
    <div v-if="chapter.children && chapter.children.length && !isEditing">
      <ChapterBlock
        v-for="(childChapter, childIndex) in chapter.children"
        :key="childChapter.hash"
        :chapter="childChapter"
        :chapter-path="[...chapterPath, childIndex]"
        :blocks="getChildChapterBlocks(childChapter)"
        :files="files"
        :documentId="documentId"
        :docProject="docProject"
        :loading="loading"
        :chat="chat"
        :message="message"
        :editable="editable"
        @add-file="$emit('add-file', $event)"
        @copy-chapter="handleChildCopy"
        @create-task="onCreateTask"
        @generate-code="$emit('generate-code', $event)"
        @reload-file="$emit('reload-file', $event)"
        @open-file="$emit('open-file', $event)"
        @save-file="$emit('save-file', $event)"
        @edit-message="$emit('edit-message', $event)"
        @sub-task="$emit('sub-task', $event)"
        @block-edited="$emit('block-edited', $event)"
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
    // Position of this chapter in the parsed tree: lets the owner rewrite the
    // exact section after a block edit, even when two sections look the same.
    chapterPath: { type: Array, default: () => [] },
    editable: { type: Boolean, default: false },
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
    'sub-task',
    'block-edited'
  ],
  data() {
    return {
      isHovered: false,
      isEditing: false
    }
  },
  computed: {
    fullChapterContent() {
      return parser.collectAllChildContent(this.chapter)
    }
  },
  methods: {
    getChildChapterBlocks(childChapter) {
      return parser.parseChildBlocks(parser.getChapterBody(childChapter.content || ''), parser.getRenderer)
    },
    isCodeBlock(block) {
      // Legacy fenced blocks expose a fileName, CODX sentinel blocks are
      // flagged with isFileBlock so they always render as code.
      return !!block.fileName || block.isFileBlock === true
    },
    startEditing() {
      this.isEditing = true
      this.$nextTick(() => {
        if (this.$refs.blockEditor) {
          this.$refs.blockEditor.startEdit()
        }
      })
    },
    cancelEdit() {
      this.isEditing = false
    },
    onEditStart() {
      // Edit mode activated
    },
    onEditSave(editData) {
      const { originalContent, newContent } = editData
      this.isEditing = false

      // The chapter editor works on the section INCLUDING its child sections,
      // so the owner must replace the whole subtree (children are re-parsed
      // from the saved text on the next render).
      this.$emit('block-edited', {
        originalContent,
        newContent,
        chapterPath: this.chapterPath,
        replaceChildren: true,
        chapterTitle: this.chapter.title,
        chapterLevel: this.chapter.level
      })
    },
    // A single block (code, mermaid, markdown) saved its new body. Rewrite only
    // that block's line span inside this chapter, then let the owner stitch the
    // chapter back into the message.
    onBlockEdited(editData) {
      const blockIndex = editData.blockIndex
      const nextChapterContent = blockIndex == null
        ? null
        : parser.replaceBlockInChapterContent(
            this.chapter.content,
            blockIndex,
            editData.newContent
          )

      if (nextChapterContent == null || nextChapterContent === this.chapter.content) {
        return
      }

      this.$emit('block-edited', {
        originalContent: this.chapter.content,
        newContent: nextChapterContent,
        chapterPath: this.chapterPath,
        blockIndex,
        chapterTitle: this.chapter.title,
        chapterLevel: this.chapter.level
      })
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
    createTaskFromChapter() {
      const fullContent = this.fullChapterContent
      this.$emit('create-task', {
        title: this.chapter.title,
        content: fullContent
      })
    },
    handleChildCopy(chapterData) {
      this.$emit('copy-chapter', chapterData)
    },
    onCreateTask(taskData) {
      this.$emit('create-task', taskData)
    },
    onCodeSubTask(subTaskData) {
      this.$emit('create-task', {
        title: subTaskData.file ? subTaskData.file.split('/').reverse()[0] : '',
        content: subTaskData.content || ''
      })
    }
  }
}
</script>
