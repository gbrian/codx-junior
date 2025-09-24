<template>
  <div class="dropdown" :title="name">
    <div tabindex="0"  class="avatar" @click="isOpen = !isOpen">
      <div class="rounded-full tooltip" :class="`w-${width || 6}`" :data-tip="name" >
        <img :src="image" />
      </div>
    </div>
    <ul tabindex="0" class="dropdown-content menu bg-base-100 rounded-box z-[1] w-52 p-2 shadow">
      <slot></slot>
    </ul>
  </div>
</template>
<script>
export default {
  props: ['user', 'width'],
  data () {
    return {
      isOpen: false,
      name: this.user.username || this.user.name,
      image: this.user.avatar
    }
  }
}
</script>