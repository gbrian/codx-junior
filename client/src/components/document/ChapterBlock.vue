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
      <div v-for="block in blocks" :title="`${block.type} - ${block.fileName}`" 
        :key="block.hash">
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
          v-if="block.fileName"
        />
        <MarkdownViewer
          :files="files"
          :documentId="documentId"
          :text="block.content"
          @add-file="$emit('add-file', $event)"
          @copy-chapter="$emit('copy-chapter', $event)"
          @create-task="$emit('create-task', $event)"
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

function isMarkdownBlockType(blockType) {
  return ['markdown', 'md'].includes(blockType)
}

// Detect fence markers (``` or ~~~) with optional info string
function getFence(line) {
  const match = line.match(/^( {0,3})(`{3,}|~{3,})(.*)$/)
  if (!match) return null

  return {
    char: match[2][0],
    length: match[2].length,
    info: match[3].trim()
  }
}

function isClosingFence(line, fence) {
  const lineFence = getFence(line)
  return !!(
    lineFence &&
    fence &&
    lineFence.char === fence.char &&
    lineFence.length >= fence.length &&
    !lineFence.info
  )
}

// Count matching closing fences after fromIndex
// Used to disambiguate anonymous fences inside markdown blocks
function countClosingFencesAhead(lines, fromIndex, fence) {
  let count = 0
  for (let i = fromIndex + 1; i < lines.length; i++) {
    if (isClosingFence(lines[i], fence)) count++
  }
  return count
}

// An anonymous fence inside a markdown block opens a nested block
// only if enough closing fences remain to also close the outer block
function isNestedAnonymousFence(lines, index, currentType, currentFence) {
  return (
    isMarkdownBlockType(currentType) &&
    countClosingFencesAhead(lines, index, currentFence) >= 2
  )
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
    // Parse content into blocks, keeping nested fences inside markdown file blocks
    parseChildBlocks(content) {
      const blocks = []
      const lines = content.split('\n')
      let currentType = 'markdown'
      let currentContent = []
      let currentFileName = ''
      let inCodeBlock = false
      let currentFence = null
      let nestedFences = []

      const setAllFinished = () => {
        blocks.forEach(b => (b.finished = true))
      }

      const resetCurrentBlock = () => {
        currentType = 'markdown'
        currentContent = []
        currentFileName = ''
        currentFence = null
        nestedFences = []
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
          renderer: this.getRenderer(currentType, currentFileName),
          finished: false
        })
        resetCurrentBlock()
      }

      for (let i = 0; i < lines.length; i++) {
        const line = lines[i]
        const fence = getFence(line)

        if (!inCodeBlock && fence && fence.info) {
          if (currentContent.length) addBlock()
          const infoParts = fence.info.split(/\s+/).filter(Boolean)
          inCodeBlock = true
          currentFence = fence
          currentType = infoParts[0] || 'text'
          currentFileName = infoParts.slice(1).join(' ')
          continue
        }

        if (inCodeBlock) {
          const nestedFence = nestedFences[nestedFences.length - 1]

          if (nestedFence && isClosingFence(line, nestedFence)) {
            nestedFences.pop()
            currentContent.push(line)
            continue
          }

          if (isMarkdownBlockType(currentType) && fence && fence.info && !isClosingFence(line, currentFence)) {
            nestedFences.push(fence)
            currentContent.push(line)
            continue
          }

          if (!nestedFences.length && isClosingFence(line, currentFence)) {
            // Anonymous fence: pre-count ahead to decide open vs close
            if (isNestedAnonymousFence(lines, i, currentType, currentFence)) {
              nestedFences.push(fence)
              currentContent.push(line)
              continue
            }
            addBlock()
            inCodeBlock = false
            continue
          }
        }

        currentContent.push(line)
      }

      if (currentContent.length) addBlock()
      setAllFinished()
      return blocks
    },
    // Blocks with a file path are always rendered as code files
    getRenderer(blockType, fileName) {
      if (fileName) return 'code'
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