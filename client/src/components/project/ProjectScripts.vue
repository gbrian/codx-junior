<script setup>
import ConsoleScriptConfirm from '@/components/console/ConsoleScriptConfirm.vue'
import { consoleScriptCommand } from '@/api/modules/console'
</script>

<template>
  <div class="w-full h-full flex flex-col gap-2 p-2">
    <div class="text-xl">Scripts</div>
    <!-- List of existing scripts -->
    <div v-for="script in scripts" :key="script.name"
      class="flex gap-2 justify-between items-center p-2 rounded-md click"
      @click="editScript(script)"
    >
      <div class="grow flex flex-col gap-1">
        <div>{{ script.name }}</div>
        <div class="text-xs">{{ script.description }}</div>
      </div>
      <span :class="script.background && 'text-error'"><i class="fa-solid fa-circle-play"></i></span>
      <span :class="script.restart && 'text-info'"><i class="fa-solid fa-power-off"></i></span>

      <div class="flex gap-2">
        <div class="divider divider-horizontal"></div>
        <button
          @click.stop="requestRun(script)"
          class="btn btn-sm btn-ghost"
          :disabled="!scriptCommand(script)"
          :title="runTitle(script)"
          :aria-label="runTitle(script)"
        >
          <i class="fa-solid fa-terminal"></i>
        </button>
        <button @click="deleteScript(script)" class="btn btn-sm btn-danger">
          <i class="fa-solid fa-trash-can"></i>
        </button>
      </div>
    </div>
    <div class="flex justify-end">
      <button class="btn btn-sm" @click="addScript">Add script</button>
    </div>

    <!-- Last console run output -->
    <div v-if="lastRun" class="border border-base-300 rounded-md p-2 flex flex-col gap-1">
      <div class="flex items-center gap-2 text-xs">
        <span :class="lastRunFailed ? 'text-error' : 'text-success'" class="font-bold whitespace-nowrap">
          <i class="fa-solid fa-terminal"></i>
          {{ lastRun.timed_out ? 'timed out' : `exit ${lastRun.exit_code}` }}
        </span>
        <span class="opacity-60 truncate font-mono">{{ lastRun.command }}</span>
        <div class="grow"></div>
        <button class="btn btn-xs btn-ghost" @click="lastRun = null" title="Dismiss output">
          <i class="fa-solid fa-xmark"></i>
        </button>
      </div>
      <pre class="text-xs font-mono whitespace-pre-wrap break-words max-h-40 overflow-auto">{{ lastRun.output }}</pre>
    </div>

    <!-- Modal for adding/editing scripts -->
    <modal v-if="isModalOpen" :close="true" @close="isModalOpen=false">
      <div class="flex flex-col gap-2">
        <div>
          <h2>{{ isEditing ? 'Edit Script' : 'Add New Script' }}</h2>
        </div>
        
        <div class="flex flex-col gap-2">
          <input type="text" v-model="currentScript.name" placeholder="Script Name" class="input input-bordered w-full" />
          <textarea v-model="currentScript.description" placeholder="Description" class="textarea textarea-bordered w-full"></textarea>
          <textarea v-model="currentScript.script" placeholder="Bash Script" class="textarea textarea-bordered w-full"></textarea>
          <div class="flex items-center gap-2">
            <input type="checkbox" v-model="currentScript.background" class="checkbox" />
            <span>Run in background</span>
          </div>
          <div class="flex items-center gap-2">
            <input type="checkbox" v-model="currentScript.restart" class="checkbox" />
            <span>Restart if stopped</span>
          </div>
        </div>
        <button class="btn btn-sm" @click="isModalOpen = false">
          Close
        </button>
      </div>
    </modal>

    <!-- Console run confirmation -->
    <ConsoleScriptConfirm
      :show="!!scriptToRun"
      :script="scriptToRun"
      :busy="running"
      @confirm="confirmRun"
      @cancel="cancelRun"
    />
  </div>
</template>

<script>
export default {
  props: ['settings'],
  data() {
    return {
      isModalOpen: false,
      isEditing: false,
      currentScript: this.defaultScript(),
      // Console run: script waiting for confirmation, execution flag and output
      scriptToRun: null,
      running: false,
      lastRun: null
    }
  },
  computed: {
    scripts() {
      return this.settings.project_scripts
    },
    lastRunFailed() {
      return this.lastRun?.timed_out || this.lastRun?.exit_code !== 0
    }
  },
  methods: {
    defaultScript() {
      return {
        name: '',
        description: '',
        script: '',
        background: false,
        restart: false,
      }
    },
    addScript() {
      this.settings.project_scripts = [...this.settings.project_scripts || [], {}]
    },
    editScript(script) {
      this.isEditing = true
      this.currentScript = script
      this.isModalOpen = true
    },
    deleteScript(script) {
      this.settings.project_scripts = this.settings.project_scripts.filter(s => s !== script)
    },
    // ── Console run ────────────────────────────────────────────────────────
    scriptCommand(script) {
      return consoleScriptCommand(script)
    },
    runTitle(script) {
      return this.scriptCommand(script)
        ? `Run "${script.name}" in the console`
        : 'This script has no command'
    },
    requestRun(script) {
      if (!this.scriptCommand(script)) return
      this.scriptToRun = script
    },
    cancelRun() {
      this.scriptToRun = null
    },
    async confirmRun() {
      const script = this.scriptToRun
      if (!script || this.running) return
      this.running = true
      try {
        const result = await this.$storex.api.console.runScript(script)
        this.lastRun = {
          command: result?.command || this.scriptCommand(script),
          exit_code: result?.exit_code,
          timed_out: !!result?.timed_out,
          output: [result?.stdout, result?.stderr].filter(Boolean).join('\n').trim()
        }
        this.$ui.addNotification({
          text: `${this.lastRunFailed ? '⚠️' : '✅'} ${script.name}: ${
            this.lastRun.timed_out ? 'timed out' : `exit ${this.lastRun.exit_code}`
          }`,
          type: this.lastRunFailed ? 'error' : 'info'
        })
        this.scriptToRun = null
      } catch (error) {
        const detail = error?.response?.data?.detail || error?.message || error
        this.$ui.addNotification({
          text: `❌ ${script.name}: ${detail}`,
          type: 'error'
        })
      } finally {
        this.running = false
      }
    }
  }
}
</script>