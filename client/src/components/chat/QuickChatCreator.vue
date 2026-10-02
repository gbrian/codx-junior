<script setup>
import ChatCard from './ChatCard.vue'
</script>

<template>
  <div class="dropdown dropdown-end">
    <div class="indicator">
      <!-- Indicator badge showing templates exist -->
      <span 
        v-if="templates.length > 0" 
        class="indicator-item badge badge-xs cursor-pointer transition-all hover:scale-110"
        @click="showTemplateModal = true"
      >
        <i class="fa-solid fa-ellipsis"></i>
      </span>
      
      <!-- Quick Chat Icon Button -->
      <div 
        class="tooltip tooltip-right cursor-pointer shrink-0" 
        data-tip="Quick chat"
        @click="createQuickChat"
      >
        <div class="w-10 h-10 rounded-2xl flex items-center justify-center text-lg transition-all duration-200 hover:rounded-xl bg-base-300 text-base-content hover:bg-base-content/10">
          <i class="fa-solid fa-comments"></i>
        </div>
      </div>
    </div>

    <!-- Templates Modal with Enhanced Design -->
    <modal :close="true" v-if="showTemplateModal && templates.length > 0" @close="showTemplateModal = false">
      <template #header>
        <div class="flex items-center justify-between gap-4">
          <div class="text-lg font-bold">Chat Templates</div>
          
          <div class="relative flex-1">
            <input
              v-model="searchText"
              type="text"
              placeholder="Search templates..."
              class="input input-bordered input-sm w-full"
              @focus="searchFocused = true"
              @blur="searchFocused = false"
            />
            <i class="fa-solid fa-magnifying-glass absolute right-3 top-1/2 -translate-y-1/2 text-base-content/30 text-sm pointer-events-none"></i>
          </div>
        </div>
      </template>
      
      <div class="p-4">
        <!-- Empty State -->
        <div 
          v-if="filteredTemplates.length === 0"
          class="text-center py-12 space-y-3"
        >
          <i class="fa-solid fa-inbox text-base-content/20 text-3xl"></i>
          <div class="text-sm text-base-content/50">
            {{ searchText ? 'No templates match your search' : 'No templates available' }}
          </div>
          <button 
            v-if="searchText"
            @click="searchText = ''"
            class="btn btn-xs btn-ghost"
          >
            Clear search
          </button>
        </div>
        
        <!-- Templates Grid -->
        <div 
          v-else
          class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 max-h-[420px] overflow-y-auto pr-2"
        >
          <div 
            v-for="template in filteredTemplates" 
            :key="template.id"
            class="cursor-pointer transition-transform duration-200 hover:scale-[1.02]"
            @click="selectTemplate(template)"
          >
            <ChatCard 
              :chat="template"
              :is-active="false"
              :chat-project="getTemplateProject(template)"
              :working-project="getTemplateWorkingProject(template)"
              :snippet="template.description || 'No description'"
              :message-count="getMessageCount(template)"
              :show-metadata="true"
            />
          </div>
        </div>
      </div>
    </modal>
  </div>
</template>

<script>
export default {
  data() {
    return {
      showTemplateModal: false,
      searchText: '',
      searchFocused: false
    }
  },
  computed: {
    templates() {
      return this.$storex.chats.allChats.filter(c => c.is_template)
    },
    filteredTemplates() {
      if (!this.searchText.trim()) {
        return this.templates
      }
      
      const query = this.searchText.toLowerCase()
      return this.templates.filter(template => {
        const projectName = this.getTemplateProject(template)?.project_name?.toLowerCase() || ''
        return (
          template.name?.toLowerCase().includes(query) ||
          template.description?.toLowerCase().includes(query) ||
          projectName.includes(query)
        )
      })
    }
  },
  methods: {
    getTemplateProject(template) {
      if (!template.project_id) return null
      return this.$storex.projects.allProjects.find(p => p.id === template.project_id)
    },
    getTemplateWorkingProject(template) {
      return this.$chats.getChatWorkingProject(template)
    },
    getMessageCount(template) {
      return template.message_count || 0
    },
    async selectTemplate(template) {
      this.showTemplateModal = false
      this.searchText = ''
      const chat = await this.$chats.createChatFromTemplate({
        template,
        project: this.$storex.projects.activeProject
      })
      if (chat) {
        await this.$service.chat.openChat(chat)
      }
    },
    async createQuickChat() {
      await this.$service.chat.newQuickChat()
    }
  }
}
</script>