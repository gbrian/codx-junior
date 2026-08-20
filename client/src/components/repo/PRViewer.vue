<script setup>
import "@git-diff-view/vue/styles/diff-view.css"
import { DiffParser } from "@git-diff-view/vue"
import CodxMenu from "../CodxMenu.vue"
import { SplitterGroup, SplitterPanel, SplitterResizeHandle } from 'radix-vue'
import ChatEntryVue from '../ChatEntry.vue'
</script>

<template>
  <div class="azure-pr-view flex flex-col h-full overflow-hidden bg-base-100">
    <!-- Top toolbar -->
    <header class="flex items-center justify-between px-3 py-1.5 bg-base-200 border-b border-base-content/10 shrink-0">
      <div class="flex items-center gap-3">
        <div class="flex items-center gap-2">
          <i class="fa-solid fa-code-branch text-warning"></i>
          <span class="font-mono text-sm font-semibold">{{ fromBranch }}</span>
          <i class="fa-solid fa-arrow-right text-xs text-base-content/40"></i>
          <span class="font-mono text-sm font-semibold">{{ toBranch }}</span>
        </div>
        <div class="divider divider-horizontal mx-1"></div>
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
      </div>

      <div class="flex items-center gap-2">
        <!-- Diff view toggle -->
        <div class="dropdown dropdown-bottom">
          <button class="btn btn-xs btn-ghost gap-1">
            <i class="fa-solid fa-code-compare"></i>
            <span class="hidden sm:inline">{{ diffViewMode === 'unified' ? 'Unified' : 'Split' }}</span>
            <i class="fa-solid fa-chevron-down text-[8px]"></i>
          </button>
          <ul class="dropdown-content menu bg-base-100 rounded-box z-50 w-32 p-1 shadow">
            <li><a @click="setDiffViewMode('unified')" :class="{ 'active': diffViewMode === 'unified' }">Unified</a></li>
            <li><a @click="setDiffViewMode('split')" :class="{ 'active': diffViewMode === 'split' }">Split</a></li>
          </ul>
        </div>

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
        <!-- Left panel: File list grouped by folder -->
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

            <!-- File list grouped by folder -->
            <div class="grow overflow-y-auto">
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
                      <span class="truncate grow">{{ file.title }}</span>
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
            <div class="grow overflow-auto">
              <div v-if="!selectedFile" class="flex flex-col items-center justify-center h-full text-base-content/40">
                <i class="fa-solid fa-code-compare text-4xl mb-3"></i>
                <span class="text-sm">Select a file to view changes</span>
              </div>

              <div v-else class="diff-viewer">
                <!-- File header -->
                <div class="flex items-center justify-between px-3 py-1.5 bg-base-200/50 border-b border-base-content/10 shrink-0">
                  <div class="flex items-center gap-2 text-xs">
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

                <!-- UNIFIED VIEW -->
                <div v-if="diffViewMode === 'unified'" class="diff-lines">
                  <template v-for="(line, index) in selectedFile.diffLines" :key="index">
                    <!-- Diff line -->
                    <div
                      class="diff-line flex"
                      :class="getLineClass(line, index)"
                      @click="onLineClick(line, index)"
                    >
                      <!-- Left line number (deleted) -->
                      <div class="line-number w-12 shrink-0 text-right pr-2 select-none text-[11px] font-mono text-base-content/40"
                        v-if="line.oldLineNumber !== null">
                        {{ line.oldLineNumber }}
                      </div>
                      <div class="line-number w-12 shrink-0" v-else></div>

                      <!-- Diff indicator -->
                      <div class="diff-indicator w-6 shrink-0 text-center select-none text-[11px] font-mono"
                        :class="getDiffIndicatorClass(line)">
                        {{ getDiffIndicator(line) }}
                      </div>

                      <!-- Line content -->
                      <div
                        class="line-content grow font-mono text-[11px] px-2 whitespace-pre"
                        :class="{
                          'cursor-pointer': !line.isContext,
                          'hover:bg-base-200/50': !line.isContext
                        }"
                      >
                        {{ line.content }}
                      </div>

                      <!-- Right line number (added) -->
                      <div class="line-number w-12 shrink-0 text-right pr-2 select-none text-[11px] font-mono text-base-content/40"
                        v-if="line.newLineNumber !== null">
                        {{ line.newLineNumber }}
                      </div>
                      <div class="line-number w-12 shrink-0" v-else></div>

                      <!-- Inline comment indicator / add comment button -->
                      <div class="comment-actions w-10 shrink-0 flex justify-center items-center gap-1">
                        <template v-if="getLineComments(line).length">
                          <button
                            class="btn btn-xs btn-ghost h-5 w-5 p-0 text-info"
                            @click.stop="toggleLineComments(line, index)"
                            title="View comments"
                          >
                            <i class="fa-solid fa-comment text-[10px]"></i>
                            <span class="badge badge-xs badge-info">{{ getLineComments(line).length }}</span>
                          </button>
                        </template>
                        <template v-else-if="!line.isContext">
                          <button
                            class="btn btn-xs btn-ghost h-5 w-5 p-0 text-base-content/30 hover:text-info"
                            @click.stop="startLineComment(line, index)"
                            title="Add comment"
                          >
                            <i class="fa-solid fa-plus text-[10px]"></i>
                          </button>
                        </template>
                      </div>
                    </div>

                    <!-- Inline comments section for this line -->
                    <div
                      v-if="isLineCommentsVisible(index) && getLineComments(line).length"
                      class="diff-line-comments flex"
                    >
                      <div class="w-12 shrink-0"></div>
                      <div class="w-6 shrink-0"></div>
                      <div class="grow bg-info/10 border-y border-info/20 px-2 py-1">
                        <div class="flex items-center gap-1 mb-1">
                          <span class="text-[9px] text-info font-semibold">
                            <i class="fa-solid fa-comment-dots"></i>
                            {{ getLineComments(line).length }} comment{{ getLineComments(line).length > 1 ? 's' : '' }}
                          </span>
                          <button
                            class="btn btn-xs btn-ghost h-4 w-4 p-0 ml-auto"
                            @click.stop="hideLineComments(index)"
                          >
                            <i class="fa-solid fa-xmark text-[8px]"></i>
                          </button>
                        </div>
                        <div class="space-y-1">
                          <div
                            v-for="comment in getLineComments(line)"
                            :key="comment.id"
                            class="flex gap-1.5"
                            :class="{ 'opacity-60': comment.resolved }"
                          >
                            <div class="avatar shrink-0 mt-0.5">
                              <div class="w-4 h-4 rounded-full bg-base-300 flex items-center justify-center">
                                <span class="text-[8px] font-semibold">{{ comment.author?.[0] || '?' }}</span>
                              </div>
                            </div>
                            <div class="grow min-w-0">
                              <div class="flex items-center justify-between gap-1">
                                <div class="flex items-center gap-1">
                                  <span class="text-[9px] font-semibold">{{ comment.author || 'Anonymous' }}</span>
                                  <span class="text-[7px] text-base-content/40">{{ formatTime(comment.timestamp) }}</span>
                                </div>
                                <div class="flex items-center gap-0.5">
                                  <button
                                    class="btn btn-xs btn-ghost h-auto py-0 px-0.5 text-[7px]"
                                    @click.stop="toggleResolve(comment)"
                                  >
                                    <i :class="comment.resolved ? 'fa-solid fa-rotate-left' : 'fa-solid fa-check'"></i>
                                  </button>
                                  <button
                                    class="btn btn-xs btn-ghost h-auto py-0 px-0.5 text-[7px] text-error"
                                    @click.stop="deleteComment(comment)"
                                  >
                                    <i class="fa-solid fa-trash"></i>
                                  </button>
                                </div>
                              </div>
                              <div class="text-[9px] mt-0.5 break-words" :class="{ 'line-through': comment.resolved }">
                                {{ comment.content }}
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                      <div class="w-12 shrink-0"></div>
                      <div class="w-10 shrink-0"></div>
                    </div>

                    <!-- Comment input row -->
                    <div
                      v-if="commentingLineIndex === index"
                      class="diff-line-comment-input flex"
                    >
                      <div class="w-12 shrink-0"></div>
                      <div class="w-6 shrink-0"></div>
                      <div class="grow bg-base-200/50 border-y border-base-content/10 px-2 py-1.5">
                        <div class="flex items-start gap-2">
                          <div class="flex-1">
                            <div class="flex items-center gap-2 mb-1">
                              <span class="text-[10px] text-base-content/40 font-mono">
                                Line {{ commentingLine?.newLineNumber || commentingLine?.oldLineNumber }}
                              </span>
                              <span class="text-[9px] text-base-content/30 truncate max-w-[200px]">
                                {{ commentingLine?.content?.slice(0, 50) }}
                              </span>
                            </div>
                            <textarea
                              v-model="newComment"
                              placeholder="Add a comment..."
                              class="textarea textarea-xs textarea-bordered w-full min-h-[36px] resize-none"
                              @keydown.enter.exact.prevent="submitComment"
                              ref="commentInput"
                            ></textarea>
                          </div>
                          <div class="flex flex-col gap-1 shrink-0">
                            <button
                              class="btn btn-xs btn-primary"
                              @click="submitComment"
                              :disabled="!newComment.trim()"
                            >
                              <i class="fa-solid fa-paper-plane text-[10px]"></i>
                            </button>
                            <button
                              class="btn btn-xs btn-ghost"
                              @click="cancelComment"
                            >
                              <i class="fa-solid fa-xmark text-[10px]"></i>
                            </button>
                          </div>
                        </div>
                      </div>
                      <div class="w-12 shrink-0"></div>
                      <div class="w-10 shrink-0"></div>
                    </div>
                  </template>
                </div>

                <!-- SPLIT VIEW -->
                <div v-else class="diff-lines-split flex">
                  <!-- Left side: Old file -->
                  <div class="diff-side w-1/2 border-r border-base-content/10 overflow-auto">
                    <div class="px-2 py-1 bg-base-200/80 text-[10px] font-semibold flex items-center gap-1">
                      <i class="fa-solid fa-file text-error"></i>
                      <span>{{ selectedFile.oldFile.fileName || 'original' }}</span>
                    </div>
                    <div class="diff-side-lines">
                      <template v-for="(line, index) in selectedFile.splitLines.old" :key="'old-' + index">
                        <div
                          class="diff-line flex"
                          :class="getSplitLineClass(line, index, 'old')"
                          @click="onSplitLineClick(line, index, 'old')"
                        >
                          <div class="line-number w-12 shrink-0 text-right pr-2 select-none text-[11px] font-mono text-base-content/40">
                            {{ line.oldLineNumber }}
                          </div>
                          <div class="diff-indicator w-6 shrink-0 text-center select-none text-[11px] font-mono text-error">
                            {{ getSplitDiffIndicator(line) }}
                          </div>
                          <div class="line-content grow font-mono text-[11px] px-2 whitespace-pre">
                            {{ line.content }}
                          </div>
                          <div class="comment-actions w-8 shrink-0 flex justify-center items-center gap-1">
                            <template v-if="getSplitLineComments(line, 'old').length">
                              <button
                                class="btn btn-xs btn-ghost h-5 w-5 p-0 text-info"
                                @click.stop="toggleSplitLineComments(line, index, 'old')"
                              >
                                <i class="fa-solid fa-comment text-[10px]"></i>
                                <span class="badge badge-xs badge-info">{{ getSplitLineComments(line, 'old').length }}</span>
                              </button>
                            </template>
                            <template v-else-if="line.type === 'del'">
                              <button
                                class="btn btn-xs btn-ghost h-5 w-5 p-0 text-base-content/30 hover:text-info"
                                @click.stop="startSplitLineComment(line, index, 'old')"
                              >
                                <i class="fa-solid fa-plus text-[10px]"></i>
                              </button>
                            </template>
                          </div>
                        </div>

                        <!-- Comments panel for split view -->
                        <div
                          v-if="isSplitLineCommentsVisible(index, 'old') && getSplitLineComments(line, 'old').length"
                          class="diff-line-comments flex"
                        >
                          <div class="w-12 shrink-0"></div>
                          <div class="w-6 shrink-0"></div>
                          <div class="grow bg-info/10 border-y border-info/20 px-2 py-1">
                            <div class="flex items-center gap-1 mb-1">
                              <span class="text-[9px] text-info font-semibold">
                                <i class="fa-solid fa-comment-dots"></i>
                                {{ getSplitLineComments(line, 'old').length }} comment{{ getSplitLineComments(line, 'old').length > 1 ? 's' : '' }}
                              </span>
                              <button
                                class="btn btn-xs btn-ghost h-4 w-4 p-0 ml-auto"
                                @click.stop="hideSplitLineComments(index, 'old')"
                              >
                                <i class="fa-solid fa-xmark text-[8px]"></i>
                              </button>
                            </div>
                            <div class="space-y-1">
                              <div
                                v-for="comment in getSplitLineComments(line, 'old')"
                                :key="comment.id"
                                class="flex gap-1.5"
                                :class="{ 'opacity-60': comment.resolved }"
                              >
                                <div class="avatar shrink-0 mt-0.5">
                                  <div class="w-4 h-4 rounded-full bg-base-300 flex items-center justify-center">
                                    <span class="text-[8px] font-semibold">{{ comment.author?.[0] || '?' }}</span>
                                  </div>
                                </div>
                                <div class="grow min-w-0">
                                  <div class="flex items-center justify-between gap-1">
                                    <div class="flex items-center gap-1">
                                      <span class="text-[9px] font-semibold">{{ comment.author || 'Anonymous' }}</span>
                                      <span class="text-[7px] text-base-content/40">{{ formatTime(comment.timestamp) }}</span>
                                    </div>
                                    <div class="flex items-center gap-0.5">
                                      <button
                                        class="btn btn-xs btn-ghost h-auto py-0 px-0.5 text-[7px]"
                                        @click.stop="toggleResolve(comment)"
                                      >
                                        <i :class="comment.resolved ? 'fa-solid fa-rotate-left' : 'fa-solid fa-check'"></i>
                                      </button>
                                      <button
                                        class="btn btn-xs btn-ghost h-auto py-0 px-0.5 text-[7px] text-error"
                                        @click.stop="deleteComment(comment)"
                                      >
                                        <i class="fa-solid fa-trash"></i>
                                      </button>
                                    </div>
                                  </div>
                                  <div class="text-[9px] mt-0.5 break-words" :class="{ 'line-through': comment.resolved }">
                                    {{ comment.content }}
                                  </div>
                                </div>
                              </div>
                            </div>
                          </div>
                          <div class="w-8 shrink-0"></div>
                        </div>
                      </template>
                    </div>
                  </div>

                  <!-- Right side: New file -->
                  <div class="diff-side w-1/2 overflow-auto">
                    <div class="px-2 py-1 bg-base-200/80 text-[10px] font-semibold flex items-center gap-1">
                      <i class="fa-solid fa-file text-success"></i>
                      <span>{{ selectedFile.newFile.fileName || 'modified' }}</span>
                    </div>
                    <div class="diff-side-lines">
                      <template v-for="(line, index) in selectedFile.splitLines.new" :key="'new-' + index">
                        <div
                          class="diff-line flex"
                          :class="getSplitLineClass(line, index, 'new')"
                          @click="onSplitLineClick(line, index, 'new')"
                        >
                          <div class="line-number w-12 shrink-0 text-right pr-2 select-none text-[11px] font-mono text-base-content/40">
                            {{ line.newLineNumber }}
                          </div>
                          <div class="diff-indicator w-6 shrink-0 text-center select-none text-[11px] font-mono text-success">
                            {{ getSplitDiffIndicator(line) }}
                          </div>
                          <div class="line-content grow font-mono text-[11px] px-2 whitespace-pre">
                            {{ line.content }}
                          </div>
                          <div class="comment-actions w-8 shrink-0 flex justify-center items-center gap-1">
                            <template v-if="getSplitLineComments(line, 'new').length">
                              <button
                                class="btn btn-xs btn-ghost h-5 w-5 p-0 text-info"
                                @click.stop="toggleSplitLineComments(line, index, 'new')"
                              >
                                <i class="fa-solid fa-comment text-[10px]"></i>
                                <span class="badge badge-xs badge-info">{{ getSplitLineComments(line, 'new').length }}</span>
                              </button>
                            </template>
                            <template v-else-if="line.type === 'add'">
                              <button
                                class="btn btn-xs btn-ghost h-5 w-5 p-0 text-base-content/30 hover:text-info"
                                @click.stop="startSplitLineComment(line, index, 'new')"
                              >
                                <i class="fa-solid fa-plus text-[10px]"></i>
                              </button>
                            </template>
                          </div>
                        </div>

                        <!-- Comments panel for split view -->
                        <div
                          v-if="isSplitLineCommentsVisible(index, 'new') && getSplitLineComments(line, 'new').length"
                          class="diff-line-comments flex"
                        >
                          <div class="w-12 shrink-0"></div>
                          <div class="w-6 shrink-0"></div>
                          <div class="grow bg-info/10 border-y border-info/20 px-2 py-1">
                            <div class="flex items-center gap-1 mb-1">
                              <span class="text-[9px] text-info font-semibold">
                                <i class="fa-solid fa-comment-dots"></i>
                                {{ getSplitLineComments(line, 'new').length }} comment{{ getSplitLineComments(line, 'new').length > 1 ? 's' : '' }}
                              </span>
                              <button
                                class="btn btn-xs btn-ghost h-4 w-4 p-0 ml-auto"
                                @click.stop="hideSplitLineComments(index, 'new')"
                              >
                                <i class="fa-solid fa-xmark text-[8px]"></i>
                              </button>
                            </div>
                            <div class="space-y-1">
                              <div
                                v-for="comment in getSplitLineComments(line, 'new')"
                                :key="comment.id"
                                class="flex gap-1.5"
                                :class="{ 'opacity-60': comment.resolved }"
                              >
                                <div class="avatar shrink-0 mt-0.5">
                                  <div class="w-4 h-4 rounded-full bg-base-300 flex items-center justify-center">
                                    <span class="text-[8px] font-semibold">{{ comment.author?.[0] || '?' }}</span>
                                  </div>
                                </div>
                                <div class="grow min-w-0">
                                  <div class="flex items-center justify-between gap-1">
                                    <div class="flex items-center gap-1">
                                      <span class="text-[9px] font-semibold">{{ comment.author || 'Anonymous' }}</span>
                                      <span class="text-[7px] text-base-content/40">{{ formatTime(comment.timestamp) }}</span>
                                    </div>
                                    <div class="flex items-center gap-0.5">
                                      <button
                                        class="btn btn-xs btn-ghost h-auto py-0 px-0.5 text-[7px]"
                                        @click.stop="toggleResolve(comment)"
                                      >
                                        <i :class="comment.resolved ? 'fa-solid fa-rotate-left' : 'fa-solid fa-check'"></i>
                                      </button>
                                      <button
                                        class="btn btn-xs btn-ghost h-auto py-0 px-0.5 text-[7px] text-error"
                                        @click.stop="deleteComment(comment)"
                                      >
                                        <i class="fa-solid fa-trash"></i>
                                      </button>
                                    </div>
                                  </div>
                                  <div class="text-[9px] mt-0.5 break-words" :class="{ 'line-through': comment.resolved }">
                                    {{ comment.content }}
                                  </div>
                                </div>
                              </div>
                            </div>
                          </div>
                          <div class="w-8 shrink-0"></div>
                        </div>
                      </template>
                    </div>
                  </div>

                  <!-- Split view comment input -->
                  <div
                    v-if="splitCommentingSide && splitCommentingSide === 'old'"
                    class="diff-line-comment-input flex border-t border-base-content/10 bg-base-200/50 px-2 py-1.5"
                  >
                    <div class="w-full">
                      <div class="flex items-start gap-2">
                        <div class="flex-1">
                          <div class="flex items-center gap-2 mb-1">
                            <span class="text-[10px] text-base-content/40 font-mono">
                              Line {{ splitCommentingLine?.oldLineNumber }}
                            </span>
                            <span class="text-[9px] text-base-content/30 truncate max-w-[200px]">
                              {{ splitCommentingLine?.content?.slice(0, 50) }}
                            </span>
                          </div>
                          <textarea
                            v-model="newComment"
                            placeholder="Add a comment..."
                            class="textarea textarea-xs textarea-bordered w-full min-h-[36px] resize-none"
                            @keydown.enter.exact.prevent="submitComment"
                            ref="commentInput"
                          ></textarea>
                        </div>
                        <div class="flex flex-col gap-1 shrink-0">
                          <button
                            class="btn btn-xs btn-primary"
                            @click="submitComment"
                            :disabled="!newComment.trim()"
                          >
                            <i class="fa-solid fa-paper-plane text-[10px]"></i>
                          </button>
                          <button
                            class="btn btn-xs btn-ghost"
                            @click="cancelComment"
                          >
                            <i class="fa-solid fa-xmark text-[10px]"></i>
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div
                    v-if="splitCommentingSide && splitCommentingSide === 'new'"
                    class="diff-line-comment-input flex border-t border-base-content/10 bg-base-200/50 px-2 py-1.5"
                  >
                    <div class="w-full">
                      <div class="flex items-start gap-2">
                        <div class="flex-1">
                          <div class="flex items-center gap-2 mb-1">
                            <span class="text-[10px] text-base-content/40 font-mono">
                              Line {{ splitCommentingLine?.newLineNumber }}
                            </span>
                            <span class="text-[9px] text-base-content/30 truncate max-w-[200px]">
                              {{ splitCommentingLine?.content?.slice(0, 50) }}
                            </span>
                          </div>
                          <textarea
                            v-model="newComment"
                            placeholder="Add a comment..."
                            class="textarea textarea-xs textarea-bordered w-full min-h-[36px] resize-none"
                            @keydown.enter.exact.prevent="submitComment"
                            ref="commentInput"
                          ></textarea>
                        </div>
                        <div class="flex flex-col gap-1 shrink-0">
                          <button
                            class="btn btn-xs btn-primary"
                            @click="submitComment"
                            :disabled="!newComment.trim()"
                          >
                            <i class="fa-solid fa-paper-plane text-[10px]"></i>
                          </button>
                          <button
                            class="btn btn-xs btn-ghost"
                            @click="cancelComment"
                          >
                            <i class="fa-solid fa-xmark text-[10px]"></i>
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
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
                <i class="fa-solid fa-arrow-up-right-from-square"></i> Jump to line
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
const parser = new DiffParser()

export default {
  props: {
    fromBranch: { type: String, default: 'main' },
    toBranch: { type: String, default: 'develop' },
    repoChanges: { type: Object, default: null },
    project: { type: Object, default: null },
    chat: { type: Object, default: null },
    loading: { type: Boolean, default: false }
  },
  emits: ['refresh', 'comment', 'select-branch', 'chat-message'],
  data() {
    return {
      files: null,
      selectedFile: null,
      recentlyViewedFiles: [],
      fileFilter: '',
      diffViewMode: 'unified',
      newComment: '',
      commentingLine: null,
      commentingLineIndex: null,
      commentsByFile: {},
      folderExpanded: {},
      commentFilter: 'all',
      commentsModalOpen: false,
      // Track which line indices have their comments panel expanded (unified view)
      visibleLineComments: new Set(),
      // Split view state
      splitCommentingLine: null,
      splitCommentingIndex: null,
      splitCommentingSide: null,
      // Track which line indices have their comments panel expanded (split view)
      splitVisibleLineCommentsOld: new Set(),
      splitVisibleLineCommentsNew: new Set()
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

        if (!grouped[folderPath]) {
          grouped[folderPath] = []
        }
        grouped[folderPath].push(file)
      })

      Object.keys(grouped).forEach(folder => {
        grouped[folder].sort((a, b) => a.title.localeCompare(b.title))
      })

      const sorted = {}
      Object.keys(grouped).sort().forEach(key => {
        sorted[key] = grouped[key]
      })

      return sorted
    },

    changeCount() {
      return this.files?.length || 0
    },
    insertions() {
      return this.files?.reduce((sum, f) => sum + (f.insertions || 0), 0) || 0
    },
    deletions() {
      return this.files?.reduce((sum, f) => sum + (f.deletions || 0), 0) || 0
    },
    selectedFileIndex() {
      if (!this.selectedFile || !this.visibleFiles.length) return -1
      return this.visibleFiles.findIndex(f => f.fileFullName === this.selectedFile.fileFullName)
    },
    hasPreviousFile() {
      return this.selectedFileIndex > 0
    },
    hasNextFile() {
      return this.selectedFileIndex < this.visibleFiles.length - 1
    },
    fileComments() {
      if (!this.selectedFile) return []
      return this.commentsByFile[this.selectedFile.fileFullName] || []
    },
    totalCommentCount() {
      return Object.values(this.commentsByFile).reduce((sum, comments) => sum + comments.length, 0)
    },

    allComments() {
      const comments = []
      Object.entries(this.commentsByFile).forEach(([fileName, fileComments]) => {
        fileComments.forEach(comment => {
          comments.push({
            ...comment,
            fileName
          })
        })
      })
      return comments.sort((a, b) => b.timestamp - a.timestamp)
    },

    filteredAllComments() {
      if (this.commentFilter === 'all') return this.allComments
      if (this.commentFilter === 'unresolved') return this.allComments.filter(c => !c.resolved)
      if (this.commentFilter === 'resolved') return this.allComments.filter(c => c.resolved)
      return this.allComments
    }
  },
  watch: {
    repoChanges(newChanges) {
      if (newChanges) {
        this.buildFiles()
      } else {
        this.files = null
        this.selectedFile = null
      }
    },
    fileFilter() {
      if (!this.visibleFiles.find(f => f.fileFullName === this.selectedFile?.fileFullName)) {
        this.selectedFile = null
      }
    },
    selectedFile() {
      // Reset visible comments when switching files
      this.visibleLineComments.clear()
      this.splitVisibleLineCommentsOld.clear()
      this.splitVisibleLineCommentsNew.clear()
      // Auto-expand lines that have comments (visible by default)
      this.$nextTick(() => {
        this.autoExpandCommentedLines()
      })
    },
    diffViewMode() {
      // Reset commenting state when switching modes
      this.commentingLine = null
      this.commentingLineIndex = null
      this.splitCommentingLine = null
      this.splitCommentingIndex = null
      this.splitCommentingSide = null
      this.newComment = ''
      this.$nextTick(() => {
        this.autoExpandCommentedLines()
      })
    }
  },
  methods: {
    // Set diff view mode explicitly
    setDiffViewMode(mode) {
      this.diffViewMode = mode
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
          const diff = branch_file_and_commits[filePath].diff
          return this.buildDiffFile(diff, repoPath)
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
    },

    buildDiffFile(diff, repoPath) {
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
        const diffLines = this.parseDiffLines(diff)
        const splitLines = this.parseSplitLines(diff)

        let insertions = 0
        let deletions = 0
        diffLines.forEach(line => {
          if (line.type === 'add') insertions++
          if (line.type === 'del') deletions++
        })

        return {
          title,
          fileName,
          fileFullName,
          diff,
          diffLines,
          splitLines,
          oldFile: { fileName: oldName },
          newFile: { fileName: newName },
          isDeleted,
          isNewFile,
          isChanged,
          insertions,
          deletions,
          selected: false,
          commentCount: 0
        }
      } catch (ex) {
        console.error('Error parsing diff:', ex)
        return null
      }
    },

    parseDiffLines(diff) {
      const lines = diff.split('\n')
      const result = []
      let oldLineNum = 0
      let newLineNum = 0

      for (let i = 0; i < lines.length; i++) {
        const line = lines[i]

        if (line.startsWith('diff --git') || line.startsWith('index ') || line.startsWith('--- ') || line.startsWith('+++ ')) {
          continue
        }

        if (line.startsWith('@@')) {
          const match = line.match(/@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@/)
          if (match) {
            oldLineNum = parseInt(match[1])
            newLineNum = parseInt(match[2])
          }
          result.push({
            type: 'hunk',
            content: line,
            oldLineNumber: null,
            newLineNumber: null,
            isContext: false
          })
          continue
        }

        if (line.startsWith('+') && !line.startsWith('+++')) {
          result.push({
            type: 'add',
            content: line,
            oldLineNumber: null,
            newLineNumber: newLineNum++,
            isContext: false
          })
        } else if (line.startsWith('-') && !line.startsWith('---')) {
          result.push({
            type: 'del',
            content: line,
            oldLineNumber: oldLineNum++,
            newLineNumber: null,
            isContext: false
          })
        } else {
          result.push({
            type: 'context',
            content: line,
            oldLineNumber: oldLineNum++,
            newLineNumber: newLineNum++,
            isContext: true
          })
        }
      }

      return result
    },

    // Parse diff into separate old/new line arrays for split view
    parseSplitLines(diff) {
      const lines = diff.split('\n')
      const oldLines = []
      const newLines = []
      let oldLineNum = 0
      let newLineNum = 0

      for (let i = 0; i < lines.length; i++) {
        const line = lines[i]

        if (line.startsWith('diff --git') || line.startsWith('index ') || line.startsWith('--- ') || line.startsWith('+++ ')) {
          continue
        }

        if (line.startsWith('@@')) {
          const match = line.match(/@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@/)
          if (match) {
            oldLineNum = parseInt(match[1])
            newLineNum = parseInt(match[2])
          }
          oldLines.push({ type: 'hunk', content: line, oldLineNumber: null })
          newLines.push({ type: 'hunk', content: line, newLineNumber: null })
          continue
        }

        if (line.startsWith('+') && !line.startsWith('+++')) {
          newLines.push({ type: 'add', content: line, newLineNumber: newLineNum++ })
        } else if (line.startsWith('-') && !line.startsWith('---')) {
          oldLines.push({ type: 'del', content: line, oldLineNumber: oldLineNum++ })
        } else {
          oldLines.push({ type: 'context', content: line, oldLineNumber: oldLineNum++ })
          newLines.push({ type: 'context', content: line, newLineNumber: newLineNum++ })
        }
      }

      return { old: oldLines, new: newLines }
    },

    selectFile(file) {
      this.selectedFile = file
      this.commentingLine = null
      this.commentingLineIndex = null
      this.splitCommentingLine = null
      this.splitCommentingIndex = null
      this.splitCommentingSide = null
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

    selectAllFiles() {
      this.visibleFiles.forEach(f => { f.selected = true })
    },

    clearSelection() {
      this.visibleFiles.forEach(f => { f.selected = false })
    },

    // Auto-expand comment panels for lines that have comments
    autoExpandCommentedLines() {
      if (!this.selectedFile) return
      const fileComments = this.commentsByFile[this.selectedFile.fileFullName] || []
      if (!fileComments.length) return

      if (this.diffViewMode === 'unified') {
        // For unified view, expand by line index
        fileComments.forEach(comment => {
          const lineIndex = this.selectedFile.diffLines.findIndex(l => {
            const matchOld = comment.lineType === 'old' && l.oldLineNumber === comment.lineNumber
            const matchNew = comment.lineType === 'new' && l.newLineNumber === comment.lineNumber
            return matchOld || matchNew
          })
          if (lineIndex !== -1) {
            this.visibleLineComments.add(lineIndex)
          }
        })
      } else {
        // For split view, expand by side and index
        fileComments.forEach(comment => {
          const side = comment.lineType || 'new'
          const lines = this.selectedFile.splitLines[side]
          const lineIndex = lines.findIndex(l => {
            if (side === 'old') return l.oldLineNumber === comment.lineNumber
            return l.newLineNumber === comment.lineNumber
          })
          if (lineIndex !== -1) {
            if (side === 'old') {
              this.splitVisibleLineCommentsOld.add(lineIndex)
            } else {
              this.splitVisibleLineCommentsNew.add(lineIndex)
            }
          }
        })
      }
    },

    onLineClick(line, index) {
      if (line.isContext) return
      this.commentingLine = null
      this.commentingLineIndex = null
    },

    startLineComment(line, index) {
      this.commentingLine = line
      this.commentingLineIndex = index
      this.newComment = ''
      this.$nextTick(() => {
        const input = this.$refs.commentInput
        if (input) input.focus()
      })
    },

    toggleLineComments(line, index) {
      if (this.visibleLineComments.has(index)) {
        this.visibleLineComments.delete(index)
      } else {
        this.visibleLineComments.add(index)
      }
    },

    isLineCommentsVisible(index) {
      return this.visibleLineComments.has(index)
    },

    hideLineComments(index) {
      this.visibleLineComments.delete(index)
    },

    cancelComment() {
      this.commentingLine = null
      this.commentingLineIndex = null
      this.splitCommentingLine = null
      this.splitCommentingIndex = null
      this.splitCommentingSide = null
      this.newComment = ''
    },

    submitComment() {
      if (!this.newComment.trim() || !this.selectedFile) return

      // Determine line info based on current view mode
      let line, lineNumber, lineType, lineContent

      if (this.diffViewMode === 'unified') {
        line = this.commentingLine
        if (!line) return
        lineNumber = line.newLineNumber || line.oldLineNumber
        lineType = line.newLineNumber ? 'new' : 'old'
        lineContent = line.content
      } else {
        line = this.splitCommentingLine
        if (!line) return
        lineType = this.splitCommentingSide
        lineNumber = lineType === 'old' ? line.oldLineNumber : line.newLineNumber
        lineContent = line.content
      }

      const comment = {
        id: Date.now().toString(),
        content: this.newComment.trim(),
        author: 'User',
        timestamp: Date.now(),
        resolved: false,
        lineNumber,
        lineType,
        lineContent,
        replies: []
      }

      if (!this.commentsByFile[this.selectedFile.fileFullName]) {
        this.commentsByFile[this.selectedFile.fileFullName] = []
      }

      this.commentsByFile[this.selectedFile.fileFullName].push(comment)
      this.selectedFile.commentCount = (this.selectedFile.commentCount || 0) + 1

      this.$emit('comment', {
        file: this.selectedFile,
        line,
        comment: comment.content,
        lineNumber: comment.lineNumber,
        lineType: comment.lineType
      })

      // Auto-expand the comment panel
      this.autoExpandCommentedLines()
      this.cancelComment()
    },

    toggleResolve(comment) {
      comment.resolved = !comment.resolved
    },

    deleteComment(comment) {
      if (!this.selectedFile) return
      const comments = this.commentsByFile[this.selectedFile.fileFullName]
      const index = comments.indexOf(comment)
      if (index > -1) {
        comments.splice(index, 1)
        this.selectedFile.commentCount = Math.max(0, (this.selectedFile.commentCount || 0) - 1)
      }
    },

    // Get comments for a specific line (unified view) - respects lineType
    getLineComments(line) {
      if (!this.selectedFile) return []
      return this.fileComments.filter(c => {
        // Comment must match the specific line type
        if (c.lineType === 'old' && line.oldLineNumber === c.lineNumber) return true
        if (c.lineType === 'new' && line.newLineNumber === c.lineNumber) return true
        return false
      })
    },

    getLineClass(line, index) {
      const classes = []
      if (line.type === 'add') classes.push('bg-success/10')
      if (line.type === 'del') classes.push('bg-error/10')
      if (this.commentingLineIndex === index) {
        classes.push('bg-info/20')
      }
      if (this.getLineComments(line).length) {
        classes.push('border-l-2 border-info')
      }
      return classes.join(' ')
    },

    getDiffIndicatorClass(line) {
      if (line.type === 'add') return 'text-success'
      if (line.type === 'del') return 'text-error'
      return 'text-base-content/20'
    },

    getDiffIndicator(line) {
      if (line.type === 'add') return '+'
      if (line.type === 'del') return '-'
      if (line.type === 'hunk') return '~'
      return ' '
    },

    // Split view methods
    getSplitLineClass(line, index, side) {
      const classes = []
      if (line.type === 'add') classes.push('bg-success/10')
      if (line.type === 'del') classes.push('bg-error/10')
      if (this.splitCommentingSide === side && this.splitCommentingIndex === index) {
        classes.push('bg-info/20')
      }
      const comments = this.getSplitLineComments(line, side)
      if (comments.length) {
        classes.push('border-l-2 border-info')
      }
      return classes.join(' ')
    },

    getSplitDiffIndicator(line) {
      if (line.type === 'add') return '+'
      if (line.type === 'del') return '-'
      if (line.type === 'hunk') return '~'
      return ' '
    },

    onSplitLineClick(line, index, side) {
      // Only allow commenting on changed lines
      if (line.type === 'context') return
      this.splitCommentingLine = null
      this.splitCommentingIndex = null
      this.splitCommentingSide = null
    },

    startSplitLineComment(line, index, side) {
      this.splitCommentingLine = line
      this.splitCommentingIndex = index
      this.splitCommentingSide = side
      this.newComment = ''
      this.$nextTick(() => {
        const input = this.$refs.commentInput
        if (input) input.focus()
      })
    },

    toggleSplitLineComments(line, index, side) {
      const set = side === 'old' ? this.splitVisibleLineCommentsOld : this.splitVisibleLineCommentsNew
      if (set.has(index)) {
        set.delete(index)
      } else {
        set.add(index)
      }
    },

    isSplitLineCommentsVisible(index, side) {
      const set = side === 'old' ? this.splitVisibleLineCommentsOld : this.splitVisibleLineCommentsNew
      return set.has(index)
    },

    hideSplitLineComments(index, side) {
      const set = side === 'old' ? this.splitVisibleLineCommentsOld : this.splitVisibleLineCommentsNew
      set.delete(index)
    },

    // Get comments for a specific line in split view - respects lineType
    getSplitLineComments(line, side) {
      if (!this.selectedFile) return []
      return this.fileComments.filter(c => {
        // Only show comments that match this side
        if (c.lineType !== side) return false
        if (side === 'old') return line.oldLineNumber === c.lineNumber
        return line.newLineNumber === c.lineNumber
      })
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

    openCommentsModal() {
      this.$refs.commentsModal.showModal()
    },

    closeCommentsModal() {
      this.$refs.commentsModal.close()
    },

    jumpToComment(comment) {
      const file = this.files.find(f => f.fileFullName === comment.fileName)
      if (file) {
        this.selectFile(file)
        // Switch to appropriate view mode and expand comment
        if (this.diffViewMode === 'unified') {
          const lineIndex = file.diffLines.findIndex(l => {
            const matchOld = comment.lineType === 'old' && l.oldLineNumber === comment.lineNumber
            const matchNew = comment.lineType === 'new' && l.newLineNumber === comment.lineNumber
            return matchOld || matchNew
          })
          if (lineIndex !== -1) {
            this.visibleLineComments.add(lineIndex)
          }
        } else {
          const side = comment.lineType || 'new'
          const lines = file.splitLines[side]
          const lineIndex = lines.findIndex(l => {
            if (side === 'old') return l.oldLineNumber === comment.lineNumber
            return l.newLineNumber === comment.lineNumber
          })
          if (lineIndex !== -1) {
            if (side === 'old') {
              this.splitVisibleLineCommentsOld.add(lineIndex)
            } else {
              this.splitVisibleLineCommentsNew.add(lineIndex)
            }
          }
        }
      }
      this.closeCommentsModal()
    }
  },
  expose: ['buildFiles']
}
</script>