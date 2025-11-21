<script setup>
import AutoCompleteVue from "./AutoComplete.vue";
</script>
<template>
  <AutoCompleteVue :results="results" 
    @search="onSearch"
    @select="$emit('select', $event)"
    @close="$emit('close')"
  />
</template>
<script>
export default {
  props: ['project'],
  data() {
    return {
      results: []
    }
  },
  methods: {
    onSearch(query) {
      this.results = this.project?.$state.searchMentions(query, 20)
    }
  }
}
</script>