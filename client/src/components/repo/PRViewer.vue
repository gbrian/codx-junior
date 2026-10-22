<script setup>
import "@git-diff-view/vue/styles/diff-view.css"
import { SplitterGroup, SplitterPanel, SplitterResizeHandle } from 'radix-vue'
import BranchSelector from '@/components/vibe/panels/BranchSelector.vue'
import DiffViewer from '@/components/DiffViewer.vue'
</script>

<template>
  <div class="azure-pr-view flex flex-col h-full overflow-hidden bg-base-100">
    <!-- Top toolbar -->
    <header class="flex items-center justify-between px-3 py-1.5 bg-base-200 border-b border-base-content/10 shrink-0 gap-2 flex-wrap">
      <!-- Branch selector -->
      <div class="flex items-center gap-2 grow min-w-0">
        <i class="fa-solid fa-code-branch text-warning shrink-0"></i>
        <BranchSelector
          v-if="project"
          :project="project"
          :current-branch="fromBranch"
          :compare-branch="toBranch"
          :available-branches="availableBranches"
          :loading="loading"
          @branch-changed="onFromBranchChanged"
          @compare-branch-changed="onToBranchChanged"
        />
        <span v-else class="flex items-center gap-2 font-mono text-sm">
          <span class="font-semibold">{{ fromBranch }}</span>
          <i class="fa-solid fa-arrow-right text-xs text-base-content/40"></i>
          <span class="font-semibold">{{ toBranch }}</span>
        </span>
      </div>

      <!-- Stats + Actions -->
      <div class="flex items-center gap-2 shrink-0">
        <div class="flex items-center gap-2 text-xs text-base-content/60">
          <span class="badge badge-sm badge-ghost">
            <i class="fa-solid fa-file-pen text-warning"></i> {{ changeCount }}
          </span>
          <span class="badge badge-sm badge-success badge-ghost">
            <i class="fa-solid fa-plus"></i> {{ insertions }}
          </span>
          <span class="badge badge-sm badge-error badge-ghost">
            <i class="fa-solid fa-minus"></i> {{ deletions }}
          </span>
        </div>

        <div class="divider divider-horizontal mx-1"></div>

        <!-- Navigation -->
        <button class="btn btn-xs btn-ghost" @click="navigateFile(-1)" :disabled="!hasPreviousFile" title="Previous file">
          <i class="fa-solid fa-chevron-left"></i>
        </button>
        <button class="btn btn-xs btn-ghost" @click="navigateFile(1)" :disabled="!hasNextFile" title="Next file">
          <i class="fa-solid fa-chevron-right"></i>
        </button>

        <!-- Comments modal toggle -->
        <button class="btn btn-xs btn-ghost gap-1" @click="openCommentsModal" title="View all comments">
          <i class="fa-solid fa-comment-dots"></i>
          <span class="badge badge-xs badge-info">{{ totalCommentCount }}</span>
        </button>

        <!-- Reload -->
        <button class="btn btn-xs btn-ghost" @click="$emit('refresh')" :disabled="loading" title="Refresh">
          <i class="fa-solid fa-rotate-right" :class="{ 'animate-spin': loading }"></i>
        </button>
      </div>
    </header>

    <!-- Loading state -->
    <div v-if="loading" class="flex items-center justify-center grow gap-2 text-base-content/50">
      <i class="fa-solid fa-spinner animate-spin text-xl"></i>
      <span>Loading changes...</span>
    </div>

    <template v-else-if="files?.length">
      <!-- Main splitter layout -->
      <SplitterGroup class="grow" direction="horizontal">
        <!-- Left panel: File list grouped by folder or by the chat that changed it -->
        <SplitterPanel :min-size="15" :defaultSize="25" :collapsible="true" class="overflow-hidden">
          <div class="flex flex-col h-full">
            <!-- File list header -->
            <div class="flex items-center justify-between px-2 py-1.5 bg-base-200/50 border-b border-base-content/10 shrink-0">
              <span class="text-xs font-semibold">Files ({{ files.length }})</span>
              <div class="flex items-center gap-1">
                <button class="btn btn-xs btn-ghost" @click="selectAllFiles" title="Select all">
                  <i class="fa-solid fa-check-double text-[10px]"></i>
                </button>
                <button class="btn btn-xs btn-ghost" @click="clearSelection" title="Clear selection">
                  <i class="fa-solid fa-xmark text-[10px]"></i>
                </button>
              </div>
            </div>

            <!-- Grouping: folders / chats that changed the files -->
            <div class="flex items-center gap-1 px-2 py-1 border-b border-base-content/10 shrink-0">
              <div class="join">
                <button
                  class="join-item btn btn-xs"
                  :class="groupMode === 'folder' ? 'btn-primary' : 'btn-ghost'"
                  @click="setGroupMode('folder')"
                  title="Group files by folder"
                  aria-label="Group files by folder"
                >
                  <i class="fa-solid fa-folder-tree text-[10px]"></i>
                </button>
                <button
                  class="join-item btn btn-xs"
                  :class="groupMode === 'chat' ? 'btn-primary' : 'btn-ghost'"
                  @click="setGroupMode('chat')"
                  :title="`Group files by the chat that changed them (${chats.length} chats)`"
                  aria-label="Group files by chat"
                >
                  <i class="fa-solid fa-comments text-[10px]"></i>
                  <span v-if="chats.length" class="ml-1">{{ chats.length }}</span>
                </button>
              </div>

              <button
                v-if="groupMode === 'chat'"
                class="btn btn-xs btn-ghost"
                @click="showProbableChats = !showProbableChats"
                :title="showProbableChats ? 'Show confirmed chats only' : 'Include probable chats'"
                aria-label="Toggle probable chats"
              >
                <i class="fa-solid" :class="showProbableChats ? 'fa-filter' : 'fa-filter-circle-xmark'"></i>
              </button>

              <button
                class="btn btn-xs btn-ghost ml-auto"
                @click="refreshChatAnalysis()"
                :disabled="chatAnalysisLoading"
                :title="chatAnalysisLoading ? 'Scanning chats…' : 'Re-scan the chats that changed these files'"
                aria-label="Re-scan chats"
              >
                <i class="fa-solid fa-rotate" :class="{ 'animate-spin': chatAnalysisLoading }"></i>
              </button>
            </div>

            <!-- Filter bar -->
            <div class="flex items-center gap-1 px-2 py-1.5 border-b border-base-content/10 shrink-0">
              <div class="relative grow">
                <i class="fa-solid fa-magnifying-glass absolute left-2 top-1/2 -translate-y-1/2 text-[10px] text-base-content/40"></i>
                <input
                  type="text"
                  v-model="fileFilter"
                  placeholder="Filter files..."
                  class="input input-xs input-bordered w-full pl-6"
                />
              </div>
            </div>

            <!-- File list grouped by chat (chat view of the file tree) -->
            <div v-if="groupMode === 'chat'" class="grow overflow-y-auto">
              <div v-if="chatAnalysisLoading && !analysisGroups.length" class="flex flex-col items-center justify-center py-8 gap-2 text-base-content/40">
                <i class="fa-solid fa-spinner animate-spin"></i>
                <span class="text-xs">Scanning chats…</span>
              </div>

              <div v-else-if="chatAnalysisError" class="flex flex-col items-center justify-center py-8 px-2 gap-2 text-error/80 text-center">
                <i class="fa-solid fa-triangle-exclamation"></i>
                <span class="text-xs break-words">{{ chatAnalysisError }}</span>
              </div>

              <template v-else-if="analysisGroups.length">
                <div v-for="group in analysisGroups" :key="group.key" class="file-folder-group">
                  <div
                    class="flex items-center gap-1 px-2 py-1 text-xs font-semibold bg-base-200/80 cursor-pointer hover:bg-base-300/80"
                    @click="toggleChatGroup(group.key)"
                  >
                    <i :class="isChatGroupExpanded(group.key) ? 'fa-solid fa-chevron-down' : 'fa-solid fa-chevron-right'" class="text-[10px]"></i>
                    <i class="text-[10px]" :class="group.chat ? 'fa-solid fa-comments text-info' : 'fa-solid fa-circle-question text-base-content/40'"></i>
                    <span class="truncate" :title="groupTitle(group)">{{ group.title }}</span>
                    <span class="ml-auto text-[10px] text-base-content/40">{{ group.files.length }}</span>
                    <span
                      v-if="group.chat"
                      class="badge badge-xs badge-ghost"
                      :title="signalTooltip(group.chat)"
                    >{{ group.chat.score }}</span>
                    <button
                      v-if="group.chat"
                      class="btn btn-xs btn-ghost px-1"
                      @click.stop="openChat(group.chat)"
                      title="Open chat"
                      :aria-label="`Open chat ${group.title}`"
                    >
                      <i class="fa-solid fa-up-right-from-square text-[9px]"></i>
                    </button>
                    <button
                      v-if="group.chat?.messageId"
                      class="btn btn-xs btn-ghost px-1"
                      @click.stop="jumpToMessage(group.chat)"
                      title="Jump to the matched message"
                      aria-label="Jump to the matched message"
                    >
                      <i class="fa-solid fa-crosshairs text-[9px]"></i>
                    </button>
                  </div>

                  <div v-if="isChatGroupExpanded(group.key)" class="file-list pl-2 border-l border-base-content/10">
                    <div
                      v-for="file in group.files"
                      :key="file.fileFullName"
                      class="file-item flex items-center gap-1.5 px-2 py-1 text-xs cursor-pointer hover:bg-base-200"
                      :class="{ 'bg-base-200': selectedFile?.fileFullName === file.fileFullName }"
                      @click="selectFile(file)"
                    >
                      <input
                        type="checkbox"
                        v-model="file.selected"
                        class="checkbox checkbox-xs"
                        @click.stop
                      />
                      <i class="fa-solid fa-file text-[10px]" :class="getFileIconClass(file)"></i>
                      <span class="truncate grow" :title="file.fileFullName">{{ file.title }}</span>
                      <span class="badge badge-xs badge-success badge-ghost" v-if="file.insertions">{{ file.insertions }}</span>
                      <span class="badge badge-xs badge-error badge-ghost" v-if="file.deletions">{{ file.deletions }}</span>
                      <i class="fa-solid fa-comment-dots text-info text-[10px]" v-if="file.commentCount"></i>
                    </div>
                  </div>
                </div>
              </template>

              <div v-else class="flex flex-col items-center justify-center py-8 px-3 gap-2 text-base-content/40 text-center">
                <i class="fa-solid fa-comments text-2xl"></i>
                <span class="text-xs">No chat found for these changes</span>
                <span class="text-[10px] opacity-70">Only chats holding a linked file, a code block or a diff of the PR are listed</span>
              </div>
            </div>

            <!-- File list grouped by folder -->
            <div v-else class="grow overflow-y-auto">
              <template v-for="(folderFiles, folderPath) in visibleFilesByFolder" :key="folderPath">
                <div class="file-folder-group">
                  <div
                    class="flex items-center gap-1 px-2 py-1 text-xs font-semibold bg-base-200/80 cursor-pointer hover:bg-base-300/80"
                    @click="toggleFolder(folderPath)"
                  >
                    <i :class="folderExpanded[folderPath] ? 'fa-solid fa-chevron-down' : 'fa-solid fa-chevron-right'" class="text-[10px]"></i>
                    <i class="fa-solid fa-folder text-warning text-[10px]"></i>
                    <span class="truncate">{{ folderPath || '/' }}</span>
                    <span class="ml-auto text-[10px] text-base-content/40">{{ folderFiles.length }}</span>
                  </div>
                  <div v-if="folderExpanded[folderPath]" class="file-list pl-2 border-l border-base-content/10">
                    <div
                      v-for="file in folderFiles"
                      :key="file.fileFullName"
                      class="file-item flex items-center gap-1.5 px-2 py-1 text-xs cursor-pointer hover:bg-base-200"
                      :class="{ 'bg-base-200': selectedFile?.fileFullName === file.fileFullName }"
                      @click="selectFile(file)"
                    >
                      <input
                        type="checkbox"
                        v-model="file.selected"
                        class="checkbox checkbox-xs"
                        @click.stop
                      />
                      <i class="fa-solid fa-file text-[10px]" :class="getFileIconClass(file)"></i>
                      <span class="truncate grow" :title="file.fileFullName">{{ file.title }}</span>
                      <span
                        v-if="chatsForFile(file).length"
                        class="badge badge-xs badge-info badge-ghost shrink-0"
                        :title="fileChatsTooltip(file)"
                      >
                        <i class="fa-solid fa-comments text-[8px]"></i>{{ chatsForFile(file).length }}
                      </span>
                      <span class="badge badge-xs badge-success badge-ghost" v-if="file.insertions">{{ file.insertions }}</span>
                      <span class="badge badge-xs badge-error badge-ghost" v-if="file.deletions">{{ file.deletions }}</span>
                      <i class="fa-solid fa-comment-dots text-info text-[10px]" v-if="file.commentCount"></i>
                    </div>
                  </div>
                </div>
              </template>

              <div v-if="!visibleFiles.length" class="flex flex-col items-center justify-center py-8 text-base-content/40">
                <i class="fa-solid fa-filter text-2xl mb-2"></i>
                <span class="text-xs">No files match the filter</span>
              </div>
            </div>
          </div>
        </SplitterPanel>

        <SplitterResizeHandle class="w-1 hover:bg-slate-600" />

        <!-- Center panel: Diff viewer -->
        <SplitterPanel :min-size="30" :defaultSize="75" class="overflow-hidden">
          <div class="flex flex-col h-full">
            <!-- File tabs -->
            <div class="flex items-center gap-1 px-1 py-1 bg-base-200/30 border-b border-base-content/10 shrink-0 overflow-x-auto">
              <div
                v-for="file in recentlyViewedFiles"
                :key="file.fileFullName"
                class="file-tab flex items-center gap-1.5 px-2 py-1 text-xs rounded-md cursor-pointer whitespace-nowrap"
                :class="{
                  'bg-base-100 text-base-content': selectedFile?.fileFullName === file.fileFullName,
                  'hover:bg-base-200': selectedFile?.fileFullName !== file.fileFullName
                }"
                @click="selectFile(file)"
              >
                <i class="fa-solid fa-file text-[10px]" :class="getFileIconClass(file)"></i>
                <span class="truncate max-w-[150px]">{{ file.title }}</span>
                <button
                  class="btn btn-xs btn-ghost h-4 w-4 p-0"
                  @click.stop="closeFileTab(file)"
                >
                  <i class="fa-solid fa-xmark text-[8px]"></i>
                </button>
              </div>
            </div>

            <!-- Diff content -->
            <div class="grow min-h-0 overflow-hidden">
              <div v-if="!selectedFile" class="flex flex-col items-center justify-center h-full text-base-content/40">
                <i class="fa-solid fa-code-compare text-4xl mb-3"></i>
                <span class="text-sm">Select a file to view changes</span>
              </div>

              <div v-else class="flex flex-col h-full">
                <!-- File header -->
                <div class="flex items-center justify-between px-3 py-1.5 bg-base-200/50 border-b border-base-content/10 shrink-0">
                  <div class="flex items-center gap-2 text-xs min-w-0">
                    <i class="fa-solid fa-file" :class="getFileIconClass(selectedFile)"></i>
                    <span class="font-mono truncate max-w-[300px]" :title="selectedFile.fileFullName">
                      {{ selectedFile.fileFullName }}
                    </span>
                    <span class="badge badge-xs" :class="getFileStatusBadge(selectedFile)">
                      {{ getFileStatusText(selectedFile) }}
                    </span>
                  </div>
                  <div class="flex items-center gap-1">
                    <button class="btn btn-xs btn-ghost" @click="copyDiff" title="Copy diff">
                      <i class="fa-regular fa-copy text-[10px]"></i>
                    </button>
                    <button class="btn btn-xs btn-ghost" @click="openInEditor" title="Open in editor">
                      <i class="fa-solid fa-up-right-from-square text-[10px]"></i>
                    </button>
                  </div>
                </div>

                <!-- Same diff renderer used by CodeViewer -->
                <DiffViewer
                  :key="selectedFile.fileFullName"
                  class="grow min-h-0"
                  :diff="selectedFile.diff"
                  :file="selectedFile.fileName"
                  :language="selectedFile.extension"
                  :add-widget="true"
                  :extend-data="extendData"
                >
                  <!-- Inline comment form provided by git-diff-view's line widget -->
                  <template #widget="{ onClose, side, lineNumber }">
                    <div class="flex flex-col gap-2 p-2 w-full">
                      <div class="flex items-center gap-2">
                        <span class="text-[10px] text-base-content/40 font-mono">
                          {{ side === 1 ? 'Original' : 'New' }} line {{ lineNumber }}
                        </span>
                        <button class="btn btn-xs btn-ghost btn-circle ml-auto" @click.stop="cancelComment(onClose)" title="Cancel">
                          <i class="fa-solid fa-xmark text-[10px]"></i>
                        </button>
                      </div>
                      <textarea
                        v-model="newComment"
                        placeholder="Add a comment..."
                        class="textarea textarea-xs textarea-bordered w-full min-h-[36px] resize-none"
                        @keydown.enter.exact.prevent="submitComment({ side, lineNumber, onClose })"
                      ></textarea>
                      <div class="flex justify-end">
                        <button
                          class="btn btn-xs btn-primary gap-1"
                          :disabled="!newComment.trim()"
                          @click="submitComment({ side, lineNumber, onClose })"
                        >
                          <i class="fa-solid fa-paper-plane text-[10px]"></i> Comment
                        </button>
                      </div>
                    </div>
                  </template>
                </DiffViewer>
              </div>
            </div>
          </div>
        </SplitterPanel>
      </SplitterGroup>
    </template>

    <!-- No files state -->
    <div v-else class="flex flex-col items-center justify-center grow text-base-content/40">
      <i class="fa-solid fa-inbox text-4xl mb-3"></i>
      <span class="text-sm">No changes found between branches</span>
    </div>

    <!-- Comments Modal -->
    <dialog id="commentsModal" class="modal" ref="commentsModal">
      <div class="modal-box w-11/12 max-w-3xl">
        <div class="flex items-center justify-between mb-4">
          <div class="flex items-center gap-2">
            <i class="fa-solid fa-comment-dots text-info"></i>
            <h3 class="font-bold">Comments</h3>
            <span class="badge badge-info">{{ totalCommentCount }}</span>
          </div>
          <button class="btn btn-xs btn-ghost" @click="closeCommentsModal">
            <i class="fa-solid fa-xmark"></i>
          </button>
        </div>

        <div class="tabs tabs-boxed tabs-xs mb-4">
          <a class="tab" :class="{ 'tab-active': commentFilter === 'all' }" @click="commentFilter = 'all'">All</a>
          <a class="tab" :class="{ 'tab-active': commentFilter === 'unresolved' }" @click="commentFilter = 'unresolved'">Unresolved</a>
          <a class="tab" :class="{ 'tab-active': commentFilter === 'resolved' }" @click="commentFilter = 'resolved'">Resolved</a>
        </div>

        <div class="overflow-y-auto max-h-[60vh] space-y-2">
          <div v-if="!filteredAllComments.length" class="flex flex-col items-center justify-center py-8 text-base-content/40">
            <i class="fa-regular fa-comment-slash text-2xl mb-2"></i>
            <span class="text-xs">No comments</span>
          </div>

          <div
            v-for="comment in filteredAllComments"
            :key="comment.id"
            class="flex gap-2 p-2 rounded bg-base-200/30"
            :class="{ 'opacity-50': comment.resolved }"
          >
            <div class="avatar shrink-0 mt-0.5">
              <div class="w-6 h-6 rounded-full bg-base-300 flex items-center justify-center">
                <span class="text-[10px] font-semibold">{{ comment.author?.[0] || '?' }}</span>
              </div>
            </div>

            <div class="grow min-w-0">
              <div class="flex items-center justify-between gap-2">
                <div class="flex items-center gap-2">
                  <span class="text-xs font-semibold">{{ comment.author || 'Anonymous' }}</span>
                  <span class="text-[10px] text-base-content/40">{{ formatTime(comment.timestamp) }}</span>
                </div>
                <div class="flex items-center gap-1">
                  <button
                    class="btn btn-xs btn-ghost h-auto py-0 px-1 text-[9px]"
                    @click="toggleResolve(comment)"
                  >
                    <i :class="comment.resolved ? 'fa-solid fa-rotate-left' : 'fa-solid fa-check'"></i>
                  </button>
                  <button
                    class="btn btn-xs btn-ghost h-auto py-0 px-1 text-[9px] text-error"
                    @click="deleteComment(comment)"
                  >
                    <i class="fa-solid fa-trash"></i>
                  </button>
                </div>
              </div>

              <div class="flex items-center gap-2 mt-1 text-[10px] text-base-content/40">
                <span class="font-mono truncate">{{ comment.fileName }}</span>
                <span>Line {{ comment.lineNumber }}</span>
                <span class="badge badge-xs" :class="comment.lineType === 'old' ? 'badge-error' : 'badge-success'">
                  {{ comment.lineType === 'old' ? 'Original' : 'New' }}
                </span>
              </div>

              <div class="text-xs mt-1 break-words" :class="{ 'line-through': comment.resolved }">
                {{ comment.content }}
              </div>

              <button
                class="btn btn-xs btn-ghost h-auto py-0 px-1 mt-1 text-[9px] text-info"
                @click="jumpToComment(comment)"
              >
                <i class="fa-solid fa-arrow-up-right-from-square"></i> Jump to file
              </button>

              <div v-if="comment.replies?.length" class="ml-3 mt-2 space-y-1 border-l border-base-content/10 pl-2">
                <div
                  v-for="reply in comment.replies"
                  :key="reply.id"
                  class="flex gap-1.5"
                >
                  <div class="avatar shrink-0 mt-0.5">
                    <div class="w-4 h-4 rounded-full bg-base-300 flex items-center justify-center">
                      <span class="text-[8px] font-semibold">{{ reply.author?.[0] || '?' }}</span>
                    </div>
                  </div>
                  <div class="grow min-w-0">
                    <div class="flex items-center justify-between gap-1">
                      <span class="text-[9px] font-semibold">{{ reply.author || 'Anonymous' }}</span>
                      <span class="text-[7px] text-base-content/40">{{ formatTime(reply.timestamp) }}</span>
                    </div>
                    <div class="text-[9px] mt-0.5 break-words">{{ reply.content }}</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      <form method="dialog" class="modal-backdrop">
        <button>close</button>
      </form>
    </dialog>
  </div>
</template>

<script>
export default {
  props: {
    fromBranch: { type: String, default: 'main' },
    toBranch: { type: String, default: 'develop' },
    availableBranches: { type: Array, default: () => [] },
    repoChanges: { type: Object, default: null },
    project: { type: Object, default: null },
    chat: { type: Object, default: null },
    loading: { type: Boolean, default: false }
  },
  emits: [
    'refresh',
    'comment',
    'select-branch',
    'chat-message',
    'branch-changed',
    'compare-branch-changed',
    'visible-files-changed',
    'open-chat',
    'jump-to-message'
  ],
  data() {
    return {
      files: null,
      selectedFile: null,
      recentlyViewedFiles: [],
      fileFilter: '',
      newComment: '',
      commentsByFile: {},
      folderExpanded: {},
      commentFilter: 'all',
      commentsModalOpen: false,
      // Kept for Programmatic API compat (search panel jumps)
      visibleLineComments: new Set(),
      // File tree grouping: 'folder' (default) | 'chat'
      groupMode: 'folder',
      chatGroupExpanded: {},
      // PR ↔ chat correlation result
      chatAnalysis: null,
      chatAnalysisLoading: false,
      chatAnalysisError: null,
      showProbableChats: false,
      analysisToken: 0,
      analysisTimer: null
    }
  },
  created() {
    if (this.repoChanges) {
      this.buildFiles()
    }
  },
  computed: {
    visibleFiles() {
      if (!this.files) return []
      if (!this.fileFilter) return this.files
      const filter = this.fileFilter.toLowerCase()
      return this.files.filter(f =>
        f.fileFullName.toLowerCase().includes(filter) ||
        f.title.toLowerCase().includes(filter)
      )
    },

    visibleFilesByFolder() {
      if (!this.visibleFiles.length) return {}
      const grouped = {}
      this.visibleFiles.forEach(file => {
        const lastSlashIndex = file.fileFullName.lastIndexOf('/')
        const folderPath = lastSlashIndex > 0
          ? file.fileFullName.substring(0, lastSlashIndex)
          : '/'
        if (!grouped[folderPath]) grouped[folderPath] = []
        grouped[folderPath].push(file)
      })
      Object.keys(grouped).forEach(folder => {
        grouped[folder].sort((a, b) => a.title.localeCompare(b.title))
      })
      const sorted = {}
      Object.keys(grouped).sort().forEach(key => { sorted[key] = grouped[key] })
      return sorted
    },

    changeCount() { return this.files?.length || 0 },
    insertions() { return this.files?.reduce((sum, f) => sum + (f.insertions || 0), 0) || 0 },
    deletions() { return this.files?.reduce((sum, f) => sum + (f.deletions || 0), 0) || 0 },

    selectedFileIndex() {
      if (!this.selectedFile || !this.visibleFiles.length) return -1
      return this.visibleFiles.findIndex(f => f.fileFullName === this.selectedFile.fileFullName)
    },
    hasPreviousFile() { return this.selectedFileIndex > 0 },
    hasNextFile() { return this.selectedFileIndex < this.visibleFiles.length - 1 },

    selectedFileComments() {
      if (!this.selectedFile) return []
      return this.commentsByFile[this.selectedFile.fileFullName] || []
    },

    /**
     * Lines that carry comments, in the shape git-diff-view expects so the
     * diff marks them (old/new side keyed by line number).
     */
    extendData() {
      const oldFile = {}
      const newFile = {}
      this.selectedFileComments.forEach(comment => {
        const target = comment.lineType === 'old' ? oldFile : newFile
        target[comment.lineNumber] = { data: 'comment' }
      })
      return { oldFile, newFile }
    },

    totalCommentCount() {
      return Object.values(this.commentsByFile).reduce((sum, comments) => sum + comments.length, 0)
    },

    allComments() {
      const comments = []
      Object.entries(this.commentsByFile).forEach(([fileName, fileComments]) => {
        fileComments.forEach(comment => comments.push({ ...comment, fileName }))
      })
      return comments.sort((a, b) => b.timestamp - a.timestamp)
    },

    filteredAllComments() {
      if (this.commentFilter === 'all') return this.allComments
      if (this.commentFilter === 'unresolved') return this.allComments.filter(c => !c.resolved)
      if (this.commentFilter === 'resolved') return this.allComments.filter(c => c.resolved)
      return this.allComments
    },

    /** Chats correlated with the PR, best evidence first */
    chats() {
      const all = this.chatAnalysis?.chats || []
      return this.showProbableChats ? all : all.filter(chat => chat.confirmed)
    },

    probableChatCount() {
      const all = this.chatAnalysis?.chats || []
      return all.filter(chat => !chat.confirmed).length
    },

    /** repo-relative path → scored chats that touched it */
    fileChatsMap() {
      return this.chatAnalysis?.fileChats || {}
    },

    /**
     * File tree grouped by chat: every file is listed under the chat that
     * changed it (a file may appear in several chats, duplicates are intentional
     * — that is what "which chat modified this?" means), plus a last group with
     * the files no chat could be matched to.
     */
    analysisGroups() {
      const files = this.files || []
      if (!files.length) return []

      const byPath = new Map()
      files.forEach(file => {
        if (!byPath.has(file.fileName)) byPath.set(file.fileName, file)
      })

      const groups = []
      const claimed = new Set()

      this.chats.forEach(chat => {
        const chatFiles = (chat.files || [])
          .map(path => byPath.get(path))
          .filter(file => !!file && (!this.fileFilter || this.visibleFiles.includes(file)))
        if (!chatFiles.length) return
        chatFiles.forEach(file => claimed.add(file.fileName))
        groups.push({
          key: `chat-${chat.id}`,
          title: chat.name,
          chat,
          files: chatFiles
        })
      })

      const unmatched = this.visibleFiles.filter(file => !claimed.has(file.fileName))
      if (unmatched.length) {
        groups.push({ key: 'chat-none', title: 'No chat found', chat: null, files: unmatched })
      }

      return groups
    },

    /** Chats store revision: re-scan when a chat changes */
    activityRevision() {
      return this.$storex?.chats?.activityRevision || 0
    }
  },
  watch: {
    repoChanges(newChanges) {
      if (newChanges) {
        this.buildFiles()
      } else {
        this.files = null
        this.selectedFile = null
        this.chatAnalysis = null
      }
    },
    fileFilter() {
      if (!this.visibleFiles.find(f => f.fileFullName === this.selectedFile?.fileFullName)) {
        this.selectedFile = null
      }
      this.$emit('visible-files-changed', this.visibleFiles)
    },
    selectedFile() {
      this.newComment = ''
      this.visibleLineComments.clear()
    },
    activityRevision() {
      this.scheduleChatAnalysis()
    }
  },
  beforeUnmount() {
    clearTimeout(this.analysisTimer)
  },
  methods: {
    onFromBranchChanged(branch) {
      this.$emit('branch-changed', branch)
    },

    onToBranchChanged(branch) {
      this.$emit('compare-branch-changed', branch)
    },

    buildFiles() {
      if (!this.repoChanges?.branch_file_and_commits) {
        this.files = null
        return
      }

      const { branch_file_and_commits } = this.repoChanges
      const repoPath = this.repoChanges.repo_path || ''

      this.files = Object.keys(branch_file_and_commits)
        .map(filePath => {
          const entry = branch_file_and_commits[filePath] || {}
          return this.buildDiffFile(entry.diff || '', repoPath, entry)
        })
        .filter(Boolean)
        .sort((a, b) => a.fileFullName.localeCompare(b.fileFullName))

      Object.keys(this.visibleFilesByFolder).forEach(folder => {
        if (this.folderExpanded[folder] === undefined) {
          this.folderExpanded[folder] = true
        }
      })

      if (this.files.length && !this.selectedFile) {
        this.selectFile(this.files[0])
      }

      this.$emit('visible-files-changed', this.visibleFiles)
      this.refreshChatAnalysis()
    },

    buildDiffFile(diff, repoPath, entry = {}) {
      try {
        const lines = diff.replace('diff --git ', '').split('\n')
        const [oldFile, newFile] = lines[0].trim().split(' ')
        const oldName = oldFile?.replace('a/', '') || ''
        const newName = newFile?.replace('b/', '') || ''

        const isDeleted = diff.includes('deleted file mode') || false
        const isNewFile = !isDeleted && newName && !oldName
        const isChanged = !isDeleted && newName && oldName

        const fileName = oldName || newName
        const fileFullName = fileName.startsWith(repoPath)
          ? fileName
          : repoPath + (fileName[0] === '/' ? '' : '/') + fileName

        const title = fileName.split('/').pop()
        const extension = fileFullName.split('.').reverse()[0]
        const diffLines = this.parseDiffLines(diff)

        let insertions = 0
        let deletions = 0
        diffLines.forEach(line => {
          if (line.type === 'add') insertions++
          if (line.type === 'del') deletions++
        })

        return {
          title, fileName, fileFullName, extension, diff, diffLines,
          // Per-file metadata from repo.changes (commit dates, authors)
          commits: entry.commits || [],
          lastModification: entry.last_modification || null,
          oldFile: { fileName: oldName },
          newFile: { fileName: newName },
          isDeleted, isNewFile, isChanged,
          insertions, deletions,
          selected: false, commentCount: 0
        }
      } catch (ex) {
        console.error('Error parsing diff:', ex)
        return null
      }
    },

    /** Kept for the search panel, which matches on parsed diff lines */
    parseDiffLines(diff) {
      const lines = diff.split('\n')
      const result = []
      let oldLineNum = 0
      let newLineNum = 0

      for (let i = 0; i < lines.length; i++) {
        const line = lines[i]
        if (line.startsWith('diff --git') || line.startsWith('index ') || line.startsWith('--- ') || line.startsWith('+++ ')) continue

        if (line.startsWith('@@')) {
          const match = line.match(/@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@/)
          if (match) {
            oldLineNum = parseInt(match[1])
            newLineNum = parseInt(match[2])
          }
          result.push({ type: 'hunk', content: line, oldLineNumber: null, newLineNumber: null, isContext: false })
          continue
        }

        if (line.startsWith('+') && !line.startsWith('+++')) {
          result.push({ type: 'add', content: line, oldLineNumber: null, newLineNumber: newLineNum++, isContext: false })
        } else if (line.startsWith('-') && !line.startsWith('---')) {
          result.push({ type: 'del', content: line, oldLineNumber: oldLineNum++, newLineNumber: null, isContext: false })
        } else {
          result.push({ type: 'context', content: line, oldLineNumber: oldLineNum++, newLineNumber: newLineNum++, isContext: true })
        }
      }
      return result
    },

    selectFile(file) {
      this.selectedFile = file
      this.newComment = ''

      if (!this.recentlyViewedFiles.find(f => f.fileFullName === file.fileFullName)) {
        this.recentlyViewedFiles.unshift(file)
        if (this.recentlyViewedFiles.length > 10) {
          this.recentlyViewedFiles = this.recentlyViewedFiles.slice(0, 10)
        }
      }
    },

    closeFileTab(file) {
      this.recentlyViewedFiles = this.recentlyViewedFiles.filter(f => f.fileFullName !== file.fileFullName)
      if (this.selectedFile?.fileFullName === file.fileFullName) {
        this.selectedFile = this.recentlyViewedFiles[0] || null
      }
    },

    navigateFile(direction) {
      if (!this.visibleFiles.length) return
      const newIndex = this.selectedFileIndex + direction
      if (newIndex >= 0 && newIndex < this.visibleFiles.length) {
        this.selectFile(this.visibleFiles[newIndex])
      }
    },

    toggleFolder(folderPath) {
      this.folderExpanded[folderPath] = !this.folderExpanded[folderPath]
    },

    selectAllFiles() { this.visibleFiles.forEach(f => { f.selected = true }) },
    clearSelection() { this.visibleFiles.forEach(f => { f.selected = false }) },

    // ── PR ↔ chat correlation ────────────────────────────────────────────────

    setGroupMode(mode) {
      this.groupMode = mode
      if (mode === 'chat' && !this.chatAnalysis) {
        this.refreshChatAnalysis()
      }
    },

    isChatGroupExpanded(key) {
      const value = this.chatGroupExpanded[key]
      return value === undefined ? true : !!value
    },

    toggleChatGroup(key) {
      this.chatGroupExpanded = { ...this.chatGroupExpanded, [key]: !this.isChatGroupExpanded(key) }
    },

    chatsForFile(file) {
      return this.fileChatsMap[file?.fileName] || []
    },

    fileChatsTooltip(file) {
      const list = this.chatsForFile(file)
      if (!list.length) return ''
      return list
        .map(chat => `${chat.name} (${chat.score})`)
        .join('\n')
    },

    groupTitle(group) {
      if (!group.chat) return group.title
      return `${group.title} · ${group.chat.score}`
    },

    signalTooltip(chat) {
      return (chat.signals || []).map(signal => signal.label).join('\n')
    },

    scheduleChatAnalysis() {
      clearTimeout(this.analysisTimer)
      this.analysisTimer = setTimeout(() => this.refreshChatAnalysis(), 1200)
    },

    async refreshChatAnalysis() {
      if (!this.$service?.prAnalysis || !this.project?.$api || !this.repoChanges?.branch_file_and_commits) {
        this.chatAnalysis = null
        return
      }

      const token = ++this.analysisToken
      this.chatAnalysisLoading = true
      this.chatAnalysisError = null

      try {
        const result = await this.$service.prAnalysis.findChatsForPR({
          project: this.project,
          fromBranch: this.fromBranch,
          toBranch: this.toBranch,
          repoChanges: this.repoChanges,
          chat: this.chat
        })
        if (token !== this.analysisToken) return
        this.chatAnalysis = result
      } catch (error) {
        if (token !== this.analysisToken) return
        console.error('[PRViewer] chat analysis failed:', error)
        this.chatAnalysisError = error?.message || 'Unable to correlate chats with the PR'
        this.chatAnalysis = null
      } finally {
        if (token === this.analysisToken) {
          this.chatAnalysisLoading = false
        }
      }
    },

    async openChat(chat) {
      if (!chat?.id) return
      this.$emit('open-chat', chat)
      const stored = this.$storex.chats.allChats.find(item => item.id === chat.id)
      if (stored) {
        await this.$chats.setActiveChat(stored)
      }
    },

    jumpToMessage(chat) {
      if (!chat?.messageId) return
      this.$emit('jump-to-message', { chatId: chat.id, messageId: chat.messageId })
    },

    // ── Comments ─────────────────────────────────────────────────────────────

    cancelComment(onClose) {
      this.newComment = ''
      if (onClose) onClose()
    },

    /**
     * Comment created from the diff line widget.
     * `side` follows git-diff-view: 1 = original (old), otherwise new.
     */
    submitComment({ side, lineNumber, onClose }) {
      if (!this.newComment.trim() || !this.selectedFile) return

      const lineType = side === 1 ? 'old' : 'new'
      const comment = {
        id: Date.now().toString(),
        content: this.newComment.trim(),
        author: 'User',
        timestamp: Date.now(),
        resolved: false,
        lineNumber,
        lineType,
        lineContent: '',
        replies: []
      }

      if (!this.commentsByFile[this.selectedFile.fileFullName]) {
        this.commentsByFile[this.selectedFile.fileFullName] = []
      }

      this.commentsByFile[this.selectedFile.fileFullName].push(comment)
      this.selectedFile.commentCount = (this.selectedFile.commentCount || 0) + 1

      this.$emit('comment', {
        file: this.selectedFile,
        line: null,
        comment: comment.content,
        lineNumber: comment.lineNumber,
        lineType: comment.lineType
      })

      this.newComment = ''
      if (onClose) onClose()
    },

    toggleResolve(comment) { comment.resolved = !comment.resolved },

    deleteComment(comment) {
      if (!this.selectedFile) return
      const comments = this.commentsByFile[this.selectedFile.fileFullName]
      const index = comments.indexOf(comment)
      if (index > -1) {
        comments.splice(index, 1)
        this.selectedFile.commentCount = Math.max(0, (this.selectedFile.commentCount || 0) - 1)
      }
    },

    getFileIconClass(file) {
      if (file.isNewFile) return 'text-success'
      if (file.isDeleted) return 'text-error'
      return 'text-warning'
    },

    getFileStatusBadge(file) {
      if (file.isNewFile) return 'badge-success'
      if (file.isDeleted) return 'badge-error'
      return 'badge-warning'
    },

    getFileStatusText(file) {
      if (file.isNewFile) return 'Added'
      if (file.isDeleted) return 'Deleted'
      return 'Modified'
    },

    copyDiff() {
      if (!this.selectedFile) return
      const diffBlock = ['```diff', this.selectedFile.diff, '```'].join('\n')
      navigator.clipboard.writeText(diffBlock)
    },

    openInEditor() {
      if (!this.selectedFile) return
      this.$emit('open-file', this.selectedFile.fileFullName)
    },

    formatTime(timestamp) {
      const diff = Date.now() - timestamp
      if (diff < 60000) return 'just now'
      if (diff < 3600000) return Math.floor(diff / 60000) + 'm ago'
      if (diff < 86400000) return Math.floor(diff / 3600000) + 'h ago'
      return new Date(timestamp).toLocaleDateString()
    },

    openCommentsModal() { this.$refs.commentsModal.showModal() },
    closeCommentsModal() { this.$refs.commentsModal.close() },

    jumpToComment(comment) {
      const file = this.files.find(f => f.fileFullName === comment.fileName)
      if (file) {
        this.selectFile(file)
      }
      this.closeCommentsModal()
    }
  },
  expose: ['buildFiles', 'files', 'visibleFiles', 'selectFile', 'visibleLineComments', 'chatAnalysis', 'refreshChatAnalysis']
}
</script>