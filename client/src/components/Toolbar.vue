<template>
  <div class="toolbar">
    <button @click="zoomIn" class="btn btn-icon">
      <IconZoomIn />
    </button>
    <button @click="zoomOut" class="btn btn-icon">
      <IconZoomOut />
    </button>
  </div>
</template>

<script>
import IconZoomIn from './icons/IconZoomIn.vue';
import IconZoomOut from './icons/IconZoomOut.vue';

export default {
  components: {
    IconZoomIn,
    IconZoomOut
  },
  methods: {
    zoomIn() {
      // Logic for zooming in
    },
    zoomOut() {
      // Logic for zooming out
    }
  }
};
</script>

<style scoped>
.btn-icon {
  background: none;
  border: none;
  cursor: pointer;
  padding: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>