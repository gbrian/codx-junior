<template>
  <div class="dropdown dropdown-top dropdown-open mb-1" v-if="showTermSearch">
    <div tabindex="0" role="button" class="rounded-md bg-base-300 w-fit p-2 hidden">
      <div class="flex p-1 items-center text-sky-600">
        <i class="fa-solid fa-at"></i>
        <input type="text" v-model="termSearchQuery"
          ref="termSearcher"
          class="-ml-1 input input-xs text-lg bg-transparent" placeholder="search term..."
          @keydown.down.stop="onSelNext"
          @keydown.up.stop="onSelPrev"
        />
        <button class="btn btn-xs btn-circle btn-outline btn-error"
          @click="closeTermSearch"
          v-if="termSearchQuery">
          <i class="fa-solid fa-circle-xmark"></i>
        </button>
      </div>
    </div>
    <ul tabindex="0" class="dropdown-content z-[1] menu p-2 shadow bg-base-300 rounded-box w-fit">
      <li class="tooltip text-lg" :data-tip="term.tooltip" v-for="term, ix in searchTerms" :key="term.name">
        <a @click="addSerchTerm(term)">
          <div :class="[searchTermSelIx === ix ? 'underline':'']">
            <span class="text-sky-600 font-bold">@{{ term.name }}</span>
          </div>
        </a>
      </li>
    </ul>
  </div>
</template>
<script>
export default {
  props: ['mentionList', 'content'],
  data() {
    return {
      termSearchQuery: null,
      searchTerms: null,
      searchTermSelIx: -1,
          }
  },
  computed: {
    showTermSearch() {
      return this.searchTerms?.length
    },
    lastWord() {
      return this.content?.split(" ").reverse()[0]
    }
  },
  watch: {
    content(newVal) {
      if (newVal?.length > 2) {
        this.detectSearchTerm()
      } 
    },
  },
  methods: {
    async searchKeywords() {
      this.searchTerms = this.termSearchQuery ? 
        this.mentionList.filter(mention => mention.searchIndex.includes(this.termSearchQuery)) : []
      this.searchTermSelIx = 0
    },
    detectSearchTerm() {
      const mention = this.lastWord[0] === '@' ? this.lastWord?.slice(1) : null      
      this.termSearchQuery = mention?.toLowerCase()
      this.searchKeywords()
      if (this.showTermSearch && !mention) {
        this.closeTermSearch()
      }
    },
    addSerchTerm(mention) {
      this.$emit('select', { 
        orgText: this.lastWord,
        mention
      })
      this.closeTermSearch()
    },
    closeTermSearch() {
      this.searchTerms = null
      this.termSearchQuery = null
    },
    onSelNext() {
      this.searchTermSelIx++
      if (this.searchTermSelIx === this.searchTerms?.length) {
        this.searchTermSelIx = 0
      }
    },
    onSelPrev() {
      this.searchTermSelIx--
      if (this.searchTermSelIx === -1) {
        this.searchTermSelIx = this.searchTerms?.length - 1
      }
    }
  }
}
</script>