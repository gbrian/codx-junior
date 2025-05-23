<template>
  <div class="dropdown">
    <div tabindex="0"  class="avatar" @click="isOpen = !isOpen">
      <div class="rounded-full tooltip" :class="`w-${width || 6}`" :data-tip="user.username" >
        <img :src="user.avatar" />
      </div>
    </div>
    <ul tabindex="0" class="dropdown-content menu bg-base-100 rounded-box z-[1] w-52 p-2 shadow"
      @mouseout="isOpen = false"
      v-if="isOpen">
      <slot></slot>
    </ul>
  </div>
</template>
<script>
export default {
  props: ['user', 'width'],
  data () {
    return {
      isOpen: false
    }
  }
}
</script>