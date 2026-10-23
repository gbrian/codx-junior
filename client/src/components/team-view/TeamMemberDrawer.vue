<script setup>
import ChatLLMModelSelector from '@/components/chat/ChatLLMModelSelector.vue'
import Document from '@/components/document/Document.vue'
import ContentEditorModal from './ContentEditorModal.vue'
import { ROLE_META, roleMeta, avatarUrl, EMPTY_GUARDRAILS } from './config'
</script>

<template>
  <div class="fixed inset-0 z-50 flex justify-end">
    <!-- Scrim -->
    <div class="absolute inset-0 bg-black/50 backdrop-blur-sm" @click="$emit('close')"></div>

    <!-- Panel -->
    <aside
      class="relative h-full w-full max-w-[32rem] bg-base-100 border-l border-base-content/10 shadow-2xl flex flex-col"
      role="dialog"
      aria-modal="true"
      :aria-label="`Edit ${draft.name || 'member'}`"
    >
      <!-- Header -->
      <header class="flex items-center gap-3 px-4 py-3 border-b border-base-content/10 shrink-0">
        <div class="avatar">
          <div class="w-10 rounded-full">
            <img :src="avatar" :alt="draft.name" />
          </div>
        </div>
        <div class="min-w-0">
          <div class="font-semibold truncate">{{ draft.name || 'New member' }}</div>
          <div class="text-xs text-base-content/50 flex items-center gap-1">
            <i :class="role.icon" class="text-[10px]"></i>{{ role.label }}
          </div>
        </div>
        <button type="button" class="btn btn-ghost btn-sm btn-square ml-auto" aria-label="Close editor" @click="$emit('close')">
          <i class="fa-solid fa-xmark"></i>
        </button>
      </header>

      <!-- Tabs -->
      <div role="tablist" class="tabs tabs-bordered px-2 shrink-0 overflow-x-auto">
        <a
          v-for="t in tabs"
          :key="t.id"
          role="tab"
          class="tab gap-1"
          :class="tab === t.id ? 'tab-active font-semibold' : ''"
          :aria-selected="tab === t.id"
          @click="tab = t.id"
        >
          <i :class="t.icon" class="text-xs"></i>{{ t.label }}
        </a>
      </div>

      <!-- Body -->
      <div class="flex-1 min-h-0 overflow-y-auto p-4">
        <!-- About -->
        <div v-if="tab === 'about'" class="flex flex-col gap-4">
          <div>
            <label class="label-text text-xs font-semibold pb-1 block">Avatar URL</label>
            <input v-model="draft.avatar" type="text" class="input input-sm input-bordered w-full" placeholder="Paste an image URL (optional)" />
            <p class="text-[11px] text-base-content/40 mt-1">Leave empty to use an auto-generated avatar.</p>
          </div>

          <div>
            <label class="label-text text-xs font-semibold pb-1 block">Full name *</label>
            <input v-model="draft.name" type="text" class="input input-sm input-bordered w-full" placeholder="e.g. Ava Thompson" />
          </div>

          <div>
            <label class="label-text text-xs font-semibold pb-1 block">Role</label>
            <select v-model="draft.category" class="select select-sm select-bordered w-full">
              <option v-for="(meta, key) in roleMetaMap" :key="key" :value="key">
                {{ meta.label }} — {{ meta.hint }}
              </option>
            </select>
          </div>

          <div>
            <label class="label-text text-xs font-semibold pb-1 block">Short description</label>
            <textarea v-model="draft.description" rows="3" class="textarea textarea-bordered textarea-sm w-full" placeholder="What does this teammate do?"></textarea>
          </div>
        </div>

        <!-- Persona -->
        <div v-else-if="tab === 'persona'" class="flex flex-col gap-3">
          <div class="alert bg-primary/10 border-primary/20 py-2 text-xs gap-2">
            <i class="fa-solid fa-circle-info text-primary"></i>
            <span>Describe in plain language how this teammate should behave, what they focus on and any rules they must follow. This is their "personality".</span>
          </div>

          <div class="flex items-center justify-between">
            <label class="label-text text-xs font-semibold">Persona &amp; instructions</label>
            <div class="flex gap-1">
              <button type="button" class="btn btn-xs btn-primary gap-1" @click="openContentEditor">
                <i class="fa-solid fa-comments text-[10px]"></i>
                Edit with chat
              </button>
              <button type="button" class="btn btn-xs btn-ghost gap-1" @click="toggleContentMode">
                <i :class="contentMode === 'view' ? 'fa-solid fa-pencil-alt' : 'fa-solid fa-eye'"></i>
                {{ contentMode === 'view' ? 'Edit' : 'View' }}
              </button>
            </div>
          </div>

          <!-- View mode: rendered markdown of the persona prompt -->
          <div
            v-if="contentMode === 'view'"
            class="rounded-md bg-base-100 border border-base-content/10 p-3 min-h-[10rem]"
          >
            <Document
              :content="draft.content"
              :documentId="`team-member-${draft.name || 'member'}`"
            />
          </div>

          <!-- Edit mode: raw prompt -->
          <div v-else>
            <textarea v-model="draft.content" rows="12" class="textarea textarea-bordered w-full text-sm" placeholder="You are a helpful teammate who…"></textarea>
            <div class="text-[11px] text-base-content/40 mt-1">{{ (draft.content || '').length }} characters</div>
          </div>
        </div>

        <!-- Capabilities -->
        <div v-else-if="tab === 'capabilities'" class="flex flex-col gap-4">
          <div>
            <label class="label-text text-xs font-semibold pb-1 block">AI engine</label>
            <ChatLLMModelSelector :selectedModel="draft.llm_model" @model-changed="draft.llm_model = $event" />
            <p class="text-[11px] text-base-content/40 mt-1">The model that powers this teammate's responses.</p>
          </div>

          <div class="flex flex-col gap-3">
            <div class="flex items-center justify-between">
              <span class="label-text text-xs font-semibold">Skills</span>
              <span class="badge badge-sm">{{ usedTools.length }} selected</span>
            </div>
            <p class="text-[11px] text-base-content/50 -mt-1">Choose the abilities this teammate can use to get work done.</p>

            <!-- Text filter -->
            <div class="relative">
              <input
                v-model="skillSearch"
                type="text"
                placeholder="Search by name or description..."
                class="input input-sm input-bordered bg-base-300 w-full pl-8"
              />
              <i class="fa-solid fa-search absolute left-2.5 top-1/2 -translate-y-1/2 text-base-content/40 text-xs"></i>
            </div>

            <div v-if="skillSearch" class="flex items-center gap-2">
              <span class="badge badge-sm badge-primary">
                <i class="fa-solid fa-filter mr-1"></i>{{ skillSearch }}
              </span>
              <button type="button" class="text-xs text-primary hover:underline" @click="skillSearch = ''">
                Clear filter
              </button>
            </div>

            <!-- Tag filter -->
            <div v-if="toolTags.length" class="flex flex-col gap-2">
              <label class="label-text text-xs pb-1">Filter by tag</label>
              <select v-model="skillTag" class="select select-sm select-bordered w-full" title="Filter tools by tag">
                <option value="">Show all tags</option>
                <option v-for="tag in toolTags" :key="tag" :value="tag">{{ tag }}</option>
              </select>
            </div>

            <div v-if="skillTag" class="flex items-center gap-2">
              <span class="badge badge-sm badge-info">
                <i class="fa-solid fa-tag mr-1"></i>{{ skillTag }}
              </span>
              <button type="button" class="text-xs text-primary hover:underline" @click="skillTag = ''">
                Clear filter
              </button>
            </div>

            <!-- Tools grid (same selection as EditProfile) -->
            <div v-if="tools.length" class="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div
                v-for="tool in filteredToolsList"
                :key="tool.tool_json.function.name"
                class="h-40 card bg-base-100 border border-base-content/10 hover:border-base-content/20 transition-colors"
              >
                <div class="card-body p-3">
                  <div class="flex items-start gap-2">
                    <input
                      type="checkbox"
                      :checked="isToolSelected(tool.tool_json.function.name)"
                      @click="toggleTool(tool)"
                      class="toggle toggle-xs checked:border-info checked:bg-info mt-0.5"
                    />
                    <div class="flex flex-col flex-1 min-w-0">
                      <h3 class="font-semibold text-sm truncate">{{ tool.tool_json.function.name }}</h3>
                      <p class="text-xs text-base-content/60 line-clamp-2">{{ tool.tool_json.function.description }}</p>
                    </div>
                  </div>

                  <div v-if="tool.tags?.length" class="flex gap-1 flex-wrap mt-2">
                    <span v-for="tag in tool.tags" :key="tag" class="badge badge-xs badge-outline">
                      {{ tag }}
                    </span>
                  </div>
                </div>
              </div>

              <div v-if="!filteredToolsList.length && (skillTag || skillSearch)" class="col-span-full flex items-center justify-center py-8">
                <div class="text-center text-base-content/50">
                  <i class="fa-solid fa-inbox text-2xl mb-2"></i>
                  <p class="text-sm">No tools found matching your filters</p>
                </div>
              </div>
            </div>

            <div v-else class="flex items-center justify-center py-8">
              <div class="text-center text-base-content/50">
                <i class="fa-solid fa-inbox text-2xl mb-2"></i>
                <p class="text-sm">No tools available</p>
              </div>
            </div>
          </div>
        </div>

        <!-- Guardrails -->
        <div v-else-if="tab === 'guardrails'" class="flex flex-col gap-4">
          <div class="flex items-center gap-2">
            <i class="fa-solid fa-shield-halved text-sm" :class="guardrailsEnabled ? 'text-info' : 'text-base-content/40'"></i>
            <span class="text-xs font-semibold uppercase tracking-wide text-base-content/60">Guardrails</span>
            <span class="badge badge-xs" :class="guardrailsEnabled ? 'badge-info' : 'badge-ghost'">
              {{ guardrailsEnabled ? 'Enabled' : 'Disabled' }}
            </span>
            <input
              type="checkbox"
              v-model="draft.guardrails.enabled"
              class="toggle toggle-xs checked:border-info checked:bg-info ml-auto"
              aria-label="Enable guardrails for this member"
            />
          </div>

          <div v-if="guardrailsEnabled" class="flex flex-col gap-4">
            <div>
              <label class="label-text text-xs font-semibold pb-1 block">
                <i class="fa-solid fa-bullseye mr-1 text-info"></i> Scope description
              </label>
              <textarea
                v-model="draft.guardrails.scope"
                rows="2"
                class="textarea textarea-bordered textarea-sm w-full resize-none"
                placeholder="Describe what this teammate is allowed to help with…"
              ></textarea>
            </div>

            <div>
              <label class="label-text text-xs font-semibold pb-1 block">
                <i class="fa-solid fa-key mr-1 text-info"></i> Scope keywords
              </label>
              <input
                v-model="scopeKeywordsText"
                type="text"
                class="input input-sm input-bordered w-full"
                placeholder="keyword1, keyword2, keyword3"
              />
              <p class="text-[10px] text-base-content/50 mt-1">Comma separated. Keywords that indicate an on-scope request.</p>
              <div v-if="draft.guardrails.scope_keywords?.length" class="flex flex-wrap gap-1 mt-1">
                <span v-for="keyword in draft.guardrails.scope_keywords" :key="keyword" class="badge badge-xs badge-outline">{{ keyword }}</span>
              </div>
            </div>

            <div>
              <label class="label-text text-xs font-semibold pb-1 flex justify-between">
                <span><i class="fa-solid fa-percent mr-1 text-info"></i> Scope similarity threshold</span>
                <span class="font-mono">{{ draft.guardrails.scope_similarity_threshold }}</span>
              </label>
              <input v-model.number="draft.guardrails.scope_similarity_threshold" type="range" min="0" max="1" step="0.05" class="range range-xs range-info" />
            </div>

            <div>
              <label class="label-text text-xs font-semibold pb-1 block">
                <i class="fa-solid fa-comment-slash mr-1 text-info"></i> Refusal message
              </label>
              <textarea
                v-model="draft.guardrails.refusal_message"
                rows="2"
                class="textarea textarea-bordered textarea-sm w-full resize-none"
                placeholder="I can only answer questions within my configured scope."
              ></textarea>
            </div>

            <div>
              <label class="label-text text-xs font-semibold pb-1 flex justify-between">
                <span><i class="fa-solid fa-triangle-exclamation mr-1 text-info"></i> Risk score threshold</span>
                <span class="font-mono">{{ draft.guardrails.risk_threshold }}</span>
              </label>
              <input v-model.number="draft.guardrails.risk_threshold" type="range" min="0" max="100" step="1" class="range range-xs range-info" />
            </div>

            <div>
              <label class="label-text text-xs font-semibold pb-1 block">
                <i class="fa-solid fa-wrench mr-1 text-info"></i> Allowed tools
              </label>
              <p class="text-[10px] text-base-content/50 mb-1">No tools selected means this teammate cannot use any tool.</p>
              <div v-if="availableToolNames.length" class="flex flex-wrap gap-1 max-h-40 overflow-y-auto p-2 rounded-md bg-base-200">
                <button
                  v-for="toolName in availableToolNames"
                  :key="toolName"
                  type="button"
                  class="badge badge-sm cursor-pointer transition-colors"
                  :class="isGuardrailToolAllowed(toolName) ? 'badge-info' : 'badge-ghost'"
                  @click="toggleGuardrailTool(toolName)"
                >
                  <i class="fa-solid mr-1" :class="isGuardrailToolAllowed(toolName) ? 'fa-check' : 'fa-plus'"></i>
                  {{ toolName }}
                </button>
              </div>
              <p v-else class="text-xs text-base-content/50">No tools available.</p>
            </div>

            <div class="flex items-center gap-2">
              <i class="fa-solid fa-robot text-info text-sm"></i>
              <span class="text-xs">Use LLM classifier</span>
              <input type="checkbox" v-model="draft.guardrails.use_llm_classifier" class="toggle toggle-xs checked:border-info checked:bg-info ml-auto" aria-label="Use LLM classifier" />
            </div>
          </div>

          <p v-else class="text-xs text-base-content/50 pl-1">
            Guardrails are off. Enable them to restrict this teammate's scope, refusal behaviour and tool usage.
          </p>
        </div>

        <!-- Advanced -->
        <div v-else class="flex flex-col gap-4">
          <div class="alert py-2 text-[11px] gap-2 bg-base-200 border-base-content/10">
            <i class="fa-solid fa-triangle-exclamation text-warning"></i>
            <span>Power-user settings — most managers can safely ignore this tab.</span>
          </div>

          <div>
            <div class="label-text text-xs font-semibold pb-1">Works with</div>
            <p class="text-[11px] text-base-content/50 mb-2">Other members this teammate can delegate to or coordinate with.</p>
            <div class="flex flex-wrap gap-2">
              <button
                v-for="m in linkableMembers"
                :key="m.name"
                type="button"
                class="btn btn-xs gap-1"
                :class="linkedProfiles.includes(m.name) ? 'btn-info' : 'btn-ghost border border-base-content/15'"
                :aria-pressed="linkedProfiles.includes(m.name)"
                @click="toggleProfile(m.name)"
              >
                <i :class="linkedProfiles.includes(m.name) ? 'fa-solid fa-check' : 'fa-solid fa-plus'" class="text-[10px]"></i>{{ m.name }}
              </button>
              <span v-if="!linkableMembers.length" class="text-xs text-base-content/50">No other members yet.</span>
            </div>
          </div>

          <div>
            <label class="label-text text-xs font-semibold pb-1 block">File trigger (advanced)</label>
            <input
              v-model="draft.file_match"
              type="text"
              class="input input-sm input-bordered w-full font-mono"
              :class="fileMatchValid ? '' : 'input-error'"
              placeholder="e.g. docs/.*\.md$"
            />
            <p class="text-[11px] mt-1" :class="fileMatchValid ? 'text-base-content/40' : 'text-error'">
              {{ fileMatchValid ? 'Optional pattern so this teammate activates for specific files.' : 'That is not a valid pattern.' }}
            </p>
          </div>

          <div class="flex items-center gap-3 p-3 rounded-lg bg-base-200 border border-base-content/10">
            <i class="fa-solid fa-share-nodes text-warning"></i>
            <div class="flex-1">
              <div class="text-sm font-medium">Shareable via API</div>
              <div class="text-[11px] text-base-content/50">Expose this teammate to external tools and integrations.</div>
            </div>
            <input v-model="draft.api_settings.active" type="checkbox" class="toggle toggle-sm toggle-warning" aria-label="Shareable via API" />
          </div>

          <div v-if="draft.api_settings?.active" class="flex flex-col gap-3 pl-3 border-l-2 border-warning/40">
            <div>
              <label class="label-text text-xs font-semibold pb-1 block">API name</label>
              <input v-model="draft.api_settings.modelName" type="text" class="input input-sm input-bordered w-full" :placeholder="apiNamePlaceholder" />
            </div>
            <div>
              <label class="label-text text-xs font-semibold pb-1 block">API description</label>
              <textarea v-model="draft.api_settings.modelDescription" rows="2" class="textarea textarea-bordered textarea-sm w-full"></textarea>
            </div>
          </div>

          <div class="p-3 rounded-lg bg-error/10 border border-error/30 mt-2">
            <div class="text-sm font-semibold text-error">Remove member</div>
            <p class="text-[11px] text-base-content/50 mb-2">Permanently remove this teammate from the project. This cannot be undone.</p>
            <button type="button" class="btn btn-sm btn-error" :disabled="saving" @click="requestDelete">
              <i class="fa-solid fa-trash"></i> Delete member
            </button>
          </div>
        </div>
      </div>

      <!-- Footer -->
      <footer class="flex items-center gap-2 px-4 py-3 border-t border-base-content/10 shrink-0">
        <span class="text-xs text-base-content/40 mr-auto">{{ saving ? 'Saving…' : 'Changes are saved to the project' }}</span>
        <button type="button" class="btn btn-sm btn-ghost" @click="$emit('close')">Cancel</button>
        <button
          type="button"
          class="btn btn-sm btn-primary"
          :disabled="saving || !draft.name || !draft.name.trim()"
          @click="submit"
        >
          <span v-if="saving" class="loading loading-spinner loading-xs"></span>
          <i v-else class="fa-solid fa-floppy-disk"></i>
          Save member
        </button>
      </footer>
    </aside>

    <!-- Chat-based content editor (modal on top of the drawer) -->
    <ContentEditorModal
      v-if="showContentEditor"
      :profile="draft"
      @update="onContentUpdated"
      @close="showContentEditor = false"
    />
  </div>
</template>

<script>
export default {
  name: 'TeamMemberDrawer',
  props: {
    /** The profile being edited. */
    member: { type: Object, required: true },
    /** All members, used by the "Works with" picker. */
    members: { type: Array, default: () => [] },
    /** Available skills (tools) as returned by the profiles API. */
    tools: { type: Array, default: () => [] },
    saving: { type: Boolean, default: false }
  },
  emits: ['save', 'delete', 'close'],
  data() {
    return {
      tab: 'about',
      draft: {},
      contentMode: 'view', // view (Document) | edit (textarea)
      showContentEditor: false,
      skillSearch: '',
      skillTag: '',
      roleMetaMap: ROLE_META,
      tabs: [
        { id: 'about', label: 'About', icon: 'fa-solid fa-user' },
        { id: 'persona', label: 'Persona', icon: 'fa-solid fa-wand-magic-sparkles' },
        { id: 'capabilities', label: 'Capabilities', icon: 'fa-solid fa-wrench' },
        { id: 'guardrails', label: 'Guardrails', icon: 'fa-solid fa-shield-halved' },
        { id: 'advanced', label: 'Advanced', icon: 'fa-solid fa-key' }
      ]
    }
  },
  computed: {
    role() {
      return roleMeta(this.draft.category)
    },
    avatar() {
      return avatarUrl(this.draft)
    },
    usedTools() {
      return this.draft.tools || []
    },
    guardrailsEnabled() {
      return !!this.draft.guardrails?.enabled
    },
    scopeKeywordsText: {
      get() {
        return (this.draft.guardrails?.scope_keywords || []).join(', ')
      },
      set(value) {
        if (!this.draft.guardrails) return
        this.draft.guardrails.scope_keywords = value
          .split(',')
          .map(keyword => keyword.trim())
          .filter(Boolean)
      }
    },
    availableToolNames() {
      return this.tools
        .map(tool => tool?.tool_json?.function?.name)
        .filter(Boolean)
        .sort()
    },
    // Distinct tags across all available tools (drives the tag filter).
    toolTags() {
      const tags = new Set()
      ;(this.tools || []).forEach(tool => {
        if (Array.isArray(tool?.tags)) tool.tags.forEach(tag => tags.add(tag))
      })
      return Array.from(tags).sort()
    },
    // Tools filtered by freetext (name/description) and tag — same as EditProfile.
    filteredToolsList() {
      let filtered = this.tools || []

      if (this.skillSearch) {
        const term = this.skillSearch.toLowerCase()
        filtered = filtered.filter(tool =>
          tool?.tool_json?.function?.name?.toLowerCase().includes(term) ||
          tool?.tool_json?.function?.description?.toLowerCase().includes(term)
        )
      }

      if (this.skillTag) {
        filtered = filtered.filter(tool =>
          Array.isArray(tool?.tags) && tool.tags.includes(this.skillTag)
        )
      }

      return filtered
    },
    fileMatchValid() {
      if (!this.draft.file_match) return true
      try {
        new RegExp(this.draft.file_match)
        return true
      } catch {
        return false
      }
    },
    linkableMembers() {
      return this.members.filter(m => m.name !== this.draft.name)
    },
    linkedProfiles() {
      return this.draft.profiles || []
    },
    apiNamePlaceholder() {
      const projectName = this.$project?.project_name || 'project'
      return `default: ${projectName}/${this.draft.name || ''}`
    }
  },
  watch: {
    member: {
      immediate: true,
      handler(member) {
        this.resetDraft(member)
      }
    }
  },
  mounted() {
    window.addEventListener('keydown', this.onKeydown)
  },
  beforeUnmount() {
    window.removeEventListener('keydown', this.onKeydown)
  },
  methods: {
    onKeydown(event) {
      if (event.key === 'Escape' && !this.showContentEditor) this.$emit('close')
    },
    resetDraft(member) {
      const source = member || {}
      // Deep clone so edits never mutate the source profile. `use_knowledge` is
      // deprecated and intentionally dropped from the draft.
      const { use_knowledge, ...rest } = JSON.parse(JSON.stringify(source))
      this.draft = {
        ...rest,
        tools: [...(source.tools || [])],
        profiles: [...(source.profiles || [])],
        api_settings: {
          active: false,
          modelName: '',
          modelDescription: '',
          ...(source.api_settings || {})
        },
        guardrails: {
          ...JSON.parse(JSON.stringify(EMPTY_GUARDRAILS)),
          ...(source.guardrails || {})
        }
      }
      this.tab = 'about'
      this.contentMode = 'view'
      this.skillSearch = ''
      this.skillTag = ''
    },
    // ── Persona ────────────────────────────────────────────────────────────
    toggleContentMode() {
      this.contentMode = this.contentMode === 'view' ? 'edit' : 'view'
    },
    openContentEditor() {
      this.showContentEditor = true
    },
    onContentUpdated({ content, chatId }) {
      if (typeof content === 'string') this.draft.content = content
      if (chatId) this.draft.chat_id = chatId
    },
    // ── Skills ─────────────────────────────────────────────────────────────
    isToolSelected(name) {
      return this.usedTools.includes(name)
    },
    toggleTool(tool) {
      const has = this.isToolSelected(tool.tool_json.function.name)
      this.draft.tools = has
        ? this.usedTools.filter(t => t !== tool.tool_json.function.name)
        : [...this.usedTools, tool.tool_json.function.name]
    },
    // ── Advanced ───────────────────────────────────────────────────────────
    toggleProfile(name) {
      this.draft.profiles = this.linkedProfiles.includes(name)
        ? this.linkedProfiles.filter(p => p !== name)
        : [...this.linkedProfiles, name]
    },
    isGuardrailToolAllowed(toolName) {
      return this.draft.guardrails?.allowed_tools?.includes(toolName)
    },
    toggleGuardrailTool(toolName) {
      const allowed = this.draft.guardrails.allowed_tools || []
      this.draft.guardrails.allowed_tools = allowed.includes(toolName)
        ? allowed.filter(name => name !== toolName)
        : [...allowed, toolName]
    },
    // ── Persistence ────────────────────────────────────────────────────────
    submit() {
      if (!this.draft.name || !this.draft.name.trim() || this.saving) return
      this.$emit('save', { profile: this.draft })
    },
    requestDelete() {
      this.$emit('delete', { profile: this.draft })
    }
  }
}
</script>

<!-- Made with ❤️ by codx-junior -->