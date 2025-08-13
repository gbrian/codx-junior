<template>
  <div tabindex="0" role="button" class="text-center">
      <div class="avatar tooltip" :data-tip="project.project_name">
        <div class="w-10 rounded-md bg-white">
          <img :src="project.project_icon" @error="user.avatar = errorAvatar" />
        </div>
      </div>
    </div>
</template>
<script>
export default {
  props: ['project']
}
</script>