<script setup>
import MarkdownViewer from '../MarkdownViewer.vue'
import Code from '../Code.vue'
import ChapterBlock from './ChapterBlock.vue'
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
        <div :class="`heading-${chapter.level}`">
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
              :title="`Copy chapter: ${chapter.title}`"
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
      <div v-for="block in blocks" :key="block.hash">
        <MarkdownViewer
          :files="files"
          :documentId="documentId"
          v-if="block.renderer === 'md'"
          :text="block.content"
          @add-file="$emit('add-file', $event)"
          @copy-chapter="$emit('copy-chapter', $event)"
          @create-task="$emit('create-task', $event)"
        />
        <Code
          :text="block.content"
          :text-language="block.type"
          :fileName="block.fileName"
          :files="files"
          :project="docProject"
          :finished="block.finished"
          :chat="chat"
          :message="message"
          @generate-code="$emit('generate-code', $event)"
          @reload-file="$emit('reload-file', $event)"
          @open-file="$emit('open-file', $event)"
          @save-file="$emit('save-file', $event)"
          @add-file="$emit('add-file', $event)"
          @edit-message="$emit('edit-message', $event)"
          @sub-task="$emit('sub-task', $event)"
          v-else
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
function generateHash(str) {
  let hash = 0
  for (const char of str) {
    hash = (hash << 5) - hash + char.charCodeAt(0)
    hash |= 0
  }
  return hash
}

function isHeading(line) {
  return /^#{1,6}\s+/.test(line)
}

function getHeaderLine(content) {
  const lines = content.split('\n')
  return lines.length > 0 && isHeading(lines[0]) ? lines[0] : ''
}

function stripHeaderFromContent(content) {
  const lines = content.split('\n')
  if (lines.length > 0 && isHeading(lines[0])) {
    return lines.slice(1).join('\n').trim()
  }
  return content
}

// Check if we're inside a code fence at this line index
function isInsideCodeFence(lines, lineIndex) {
  let inCodeFence = false
  for (let i = 0; i < lineIndex; i++) {
    if (lines[i].match(/^```/)) {
      inCodeFence = !inCodeFence
    }
  }
  return inCodeFence
}

function collectAllChildContent(chapter) {
  const headerLine = getHeaderLine(chapter.content)
  const contentWithoutHeader = stripHeaderFromContent(chapter.content)
  let allContent = contentWithoutHeader

  if (chapter.children && chapter.children.length) {
    chapter.children.forEach(child => {
      const childFullContent = collectAllChildContent(child)
      allContent += '\n\n' + childFullContent
    })
  }

  return headerLine ? headerLine + '\n\n' + allContent : allContent
}

export default {
  props: {
    chapter: { type: Object, required: true },
    blocks: { type: Array, required: true },
    files: { type: Array, default: null },
    documentId: { type: String, default: '' },
    docProject: { type: Object, default: null },
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
      return collectAllChildContent(this.chapter)
    }
  },
  methods: {
    getChildChapterBlocks(childChapter) {
      const contentWithoutHeader = stripHeaderFromContent(childChapter.content || '')
      return this.parseChildBlocks(contentWithoutHeader)
    },
    parseChildBlocks(content) {
      const blocks = []
      const lines = content.split('\n')
      let currentType = 'markdown'
      let currentContent = []
      let currentFileName = ''
      let inCodeBlock = false

      const setAllFinished = () => {
        blocks.forEach(b => (b.finished = true))
      }

      const addBlock = () => {
        const blockContent = currentContent.join('\n')
        const hash = generateHash(blockContent)
        setAllFinished()
        blocks.push({
          type: currentType,
          content: blockContent,
          hash,
          fileName: currentFileName,
          renderer: this.getRenderer(currentType),
          finished: false
        })
        currentType = 'markdown'
        currentContent = []
        currentFileName = ''
      }

      for (const line of lines) {
        const openMatch = line.match(/^```([^\s]+)\s*(.*)$/)
        const closeMatch = line === '```'

        if (!inCodeBlock && openMatch) {
          if (currentContent.length) addBlock()
          inCodeBlock = true
          currentType = openMatch[1]
          currentFileName = openMatch[2] || ''
        } else if (inCodeBlock && closeMatch) {
          addBlock()
          inCodeBlock = false
        } else {
          currentContent.push(line)
        }
      }

      if (currentContent.length) addBlock()
      setAllFinished()
      return blocks
    },
    getRenderer(blockType) {
      if (['markdown', 'md'].includes(blockType)) return 'md'
      if (['html'].includes(blockType)) return blockType
      return 'code'
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