<script setup>
import ChapterBlock from './ChapterBlock.vue'
</script>

<template>
  <div class="flex flex-col @container/document">
    <ChapterBlock
      v-for="chapter in chapters"
      :key="chapter.hash"
      :chapter="chapter"
      :files="files"
      :documentId="documentId"
      :docProject="docProject"
      :chat="chat"
      :message="message"
      @add-file="$emit('add-file', $event)"
      @copy-chapter="handleCopyChapter"
      @create-task="handleCreateTask"
      @generate-code="$emit('generate-code', $event)"
      @reload-file="$emit('reload-file', { file: $event, message })"
      @open-file="$emit('open-file', $event)"
      @save-file="$emit('save-file', $event)"
      @edit-message="$emit('edit-message', $event)"
      @sub-task="$emit('sub-task', $event)"
    />
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

function getHeadingLevel(line) {
  const match = line.match(/^(#+)\s+/)
  return match ? match[1].length : 0
}

function getHeadingText(line) {
  return line.replace(/^#+\s+/, '').trim()
}

function parseChapters(content, loading) {
  const lines = content.split('\n')
  const chapters = []
  let i = 0

  while (i < lines.length) {
    const line = lines[i]

    if (isHeading(line)) {
      const chapter = parseChapter(lines, i)
      chapters.push(chapter)
      i = chapter.endIndex
    } else if (!chapters.length && line.trim()) {
      // Handle introduction content before any heading
      const introContent = []
      while (i < lines.length && !isHeading(lines[i])) {
        introContent.push(lines[i])
        i++
      }
      const fullContent = introContent.join('\n').trim()
      if (fullContent) {
        chapters.push({
          level: 0,
          title: 'Introduction',
          content: fullContent,
          children: [],
          hash: generateHash(fullContent),
          finished: false
        })
      }
    } else {
      i++
    }
  }

  // Mark all as finished if not loading
  if (!loading) {
    markAllFinished(chapters)
  } else if (chapters.length > 0) {
    markLastUnfinished(chapters)
  }

  return chapters
}

// Parse chapter with full markdown context including header
function parseChapter(lines, startIndex) {
  const headingLine = lines[startIndex]
  const level = getHeadingLevel(headingLine)
  const title = getHeadingText(headingLine)
  const content = [headingLine]
  const children = []
  let i = startIndex + 1

  // Collect content and children
  while (i < lines.length) {
    const line = lines[i]

    if (isHeading(line)) {
      const nextLevel = getHeadingLevel(line)

      // If same or higher level, stop
      if (nextLevel <= level) {
        break
      }

      // If next level is direct child (level + 1), parse as child chapter
      if (nextLevel === level + 1) {
        const childChapter = parseChapter(lines, i)
        children.push(childChapter)
        i = childChapter.endIndex
        continue
      }

      // Otherwise collect as content (nested children will be handled by recursive calls)
      if (nextLevel > level + 1) {
        content.push(line)
        i++
        continue
      }
    }

    content.push(line)
    i++
  }

  const fullContent = content.join('\n')

  return {
    level,
    title,
    content: fullContent,
    children,
    hash: generateHash(fullContent),
    endIndex: i,
    finished: false
  }
}

function markAllFinished(chapters) {
  chapters.forEach(chapter => {
    chapter.finished = true
    if (chapter.children && chapter.children.length) {
      markAllFinished(chapter.children)
    }
  })
}

function markLastUnfinished(chapters) {
  if (!chapters.length) return

  for (let i = chapters.length - 1; i >= 0; i--) {
    const chapter = chapters[i]
    if (chapter.children && chapter.children.length) {
      markLastUnfinished(chapter.children)
      return
    }
    chapter.finished = false
    return
  }
}

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
    return {}
  },
  computed: {
    chapters() {
      return parseChapters(this.content || '', this.loading)
    },
    docProject() {
      return this.project || this.$project
    }
  },
  methods: {
    handleCopyChapter(chapterData) {
      this.$emit('copy-chapter', chapterData)
    },
    handleCreateTask(taskData) {
      this.$emit('create-task', taskData)
    }
  }
}
</script>