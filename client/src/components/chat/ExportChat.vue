<template>
  <div class="flex flex-col gap-4">
    <h3 class="text-2xl">Export Chat</h3>
    <div class="flex flex-col gap-2">
      <label class="flex gap-2 items-center">
        <input type="radio" class="radio" value="markdown" v-model="exportFormat" />
        As document (markdown)
      </label>
      <label class="flex gap-2 items-center">
        <input type="radio" class="radio" value="docx" v-model="exportFormat" />
        As Word
      </label>
      <label class="flex gap-2 items-center">
        <input type="radio" class="radio" value="pdf" v-model="exportFormat" />
        As PDF
      </label>
      <div class="flex justify-end gap-2">
        <button class="btn" @click="exportChat(false)" :disabled="loading">
          <span class="loading loading-spinner loading-xs" v-if="loading"></span>
          <i class="fa-solid fa-cloud-arrow-down" v-else></i> Download
        </button>
        <button class="btn" @click="exportChat(true)" :disabled="loading">
          <span class="loading loading-spinner loading-xs" v-if="loading"></span>
          <i class="fa-solid fa-copy" v-else></i> Copy
        </button>
      </div>
    </div>
  </div>
</template>

<script>
/**
 * asciidoc, asciidoctor, beamer, biblatex, bibtex, commonmark, commonmark_x, context, csljson, 
 * docbook, docbook4, docbook5, docx, dokuwiki, dzslides, epub, epub2, epub3, fb2, 
 * gfm, haddock, html, html4, html5, icml, ipynb, jats, jats_archiving, jats_articleauthoring, 
 * jats_publishing, jira, json, latex, man, markdown, markdown_github, markdown_mmd, 
 * markdown_phpextra, markdown_strict, markua, mediawiki, ms, muse, native, odt, 
 * opendocument, opml, org, pdf, plain, pptx, revealjs, rst, rtf, s5, 
 * slideous, slidy, tei, texinfo, textile, xwiki, zimwiki"
 */
export default {
  props: ['chat'],
  data() {
    return {
      exportFormat: 'markdown',
      loading: false
    };
  },
  methods: {
    async exportChat(clipboard) {
      const { chat, exportFormat } = this
      try {
          this.loading = true
          const data = await this.$projects.exportChat({ chat, exportFormat, clipboard })
          if (clipboard) {  
            this.copyFile(data)
          }
      } finally {
        this.loading = false
      }
      this.$emit('close')
    },
    downloadFile(data) {
      console.log("Exported data", data)
      const { chat, exportFormat } = this
      // Create a Blob from the data
      const blob = new Blob([data], { type: 'text/plain' }); // Adjust the MIME type as needed
      
      // Create an object URL from the Blob
      const url = window.URL.createObjectURL(blob);
      
      // Create an anchor element
      const a = document.createElement('a');
      a.style.display = 'none';
      a.href = url;
      a.download = `export_${chat.name}.${exportFormat}`; // Set the file name with appropriate extension
      
      // Append the anchor to the body
      document.body.appendChild(a);
      
      // Trigger a click event on the anchor
      a.click();
      
      // Remove the anchor from the document
      document.body.removeChild(a);
      
      // Revoke the object URL to free up memory
      window.URL.revokeObjectURL(url);
    },
    copyFile(data) {
      console.log("Copying data", data)
      this.$ui.copyTextToClipboard(data)
    }
  },
};
</script>