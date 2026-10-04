<script setup>
</script>

<template>
  <div class="flex flex-col gap-2">
    <!-- Current tags -->
    <div v-if="tags.length" class="flex flex-wrap gap-1.5" role="list" aria-label="Model tags">
      <span
        v-for="tag in tags"
        :key="tag"
        role="listitem"
        class="badge badge-sm badge-outline badge-accent gap-1"
      >
        <i class="fa-solid fa-tag text-[10px]" aria-hidden="true"></i>
        {{ tag }}
        <button
          type="button"
          class="hover:text-error transition-colors"
          :aria-label="`Remove tag ${tag}`"
          @click="removeTag(tag)"
        >
          <i class="fa-solid fa-xmark text-[10px]" aria-hidden="true"></i>
        </button>
      </span>
    </div>
    <span v-else class="text-xs text-base-content/40">No tags yet — add one below.</span>

    <!-- Add tag input -->
    <div class="join w-full">
      <input
        v-model="newTag"
        list="model-tag-suggestions"
        type="text"
        class="input input-bordered input-sm join-item grow font-mono text-xs"
        placeholder="Add a tag and press Enter…"
        @keydown="onKeydown"
        @blur="commitTag"
      />
      <button
        type="button"
        class="btn btn-sm btn-secondary join-item"
        :disabled="!newTag.trim()"
        title="Add tag"
        @click="commitTag"
      >
        <i class="fa-solid fa-plus"></i>
      </button>
    </div>
    <datalist id="model-tag-suggestions">
      <option v-for="s in availableSuggestions" :key="s" :value="s"></option>
    </datalist>

    <!-- Quick-add suggestions from other models -->
    <div v-if="availableSuggestions.length" class="flex flex-wrap gap-1.5">
      <button
        v-for="s in availableSuggestions"
        :key="s"
        type="button"
        class="btn btn-xs btn-ghost border border-base-content/15 gap-1"
        @click="addTag(s)"
      >
        <i class="fa-solid fa-plus text-[10px]" aria-hidden="true"></i>
        {{ s }}
      </button>
    </div>

    <label class="label py-0.5">
      <span class="label-text-alt text-xs text-base-content/50">
        Tag models by task (e.g. image, vision, coding, design). Press Enter or comma to add.
      </span>
    </label>
  </div>
</template>

<script>
export default {
  props: {
    modelValue: { type: Array, default: () => [] },
    // Suggested tags (usually collected from other models)
    suggestions: { type: Array, default: () => [] }
  },
  emits: ['update:modelValue'],
  data() {
    return {
      newTag: ''
    }
  },
  computed: {
    tags() {
      return Array.isArray(this.modelValue) ? this.modelValue : []
    },
    // Suggestions not already applied, capped for a compact UI
    availableSuggestions() {
      const existing = this.tags.map(tag => tag.toLowerCase())
      return (this.suggestions || [])
        .filter(s => s && !existing.includes(s.toLowerCase()))
        .slice(0, 12)
    }
  },
  methods: {
    onKeydown(event) {
      if (event.key === 'Enter' || event.key === ',') {
        event.preventDefault()
        this.commitTag()
      }
    },
    commitTag() {
      this.addTag(this.newTag)
      this.newTag = ''
    },
    addTag(tag) {
      const value = (tag || '').trim()
      if (!value) return
      const exists = this.tags.some(t => t.toLowerCase() === value.toLowerCase())
      if (exists) return
      this.$emit('update:modelValue', [...this.tags, value])
    },
    removeTag(tag) {
      this.$emit('update:modelValue', this.tags.filter(t => t !== tag))
    }
  }
}
</script>