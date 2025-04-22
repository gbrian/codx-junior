<template>
  <div class="dropdown click">
    <div tabindex="0"  class="avatar">
      <div class="rounded-full tooltip" :class="`w-${width || 6}`" :data-tip="user.username" >
        <img :src="user.avatar" />
      </div>
    </div>
    <ul tabindex="0" class="dropdown-content menu bg-base-100 rounded-box z-[1] w-52 p-2 shadow">
      <li>@ {{ user.username }}</li>
      <slot></slot>
    </ul>
  </div>
</template>
<script>
export default {
  props: ['user', 'width']
}
</script>