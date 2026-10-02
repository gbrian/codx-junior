<script setup>
import  vueWindowManager from 'vue-window-manager';
import "vue-window-manager/windows10.css"
import Window from './Window.vue';
import Workspace from './Workspace.vue';
</script>
<template>
  <div class="relative">
    <!--Window
      :window-title="'ウィンドウコンポーネントサンプル'"
      icon="https://cdn-icons-png.flaticon.com/512/337/337948.png">
        <div class="bg-base-300">
              <a>TESTTESTTESTTESTTESTTESTTESTTESTTES
                TTESTTESTTESTTESTTESTTESTTESTTESTTEST
                TESTTESTTESTTESTTESTTESTTESTTESTTESTTES
                TESTTESTTESTTESTTESTTESTTESTTESTTESTTES
                TESTTESTTESTTESTTESTTESTTESTTESTTESTTES
                TESTTESTTESTTESTTESTTESTTESTTESTTESTTES
                TESTTESTTESTTESTTESTTESTTESTTESTTESTTES
                TESTTESTTESTTESTTESTTESTTESTTESTTESTTES
                TESTTESTTESTTESTTESTTESTTESTTESTTESTTES
                TESTTESTTESTTESTTESTTESTTESTTESTTESTTES
                TESTTESTTESTTESTTESTTESTTESTTESTTESTTES
                TTESTTEST
              </a>
        </div>
    </Window>
    <Window
      :window-title="'ウィンドウコンポーネントサンプル'"
      icon="https://cdn-icons-png.flaticon.com/512/337/337948.png"
      class="bg-base-300"
      >
        Another window
    </Window -->
    <Window
      v-for="app in apps" :key="`${app.path}-${app.name}`"
      :window-title="app.name"
      :icon="app.icon"
      class="bg-base-300"
      @activate="app.wId = $event"
      @close="$ui.toggleApp(app)">
        <Workspace :app="app"></Workspace>
    </Window>
  </div>
</template>>
<script>
export default {
  computed: {
    apps() {
      return this.$ui.openApps
    }
  }
}
</script>