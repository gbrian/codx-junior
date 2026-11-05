<script setup>
import { defineAsyncComponent } from 'vue'
import moment from 'moment'
import { VueCodeHighlighter } from 'vue-code-highlighter'
import 'vue-code-highlighter/dist/style.css'
import hljs from '@/utils/highlight'
import Collapsible from './Collapsible.vue'
import "@git-diff-view/vue/styles/diff-view.css"
import { EXTENSION_LANGUAGE_MAP } from '../store'

// Monaco (~1 MB) and the git-diff renderer are only required when a block is
// opened, edited or diffed: keep them in their own chunks instead of evaluating
// them with the first rendered message.
const Editor = defineAsyncComponent(() => import('./monaco/Editor.vue'))
const DiffViewer = defineAsyncComponent(() => import('./DiffViewer.vue'))
const Document = defineAsyncComponent(() => import('./document/Document.vue'))
</script>

<template>
  <Collapsible v-model="showCode" class="h-full border border-base-100">
    <template #icon>
      <div v-if="!finished" >
        <span class="loading loading-bars loading-xs shrink-0 text-info"></span>
      </div>
      <div class="hover:text-info" @click.stop="$emit('add-file', file)" v-else>
        <i class="fa-solid fa-file-arrow-up"></i>
      </div>
    </template>

    <template #title>
      <div class="flex flex-col gap-2 w-full md:gap-0">
        <!-- Main header row: filename and quick actions -->
        <div class="flex gap-2 items-center flex-1 min-w-0">
          <div class="underline text-link flex gap-2 items-center cursor-pointer flex-1 min-w-0" v-if="fileName">
            <div 
              class="hover:text-info tooltip truncate" 
              :data-tip="file" 
              @click.stop="handleFileNameClick($event)"
              :title="file"
            >
              {{ fileName }} 
              <span class="text-xs text-info tooltip" title="new" data-tip="New file" v-if="isNewFile">
                <i class="fa-solid fa-circle-info"></i>
              </span>
            </div>
          </div>
          <span class="text-sm font-medium opacity-60 shrink-0" v-else>Code</span>

          <!-- Quick icons (always visible on desktop, mobile shows less) -->
          <div class="flex gap-1 shrink-0" v-if="finished">
            <div
              v-if="canEditFile"
              class="hover:text-info cursor-pointer text-sm"
              :class="editMode && 'text-warning'"
              @click.stop="onEdit"
              title="Edit code"
            >
              <i class="fa-solid fa-edit"></i>
            </div>

            <div
              v-if="canLoadHistory"
              class="hover:text-info cursor-pointer text-sm"
              :class="showHistory && 'text-info'"
              @click.stop="toggleHistory"
              :title="showHistory ? 'Hide file history' : 'File history'"
            >
              <i class="fa-solid fa-clock-rotate-left"></i>
            </div>

            <div
              class="hover:text-info cursor-pointer text-sm"
              :class="associatedChat && 'text-success'"
              @click.stop="onTaskClick"
              :title="associatedChat ? 'Open associated chat' : 'Create sub-task'"
            >
              <i :class="associatedChat ? 'fa-solid fa-comments' : 'fa-brands fa-trello'"></i>
            </div>

            <div class="hover:text-info cursor-pointer text-sm" @click.stop="showDiffInfo" title="Refresh diff stats">
              <i class="fa-solid fa-arrows-rotate" :class="{ 'animate-spin': loadingStats || gitDiffLoading }"></i>
            </div>
          </div>
        </div>

        <!-- Stats row (wrap on mobile) -->
        <div class="flex gap-2 items-center flex-wrap text-xs" v-if="finished && (stats || last_modification || size)">
          <span class="text-info flex gap-2 items-center" @click.stop="">
            <span v-if="loadingStats">Loading...</span>
            <span @click.stop="toggleView" class="cursor-pointer hover:underline" v-if="stats && !isMarkdown">
              <i class="fa-solid fa-file-lines" v-if="showDiff"></i>
              <i class="fa-solid fa-code-compare" v-else></i>
              {{ stats }}
            </span>

            <span v-if="last_modification" class="text-xs opacity-75 shrink-0">
              {{ moment(last_modification).fromNow() }}
            </span>
            <span v-if="size" class="shrink-0">
              {{ size > 1024 ? `${Math.round(size/1024)} KB` : `${size} B` }}
            </span>
          </span>

          <div class="font-mono text-xs truncate" v-if="!finished">
            {{ lastLine }}<span class="ml-1 animate-pulse text-info">_</span>
          </div>

          <span
            v-if="hasLocalChanges"
            class="badge badge-warning badge-xs gap-1 shrink-0"
            title="You have unsaved local edits"
          >
            <i class="fa-solid fa-pen-nib"></i> edited
          </span>

          <!-- Change stats bar (wrap on mobile) -->
          <div v-if="stats && !isGitDiffView && !editMode && !isNoChange && !isMarkdown && !showPreviousDiff" class="flex items-center gap-2">
            <div
              class="flex h-2 rounded-full overflow-hidden bg-base-200 w-16 md:w-24 relative transition-all duration-300"
              :class="isDangerousChange && 'ring-2 ring-error ring-opacity-70'"
            >
              <div
                class="bg-error transition-all duration-500"
                :style="{ width: deletionPercentage + '%' }"
                :title="`Deletions: ${deletionCount} lines`"
              ></div>
              <div
                class="bg-success transition-all duration-500"
                :style="{ width: additionPercentage + '%' }"
                :title="`Additions: ${additionCount} lines`"
              ></div>
            </div>
            <span class="text-xs font-medium text-base-content/60 w-12 md:w-20 text-right shrink-0">
              {{ deletionCount }} / {{ additionCount }}
            </span>
            <div v-if="isDangerousChange" class="tooltip tooltip-left" data-tip="Heavy modification detected! Review carefully.">
              <i class="fa-solid fa-triangle-exclamation text-error animate-pulse shrink-0"></i>
            </div>
          </div>
        </div>
      </div>
    </template>

    <template #actions>
      <!-- Action buttons wrapper with horizontal scroll on mobile -->
      <div class="flex gap-1 overflow-x-auto pb-1 snap-x md:overflow-visible shrink-0">
        <!-- Save Button -->
        <button class="btn btn-sm btn-success btn-outline snap-start shrink-0"
          @click.stop="saveToFile"
          v-if="canEditFile && !isNoChange && file && finished && (showCode || showDiff)"
          :class="{ 'blink-save': actionFeedback.save }"
          title="Save to file">
          <i class="fa-solid fa-check animate-bounce" v-if="actionFeedback.save"></i>
          <i class="fa-solid fa-floppy-disk" v-else></i>
          <span class="hidden sm:inline">Save</span>
        </button>

        <!-- Compare with a previous message's version of this code block (dropdown) -->
        <div class="dropdown dropdown-end shrink-0" v-if="hasPreviousVersion && finished && !editMode">
          <button
            tabindex="0"
            class="btn btn-sm btn-info btn-outline snap-start shrink-0"
            :class="{ 'btn-active': showPreviousDiff }"
            title="Compare with a previous version"
            aria-label="Compare with a previous version"
            @click.stop
          >
            <i class="fa-solid fa-clock-rotate-left"></i>
            <span class="hidden sm:inline">Compare</span>
            <i class="fa-solid fa-caret-down text-[10px]"></i>
          </button>
          <ul tabindex="0" class="dropdown-content menu bg-base-300 rounded-box z-[1] w-72 p-2 shadow border border-base-content/10">
            <li class="menu-title text-xs">
              <span>Compare with</span>
            </li>
            <li v-for="(block, idx) in previousCodeBlocks" :key="block.messageId">
              <a
                @click.stop="selectPreviousVersion(block)"
                :class="{ 'active': showPreviousDiff && selectedPreviousBlock?.messageId === block.messageId }"
              >
                <i class="fa-solid fa-clock-rotate-left"></i>
                <span class="flex flex-col items-start min-w-0">
                  <span class="text-xs font-medium truncate">
                    {{ block.user || 'Assistant' }}
                    <span class="badge badge-xs badge-ghost ml-1" v-if="idx === 0">latest</span>
                  </span>
                  <span class="text-[10px] opacity-60">
                    {{ block.when ? moment(block.when).fromNow() : 'unknown time' }}
                  </span>
                </span>
              </a>
            </li>
            <li v-if="showPreviousDiff">
              <a @click.stop="clearPreviousDiff">
                <i class="fa-solid fa-file"></i>
                <span class="text-xs">File on disk</span>
              </a>
            </li>
          </ul>
        </div>

        <!-- Patch Button (AI Pattern) -->
        <button class="btn btn-sm btn-info btn-outline snap-start shrink-0"
          @click.stop="applyPatchFromPattern"
          v-if="hasPatchPattern && !editMode && !showDiff"
          :class="{ 'blink-save': actionFeedback.patch }"
          title="Apply find-and-replace patch">
          <i class="fa-solid fa-check animate-bounce" v-if="actionFeedback.patch"></i>
          <i class="fa-solid fa-band-aid" v-else></i>
          <span class="hidden sm:inline">Patch</span>
        </button>

        <!-- Discard Diff Button -->
        <button class="btn btn-sm btn-error btn-outline snap-start shrink-0"
          @click.stop="discardDiffChanges"
          v-if="showDiff && hasDiffEdits"
          title="Discard changes">
          <i class="fa-solid fa-xmark"></i>
          <span class="hidden sm:inline">Discard</span>
        </button>

        <!-- Reset Button -->
        <button class="btn btn-sm btn-ghost btn-outline snap-start shrink-0"
          @click.stop="resetLocalChanges"
          v-if="hasLocalChanges && canEditFile"
          title="Reset to original AI-generated code">
          <i class="fa-solid fa-rotate-left"></i>
          <span class="hidden sm:inline">Reset</span>
        </button>

        <!-- Rollback Button -->
        <button class="btn btn-sm btn-error btn-outline snap-start shrink-0"
          @click.stop="confirmRollback"
          v-if="canEditFile && !isGitDiffView && !editMode && finished && file && !isNewFile"
          title="Rollback file to previous state">
          <i class="fa-solid fa-history"></i>
          <span class="hidden sm:inline">Rollback</span>
        </button>

        <!-- Copy Button -->
        <button class="btn btn-sm btn-outline snap-start shrink-0"
          @click.stop="onCopy"
          v-if="!editMode && finished"
          :class="{ 'blink-save': actionFeedback.copy }"
          title="Copy code">
          <i class="fa-solid fa-check animate-bounce" v-if="actionFeedback.copy"></i>
          <i class="fa-solid fa-copy" v-else></i>
          <span class="hidden sm:inline">Copy</span>
        </button>

        <!-- Apply Patch Button (for diff language) -->
        <button class="btn btn-sm btn-success btn-outline snap-start shrink-0"
          @click.stop="applyPatch"
          v-if="isPatch && !editMode && finished"
          title="Apply patch">
          <i class="fa-solid fa-check"></i>
          <span class="hidden sm:inline">Apply</span>
        </button>

        <!-- Cancel Edit Button -->
        <button class="btn btn-sm btn-outline snap-start shrink-0"
          @click="cancelEdit"
          v-if="editMode"
          title="Cancel edit">
          <i class="fa-solid fa-xmark"></i>
          <span class="hidden sm:inline">Cancel</span>
        </button>

        <!-- Apply Edit Button -->
        <button class="btn btn-sm btn-warning snap-start shrink-0"
          @click="applyMessageChange"
          v-if="editMode"
          title="Apply changes">
          <i class="fa-solid fa-pen-to-square"></i>
          <span class="hidden sm:inline">Apply</span>
        </button>

        <!-- Close Button -->
        <button class="btn btn-sm btn-error btn-outline snap-start shrink-0"
          @click.stop="$emit('close')"
          v-if="close"
          title="Close">
          <i class="fa-solid fa-rectangle-xmark"></i>
        </button>
      </div>
    </template>

    <div class="p-2 flex flex-col gap-2 h-full min-h-0"
      :class="{ 'bg-error/40 rounded': isContentOutdated, 'bg-success/20 rounded': isNoChange }"
    >

      <div @click="runCommand" class="cursor-pointer" v-if="isCommand">
        <i class="fa-solid fa-terminal"></i>
      </div>

      <div
        v-if="isContentOutdated && !isGitDiffView"
        class="flex items-center gap-1.5 px-2 py-1 rounded bg-error/10 text-error text-xs"
        :title="`Base file has changed: This content was generated ${moment(contentCreatedAt).fromNow()}, but the file was last modified ${moment(last_modification).fromNow()}. Consider refreshing the diff to ensure accuracy.`"
      >
        <i class="fa-solid fa-exclamation-circle shrink-0"></i>
        <span class="truncate">
          <strong>Base file has changed:</strong> generated {{ moment(contentCreatedAt).fromNow() }}, file modified {{ moment(last_modification).fromNow() }} — refresh diff to ensure accuracy.
        </span>
      </div>

      <div
        v-if="!isGitDiffView && !isNewFile && !diff"
        class="flex items-center gap-1.5 px-2 py-1 rounded bg-info/10 text-info text-xs"
        :title="`Old changes detected`"
      >
        <i class="fa-solid fa-triangle-exclamation shrink-0"></i>
        <span class="truncate">
          <strong>old changes detected:</strong>
        </span>
      </div>

      <div
        v-if="isDangerousChange && !isGitDiffView && !editMode && !showDiff && !isMarkdown"
        class="flex items-center gap-1.5 px-2 py-1 rounded bg-warning/10 text-warning text-xs"
        :title="`Heavy modification detected: ${changeRiskMessage}`"
      >
        <i class="fa-solid fa-triangle-exclamation shrink-0"></i>
        <span class="truncate">
          <strong>Heavy modification detected:</strong> {{ changeRiskMessage }}
        </span>
      </div>

      <!-- Previous-version comparison banner -->
      <div
        v-if="showPreviousDiff"
        class="flex items-center gap-1.5 px-2 py-1 rounded bg-info/10 text-info text-xs"
      >
        <i class="fa-solid fa-clock-rotate-left shrink-0"></i>
        <span class="truncate">Comparing with {{ previousCodeLabel }}</span>
        <button class="ml-auto shrink-0 opacity-70 hover:opacity-100" @click.stop="clearPreviousDiff" title="Exit comparison" aria-label="Exit comparison">
          <i class="fa-solid fa-xmark"></i>
        </button>
      </div>

      <div
        v-if="changesetErrors.length"
        class="flex items-center gap-1.5 px-2 py-1 rounded bg-error/10 text-error text-xs"
        :title="changesetErrors.join(' • ')"
      >
        <i class="fa-solid fa-circle-exclamation shrink-0"></i>
        <span class="truncate">
          <strong>Changeset errors ({{ changesetErrors.length }}):</strong> {{ changesetErrors[0] }}
        </span>
      </div>

      <!-- Git: inspecting a commit from the history panel -->
      <div
        v-if="selectedGitCommit"
        class="flex items-center gap-1.5 px-2 py-1 rounded bg-info/10 text-info text-xs"
      >
        <i class="fa-solid fa-clock-rotate-left shrink-0"></i>
        <span class="truncate grow">
          Viewing commit <span class="font-mono">{{ selectedGitCommit.short_commit }}</span>
          <span v-if="selectedGitCommit.message"> · {{ selectedGitCommit.message }}</span>
        </span>
        <button class="btn btn-xs btn-ghost gap-1 shrink-0" @click.stop="backToGitWorkingChanges">
          <i class="fa-solid fa-arrow-left text-[10px]"></i> Current file
        </button>
      </div>

      <div
        v-if="isGitDiffView && gitDiffError"
        class="flex items-start gap-2 px-2 py-1 rounded bg-error/10 text-error text-xs"
      >
        <i class="fa-solid fa-triangle-exclamation mt-0.5 shrink-0"></i>
        <span class="grow break-words">{{ gitDiffError }}</span>
        <button class="btn btn-xs btn-ghost shrink-0" title="Retry diff" aria-label="Retry diff" @click.stop="loadGitDiff">
          <i class="fa-solid fa-rotate-right text-[10px]"></i>
        </button>
      </div>

      <div v-if="isGitDiffView && gitDiffLoading" class="flex items-center gap-2 px-2 py-1 text-xs opacity-60">
        <i class="fa-solid fa-spinner animate-spin"></i> Loading diff...
      </div>

      <!-- File history (git log of the current file) -->
      <div v-if="showHistory" class="flex flex-col gap-1 grow min-h-0 overflow-auto">
        <div class="flex items-center gap-2 px-1 py-0.5 text-xs font-medium">
          <i class="fa-solid fa-clock-rotate-left text-info"></i>
          <span class="grow">File history</span>
          <button
            class="btn btn-xs btn-ghost btn-square"
            :disabled="gitHistoryLoading"
            title="Reload history"
            aria-label="Reload history"
            @click.stop="loadGitHistory"
          >
            <i class="fa-solid fa-rotate-right text-[10px]" :class="{ 'animate-spin': gitHistoryLoading }"></i>
          </button>
          <button class="btn btn-xs btn-ghost btn-square" title="Close history" aria-label="Close history" @click.stop="showHistory = false">
            <i class="fa-solid fa-xmark text-[10px]"></i>
          </button>
        </div>

        <div v-if="gitHistoryLoading" class="p-2 text-xs opacity-50 flex items-center gap-2">
          <i class="fa-solid fa-spinner animate-spin"></i> Loading history...
        </div>
        <div v-else-if="gitHistoryError" class="p-2 flex flex-col gap-1 text-xs">
          <span class="text-error break-words">{{ gitHistoryError }}</span>
          <button class="btn btn-xs btn-ghost self-start" @click.stop="loadGitHistory">Retry</button>
        </div>
        <div v-else-if="!gitHistory.length" class="p-2 text-xs opacity-40">No commits for this file</div>
        <div v-else class="flex flex-col gap-0.5">
          <button
            v-if="gitMode"
            class="flex items-center gap-2 px-2 py-1 rounded text-left text-xs transition-colors"
            :class="!selectedGitCommit ? 'bg-primary/10 text-primary' : 'hover:bg-base-300/60'"
            title="Show the current working changes"
            @click.stop="backToGitWorkingChanges"
          >
            <i class="fa-solid fa-code-compare text-[11px] shrink-0"></i>
            <span class="grow truncate">Current changes</span>
          </button>
          <button
            v-for="commit in gitHistory"
            :key="commit.commit"
            class="flex items-center gap-2 px-2 py-1 rounded text-left text-xs transition-colors"
            :class="selectedGitCommit?.commit === commit.commit ? 'bg-primary/10 text-primary' : 'hover:bg-base-300/60'"
            :title="`${commit.short_commit} · ${commit.message}`"
            @click.stop="selectGitCommit(commit)"
          >
            <i class="fa-solid fa-code-commit text-warning text-[11px] shrink-0"></i>
            <span class="font-mono text-[10px] opacity-70 shrink-0">{{ commit.short_commit }}</span>
            <span class="truncate grow">{{ commit.message }}</span>
            <span class="text-[10px] opacity-50 shrink-0 hidden sm:inline">{{ commit.author }}</span>
            <span class="badge badge-xs badge-ghost shrink-0">{{ commit.relative }}</span>
          </button>
        </div>
      </div>

      <!-- Main content area with diff or code views -->
      <div v-else class="view-code grow min-h-0 overflow-auto">
        <div :style="contentStyle" :class="{ 'h-full': isGitDiffView || editMode }">

          <!-- DiffViewer with edit mode toggle (Monaco DiffEditor when in edit mode) -->
          <DiffViewer
            v-if="showDiff && (comparisonOrgContent || isGitDiffView)"
            :org-content="isGitDiffView ? null : comparisonOrgContent"
            :new-content="isGitDiffView ? null : (diffEditContent || effectiveCode)"
            :diff="isGitDiffView ? diff : null"
            :file="file"
            :language="fileLanguage"
            class="h-full"
            @update:newContent="onDiffViewerChange"
          />

          <!-- Monaco plain edit mode (no diff) -->
          <Editor
            v-model="editContent"
            :fileName="file"
            class="h-full"
            @update:modelValue="onEditorChange"
            v-if="editMode"
          />

          <!-- Syntax-highlighted read-only view -->
          <div class="h-full" v-if="effectiveCode && !editMode && !showDiff">
            <Document
              v-if="isMarkdown"
              :content="effectiveCode"
              :files="files"
              :project="effectiveProject"
              :chat="chat"
              :message="message"
              :loading="!finished"
              class="h-full overflow-auto"
              @add-file="$emit('add-file', $event)"
              @save-file="$emit('save-file', $event)"
              @open-file="$emit('open-file', $event)"
              @edit-message="$emit('edit-message', $event)"
              @sub-task="$emit('sub-task', $event)"
            />

            <VueCodeHighlighter
              v-else
              :key="codeHash"
              class="h-full"
              :code="effectiveCode"
              :lang="validatedLanguage"
              :title="fileName"
            />
          </div>
        </div>
      </div>
    </div>

    <modal v-if="showConfirmModal">
        <h3 class="font-bold text-lg">Unsaved Changes</h3>
        <p>You have unsaved changes in the diff editor. What would you like to do?</p>
        <button class="btn btn-error" @click="confirmDiscardDiff">
          <i class="fa-solid fa-trash"></i> Discard
        </button>
        <button class="btn btn-success" @click="confirmApplyDiff">
          <i class="fa-solid fa-check"></i> Apply
        </button>
        <button class="btn" @click="cancelConfirm">
          <i class="fa-solid fa-xmark"></i> Cancel
        </button>
    </modal>

    <modal v-if="showRollbackModal">
        <h3 class="font-bold text-lg">Rollback File?</h3>
        <p class="text-warning">This will restore <strong>{{ fileName }}</strong> to its previous state. This action cannot be undone.</p>
        <div class="flex gap-2 justify-end">
          <button class="btn btn-ghost" @click="cancelRollback">
            <i class="fa-solid fa-xmark"></i> Cancel
          </button>
          <button class="btn btn-error" @click="executeRollback" :disabled="isRollingBack">
            <span v-if="isRollingBack" class="loading loading-spinner loading-xs"></span>
            <i v-else class="fa-solid fa-history"></i>
            {{ isRollingBack ? 'Rolling back...' : 'Rollback' }}
          </button>
        </div>
    </modal>

    <!-- Heavy change confirmation modal -->
    <modal v-if="showHeavyChangeConfirmModal">
        <h3 class="font-bold text-lg flex items-center gap-2">
          <i class="fa-solid fa-triangle-exclamation text-warning"></i>
          Confirm Heavy Changes
        </h3>
        <div class="flex flex-col gap-2 py-2">
          <p>
            This save will apply a significant modification to
            <strong>{{ fileName }}</strong>. Please review before continuing.
          </p>
          <div class="flex items-center gap-2 p-2 rounded bg-warning/10 text-warning text-sm">
            <i class="fa-solid fa-triangle-exclamation shrink-0"></i>
            <span>{{ changeRiskMessage }}</span>
          </div>
          <div class="flex items-center gap-3 text-xs opacity-70">
            <span class="text-error inline-flex items-center gap-1">
              <i class="fa-solid fa-minus"></i> {{ deletionCount }} deletions
            </span>
            <span class="text-success inline-flex items-center gap-1">
              <i class="fa-solid fa-plus"></i> {{ additionCount }} additions
            </span>
          </div>
        </div>
        <div class="flex gap-2 justify-end">
          <button class="btn btn-ghost" @click="cancelHeavyChangeSave">
            <i class="fa-solid fa-xmark"></i> Cancel
          </button>
          <button class="btn btn-warning" @click="confirmHeavyChangeSave">
            <i class="fa-solid fa-check"></i> Save Anyway
          </button>
        </div>
    </modal>
  </Collapsible>
</template>

<script>
import { v4 as uuidv4 } from 'uuid'

export default {
  props: ['close', 'chat', 'code', 'language', 'file', 'diff-option', 'file-diff', 'files', 'project', 'finished', 'showCodeOpened', 'message', 'fromBranch', 'toBranch', 'git-mode', 'read-only', 'history-limit'],
  emits: ['message-change', 'save-file', 'add-file', 'open-file', 'close', 'sub-task', 'commit-view'],
  data() {
    return {
      id: uuidv4(),
      // When no explicit `diff-option` prop is given, start on the content view.
      // The default (diff vs. content) is resolved in applyDefaultDiffView()
      // once we know whether the on-disk file actually changed.
      showDiff: this.diffOption != undefined ? this.diffOption : false,
      orgContent: null,
      diffEditContent: null,
      diffBaseContent: null,
      diff: this.fileDiff,
      editMode: false,
      editContent: null,
      hasUnsavedFileChanges: false,
      loadingStats: false,
      stats: null,
      last_modification: null,
      size: null,
      showCode: this.$props.showCodeOpened !== false,
      prevScrollTop: 0,
      isAtBottom: true,
      isUserScrolledUp: false,
      shouldForceScrollToBottom: true,
      deletionPercentage: 0,
      additionPercentage: 0,
      deletionCount: 0,
      additionCount: 0,
      isDangerousChange: false,
      changeRiskMessage: '',
      isNewFile: true,
      localCode: null,
      showConfirmModal: false,
      showRollbackModal: false,
      showHeavyChangeConfirmModal: false,
      isRollingBack: false,
      pendingViewSwitch: null,
      changesetErrors: [],
      patchPattern: null,
      codeUpdateCounter: 0,
      codeHash: 0,
      lastCodeValue: null,
      baseFileChanged: false,
      showPreviousDiff: false,
      selectedPreviousId: null,
      actionFeedback: {
        copy: false,
        save: false,
        patch: false
      },
      // ── Git diff / history ─────────────────────────────────────────────
      // Raw patch of the working tree, index or a commit (git mode only).
      gitHeader: '',
      gitDiffLoading: false,
      gitDiffError: null,
      // File history panel
      showHistory: false,
      gitHistory: [],
      gitHistoryLoading: false,
      gitHistoryError: null,
      // Commit being inspected from the history panel (read-only)
      selectedGitCommit: null,
      gitCommitContent: null,
      // State saved while a commit is open, restored when going back
      gitStateSnapshot: null,
      gitRequestToken: 0
    }
  },
  computed: {
    effectiveCode() {
      // A commit opened from the history panel is read-only: show the content
      // stored in that commit instead of the working tree version.
      if (this.selectedGitCommit && this.gitCommitContent !== null) {
        return this.gitCommitContent
      }
      return this.localCode !== null ? this.localCode : this.code
    },

    /** Render a git patch instead of a content-to-content diff */
    isGitDiffView() {
      return !!this.gitMode || !!this.selectedGitCommit
    },

    /** Git source currently shown: the requested mode or the selected commit */
    currentGitMode() {
      return this.selectedGitCommit ? 'commit' : this.gitMode
    },

    /** Editing is disabled for deleted files and while inspecting a commit */
    canEditFile() {
      return !this.readOnly && !this.selectedGitCommit
    },

    canLoadHistory() {
      return !!this.file && !!this.$api?.repo?.fileHistory
    },

    /**
     * Height of the content area.
     *
     * Monaco and git diffs must fill the panel: their parent gives them a real
     * height (`h-full`). Plain read-only blocks keep the line-based estimate so
     * they do not stretch inside a chat message.
     */
    contentStyle() {
      if (this.isGitDiffView || this.editMode) {
        // Fill the panel, but never collapse to 0 in contexts where the
        // CodeViewer is rendered with an auto height (e.g. a chat message).
        return { height: '100%', minHeight: '320px' }
      }
      return { height: `${this.editorHeight}px` }
    },

    /**
     * All previous versions of THIS file found in PREVIOUS messages (newest first).
     * Mapping uses the code block file name (```language filename).
     * Blocks without a file name are skipped.
     */
    previousCodeBlocks() {
      const messages = this.chat?.messages
      if (!this.file || !this.message || !messages?.length) return []
      // Skip synthetic file names generated for blocks without a real file name
      if (/^content\.[a-z0-9]+$/i.test(this.file)) return []

      const currentId = this.message.doc_id || this.message.id
      const currentIndex = messages.findIndex((m) => (m.doc_id || m.id) === currentId)
      if (currentIndex <= 0) return []

      const results = []
      for (let i = currentIndex - 1; i >= 0; i--) {
        const blocks = this.$service.chat.extractCodeBlocksFromMessage(messages[i])
        const match = blocks.find((block) => block.filePath === this.file)
        if (match) {
          results.push({
            ...match,
            message: messages[i],
            messageId: messages[i].doc_id || messages[i].id,
            user: messages[i].user,
            when: messages[i].updated_at || messages[i].created_at
          })
        }
      }
      return results
    },

    /**
     * The previous version currently chosen for comparison.
     * Falls back to the most recent one when none has been picked explicitly.
     */
    selectedPreviousBlock() {
      if (!this.previousCodeBlocks.length) return null
      if (this.selectedPreviousId) {
        const found = this.previousCodeBlocks.find((block) => block.messageId === this.selectedPreviousId)
        if (found) return found
      }
      return this.previousCodeBlocks[0]
    },

    previousCodeContent() {
      return this.selectedPreviousBlock?.content ?? null
    },

    previousCodeLabel() {
      const block = this.selectedPreviousBlock
      if (!block) return 'previous version'
      const user = block.user || 'assistant'
      const time = block.when ? moment(block.when).fromNow() : ''
      return time ? `previous version by ${user} (${time})` : `previous version by ${user}`
    },

    hasPreviousVersion() {
      return this.previousCodeBlocks.length > 0
    },

    /**
     * The "old" side of the diff:
     * - previous-version compare -> the selected block from a previous message
     * - file diff                -> the file currently on disk
     */
    comparisonOrgContent() {
      return this.showPreviousDiff ? this.previousCodeContent : this.orgContent
    },

    hasLocalChanges() {
      return this.localCode !== null && this.localCode !== this.code
    },

    hasDiffEdits() {
      return this.diffEditContent !== this.diffBaseContent
    },

    editorHeight() {
      const lineCount = this.effectiveCode?.split("\n").length || 10
      const estimated = Math.max(lineCount * 20, 200)
      return Math.min(estimated, 600)
    },

    isStreaming() {
      return !this.finished && this.code
    },

    isPatch() {
      return this.language === 'diff'
    },

    isMarkdown() {
      return this.validatedLanguage === 'md'
    },

    fileName() {
      return this.file?.split('/').reverse()[0]
    },

    isCommand() {
      return this.language === 'bash'
    },

    isNoChange() {
      return !this.isGitDiffView && this.orgContent === this.code
    },

    fileLanguage() {
      if (this.language) {
        if (hljs.getLanguage(this.language)) return this.language
      }
      const ext = this.file?.split('.').reverse()[0]
      if (ext) return EXTENSION_LANGUAGE_MAP[ext] || ext
      return 'markdown'
    },

    validatedLanguage() {
      const lang = this.fileLanguage
      try {
        if (lang && hljs.getLanguage(lang)) {
          return lang
        }
      } catch (error) {
        console.warn(`Invalid language detected: ${lang}`, error)
      }
      return 'markdown'
    },

    /**
     * Project the message is addressed to (Message.project_id).
     * A message can target a project different from the chat's working project.
     */
    messageProject() {
      const projectId = this.message?.project_id
      if (!projectId) return null
      return this.$storex.projects.allProjectsById?.[projectId] || null
    },

    /**
     * Project the chat belongs to (`project_id` is the working one, falling back
     * to the owner for chats that never overrode it).
     */
    chatProject() {
      const projectId = this.chat?.project_id || this.chat?.owner_project_id
      if (!projectId) return null
      return this.$storex.projects.allProjectsById?.[projectId] || null
    },

    /**
     * Project this code block belongs to.
     *
     * Order matters: a message can target another project than the chat
     * (`Message.project_id`) and every file path of the block is relative to
     * THAT project. The `project` prop comes from the chat/document context
     * (i.e. the chat's project), so it must never win over the message's own
     * project — otherwise the diff/read requests are sent with the wrong
     * `codx_path` and the diff comes back empty.
     */
    effectiveProject() {
      return this.messageProject || this.project || this.chatProject
    },

    $api() {
      if (this.effectiveProject?.$api) {
        return this.effectiveProject.$api
      }

      return this.$storex.projects.activeProject?.$api || this.$storex.api
    },

    lastLine() {
      return this.code?.split("\n").reverse()[0]
    },

    associatedChat() {
      return this.$service.chat.findChatByFileAndMessage({
        chat: this.chat,
        file: this.file,
        messageId: this.message?.doc_id
      })
    },
    isJSONChangeset() {
      return this.language === 'json-changeset'
    },
    hasPatchPattern() {
      return this.patchPattern !== null
    },
    contentCreatedAt() {
      return this.message?.updated_at
    },
    /**
     * Whether the diff/read requests may be triggered automatically.
     * Only when the block has full context — a chat, a message already marked
     * as done (`message.done`) and a non-stale message. Otherwise the block
     * renders the plain code and the user opens the diff explicitly through
     * the refresh action (`showDiffInfo`).
     */
    canAutoLoadDiff() {
      return !!this.chat && !!this.message && this.message.done === true
    },
    isContentOutdated() {
      if (this.isNoChange || !this.contentCreatedAt || !this.last_modification) {
        return false
      }
      const contentCreatedTime = new Date(this.contentCreatedAt).getTime()
      const fileModifiedTime = new Date(this.last_modification).getTime()
      return fileModifiedTime > contentCreatedTime
    }
  },
  watch: {
    async finished() {
      if (this.finished) {
        this.isUserScrolledUp = false
        this.shouldForceScrollToBottom = false

        if (this.gitMode) {
          await this.loadGitDiff()
        } else if (this.canAutoLoadDiff) {
          await this.loadDiffInfo()
        }
      }
      if (this.chat?.mode === 'vibe') {
        // Automatic save in vibe mode - bypass heavy change prompt
        this.saveToFile(true)
      }
    },
    file() {
      this.resetGitCommit()
      this.gitHistory = []
      this.gitHistoryError = null
      this.showHistory = false
      if (this.gitMode) this.loadGitDiff()
    },
    gitMode() {
      this.resetGitCommit()
      this.gitHistory = []
      this.gitHistoryError = null
      this.showHistory = false
      if (this.gitMode) this.loadGitDiff()
    },
    last_modification() {
      this.$forceUpdate()
    },
    code(newCode, oldCode) {
      if (newCode === oldCode) return
      
      if (this.editMode) {
        this.changesetErrors = []
        this.detectPatchPattern()
        return
      }
      
      this.localCode = null
      
      this.changesetErrors = []
      this.detectPatchPattern()
      this.codeUpdateCounter++
      this.codeHash = this.generateCodeHash(newCode)
      
      this.$nextTick(() => {
        const viewCode = this.$el?.querySelector('.view-code')
        if (!viewCode) return
        
        if (this.isStreaming) {
          viewCode.scrollTop = viewCode.scrollHeight
        } else {
          this.prevScrollTop = viewCode.scrollTop
        }
      })
    }
  },
  mounted() {
    if (this.chat?.mode === 'vibe') {
      this.showCode = false
    }
    if (this.gitMode) {
      this.loadGitDiff()
    } else if (this.finished && this.showCode && this.canAutoLoadDiff) {
      this.loadDiffInfo()
    }
    this.detectPatchPattern()
    this.codeHash = this.generateCodeHash(this.code)
    this.lastCodeValue = this.code
    const viewCode = this.$el?.querySelector('.view-code')
    if (viewCode) viewCode.addEventListener('scroll', this.saveScrollPosition)
  },
  beforeUnmount() {
    const viewCode = this.$el?.querySelector('.view-code')
    if (viewCode) viewCode.removeEventListener('scroll', this.saveScrollPosition)
  },
  methods: {
    generateCodeHash(code) {
      if (!code) return 0
      let hash = 0
      for (const char of code) {
        hash = (hash << 5) - hash + char.charCodeAt(0)
        hash |= 0
      }
      return Math.abs(hash)
    },

    // ── Git diff / history ───────────────────────────────────────────────
    /** Load the raw patch of the current git mode (worktree / staged / commit) */
    async loadGitDiff() {
      const mode = this.currentGitMode
      if (!mode || !this.file || !this.$api?.repo?.fileDiff) return

      const token = ++this.gitRequestToken
      this.gitDiffLoading = true
      this.gitDiffError = null
      try {
        const payload = await this.$api.repo.fileDiff({
          path: this.file,
          mode,
          commit: this.selectedGitCommit?.commit
        })
        if (token !== this.gitRequestToken) return
        this.diff = payload?.diff || ''
        this.gitHeader = payload?.header || ''
        this.stats = this.formatGitStats(payload) || (this.diff ? 'File changes' : 'No changes')
        this.orgContent = null
        this.diffEditContent = null
        this.diffBaseContent = null
        this.isNewFile = false
        this.showDiff = true
      } catch (ex) {
        if (token !== this.gitRequestToken) return
        this.diff = ''
        this.gitHeader = ''
        this.stats = ''
        this.gitDiffError = ex?.response?.data?.detail || ex?.message || String(ex)
      } finally {
        if (token === this.gitRequestToken) this.gitDiffLoading = false
      }
    },

    /** Human-readable stats for the header (same shape as files.diff stats) */
    formatGitStats(payload) {
      const additions = payload?.additions || 0
      const deletions = payload?.deletions || 0
      if (!additions && !deletions) return ''
      const insertionLabel = additions === 1 ? 'insertion' : 'insertions'
      const deletionLabel = deletions === 1 ? 'deletion' : 'deletions'
      return `${additions} ${insertionLabel}, ${deletions} ${deletionLabel}`
    },

    /** Load the commits that touched the current file */
    async loadGitHistory() {
      if (!this.canLoadHistory) {
        this.gitHistory = []
        this.gitHistoryError = 'File history is not available for this project'
        return
      }

      this.gitHistoryLoading = true
      this.gitHistoryError = null
      try {
        const result = await this.$api.repo.fileHistory({
          path: this.file,
          limit: this.historyLimit || 25
        })
        const commits = Array.isArray(result) ? result : (result?.commits || [])
        this.gitHistory = commits.map((commit) => ({
          ...commit,
          relative: this.relativeGitDate(commit.date)
        }))
      } catch (ex) {
        this.gitHistory = []
        this.gitHistoryError = ex?.response?.data?.detail || ex?.message || String(ex)
      } finally {
        this.gitHistoryLoading = false
      }
    },

    /** Show / hide the file history list */
    toggleHistory() {
      if (this.showHistory) {
        this.showHistory = false
        return
      }
      this.showHistory = true
      if (!this.gitHistory.length && !this.gitHistoryLoading) {
        this.loadGitHistory()
      }
    },

    /** Open a commit from the history panel (read-only view) */
    async selectGitCommit(commit) {
      if (!commit?.commit || !this.file) return
      if (!this.selectedGitCommit) this.saveGitState()

      this.selectedGitCommit = commit
      this.gitCommitContent = null
      this.showHistory = false
      this.editMode = false
      this.showPreviousDiff = false
      this.$emit('commit-view', commit)

      try {
        this.gitCommitContent = await this.$api.repo.readFromBranch(this.file, commit.commit)
      } catch {
        this.gitCommitContent = ''
      }
      await this.loadGitDiff()
    },

    /** Leave the commit view and show the current working tree/index again */
    async backToGitWorkingChanges() {
      if (!this.selectedGitCommit) return
      this.selectedGitCommit = null
      this.gitCommitContent = null
      this.gitHeader = ''
      this.showHistory = false
      this.$emit('commit-view', null)

      if (this.gitMode) {
        this.gitStateSnapshot = null
        await this.loadGitDiff()
        return
      }
      this.restoreGitState()
    },

    /** Snapshot the non-git diff state before opening a historical commit */
    saveGitState() {
      this.gitStateSnapshot = {
        showDiff: this.showDiff,
        diff: this.diff,
        orgContent: this.orgContent,
        stats: this.stats,
        isNewFile: this.isNewFile,
        showPreviousDiff: this.showPreviousDiff,
        selectedPreviousId: this.selectedPreviousId,
        diffEditContent: this.diffEditContent,
        diffBaseContent: this.diffBaseContent,
        localCode: this.localCode,
        editMode: this.editMode
      }
    },

    /** Restore the state saved by `saveGitState` */
    restoreGitState() {
      const state = this.gitStateSnapshot
      this.gitStateSnapshot = null
      if (!state) {
        this.showDiff = !!this.orgContent
        return
      }
      this.showDiff = state.showDiff
      this.diff = state.diff
      this.orgContent = state.orgContent
      this.stats = state.stats
      this.isNewFile = state.isNewFile
      this.showPreviousDiff = state.showPreviousDiff
      this.selectedPreviousId = state.selectedPreviousId
      this.diffEditContent = state.diffEditContent
      this.diffBaseContent = state.diffBaseContent
      this.localCode = state.localCode
      this.editMode = state.editMode
    },

    /** Drop the commit currently inspected and any saved state */
    resetGitCommit() {
      const hadCommit = !!this.selectedGitCommit
      this.selectedGitCommit = null
      this.gitCommitContent = null
      this.gitStateSnapshot = null
      this.gitHeader = ''
      if (hadCommit) this.$emit('commit-view', null)
    },

    /** Relative time without pulling a date library into the diff code */
    relativeGitDate(date) {
      if (!date) return ''
      const value = moment(date)
      return value.isValid() ? value.fromNow() : date
    },

    detectPatchPattern() {
      if (!this.code) {
        this.patchPattern = null
        return
      }

      const patchRegex = /^<<<<\s*\n([\s\S]*?)\n====\s*\n([\s\S]*?)\n>>>>\s*$/m
      const match = this.code.match(patchRegex)

      if (match) {
        this.patchPattern = {
          oldContent: match[1],
          newContent: match[2]
        }
      } else {
        this.patchPattern = null
      }
    },

    handleFileNameClick() {
      this.$storex.ui.openFileInViewer(this.file)
    },

    applyChangeset() {
      try {
        const changeset = JSON.parse(this.code)
        if (!Array.isArray(changeset)) {
          this.changesetErrors.push('Changeset must be a JSON array')
          return
        }

        let processedCode = this.code
        changeset.forEach((change, idx) => {
          try {
            const { search_type, search, replace, replace_all } = change
            if (!search_type || !search || replace === undefined) {
              throw new Error('Missing required fields: search_type, search, or replace')
            }

            let result
            if (search_type === 'plain') {
              const searchIndex = processedCode.indexOf(search)
              if (searchIndex === -1) {
                throw new Error(`Pattern not found in code`)
              }

              if (replace_all) {
                processedCode = processedCode.split(search).join(replace)
              } else {
                processedCode = processedCode.substring(0, searchIndex) +
                  replace +
                  processedCode.substring(searchIndex + search.length)
              }
            } else if (search_type === 'regex') {
              try {
                const flags = replace_all ? 'g' : ''
                const regex = new RegExp(search, flags)
                processedCode = processedCode.replace(regex, replace)
              } catch (regexError) {
                throw new Error(`Invalid regex pattern: ${regexError.message}`)
              }
            } else {
              throw new Error(`Unknown search_type: ${search_type}. Must be 'plain' or 'regex'`)
            }
          } catch (error) {
            this.changesetErrors.push(`[Item ${idx}] ${error.message}`)
          }
        })

        this.localCode = processedCode
      } catch (parseError) {
        this.changesetErrors.push(`Failed to parse changeset JSON: ${parseError.message}`)
      }
    },

    applyUserChange(newContent) {
      if (!newContent) return
      this.localCode = newContent
      this.diffEditContent = newContent
      this.diffBaseContent = newContent
      this.editMode = false
      this.showPreviousDiff = false
      this.showDiff = !!this.orgContent
      this.hasUnsavedFileChanges = true
    },

    resetLocalChanges() {
      this.localCode = null
      this.diffEditContent = this.code
      this.diffBaseContent = this.code
      this.hasUnsavedFileChanges = false
      this.showPreviousDiff = false
      this.showDiff = !!this.orgContent && !this.isNoChange && !this.isMarkdown
    },

    parseStatsString() {
      if (!this.stats) return { deletions: 0, insertions: 0 }
      const deleteMatch = this.stats.match(/(\d+) deletion/)
      const insertMatch = this.stats.match(/(\d+) insertion/)
      return {
        deletions: deleteMatch ? parseInt(deleteMatch[1]) : 0,
        insertions: insertMatch ? parseInt(insertMatch[1]) : 0
      }
    },

    calculateDiffPercentages() {
      if (!this.stats || !this.orgContent || this.isMarkdown) return
      const { deletions, insertions } = this.parseStatsString()
      const total = deletions + insertions
      this.deletionCount = deletions
      this.additionCount = insertions
      if (total === 0) {
        this.deletionPercentage = 0
        this.additionPercentage = 0
        return
      }
      this.deletionPercentage = (deletions / total) * 100
      this.additionPercentage = (insertions / total) * 100
      this.evaluateChangeRisk()
    },

    evaluateChangeRisk() {
      if (this.isMarkdown) return
      const { deletions, insertions } = this.parseStatsString()
      const originalLines = this.orgContent?.split('\n').length || 1
      const newLines = this.effectiveCode?.split('\n').length || 1
      const deletionRatio = deletions / originalLines
      const lineChangeRatio = Math.abs(newLines - originalLines) / originalLines
      const totalChanges = deletions + insertions
      const changeIntensity = totalChanges / originalLines
      const DANGEROUS_DELETION_RATIO = 0.4
      const DANGEROUS_INTENSITY = 0.5
      const DANGEROUS_LINE_LOSS = 0.3
      const isDeletion = deletionRatio > DANGEROUS_DELETION_RATIO
      const isHighIntensity = changeIntensity > DANGEROUS_INTENSITY
      const isLineLoss = lineChangeRatio > DANGEROUS_LINE_LOSS && deletions > insertions
      this.isDangerousChange = isDeletion || isHighIntensity || isLineLoss
      this.changeRiskMessage = this.generateRiskMessage(deletionRatio, changeIntensity, lineChangeRatio, deletions, insertions)
    },

    generateRiskMessage(delRatio, intensity, lineRatio, deletions, insertions) {
      if (delRatio > 0.4) return `${(delRatio * 100).toFixed(0)}% of original content deleted. Critical review recommended.`
      if (lineRatio > 0.3 && deletions > insertions) return `File lost ~${Math.round(lineRatio * 100)}% of its content. Check if changes are intentional.`
      if (intensity > 0.5) return `Over 50% of file modified. This may indicate significant structural changes.`
      return 'High modification level detected.'
    },

    applyPatch() {
      // Same project as the diff/read requests: the patch route is scoped by the
      // API instance's `codx_path`, so the global API wrote to the active project.
      this.$api.run.patch({ patch: this.code })
    },

    toggleView() {
      if (this.hasDiffEdits) {
        this.pendingViewSwitch = 'toggle'
        this.showConfirmModal = true
      } else {
        this.showPreviousDiff = false
        this.showDiff = !this.showDiff
      }
    },

    /**
     * Compares this block against a specific previous version from an earlier
     * message instead of against the file currently on disk.
     */
    selectPreviousVersion(block) {
      this.selectedPreviousId = block.messageId
      this.showPreviousDiff = true
      this.editMode = false
      this.showDiff = true
    },

    /**
     * Exits the previous-version comparison and returns to the on-disk diff.
     */
    clearPreviousDiff() {
      this.showPreviousDiff = false
      this.selectedPreviousId = null
      this.showDiff = !!this.orgContent && !this.isNoChange && !this.isMarkdown
    },

    /**
     * Resolves the default view (diff vs. plain content).
     * - If the `diff-option` prop is set, the user's choice always wins.
     * - Otherwise show the diff only when the on-disk file actually changed:
     *   new/empty files and unchanged files fall back to the content view.
     */
    applyDefaultDiffView() {
      // Git patches always start in diff view: they do not have two contents
      // to decide from, and the patch is exactly what the user opened.
      if (this.isGitDiffView) {
        this.showDiff = true
        return
      }
      if (this.diffOption != undefined) {
        this.showDiff = this.diffOption
        return
      }
      this.showDiff = !!this.orgContent && !this.isNewFile && !this.isNoChange && !this.isMarkdown
    },

    async loadDiffInfo() {
      // In git mode the diff comes from the repository, not from comparing the
      // provided content against the file on disk.
      if (this.isGitDiffView) {
        return this.loadGitDiff()
      }

      const diffRequest = {
        path: this.file,
        content: this.effectiveCode
      }
      if (this.fromBranch) diffRequest.from_branch = this.fromBranch
      if (this.toBranch) diffRequest.to_branch = this.toBranch

      const { diff, stats, last_modification, size } = await this.$api.files.diff(diffRequest)
      this.diff = diff
      this.stats = stats
      this.last_modification = last_modification
      this.size = size
      this.isNewFile = !last_modification
      if (!stats && diff) this.stats = 'File changes'

      let content = ""
      if (!this.isNewFile) {
        try {
          if (this.fromBranch) {
            const { content: fileContent } = await this.$api.repo.readFromBranch(this.file, this.fromBranch)
            content = fileContent
            this.isNewFile = !fileContent
          } else {
            const { content: fileContent } = await this.$api.files.read(this.file)
            content = fileContent
            this.isNewFile = !fileContent
          }
        } catch (ex) {
          console.error(ex)
          this.isNewFile = true
        }
      }

      if (this.isNewFile) {
        this.stats = "New file"
      }

      this.orgContent = content
      this.diffEditContent = this.effectiveCode
      this.diffBaseContent = this.effectiveCode
      this.calculateDiffPercentages()
      // Decide default view now that orgContent / isNewFile are known
      this.applyDefaultDiffView()
    },
    async showDiffInfo() {
      try {
        this.loadingStats = true
        this.showCode = true

        if (this.file) {
          await this.loadDiffInfo()

          if (!this.isGitDiffView && this.isJSONChangeset) {
            this.applyChangeset()
          }
        }
      } finally {
        this.loadingStats = false
      }
    },

    onEdit() {
      if (!this.canEditFile) return
      if (this.editMode) {
        this.cancelEdit()
        return
      }
      this.showPreviousDiff = false
      this.editContent = this.effectiveCode
      this.editMode = true
      this.showDiff = false
      this.hasUnsavedFileChanges = false
    },

    cancelEdit() {
      this.editMode = false
      this.editContent = null
    },

    onEditorChange(value) {
      this.editContent = value
      this.hasUnsavedFileChanges = true
    },

    onDiffViewerChange(newValue) {
      // Update diffEditContent from DiffViewer changes
      this.diffEditContent = newValue
      // Also update localCode to persist changes
      this.localCode = newValue
      this.hasUnsavedFileChanges = true
    },

    applyMessageChange() {
      this.$emit('message-change', { orgContent: this.effectiveCode, newContent: this.editContent })
      this.applyUserChange(this.editContent)
      this.cancelEdit()
    },

    discardDiffChanges() {
      this.diffEditContent = this.diffBaseContent
      this.showDiff = false
      this.showPreviousDiff = false
    },

    confirmApplyDiff() {
      this.localCode = this.diffEditContent
      this.diffBaseContent = this.diffEditContent
      this.showConfirmModal = false
      const shouldToggle = this.pendingViewSwitch === 'toggle'
      this.pendingViewSwitch = null
      if (shouldToggle) {
        this.showDiff = !this.showDiff
      }
    },

    confirmDiscardDiff() {
      this.diffEditContent = this.diffBaseContent
      this.showConfirmModal = false
      const shouldToggle = this.pendingViewSwitch === 'toggle'
      this.pendingViewSwitch = null
      if (shouldToggle) {
        this.showDiff = !this.showDiff
      }
    },

    cancelConfirm() {
      this.showConfirmModal = false
      this.pendingViewSwitch = null
    },

    confirmRollback() {
      this.showRollbackModal = true
    },

    cancelRollback() {
      this.showRollbackModal = false
    },

    async executeRollback() {
      try {
        this.isRollingBack = true
        await this.$api.files.rollback(this.file)
        this.$ui.notify({ type: 'success', message: `${this.fileName} rolled back to previous state` })
        this.showRollbackModal = false
        this.localCode = null
        if (this.gitMode) {
          await this.loadGitDiff()
        } else {
          await this.loadDiffInfo()
        }
        this.showDiff = true
      } catch (error) {
        console.error('Rollback failed:', error)
        this.$ui.notify({ type: 'error', message: `Rollback failed: ${error.message}` })
      } finally {
        this.isRollingBack = false
      }
    },

    /**
     * Entry point for saving. Guards against accidentally persisting a heavy
     * modification by asking for explicit confirmation first.
     * Pass `skipConfirm = true` for automated flows (e.g. vibe mode).
     */
    saveToFile(skipConfirm = false) {
      if (!this.canEditFile) return
      if (!skipConfirm && this.isDangerousChange) {
        this.showHeavyChangeConfirmModal = true
        return
      }
      this.performSave()
    },

    async performSave() {
      if (!this.canEditFile) return
      this.triggerActionFeedback('save')
      let content
      if (this.editMode && this.editContent) {
        content = this.editContent
      } else if (this.showDiff && this.diffEditContent) {
        content = this.diffEditContent
      } else {
        content = this.effectiveCode
      }
      // The file path is relative to THIS block's project, so the write must be
      // sent with its `codx_path`. Hand the project over: the parent (Chat.vue)
      // used to resolve it from the chat and every save of a message addressing
      // another project (`Message.project_id`) was written to the wrong root.
      this.$emit('save-file', {
        file: this.file,
        content,
        project: this.effectiveProject
      })
      this.hasUnsavedFileChanges = false
      if (this.editMode) this.cancelEdit()
      this.showDiff = false
      this.showPreviousDiff = false
      this.localCode = null
      this.diffEditContent = null
      this.diffBaseContent = null
      if (this.gitMode) {
        await this.loadGitDiff()
      } else {
        await this.loadDiffInfo()
      }
    },

    confirmHeavyChangeSave() {
      this.showHeavyChangeConfirmModal = false
      this.performSave()
    },

    cancelHeavyChangeSave() {
      this.showHeavyChangeConfirmModal = false
    },

    triggerActionFeedback(action) {
      const FEEDBACK_DURATION = 800
      this.actionFeedback[action] = true
      setTimeout(() => { this.actionFeedback[action] = false }, FEEDBACK_DURATION)
    },

    runCommand() {
      // Scripts run inside the project the block belongs to
      this.$api.apps.runScript(this.code)
    },

    onCopy() {
      this.$ui.copyTextToClipboard(this.effectiveCode)
      this.triggerActionFeedback('copy')
    },

    createSubTask() {
      const content = [
        '```' + this.fileLanguage + ' ' + this.file,
        this.effectiveCode,
        '```'
      ].join('\n')
      this.$emit('sub-task', { file: this.file, content })
    },

    onTaskClick() {
      if (this.associatedChat) {
        this.$chats.setActiveChat(this.associatedChat)
      } else {
        this.createSubTask()
      }
    },

    saveScrollPosition() {
      const viewCode = this.$el?.querySelector('.view-code')
      if (!viewCode) return
      
      if (this.isStreaming) {
        viewCode.scrollTop = viewCode.scrollHeight
        return
      }
      
      this.prevScrollTop = viewCode.scrollTop
      const distanceFromBottom = viewCode.scrollHeight - viewCode.scrollTop - viewCode.clientHeight
      this.isAtBottom = distanceFromBottom <= 40
    },

    applyPatchFromPattern() {
      if (!this.patchPattern) return
      this.applyUserChange(this.patchPattern.newContent)
      this.triggerActionFeedback('patch')
    }
  }
}
</script>

<style>
.header-code-highlight {
  display: none !important
}
.wrapper-code-highlighter {
  height: 100%
}

@keyframes blink-animation {
  0%, 49% { opacity: 1 }
  50%, 100% { opacity: 0.4 }
}

.blink-save {
  animation: blink-animation 0.8s ease-in-out
}
</style>