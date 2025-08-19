<script setup>
import DataRow from './DataRow.vue';
</script>
<template>
  <div class="w-full h-full flex gap-2 flex-col">
    <div>Data Explorer</div>
    <div class="query-toolbar flex justify-between items-center gap-4">
      <input v-model="filter" placeholder="Filter" class="grow input input-bordered" 
        @keydown.enter="search"
      />
      <input v-model="limit" placeholder="Limit" class="input input-bordered w-20" />
      <button @click="search" class="btn btn-primary">
        <i class="fa-solid fa-magnifying-glass"></i>
      </button>
    </div>
    <div class="grow results">
      <table class="table">
        <thead>
          <tr class="font-bold">
            <th>Source</th>
            <th>Language</th>
            <th>Splitter</th>
            <th>Index</th>
            <th>Total Docs</th>
            <th>Length</th>
            <th>Last Update</th>
            <th>Training</th>
          </tr>
        </thead>
        <tbody>
          <DataRow :item="item" 
            v-for="item, ix in results"
            :key="item.id + ix"
            class="border-b border-slate-700"
            :class="ix % 2 == 0 ? 'bg-base-100' : ''"
            @click="onClickRow(item)" />
        </tbody>
      </table>
    </div>
    <div class="flex gap-2 justify-end items-center">
      <button class="btn btn-error" @click="dropSelected" :disabled="!itemsSelected.length">
        Drop
      </button>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      filter: "source != ''",
      limit: 3,
      page: 1,
      results: []
    }
  },
  computed: {
    itemsSelected() {
      return this.results.filter(i => i.selected)
    }
  },
  watch: {},
  methods: {
    async query() {
      this.results = await $storex.api.data.rawQuery({ 
        filter: this.filter, 
        limit: this.limit, 
        page: this.page 
      })
      
    },
    search() {
      this.page = 1
      this.query()
    },
    async dropSelected() {
      await this.$emit('drop', this.itemsSelected.map(i => i.metadata.source))
      setTimeout(() => this.search(), 1500)
    },
    onClickRow(item) {
      if (item.details) {
        return
      }
      item.open = !item.open
      this.results = this.results
              .filter(r => !r.details)
              .map(r => [r, r.open ? { ...r, details: true, parent: r } : null])
              .reduce((a, b) => a.concat(b), [])
              .filter(a => !!a)
    }
  }
}
</script>