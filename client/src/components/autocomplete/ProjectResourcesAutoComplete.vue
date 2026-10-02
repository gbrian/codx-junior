<script setup>
import AutoCompleteVue from "./AutoComplete.vue";
import _ from 'lodash'
</script>
<template>
  <AutoCompleteVue :results="results" 
    @search="onSearch"
    @select="$emit('select-result', $event)"
    @close="$emit('close')"
  />
</template>
<script>
export default {
  props: ['project'],
  data() {
    return {
      results: [],
    }
  },
  methods: {
    async onSearch(query) {
      const res = await this.project.$api.knowledge.query(query)
      const mappedValues = res.map(r => ({
        ...r,
        name: r.metadata.source.split('/').pop()
      }))
      const unique = mappedValues.reduce((acc, v) => ({ ...acc, [v.name]: v }), {})
      this.results = Object.values(unique)
                        .sort((a, b) => a.name.length < b.name.length ? -1: 1)
    }
  }
}
</script>

