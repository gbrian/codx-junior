<script setup>
import WikiSections from '@/components/wiki/WikiSections.vue'
import Document from '@/components/document/Document.vue';
</script>

<template>
  <div class="flex flex-col gap-2 p-1 @md:p-2">
    <div class="text-2xl font-bold">
      <span class="click" @click="viewReadme = false">Wiki</span>
      <span v-if="viewReadme">/ README</span>
    </div>
    <div v-if="readme && !viewReadme">
      <label class="label flex justify-start gap-2 badge badge-outline click" @click="viewReadme = true">
        README
      </label>
    </div>
    <Document :content="readme" v-if="viewReadme" />
    <WikiSections v-else />
  </div>
</template>

<script>
export default {
  data() {
    return {
      viewReadme: false,
      readme: null
    }
  },
  created() {
    this.loadreadme()
  },
  computed: {
  },
  watch: {},
  methods: {
    async loadreadme() {
      this.readme = await this.$project.$api.projects.readme()
    }
  }
}
</script>