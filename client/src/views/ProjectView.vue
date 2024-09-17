<script setup>
import { API } from '../api/api'
</script>
<template>
  <div class="flex flex-col gap-2">
    <div class="text-xl">Projects</div>
  </div>
</template>
<script>
export default {
  data () {
    return {
      allProjects: null
    }
  },
  created () {
    this.getAllProjects()
  },
  computed: {
    projectStings () {
      return API.lastSettings
    }
  },
  methods: {
    async getAllProjects () {
      const { data } = await API.project.list()
      this.allProjects = data
    }
  }
}
</script>