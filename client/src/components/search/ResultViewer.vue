<document>

<template>
<div class="modal modal-bottom sm:modal-middle modal-open">
  <div class="modal-box flex flex-col gap-2 w-full max-w-full">
    <div class="font-bold text-wrap">
      {{ showDoc.metadata.source.split('/').reverse()[0] }}
    </div>
    <div class="flex flex-col gap-2 grow h-96 overflow-auto">
      <div class="flex gap-2 items-center">
        <button class="btn btn-xs btn-info" @click.stop="showDoc.docSelected--" :disabled="!showDoc.docSelected">
          <i class="fa-solid fa-backward"></i>
        </button>
        Doc: {{ showDoc.docSelected || 0 }} / {{ showDoc.docs.length - 1 }}
        <button class="btn btn-xs btn-warning" @click.stop="showDoc.docSelected++"
          :disabled="!((showDoc.docSelected || 0) < (showDoc.docs.length - 1))">
          <i class="fa-solid fa-forward"></i>
        </button>
      </div>
      <MarkdownVue class="prose"
        :text="'```json\n' + showDoc.docs[showDoc.docSelected || 0].page_content + '\n```'" />
    </div>
    <div class="text-xs">
      <pre>{{ showDoc.metadata }}</pre>
    </div>
    <div>
      <form class="flex gap-2" method="dialog">
        <button class="btn btn-info text-white" @click="reIndexFile(showDoc)">
          Re-index
        </button>
        <button class="btn btn-info text-white" @click="extractKeywords(showDoc)">
          Keywords
        </button>
        <button class="btn btn-error text-white" @click="unIndexFile(showDoc)">
          Drop file
        </button>
        <div class="grow"></div>
        <button class="btn" @click="showDoc = null">
          Close
        </button>
      </form>
    </div>
  </div>
</div>
</template>

<script>
export default {
  data() {
    return {
      showDoc: {
        docSelected: null,
        docs: [],
        metadata: {
          source: ''
        }
      }
    }
  },
  methods: {
    reIndexFile(doc) {
      // Add logic to re-index the file
    },
    extractKeywords(doc) {
      // Add logic to extract keywords
    },
    unIndexFile(doc) {
      // Add logic to remove file reference
    }
  }
}
</script>

</document>