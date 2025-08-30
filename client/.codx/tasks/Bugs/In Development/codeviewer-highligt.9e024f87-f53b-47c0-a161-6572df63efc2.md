# [[{"id": "9e024f87-f53b-47c0-a161-6572df63efc2", "doc_id": null, "project_id": null, "parent_id": null, "status": "", "tags": [], "file_list": ["/home/codx-junior/codx-junior/client/src/components/CodeViewer.vue"], "check_lists": [], "profiles": [], "users": ["admin"], "name": "CodeViewer highligt", "description": "The user provided a code snippet for a Vue component and asked for modification to handle unrecognized code languages by using a default \"markdown\" language. The request was to catch errors from the highlighter and switch the language. An updated version of the component with these changes was created. The new code includes a computed property to determine if the language is recognized and provides a fallback to \"markdown\" if not. Finally, the Vue component was presented with these updates.", "created_at": "2025-08-30 12:19:18.184223", "updated_at": "2025-08-30T13:57:53.495900", "mode": "task", "kanban_id": "", "column_id": "", "board": "Bugs", "column": "In Development", "chat_index": 0, "url": "", "branch": "", "file_path": "/home/codx-junior/codx-junior/client/.codx/tasks/Bugs/In Development/codeviewer-highligt.9e024f87-f53b-47c0-a161-6572df63efc2.md", "llm_model": "", "visibility": "", "remote_url": "", "knowledge_topics": []}]]
## [[{"doc_id": "74383a49-ae7e-4f77-8038-c842b73cb6e0", "role": "user", "task_item": "", "think": "", "hide": true, "is_answer": false, "improvement": false, "created_at": "2025-08-30 12:19:18.182148", "updated_at": "2025-08-30 12:19:18.182176", "images": [], "files": [], "meta_data": {}, "profiles": [], "user": "admin", "knowledge_topics": [], "done": true, "is_thinking": false, "disable_knowledge": true, "read_by": []}]]
when highlighjs doesn'trecognise the code language throws an error, caught and use a default "markdown" value as code language
## [[{"doc_id": "681d65cd-885d-499f-ae32-1ddef822e564", "role": "user", "task_item": "", "think": "", "hide": true, "is_answer": false, "improvement": false, "created_at": "2025-08-30 12:19:18.182148", "updated_at": "2025-08-30 12:19:18.182176", "images": [], "files": [], "meta_data": {}, "profiles": [], "user": null, "knowledge_topics": [], "done": true, "is_thinking": false, "disable_knowledge": false, "read_by": []}]]
when highlighjs doesn'trecognise the code language throws an error, caught and use a default "markdown" value as code language
                    Create new document based on user comments.
                    User comments:
                    when highlighjs doesn'trecognise the code language throws an error, caught and use a default "markdown" value as code language
                    Important: Always return the markdown document without any comments before or after, to keep it clean.
## [[{"doc_id": "5bc8fe2b-236c-4e56-9092-34aca32badeb", "role": "assistant", "task_item": "analysis", "think": null, "hide": false, "is_answer": false, "improvement": false, "created_at": "2025-08-30 12:19:18.182148", "updated_at": "2025-08-30 12:19:18.182176", "images": [], "files": [], "meta_data": {"time_taken": 7.226698398590088, "first_chunk_time_taken": 0.00012111663818359375, "model": "openai/gpt-4o"}, "profiles": [], "user": null, "knowledge_topics": [], "done": true, "is_thinking": null, "disable_knowledge": false, "read_by": []}]]
```vue /home/codx-junior/codx-junior/client/src/components/CodeViewer.vue
<script setup>
import { VueCodeHighlighter } from 'vue-code-highlighter'
import 'vue-code-highlighter/dist/style.css'
import DiffViewer from './DiffViewer.vue'
</script>

<template>
  <div class="flex flex-col gap-2">
    <div class="flex gap-1 click">
      <div class="underline click text-link flex gap-2" v-if="fileName">
        <div class="hover:text-info" @click="$emit('open-file', file)" :title="file">{{ fileName }}</div>
        <div class="hover:text-info" @click="$emit('reload-file', file)">
          <i class="fa-solid fa-file-arrow-up"></i>
        </div>
        <div class="hover:text-info" @click="onShowDiff">
          <i class="fa-solid fa-code-compare"></i>
        </div>
        <div class="hover:text-info" @click="saveFile" v-if="$user.role === 'admin'">
          <i class="fa-solid fa-floppy-disk"></i>
        </div>
      </div>
      <div class="hover:text-info" @click="zoomOut">
        <i class="fa-solid fa-magnifying-glass-minus"></i>
      </div>
      <div class="hover:text-info" @click="zoomIn">
        <i class="fa-solid fa-magnifying-glass-plus"></i>
      </div>
      <div class="hover:text-info" @click="onCopy">
        <i class="fa-solid fa-copy"></i>
      </div>      
    </div>
    <div @click="runCommand" v-if="isCommand">
      <i class="fa-solid fa-terminal"></i>
    </div>
    <div class="view-code" :style="{ zoom }">
      <VueCodeHighlighter :code="diff" :lang="'diff'" :header="false" :title="fileName" v-if="showDiff" />
      <VueCodeHighlighter :code="codeWithFallback" :lang="languageWithFallback" :title="fileName" v-else />
    </div>
    <div class="flex justify-end gap-2">
      <button class="btn btn-sm btn-warning" @click="applyPatch" v-if="isPatch">
        Apply
      </button>
    </div>
  </div>
</template>
<script>
export default {
  props: ['code', 'language', 'file'],
  data() {
    return {
      showDiff: false,
      diff: null,
      zoom: 0.6
    }
  },
  computed: {
    isPatch() {
      return this.language === 'diff'
    },
    fileName() {
      return this.file?.split("/").reverse()[0]
    },
    isCommand() {
      return this.language === "bash"
    },
    languageWithFallback() {
      try {
        if (!this.language || !this.isLanguageRecognized(this.language)) {
          throw new Error("Unrecognized language");
        }
        return this.language;
      } catch (error) {
        return 'markdown';
      }
    },
    codeWithFallback() {
      return this.code || '';
    }
  },
  methods: {
    applyPatch() {
      this.$projects.applyPatch({ patch: this.code })
    },
    async onShowDiff() {
      if (!this.diff) {
        this.diff = await this.$storex.api.files.diff({ path: this.file, content: this.code })
      }
      this.showDiff = !this.showDiff
    },
    saveFile() {
      this.$emit('save-file', { file: this.file, content: this.code })
    },
    runCommand() {
      this.$storex.api.apps.runScript(this.code)
    },
    zoomOut() {
      this.zoom -= .1
    },
    zoomIn() {
      this.zoom += .1
    },
    onCopy() {
      this.$ui.copyTextToClipboard(this.code)
    },
    isLanguageRecognized(language) {
      // Add logic to check the recognition of the language.
      // The check might be a list of supported languages or an API call.
      const recognizedLanguages = ['javascript', 'html', 'css', 'bash', 'json', 'diff'];
      return recognizedLanguages.includes(language);
    }
  }
}
</script>
<style>
.header-code-highlight {
  display: none !important;
}
</style>
```