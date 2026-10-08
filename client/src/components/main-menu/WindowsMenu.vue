<script setup>
import {
  MenubarContent,
  MenubarMenu,
  MenubarPortal,
  MenubarRoot,
  MenubarTrigger,
} from 'reka-ui'
import UserInfoPanel from '../UserInfoPanel.vue'
import WindowsMenuItems from './WindowsMenuItems.vue'
</script>

<template>
  <MenubarRoot v-model="openMenu" :data-theme="$ui.theme">
    <MenubarMenu value="windows-menu" class="MenubarMenu">
      <MenubarTrigger
        class="click select-none outline-none w-full text-left flex items-center"
      >
        <slot />
      </MenubarTrigger>
      <MenubarPortal>
        <MenubarContent
          side="top"
          align="start"
          :side-offset="8"
          :align-offset="0"
          :avoid-collisions="true"
          :data-theme="$ui.theme"
          class="menubar-windows-content outline-none p-0 rounded-2xl border border-base-content/10 shadow-2xl overflow-hidden bg-base-100 will-change-[transform,opacity]"
        >
          <div class="flex w-[640px] max-w-[92vw]">
            <!-- LEFT: unified user info panel -->
            <div
              class="w-56 shrink-0 border-r border-base-content/10 bg-base-200/40 p-4 overflow-y-auto max-h-[80vh]"
              @click.stop
            >
              <UserInfoPanel @close="close" />
            </div>

            <!-- RIGHT: apps grid + sections -->
            <div class="flex-1 min-w-0 flex flex-col">
              <WindowsMenuItems @close="close" />

              <!-- Status footer -->
              <div class="mt-auto flex items-center justify-between px-4 py-2 border-t border-base-content/10 text-[11px] text-base-content/60">
                <span class="flex items-center gap-1.5">
                  <span
                    class="inline-block w-2 h-2 rounded-full"
                    :class="$storex.session.connected ? 'bg-success' : 'bg-error'"
                  ></span>
                  {{ $storex.session.connected ? 'Connected' : 'Offline' }}
                </span>
                <span>codx-junior</span>
              </div>
            </div>
          </div>
        </MenubarContent>
      </MenubarPortal>
    </MenubarMenu>
  </MenubarRoot>
</template>

<script>
export default {
  emits: ['close'],
  data() {
    return {
      openMenu: ''
    }
  },
  methods: {
    close() {
      this.openMenu = ''
      this.$emit('close')
    }
  }
}
</script>

<style scoped>
.menubar-windows-content[data-state='open'] {
  animation: windowsMenuIn 160ms cubic-bezier(0.16, 1, 0.3, 1);
}

@keyframes windowsMenuIn {
  from {
    opacity: 0;
    transform: translateY(8px) scale(0.98);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}
</style>