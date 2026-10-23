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
import Collapsible from '../Collapsible.vue'
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
          class="menubar-windows-content relative outline-none p-0 rounded-2xl border border-base-content/10 shadow-2xl overflow-hidden bg-base-100 will-change-[transform,opacity]"
          :class="isMobile ? 'w-[92vw] max-w-[420px]' : ''"
        >
          <!-- Responsive body: two columns on desktop, a stacked and
               scrollable sheet on mobile (so it fits the viewport instead
               of the fixed 640px panel). Driven by $ui.isMobile. -->
          <div
            class="flex"
            :class="isMobile
              ? 'flex-col max-h-[80vh] overflow-y-auto'
              : 'w-[640px] max-w-[92vw]'"
          >
            <!-- LEFT (desktop) / TOP (mobile): unified user info panel -->
            <div
              class="bg-base-200/40"
              :class="isMobile
                ? 'w-full shrink-0 border-b border-base-content/10 p-2'
                : 'w-56 shrink-0 border-r border-base-content/10 p-4 overflow-y-auto max-h-[80vh]'"
              @click.stop
            >
              <!-- Mobile: collapse the wallet/user info by default and show a
                   compact "basic info" row (avatar + name + status + balance).
                   Tap the header to reveal the full UserInfoPanel. -->
              <Collapsible
                v-if="isMobile"
                class="w-full"
                :default-open="false"
              >
                <template #icon>
                  <div class="avatar placeholder shrink-0">
                    <div class="w-6 rounded-full bg-neutral text-neutral-content overflow-hidden">
                      <img
                        v-if="user?.avatar"
                        :src="user.avatar"
                        :alt="user?.userName"
                        class="w-full h-full object-cover"
                      />
                      <span v-else class="text-[10px]">{{ userInitial }}</span>
                    </div>
                  </div>
                </template>

                <template #title>{{ user?.userName || 'User' }}</template>

                <template #summary>
                  <span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-base-100/60 text-[11px]">
                    <span
                      class="inline-block w-1.5 h-1.5 rounded-full"
                      :class="connected ? 'bg-success' : 'bg-error'"
                    ></span>
                    {{ connected ? 'online' : 'offline' }}
                  </span>
                  <span
                    v-if="walletBalance != null"
                    class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-success/15 text-success text-[11px] font-mono font-semibold"
                  >
                    <i class="fa-solid fa-wallet"></i>{{ walletBalance }}
                  </span>
                </template>

                <div class="p-3">
                  <UserInfoPanel @close="close" />
                </div>
              </Collapsible>

              <!-- Desktop: full panel always visible in the left column -->
              <UserInfoPanel v-else @close="close" />
            </div>

            <!-- RIGHT (desktop) / BOTTOM (mobile): apps grid + sections -->
            <div class="flex-1 min-w-0 flex flex-col">
              <WindowsMenuItems :mobile="isMobile" @close="close" />

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
  emits: ['close', 'open'],
  data() {
    return {
      openMenu: ''
    }
  },
  computed: {
    // Shared responsive flag (viewport <= 1024px). Mobile swaps the fixed
    // two-column panel for a stacked, viewport-fitting sheet.
    isMobile() {
      return this.$ui.isMobile
    },
    // Basic info shown in the collapsed mobile header.
    user() {
      return this.$storex.users.user
    },
    userInitial() {
      return (this.user?.userName || '?')[0].toUpperCase()
    },
    walletBalance() {
      const balance = this.user?.wallet?.balance_cxjcoins
      return balance != null ? Number(balance).toFixed(2) : null
    },
    connected() {
      return this.$storex.session.connected
    }
  },
  watch: {
    openMenu(val) {
      if (val) {
        this.$emit('open')
      } else {
        this.$emit('close')
      }
    }
  },
  methods: {
    close() {
      this.openMenu = ''
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