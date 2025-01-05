<template>
  <div class="dropdown dropdown-left">
    <div tabindex="0" role="button" class="btn" :style="{ backgroundColor: modelValue }"></div>
    <div tabindex="0" class="grid grid-cols-8 gap-2 dropdown-content menu bg-base-300 rounded-box z-50 w-96 h-28 p-2 shadow">
      <div v-for="color in colors" :key="color" :style="{ backgroundColor: color }"
        class="click w-full h-full rounded-md" 
           @click="selectColor(color)">
      </div>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    modelValue: String
  },
  data() {
    return {
      colors: [
        '#1FBC9C', '#1CA085', '#2ECC70', '#27AF60',
        '#3398DB', '#2980B9', '#A463BF', '#8E43AD',
        '#3D556E', '#222F3D', '#F2C511', '#F39C19',
        '#E84B3C', '#C0382B', '#DDE6E8', '#BDC3C8'
      ]
    };
  },
  methods: {
    selectColor(color) {
      this.$emit('update:modelValue', color);
    }
  }
}
</script>