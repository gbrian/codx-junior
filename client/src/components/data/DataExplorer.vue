<script setup>
import moment from 'moment';
</script>
<template>
  <div class="w-full h-full flex gap-2 flex flex-col">
    <div>Data Explorer</div>
    <div class="query-toolbar flex justify-between items-center gap-4">
      <input v-model="filter" placeholder="Filter" class=" grow input input-bordered" 
        @keydown.enter="search"
      />
      <input v-model="limit" placeholder="Limit" class="input input-bordered w-20" />
      <button @click="search" class="btn btn-primary">
        <i class="fa-solid fa-magnifying-glass"></i>
      </button>
    </div>
    <div class="grow results w-full overflow-auto">
      <table class="table table-compact">
        <thead>
          <tr class="text-xl font-bold">
            <th>Id</th>
            <th>Source</th>
            <th>Language</th>
            <th>Loader Type</th>
            <th>Splitter</th>
            <th>Index</th>
            <th>Total Docs</th>
            <th>Length</th>
            <th>Index Date</th>
            <th>Last Update</th>
            <th>Training</th>
            <th>Page Content</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in results" :key="item.id">
            <td>
              <div class="flex gap-2 items-center">
                <input type="checkbox" class="checkbox" v-model="item.selected" />
                <span class="text-error" :title="item.metadata.error"
                  v-if="item.metadata.error">
                  <i class="fa-solid fa-circle-exclamation"></i>
                </span>
                {{ item.id }}
              </div>
            </td>
            <td class="underline click" @click="$ui.openFile(item.metadata.source)">{{ item.metadata.source }}</td>
            <td>{{ item.metadata.language }}</td>
            <td>{{ item.metadata.loader_type }}</td>
            <td>{{ item.metadata.splitter }}</td>
            <td>{{ item.metadata.index }}</td>
            <td>{{ item.metadata.total_docs }}</td>
            <td>{{ item.metadata.length }}</td>
            <td>{{ item.metadata.index_date }}</td>
            <td>{{ moment(item.metadata.last_update * 1000).fromNow() }}</td>
            <td>
              <pre v-if="item.metadata.training?.length">
                {{ item.metadata.training?.length }} entries
              </pre>
            </td>
            <td>{{ item.page_content.slice(0, 100) + (item.page_content.length > 100 ? '...' : '') }}</td>
          </tr>
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
      this.results = await this.$storex.api.data.rawQuery({ 
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
    }
  }
}
</script>