<template>
  <span class="text-primary" v-if="mode === 'task'"><i class="fa-regular fa-file-lines"></i></span>
  <span class="text-secondary" v-if="mode === 'chat'"><i class="fa-regular fa-comment"></i></span>
  <span class="text-accent" v-if="mode === 'code'"><i class="fa-solid fa-code"></i></span>
  <span class="text-info" v-if="mode === 'browser'"><i class="fa-brands fa-chrome"></i></span>
  <span class="text-info" v-if="mode === 'topic'"><i class="fa-regular fa-comments"></i></span>
  <span class="text-info" v-if="mode === 'answer'"><i class="fa-solid fa-check-double"></i></span>
</template>

<script>
export default {
  props: ['mode']
}
</script>