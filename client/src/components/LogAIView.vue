<script setup>
import ChatView from '@/views/ChatView.vue';
</script>

<template>
  <div class="w-full h-full flex flex-col gap-2">
    <div v-if="!aiChat" class="flex items-center justify-center h-full">
      <button class="btn btn-primary" @click="initAIChat">
        <i class="fa-solid fa-robot mr-2"></i>
        Start AI Log Analysis
      </button>
    </div>
    <div v-else class="w-full h-full flex flex-col">
      <div class="flex items-center gap-2 px-2 py-1 bg-base-200 rounded">
        <i class="fa-solid fa-robot text-primary"></i>
        <span class="text-sm font-semibold">AI Log Analysis</span>
        <div class="grow"></div>
        <button class="btn btn-xs btn-ghost" @click="analyzeNewLogs" :disabled="analyzing">
          <i :class="['fa-solid', analyzing ? 'fa-spinner animate-spin' : 'fa-magnifying-glass']"></i>
          <span class="ml-1">Analyze logs</span>
        </button>
      </div>
      <div class="grow overflow-hidden">
        <ChatView :chat="aiChat" class="h-full" />
      </div>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    logs: {
      type: Array,
      default: () => []
    }
  },
  data() {
    return {
      aiChat: null,
      analyzing: false,
      lastAnalyzedLogCount: 0
    }
  },
  computed: {
    activeProject() {
      return this.$storex.projects.activeProject
    },
    newLogs() {
      return this.logs.slice(this.lastAnalyzedLogCount)
    }
  },
  watch: {
    // Auto-analyze when new logs arrive if chat already initialized
    logs(newVal) {
      if (this.aiChat && newVal.length > this.lastAnalyzedLogCount) {
        this.analyzeNewLogs()
      }
    }
  },
  methods: {
    async initAIChat() {
      // Create a temporary task-mode chat for log analysis
      this.aiChat = await this.$storex.chats.createNewChat({
        name: 'Log Analysis',
        mode: 'task',
        temp: true,
        project_id: this.activeProject?.id,
        owner_project_id: this.activeProject?.id,
        profiles: [],
        messages: []
      })
      await this.analyzeNewLogs()
    },
    async analyzeNewLogs() {
      if (!this.aiChat || this.analyzing || !this.logs.length) return
      this.analyzing = true
      try {
        const logsToAnalyze = this.newLogs.length ? this.newLogs : this.logs.slice(-100)
        const logContent = logsToAnalyze.join('\n')
        const userMessage = {
          role: 'user',
          content: `Please analyze the following application logs and provide insights on errors, warnings, and overall health:\n\`\`\`\n${logContent}\n\`\`\``,
          done: false
        }
        this.lastAnalyzedLogCount = this.logs.length
        // Add message to chat and trigger AI response
        await this.activeProject.$api.chats.chatWithProject({
          ...this.aiChat,
          messages: [...(this.aiChat.messages || []), userMessage]
        })
        // Reload chat to get updated messages
        await this.$storex.chats.reloadChat(this.aiChat)
        this.aiChat = this.$storex.chats.allChats.find(c => c.id === this.aiChat.id) || this.aiChat
      } catch (err) {
        console.error('AI log analysis error:', err)
      } finally {
        this.analyzing = false
      }
    }
  },
  beforeUnmount() {
    // Clean up temp chat on unmount
    if (this.aiChat?.temp) {
      this.$storex.chats.deleteChat(this.aiChat)
    }
  }
}
</script>