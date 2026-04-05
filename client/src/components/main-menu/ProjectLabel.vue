<template>
  <div class="flex gap-2 items-center">
    <div class="avatar">
      <img class="w-7 h-7 rounded" :src="project.project_icon" />
    </div>
    {{ project.project_name }}
  </div>
</template>
<script>
export default {
  props: ['project']
}
</script>