<script setup>
import { computed, onMounted, ref } from 'vue'
</script>

<template>
  <div class="h-full px-1 flex items-center gap-1">
    <!-- Fullscreen toggle button -->
    <button
      @click="toggleFullscreen"
      class="btn btn-ghost btn-xs gap-1 text-base-content hover:bg-base-300"
      :title="isMaximized ? 'Exit fullscreen' : 'Enter fullscreen'"
    >
      <i v-if="isMaximized" class="fa-solid fa-compress text-sm"></i>
      <i v-else class="fa-solid fa-expand text-sm"></i>
    </button>
  </div>
</template>

<script>
export default {
  props: {
    params: {
      type: Object,
      required: true
    }
  },
  data() {
    return {
      isMaximized: false
    }
  },
  mounted() {
    this.updateMaximized()
    const disposable = this.params.api.onDidConstraintsChange(() => {
        setTimeout(() => this.updateMaximized(), 200)
    });
    return () => {
        disposable.dispose();
    };
  },
  methods: {
    getMaximized() {
      return this.params.group.panels.find(p => p.api.isMaximized())
    },
    getPanelApi() {
      return this.getMaximized()?.api || 
            this.params.group.panels[0]?.api
    },
    toggleFullscreen() {
      if (this.getMaximized()) {
        this.getPanelApi()?.exitMaximized()
      } else {
        this.getPanelApi()?.maximize()
      }
      this.updateMaximized()
    },
    updateMaximized() {
      this.isMaximized = this.getMaximized()
    }
  }
}
</script>

<style scoped>
.btn {
  transition: all 0.2s ease;
}

.btn:hover {
  transform: scale(1.05);
}
</style>