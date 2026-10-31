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
          :disabled="!commandOf(script)"
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
          {{ lastRunSummary }}
        </span>
        <span class="opacity-60 truncate font-mono">{{ lastRun.command }}</span>
        <div class="grow"></div>
        <button class="btn btn-xs btn-ghost" @click="dismiss" title="Dismiss output" aria-label="Dismiss output">
          <i class="fa-solid fa-xmark"></i>
        </button>
      </div>
      <pre class="text-xs font-mono whitespace-pre-wrap break-words max-h-40 overflow-auto">{{ lastRun.output || '(no output)' }}</pre>
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
import ConsoleScriptConfirm from '@/components/console/ConsoleScriptConfirm.vue'
import { useConsole } from '@/composables/useConsole'

export default {
  components: { ConsoleScriptConfirm },
  props: ['settings'],
  setup() {
    // Shared "ask → run → report" cycle: pending script, busy flag, last result,
    // error and notification all live in the composable.
    return useConsole()
  },
  data() {
    return {
      isModalOpen: false,
      isEditing: false,
      currentScript: this.defaultScript()
    }
  },
  computed: {
    scripts() {
      return this.settings.project_scripts
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
    runTitle(script) {
      return this.commandOf(script)
        ? `Run "${script.name}" in the console`
        : 'This script has no command'
    }
  }
}
</script>