<script setup>
import emojiDefs from 'markdown-it-emoji/lib/data/full.mjs'
</script>

<template>
  <div class="flex flex-wrap gap-2">
    <div v-for="emoji in filteredEmojis" :key="emoji" class="cursor-pointer" @click="selectEmoji(emoji)">
      <span :title="emoji">{{ emojiDefs[emoji] }}</span>
    </div>
  </div>
</template>

<script>
export default {
  props: ['emojiName'],
  data() {
    return {
      maxEmojis: 5,
      emojiList: Object.keys(emojiDefs)
    }
  },
  computed: {
    // Create a filtered list of emojis based on the emojiName prop
    filteredEmojis() {
      const cleanName = this.emojiName.replace(":", "").toLowerCase()
      return this.emojiList
        .filter(emoji => emoji.includes(cleanName))
        .slice(0, this.maxEmojis)
    }
  },
  methods: {
    // Emit the selected emoji to the parent component
    selectEmoji(name) {
      this.$emit('emoji', { name, emoji: emojiDefs[name] })
    }
  }
}
</script>