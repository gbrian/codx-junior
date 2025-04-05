<template lang="pug">
  .flex.gap-2.items-center
    .avatar
      .w-6.rounded-full
        img(:src="project.project_icon")
    span {{ project.project_name }}
</template>
<script>
export default {
  props: ['project']
}
</script>