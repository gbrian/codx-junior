<script setup>
</script>

<template>
  <div class="w-full h-full flex flex-col gap-2">
    <h1 class="text-xl font-bold">Project Scripts</h1>
    <ul>
      <li
        v-for="script in projectScripts"
        :key="script.name"
        class="border p-4 rounded shadow-md"
      >
        <h2 class="text-lg font-medium">{{ script.name }}</h2>
        <p>{{ script.description }}</p>
        <p>
          Status:
          <span
            :class="{
              'text-green-500': script.status === 'running',
              'text-red-500': script.status === 'error',
              'text-yellow-500': script.status === 'stopped'
            }"
            >{{ script.status }}</span
          >
        </p>
        <p>Background: <span>{{ script.background ? 'Yes' : 'No' }}</span></p>
        <p>Restart: <span>{{ script.restart ? 'Yes' : 'No' }}</span></p>
      </li>
    </ul>
  </div>
</template>

<script>
export default {
  data() {
    return {
    }
  },
  computed: {
    projectScripts() {
      return this.$project.projectScripts
    }
  },
  methods: {
  }
}
</script>