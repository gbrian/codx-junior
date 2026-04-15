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
      />
      <Code
        :text="block.content"
        :text-language="block.type"
        :fileName="block.fileName"
        :files="files"
        :project="docProject"
        @generate-code="$emit('generate-code', $event)"
        @reload-file="$emit('reload-file', { file: $event, message })"
        @open-file="$emit('open-file', $event)"
        @save-file="$emit('save-file', $event)"
        @add-file="$emit('add-file', $event)"
        @edit-message="$emit('edit-message', $event)"
        @sub-task="$emit('sub-task', $event)"
        v-else
      />
    </div>
  </div>
</template>

<script>
function generateHash(str) {
  let hash = 0
  for (const char of str) {
    hash = (hash << 5) - hash + char.charCodeAt(0)
    hash |= 0 // Constrain to 32bit integer
  }
  return hash
}

function getRenderer(blockType) {
  if (['markdown', 'md'].includes(blockType)) {
    return 'md'
  }
  if (['html'].includes(blockType)) {
    return blockType
  }
  return 'code'
}

function parseContent(content) {
  const blocks = [];
  const lines = content.split('\n');
  let currentType = 'markdown'; // Default type
  let currentContent = [];
  let currentFileName = '';
  let fenceCount = 0

  function addBlock() {
    const content = currentContent.join('\n')
    const hash = generateHash(content)
    blocks.push({
      type: currentType,
      content,
      hash,
      fileName: currentFileName,
      renderer: getRenderer(currentType)
    });
    currentType = 'markdown'; // Default type
    currentContent = [];
    currentFileName = '';
    fenceCount = 0
  }
  lines.forEach(line => {
    const match = line.trim().match(/^```(\w+)\s*(.*)$/);
    if (match){
      if (!fenceCount) {
        if (currentContent.length) {
          addBlock()
        }
        currentType = match[1];
        currentFileName = match[2];
      }      
      fenceCount++
    } else if (line.trim() === '```') {
      // End of a block
      --fenceCount
      if (!fenceCount && currentContent.length > 0) {
        addBlock()
      }
    } else if (currentContent) {
      currentContent.push(line);
    }
  });

  // Push the last block if any content is left
  if (currentContent) {
    addBlock()
  }
  console.log("Document blocks: ", blocks)
  return blocks;
}

export default {
  props: ['content', 'files', 'project'],
  computed: {
    blocks() {
      return parseContent(this.content || '')
    },
    docProject() {
      return this.project || this.$project
    },
  },
}
</script>