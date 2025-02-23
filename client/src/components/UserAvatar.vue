<template>
  <div class="dropdown dropdown-end group">
    <div tabindex="0" role="button" class="tooltip tooltip-left" :data-tip="user.userName">
      <div class="avatar indicator hover:shadow click">
        <div class="w-10 group-hover:w-12 rounded-full">
          <img :src="user.avatar" :alt="user.userName" />
        </div>
      </div>
    </div>
    <ul tabindex="0" class="dropdown-content menu bg-base-100 rounded-box z-[1] w-52 p-2 shadow">
      <li><a>Chat...</a></li>
    </ul>
  </div>
</template>
<script>
export default {
  props: ['user']
}
</script>