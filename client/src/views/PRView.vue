<template>
  <div class="pr-view">
    <h1>Visualize Code Changes</h1>
    <div>
      <label for="branch1">Select Branch 1:</label>
      <select v-model="branch1" @change="fetchChanges">
        <option v-for="branch in branches" :key="branch" :value="branch">{{ branch }}</option>
      </select>
      
      <label for="branch2">Select Branch 2:</label>
      <select v-model="branch2" @change="fetchChanges">
        <option v-for="branch in branches" :key="branch" :value="branch">{{ branch }}</option>
      </select>
    </div>
    
    <div v-if="changes">
      <h2>Changes between {{ branch1 }} and {{ branch2 }}</h2>
      <pre>{{ changes }}</pre>
    </div>
  </div>
</template>

<script>
import { API } from '../api/api'

export default {
  data() {
    return {
      branches: [], // Array to hold branch names
      branch1: null,
      branch2: null,
      changes: null,
    }
  },
  async created() {
    await this.loadBranches();
  },
  methods: {
    async loadBranches() {
      // Fetch the list of branches from the API
      const response = await API.getBranches();
      this.branches = response.data;
    },
    async fetchChanges() {
      if (this.branch1 && this.branch2) {
        // Fetch code changes between the two branches
        const response = await API.getCodeChanges(this.branch1, this.branch2);
        this.changes = response.data;
      }
    }
  }
}
</script>