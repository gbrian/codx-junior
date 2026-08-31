<script setup>
import AISettings from './AISettings.vue'
import AgentSettings from '@/components/ai_settings/AgentSettings.vue'
import ExportImportButton from '@/components/ExportImportButton.vue'
import SecurityUserList from '@/components/security/SecurityUserList.vue'
import Workspaces from '@/components/workspaces/Workspaces.vue'
import ProjectScripts from '@/components/project/ProjectScripts.vue'
import OAuthSettings from '@/components/oauth_settings/OAuthSettings.vue'
import PluginsEditor from '@/components/global_settings/plugins/PluginsEditor.vue'
import EnvVariablesEditor from '@/components/global_settings/EnvVariablesEditor.vue'
import GeneralSettings from '@/components/global_settings/GeneralSettings.vue'
import ChatGlobalPrompts from '@/components/global_settings/ChatGlobalPrompts.vue'
</script>

<template>
  <div class="w-full h-full container" v-if="settings">
    <div class="w-full h-full flex gap-0">
      <!-- Desktop Sidebar -->
      <aside class="hidden @md:flex w-64 bg-base-200 border-r border-base-300 flex-col">
        <div class="p-6 border-b border-base-300">
          <h1 class="text-lg font-bold text-base-content">Global Settings</h1>
          <p class="text-xs text-base-content/60 mt-1">Manage your workspace</p>
        </div>

        <nav class="flex-1 overflow-y-auto p-4 space-y-2">
          <button
            v-for="item in navItems"
            :key="item.id"
            @click="activeTab = item.id"
            :class="[
              'w-full text-left px-4 py-3 rounded-lg transition-colors duration-200',
              'flex items-center gap-3',
              activeTab === item.id
                ? 'bg-primary text-primary-content font-medium'
                : 'text-base-content/70 hover:bg-base-300 hover:text-base-content'
            ]"
          >
            <i :class="`fa-solid ${item.icon} w-4 text-center`"></i>
            <span class="text-sm">{{ item.label }}</span>
          </button>
        </nav>

        <!-- Desktop Footer Actions -->
        <div class="p-4 border-t border-base-300 space-y-2">
          <button
            @click="reloadSettings"
            class="w-full btn btn-sm btn-ghost justify-start gap-2"
          >
            <i class="fa-solid fa-arrow-rotate-right text-xs"></i>
            <span>Reload</span>
          </button>
          <button
            @click="saveSettings"
            class="w-full btn btn-sm btn-primary justify-start gap-2"
          >
            <i class="fa-solid fa-floppy-disk text-xs"></i>
            <span>Save Changes</span>
          </button>
          <ExportImportButton :data="settings" @change="submit" class="w-full">
            <i class="fa-solid fa-download text-xs"></i>
          </ExportImportButton>
        </div>
      </aside>

      <!-- Mobile Drawer -->
      <div class="drawer @md:hidden w-full">
        <input id="settings-drawer" type="checkbox" class="drawer-toggle" v-model="drawerOpen" />
        <div class="drawer-content flex flex-col w-full h-full overflow-auto">
          <!-- Mobile Header with Menu Button -->
          <div class="border-b border-base-300 px-4 py-4 bg-base-100 flex items-center justify-between">
            <label for="settings-drawer" class="btn btn-ghost btn-sm btn-circle">
              <i class="fa-solid fa-bars text-lg"></i>
            </label>
            <h2 class="text-lg font-bold text-base-content flex-1 ml-4">
              {{ getActiveLabel() }}
            </h2>
          </div>

          <!-- Mobile Main Content -->
          <div class="flex-1 overflow-y-auto p-4">
            <SecurityUserList :settings="settings" v-if="activeTab === 'users'" />
            <Workspaces :settings="settings" v-if="activeTab === 'workspaces'" />
            <ProjectScripts :settings="settings" v-if="activeTab === 'scripts'" />
            <OAuthSettings :settings="settings" v-if="activeTab === 'oauth'" />
            <PluginsEditor v-if="activeTab === 'plugins'" />
            <GeneralSettings :settings="settings" v-if="activeTab === 'general'" />
            <AISettings :settings="settings" v-if="activeTab === 'ai'" />
            <AgentSettings v-if="activeTab === 'agents'" />
            <EnvVariablesEditor :settings="settings" v-if="activeTab === 'env'" />
            <ChatGlobalPrompts :settings="settings" v-if="activeTab === 'chat'" />
          </div>

          <!-- Mobile Footer Actions -->
          <div class="border-t border-base-300 px-4 py-3 bg-base-100 flex gap-2">
            <button
              @click="reloadSettings"
              class="btn btn-sm btn-ghost btn-circle"
              title="Reload"
            >
              <i class="fa-solid fa-arrow-rotate-right text-sm"></i>
            </button>
            <button
              @click="saveSettings"
              class="btn btn-sm btn-primary flex-1"
            >
              <i class="fa-solid fa-floppy-disk text-xs"></i>
              <span>Save</span>
            </button>
            <ExportImportButton :data="settings" @change="submit" class="btn btn-sm btn-ghost btn-circle">
              <i class="fa-solid fa-download text-sm"></i>
            </ExportImportButton>
          </div>
        </div>

        <!-- Mobile Drawer Sidebar -->
        <div class="drawer-side z-40">
          <label for="settings-drawer" class="drawer-overlay"></label>
          <aside class="w-64 bg-base-200 border-r border-base-300 flex flex-col h-full">
            <div class="p-6 border-b border-base-300">
              <h1 class="text-lg font-bold text-base-content">Settings</h1>
              <p class="text-xs text-base-content/60 mt-1">Navigate</p>
            </div>

            <nav class="flex-1 overflow-y-auto p-4 space-y-2">
              <button
                v-for="item in navItems"
                :key="item.id"
                @click="selectTab(item.id)"
                :class="[
                  'w-full text-left px-4 py-3 rounded-lg transition-colors duration-200',
                  'flex items-center gap-3',
                  activeTab === item.id
                    ? 'bg-primary text-primary-content font-medium'
                    : 'text-base-content/70 hover:bg-base-300 hover:text-base-content'
                ]"
              >
                <i :class="`fa-solid ${item.icon} w-4 text-center`"></i>
                <span class="text-sm">{{ item.label }}</span>
              </button>
            </nav>
          </aside>
        </div>
      </div>

      <!-- Desktop Main Content -->
      <main class="hidden @md:flex flex-1 flex-col overflow-hidden">
        <div class="border-b border-base-300 px-8 py-4 bg-base-100">
          <h2 class="text-2xl font-bold text-base-content">
            {{ getActiveLabel() }}
          </h2>
          <p class="text-sm text-base-content/60 mt-1">{{ getActiveDescription() }}</p>
        </div>

        <div class="flex-1 overflow-y-auto p-8">
          <SecurityUserList :settings="settings" v-if="activeTab === 'users'" />
          <Workspaces :settings="settings" v-if="activeTab === 'workspaces'" />
          <ProjectScripts :settings="settings" v-if="activeTab === 'scripts'" />
          <OAuthSettings :settings="settings" v-if="activeTab === 'oauth'" />
          <PluginsEditor v-if="activeTab === 'plugins'" />
          <GeneralSettings :settings="settings" v-if="activeTab === 'general'" />
          <AISettings :settings="settings" v-if="activeTab === 'ai'" />
          <AgentSettings v-if="activeTab === 'agents'" />
          <EnvVariablesEditor :settings="settings" v-if="activeTab === 'env'" />
          <ChatGlobalPrompts :settings="settings" v-if="activeTab === 'chat'" />
        </div>
      </main>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      activeTab: 'general',
      settings: null,
      drawerOpen: false,
      navItems: [
        { id: 'general', label: 'General', icon: 'fa-sliders' },
        { id: 'ai', label: 'AI Models', icon: 'fa-brain' },
        { id: 'agents', label: 'Agents', icon: 'fa-robot' },
        { id: 'chat', label: 'Chat Prompts', icon: 'fa-comments' },
        { id: 'plugins', label: 'Plugins', icon: 'fa-puzzle-piece' },
        { id: 'workspaces', label: 'Workspaces', icon: 'fa-cube' },
        { id: 'users', label: 'Users', icon: 'fa-users' },
        { id: 'scripts', label: 'Scripts', icon: 'fa-code' },
        { id: 'oauth', label: 'OAuth', icon: 'fa-key' },
        { id: 'env', label: 'ENV Variables', icon: 'fa-leaf' }
      ]
    }
  },
  created() {
    this.loadSettings()
  },
  methods: {
    async loadSettings() {
      const data = await this.$storex.api.settings.global.read()
      this.settings = data
    },
    async saveSettings() {
      await this.$storex.api.settings.global.write(this.settings)
      await this.loadSettings()
      this.$projects.loadAllProjects()
      this.$projects.reloadProject()
      this.$ui.addNotification({ text: 'Settings saved successfully' })
    },
    reloadSettings() {
      this.loadSettings()
      this.$ui.addNotification({ text: 'Settings reloaded' })
    },
    async submit(importData) {
      try {
        this.settings = { ...this.settings, ...importData }
        this.$ui.addNotification({ text: 'Settings imported' })
      } catch (e) {
        console.error('Import failed', e)
        this.$ui.addNotification({ text: 'Import failed', type: 'error' })
      }
    },
    selectTab(tabId) {
      this.activeTab = tabId
      this.drawerOpen = false
    },
    getActiveLabel() {
      return this.navItems.find(item => item.id === this.activeTab)?.label || 'Settings'
    },
    getActiveDescription() {
      const descriptions = {
        general: 'Configure basic settings and preferences',
        ai: 'Manage AI models and LLM configurations',
        agents: 'Define and configure AI agents',
        chat: 'Set global prompts for all chat interactions',
        plugins: 'Install and manage plugins',
        workspaces: 'Organize and manage workspaces',
        users: 'Control user access and permissions',
        scripts: 'Create and manage project scripts',
        oauth: 'Configure OAuth providers',
        env: 'Manage environment variables'
      }
      return descriptions[this.activeTab] || ''
    }
  }
}
</script>