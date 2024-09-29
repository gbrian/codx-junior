<script setup>
import Code from './Code.vue'
import { full as emoji } from 'markdown-it-emoji'
import MarkdownIt from 'markdown-it'
import highlight  from 'markdown-it-highlightjs'
</script>
<template>
  <div>
    <div class="text-md text-wrap mt-2 max-w-full w-full overflow-y-auto prose" v-html="html"></div>
    <Code v-for="code in codeBlocks" :key="code.id"
      :code="code"
      ref="codeSection"
      @generate-code="$emit('generate-code', $event)"
    >
    </Code>
  </div>
</template>
<script>
const md = new MarkdownIt({
  html: true
})
md.use(emoji)
md.use(highlight)

export default {
  props: ['text'],
  data () {
    return {
      codeBlocks: [],
      showDoc: false,
      srcView: false
    }
  },
  mounted () {
    this.updateCodeBlocks()
    this.captureLinks()
  },
  computed: {
    html () {
      if (!this.showDoc) {
        try {
          return md.render(this.sanitizedText)
        } catch (ex) {
          console.error("Message can't be rendered", this.text)
        }
      }
      return this.showDocPreview
    },
    showDocPreview () {
      return md.render("```json\n" + JSON.stringify(this.text, null, 2) + "\n```")
    },
    sanitizedText () {
      return this.text?.replace("```thymeleaf", "```html")
    }
  },
  watch: {
    text () {
      this.codeBlocks = []
      requestAnimationFrame(() => this.captureLinks())
    }
  },
  methods: {
    captureLinks () {
      const linkBlocks = [...this.$el.querySelectorAll('a')]
      linkBlocks.forEach(a => a.onclick = ev => {
        ev.preventDefault()
        this.$emit('link', { a, url: a.attributes["href"].value, text: a.innerText })
      })
    },
    updateCodeBlocks () {
      setInterval(() => {
        const codeBlocks = [...this.$el.querySelectorAll('code[class^="language"]')]
                            .filter(cb => !this.codeBlocks.find(ccb => ccb === cb))
        if (codeBlocks.length) {
          this.codeBlocks = [...this.codeBlocks, ...codeBlocks]
          console.log("Code blocks", codeBlocks)
        }
      }, 500)      
    }
  }
}
</script>