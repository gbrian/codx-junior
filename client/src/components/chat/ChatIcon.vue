<template>
  <span class="tooltip tooltip-left" :data-tip="mode">
    <span class="text-primary" v-if="mode === 'task'"><i class="fa-regular fa-file-lines"></i></span>
    <span class="text-secondary" v-if="!mode || mode === 'chat'"><i class="fa-regular fa-comment"></i></span>
    <span class="text-accent" v-if="mode === 'code'"><i class="fa-solid fa-code"></i></span>
    <span class="text-info" v-if="mode === 'browser'"><i class="fa-brands fa-chrome"></i></span>
    <span class="text-info" v-if="mode === 'topic'"><i class="fa-regular fa-comments"></i></span>
    <span class="text-info" v-if="mode === 'answer'"><i class="fa-solid fa-check-double"></i></span>
    <span class="text-info" v-if="mode === 'prview'"><i class="fa-solid fa-code-pull-request"></i></span>
    <span class="text-warning" v-if="mode === 'slides'"><i class="fa-solid fa-chalkboard"></i></span>
    <span class="text-warning" v-if="mode === 'vibe'"><i class="fa-solid fa-hand-sparkles"></i></span>
  </span>
</template>

<script>
export default {
  props: ['mode']
}
</script>