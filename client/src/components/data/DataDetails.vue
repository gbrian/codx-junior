<script setup>
</script>
<template>
  <div class="h-full flex flex-col gap-2">
    <table class="">
      <thead>
        <tr class="tabs">
          <th class="tab" :class="{ 'text-warning': selectedTab === 'content' }" @click="selectedTab = 'content'">
            Content</th>
          <th class="tab" :class="{ 'text-warning': selectedTab === 'summary' }" @click="selectedTab = 'summary'">
            Summary</th>
          <th class="tab" :class="{ 'text-warning': selectedTab === 'training' }" @click="selectedTab = 'training'">
            Training</th>
          <th class="tab" :class="{ 'text-warning': selectedTab === 'JSON' }" @click="selectedTab = 'JSON'">JSON</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>
            <markdown :text="makdowText" />
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
<script>
export default {
  props: ['item'],
  data() {
    return {
      selectedTab: 'content'
    }
  },
  computed: {
    extension() {
      return this.item.metadata.source.split(".").reverse()[0]
    },
    makdowText() {
      const md = (content, ext) =>
        ["```" + ext + " " + this.selectedTab, content, "```"].join("\n")
      switch (this.selectedTab) {
        case 'summary':
          return md(this.item.metadata.summary, 'txt')
        case 'training':
          return md(JSON.stringify(this.item.metadata.training, null, 2), 'json')
        case 'JSON':
          return md(JSON.stringify(this.item, null, 2), 'json')
        default:
          return md(this.item.page_content, this.extension)
      }
    }
  },
  watch: {},
  methods: {}
}
</script>