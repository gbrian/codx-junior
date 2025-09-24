<script setup>
import { computed, defineComponent } from 'vue';
import MarkdownViewer from '../MarkdownViewer.vue';
import Code from '../Code.vue';
</script>
<template>
  <div class="flex flex-col">
    <div v-for="(block, index) in blocks" :key="index">
      <MarkdownViewer v-if="block.renderer === 'md'" :text="block.content" />
      <Code 
        :text="block.content"
        :text-language="block.type"
        :fileName="block.fileName"
        @generate-code="$emit('generate-code', $event)" 
        @reload-file="$emit('reload-file', { file: $event, message })"
        @open-file="$emit('open-file', $event)"
        @save-file="$emit('save-file', $event)"
        @edit-message="$emit('edit-message', $event)"
        v-if="block.renderer === 'code'" />
    </div>
  </div>
</template>
<script>
// Define a function to parse the content into an array of objects with type and content
function parseContent(content) {
  const blocks = [];
  const lines = content.split('\n');
  let currentType = 'markdown'; // Default type
  let currentContent = [];
  let currentFileName = '';

  function addBlock() {
    blocks.push({
      type: currentType,
      content: currentContent.join('\n'),
      fileName: currentFileName,
      renderer: ['markdown', 'md'].includes(currentType) ? 'md': 'code'
    });
  }
  lines.forEach(line => {
    const match = line.match(/^```(\w+)\s*(.*)$/);
    if (match) {
      // If there is a match, it means a new block is starting
      if (currentContent.length > 0) {
        addBlock()
      }
      currentType = match[1];
      currentFileName = match[2];
      currentContent = [];
    } else if (line === '```') {
      // End of a block
      if (currentContent.length > 0) {
        addBlock()
      }
      currentType = 'markdown'; // Reset to default type
      currentContent = [];
      currentFileName = '';
    } else {
      currentContent.push(line);
    }
  });

  // Push the last block if any content is left
  if (currentContent.length > 0) {
    addBlock()
  }
  console.log("Document blocks: ", blocks)
  return blocks;
}

export default {
  props: ['content'],
  computed: {
    blocks() {
      return parseContent(this.content)
    }
  }
}
</script>

