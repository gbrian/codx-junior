<script setup>
import MarkdownViewer from '../MarkdownViewer.vue';
import Code from '../Code.vue';
import HTMLViewer from '../HTMLViewer.vue';
</script>

<template>
  <div class="flex flex-col @container/document">
    <div v-for="block in blocks" :key="block.hash">
      <MarkdownViewer
        :files="files"
        v-if="block.renderer === 'md'"
        :text="block.content"
        @add-file="$emit('add-file', $event)"
      />
      <Code
        :class="!block.finished && 'border border-dashed border-slate-400'"
        :text="block.content"
        :text-language="block.type"
        :fileName="block.fileName"
        :files="files"
        :project="docProject"
        :finished="block.finished"
        :chat="chat"
        @generate-code="$emit('generate-code', $event)"
        @reload-file="$emit('reload-file', { file: $event, message })"
        @open-file="$emit('open-file', $event)"
        @save-file="$emit('save-file', $event)"
        @add-file="$emit('add-file', $event)"
        @edit-message="$emit('edit-message', $event)"
        @sub-task="$emit('sub-task', $event)"
        v-else
      />
      <div class="chat-footer opacity-50 text-xs font-bold" v-if="!block.finished">
        loading <span class="loading loading-spinner"></span>
      </div>
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

function getRenderer(blockType) {
  if (['markdown', 'md'].includes(blockType)) return 'md'
  if (['html'].includes(blockType)) return blockType
  return 'code'
}

function parseContent(content, loading) {
  const blocks = []
  const lines = content.split('\n')
  let currentType = 'markdown'
  let currentContent = []
  let currentFileName = ''
  // Track nesting depth: 0 = markdown level, 1+ = inside typed block(s)
  let nestingDepth = 0

  function setAllFinished() {
    blocks.forEach(b => b.finished = true)
  }

  function addBlock() {
    const blockContent = currentContent.join('\n')
    const hash = generateHash(blockContent)
    setAllFinished()
    blocks.push({
      type: currentType,
      content: blockContent,
      hash,
      fileName: currentFileName,
      renderer: getRenderer(currentType),
      finished: false
    })
    // Reset state
    currentType = 'markdown'
    currentContent = []
    currentFileName = ''
  }

  for (const line of lines) {
    const openMatch = line.match(/^```(\w+)\s*(.*)$/)
    const closeMatch = line === '```'

    if (nestingDepth === 0 && openMatch) {
      // At top level: opening a new typed block — flush any markdown content first
      if (currentContent.length) {
        addBlock()
      }
      nestingDepth = 1
      currentType = openMatch[1]
      currentFileName = openMatch[2] || ''
    } else if (nestingDepth === 1 && closeMatch) {
      // Closing the top-level typed block
      addBlock()
      nestingDepth = 0
    } else if (nestingDepth >= 1 && openMatch) {
      // Nested opening inside a typed block — treat as content, increase depth
      nestingDepth++
      currentContent.push(line)
    } else if (nestingDepth > 1 && closeMatch) {
      // Closing a nested block — treat as content, decrease depth
      nestingDepth--
      currentContent.push(line)
    } else {
      // Regular content line at any level
      currentContent.push(line)
    }
  }

  // Flush any remaining content
  if (currentContent.length) {
    addBlock()
  }
  if (!loading) {
    setAllFinished()
  }
  return blocks
}

export default {
  props: ['content', 'files', 'project', 'chat', 'loading'],
  emits: ['generate-code', 'reload-file', 'open-file', 'save-file', 'add-file', 'edit-message', 'sub-task'],
  computed: {
    blocks() {
      return parseContent(this.content || '', this.loading)
    },
    docProject() {
      return this.project || this.$project
    },
  },
}
</script>