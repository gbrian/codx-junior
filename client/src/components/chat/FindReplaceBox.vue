<script setup>
</script>

<template>
  <div class="flex flex-col gap-3 px-3 py-3 bg-base-100 border-b border-base-300/50">
    <!-- Find input row -->
    <div class="flex gap-2 items-center">
      <input
        ref="findInput"
        type="text"
        placeholder="Find..."
        class="input input-sm input-bordered flex-1 bg-base-200"
        @input="onFindChange"
        @keydown.enter="goToNextMatch"
      />
      <span v-if="matchCount > 0" class="text-xs text-base-content/60 whitespace-nowrap">
        {{ currentMatchIndex + 1 }} / {{ matchCount }}
      </span>
      <button
        class="btn btn-xs btn-ghost"
        title="Previous match"
        @click="goToPreviousMatch"
        :disabled="matchCount === 0"
      >
        <i class="fa-solid fa-chevron-up"></i>
      </button>
      <button
        class="btn btn-xs btn-ghost"
        title="Next match"
        @click="goToNextMatch"
        :disabled="matchCount === 0"
      >
        <i class="fa-solid fa-chevron-down"></i>
      </button>
    </div>

    <!-- Replace input row -->
    <div class="flex gap-2 items-center">
      <input
        ref="replaceInput"
        type="text"
        placeholder="Replace with..."
        class="input input-sm input-bordered flex-1 bg-base-200"
        @keydown.enter="replaceOne"
      />
      <button
        class="btn btn-xs btn-primary"
        title="Replace current match"
        @click="replaceOne"
        :disabled="matchCount === 0"
      >
        <i class="fa-solid fa-replace"></i>
        <span class="hidden sm:inline text-xs">Replace</span>
      </button>
      <button
        class="btn btn-xs btn-primary"
        title="Replace all matches"
        @click="replaceAll"
        :disabled="matchCount === 0"
      >
        <i class="fa-solid fa-share-nodes"></i>
        <span class="hidden sm:inline text-xs">All</span>
      </button>
    </div>

    <!-- Close button -->
    <button
      class="btn btn-xs btn-ghost self-end"
      title="Close find/replace"
      @click="$emit('close')"
    >
      <i class="fa-solid fa-xmark"></i>
    </button>
  </div>
</template>

<script>
export default {
  emits: ['close', 'find-replace'],
  props: {
    editorText: { type: String, default: '' }
  },
  data() {
    return {
      findText: '',
      replaceText: '',
      currentMatchIndex: 0,
      matchCount: 0,
      matches: []
    }
  },
  methods: {
    onFindChange(event) {
      this.findText = event.target.value
      this.currentMatchIndex = 0
      this.updateMatches()
      this.highlightMatches()
    },
    updateMatches() {
      if (!this.findText) {
        this.matches = []
        this.matchCount = 0
        return
      }

      const text = this.editorText
      const searchTerm = this.findText
      const regex = new RegExp(this.escapeRegex(searchTerm), 'gi')
      this.matches = []
      
      let match
      while ((match = regex.exec(text)) !== null) {
        this.matches.push({
          index: match.index,
          length: match[0].length
        })
      }
      
      this.matchCount = this.matches.length
    },
    escapeRegex(str) {
      return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    },
    highlightMatches() {
      this.$emit('find-replace', {
        type: 'highlight',
        matches: this.matches,
        currentIndex: this.currentMatchIndex
      })
    },
    goToNextMatch() {
      if (this.matchCount === 0) return
      this.currentMatchIndex = (this.currentMatchIndex + 1) % this.matchCount
      this.highlightMatches()
      this.scrollToCurrentMatch()
    },
    goToPreviousMatch() {
      if (this.matchCount === 0) return
      this.currentMatchIndex = (this.currentMatchIndex - 1 + this.matchCount) % this.matchCount
      this.highlightMatches()
      this.scrollToCurrentMatch()
    },
    scrollToCurrentMatch() {
      const match = this.matches[this.currentMatchIndex]
      if (!match) return
      
      this.$emit('find-replace', {
        type: 'scroll',
        index: match.index,
        length: match.length
      })
    },
    replaceOne() {
      if (this.matchCount === 0) return
      
      const match = this.matches[this.currentMatchIndex]
      this.$emit('find-replace', {
        type: 'replace-one',
        match,
        replaceText: this.replaceText
      })
      
      this.updateMatches()
      if (this.matchCount > 0) {
        this.currentMatchIndex = Math.min(this.currentMatchIndex, this.matchCount - 1)
        this.highlightMatches()
      }
    },
    replaceAll() {
      if (this.matchCount === 0) return
      
      this.$emit('find-replace', {
        type: 'replace-all',
        findText: this.findText,
        replaceText: this.replaceText
      })
      
      this.updateMatches()
      this.currentMatchIndex = 0
    },
    focusFindInput() {
      this.$nextTick(() => this.$refs.findInput?.focus())
    }
  }
}
</script>