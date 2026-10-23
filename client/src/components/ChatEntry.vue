<script setup>
import Markdown from './Markdown.vue'
import moment from 'moment'
import { CodeDiff } from 'v-code-diff'
import ChatIcon from './chat/ChatIcon.vue'
import Document from './document/Document.vue'
import ProfileAvatar from './profile/ProfileAvatar.vue'
import DocumentSummary from './document/DocumentSummary.vue'
import MessagePRView from './chat/MessagePRView.vue'
import MessageFileView from './chat/MessageFileView.vue'
import ChatEntrySelectionMenu from './ChatEntrySelectionMenu.vue'
import ChatAttachmentPreview from './chat/ChatAttachmentPreview.vue'
import ChatMessageEvents from './chat/ChatMessageEvents.vue'
</script>

<template>
  <!-- =============================================
       NOTION-STYLE DESKTOP BLOCK RENDERING
       ============================================= -->
  <!-- `has-[.dropdown:focus-within]:z-30` lifts the WHOLE entry while its ⋯ menu
       is open. The menu lives inside the sticky header (a z-20 stacking context),
       so its own z-[200] cannot escape; without this the next message's sticky
       z-20 header (later in DOM) paints over the overflowing menu items. -->
  <div
    class="notion-entry group/entry relative w-full has-[.dropdown:focus-within]:z-30"
    :class="[
      displayMessage.hide && 'opacity-40 hover:opacity-100 transition-opacity',
    ]"
    tabindex="0"
  >
    <!-- ── Row: Header + Content ── -->
    <!-- Compact by default; comfortable once the chat panel reaches @lg (512px+). -->
    <div class="flex gap-2 items-start w-full @lg/panel:gap-3">

      <!-- Main block column -->
      <div class="flex-1 min-w-0 pb-0.5">

        <!-- Header row: only shown on first message of a speaker group -->
        <!-- Sticky: stays pinned to the top of the messages viewport while a long
             message scrolls, so author/actions are always reachable. -->
        <!-- Layout: LEFT = identity + state (archive, time, seen, events/tools,
             avatars, badges) · RIGHT = actions. -->
        <!-- Narrow (mobile) panels use a single tight row: the action icons move
             into the ⋯ dropdown (see below) instead of wrapping. -->
        <!-- Channels (team channel / DM) are the exception: the header sits
             directly ON the channel background (transparent, not sticky), so it
             never paints a surface that differs from the conversation canvas. -->
        <!-- `focus-within:z-30`: while a header control (the ⋯ menu) holds focus
             this header outranks the following messages' sticky z-20 headers. -->
        <div
          class="flex items-center gap-2 leading-none flex-wrap px-1"
          :class="isChannel
            ? 'pb-1'
            : 'sticky top-0 z-20 focus-within:z-30 -mt-1 pb-1.5 @lg/panel:pb-3 bg-base-100 border-b border-base-content/10 @lg/panel:border-base-content/30'"
        >

          <!-- ─────────────────────────── LEFT: identity + state ─────────────────────────── -->

          <!-- Archive toggle -->
          <button
            v-if="isDone"
            class="btn btn-xs btn-ghost tooltip tooltip-bottom"
            :class="displayMessage.hide ? 'text-warning/70' : '' "
            :data-tip="displayMessage.hide ? 'Unarchive' : 'Archive'"
            @click.stop="$emit('hide', message)"
          >
            <i class="fa-solid fa-box-archive"></i>
          </button>

          <!-- Timestamp -->
          <span class="text-[11px] text-base-content/40 tabular-nums">{{ formatDate(displayMessage.updated_at) }}</span>
          <span v-if="timeTaken" class="hidden @lg/panel:inline text-[11px] text-base-content/30 tabular-nums">{{ timeTaken }}</span>

          <!-- Seen double-check (other users' messages only) -->
          <button
            v-if="!isMyMessage && isDone"
            class="h-5 w-5 min-h-0 tooltip tooltip-bottom flex items-center justify-center transition-all"
            :class="isMessageSeen ? 'text-success hover:text-success/80' : 'text-base-content/30 hover:text-base-content/50'"
            :data-tip="isMessageSeen ? 'Mark un-seen' : 'Mark seen'"
            @click.stop="toggleUnseenStatus"
          >
            <i class="fa-solid fa-check-double text-sm"></i>
          </button>

          <!-- Inline events trigger (assistant only).
               - Hidden on mobile (*) — reachable from the ⋯ menu.
               - Hidden when there are tools, since the tools button toggles the same inline list.
               - Hidden in channels: tool/run events are developer detail. -->
          <button
            v-if="isAssistant && !isChannel && !toolEventCount"
            class="hidden @lg/panel:flex btn btn-xs btn-ghost tooltip tooltip-bottom"
            :class="eventsOpen && 'btn-active text-warning'"
            data-tip="Events & Tools"
            @click.stop="toggleEventsPanel"
          >
            <i class="fa-solid fa-stream text-info"></i>
          </button>

          <!-- Tools counter — shows the icon + count and toggles the inline tools list
               rendered inside this message (see <ChatMessageEvents> below). -->
          <button
            v-if="isAssistant && !isChannel && toolEventCount"
            class="btn btn-xs btn-ghost gap-1 tooltip tooltip-bottom"
            :class="eventsOpen && 'btn-active text-warning'"
            data-tip="Tools"
            @click.stop="toggleEventsPanel"
          >
            <i class="fa-solid fa-wrench text-info"></i>
            <span class="text-[11px] tabular-nums">x{{ toolEventCount }}</span>
          </button>

          <span class="font-semibold text-sm text-base-content truncate max-w-[60%] @lg/panel:max-w-none">
            {{ displayMessage.user }}
          </span>


          <!-- Avatars — DaisyUI overlapping avatar group to save space -->
          <div
            v-if="isAssistant || messageProfiles.length"
            class="avatar-group -space-x-3 rtl:space-x-reverse shrink-0"
          >
            <div v-if="isAssistant" class="avatar">
              <div class="w-5">
                <img src="/only_icon.png" alt="Assistant" />
              </div>
            </div>
            <ProfileAvatar
              v-for="profile in messageProfiles"
              :key="profile.name"
              :profile="profile"
              width="5"
            />
          </div>

          <!-- Project override — a message can target a project different from
               the chat's working project (message.project_id): show which one so
               the files/code it mentions are not read in the wrong context.
               Narrow panels keep only the icon; the name appears at @lg/panel. -->
          <span
            v-if="isProjectOverridden"
            class="badge badge-xs badge-info badge-outline gap-1 shrink-0 max-w-[9rem] tooltip tooltip-bottom"
            :data-tip="projectLabel"
            :aria-label="projectLabel"
          >
            <img
              v-if="messageProject?.project_icon"
              :src="messageProject.project_icon"
              alt=""
              class="w-3 h-3 rounded-full object-cover shrink-0"
            />
            <i v-else class="fa-solid fa-folder shrink-0"></i>
            <span class="hidden @lg/panel:inline truncate">{{ messageProject?.project_name || 'Project' }}</span>
          </span>

          <!-- Status badges -->
          <span v-if="cancellationTime" class="badge badge-xs badge-error">
            <i class="fa-solid fa-ban mr-0.5"></i>Cancelled
          </span>
          <span v-if="displayMessage.is_answer" class="badge badge-xs badge-success gap-1">
            <ChatIcon mode="answer" /> Knowledge
          </span>
          <!-- `mode` carries the CHANNEL TYPE in team chats, not a knowledge
               topic, so the topic badge only makes sense outside channels. -->
          <span v-if="isTopic && !isChannel" class="badge badge-xs badge-info gap-1">
            <ChatIcon mode="topic" /> Topic
          </span>
          <span v-if="displayMessage.hide" class="text-[11px] text-warning/50">
            <i class="fa-solid fa-box-archive"></i> Archived
          </span>

          <div class="grow"></div>

          <!-- ─────────────────────────── RIGHT: actions ─────────────────────────── -->
          <!-- relative + z-20 lifts this (and its dropdown) above the content block. -->
          <div
            class="relative z-20
                  focus-within:opacity-100
                  transition-all duration-150 translate-y-0
                  flex items-center gap-0.5"
          >
            <!-- Stop generation — the only action that stays inline on every
                 panel width, cancelling must never hide behind a menu. -->
            <button
              v-if="!isDone && cancellationTokenId"
              class="btn btn-xs btn-error gap-1"
              @click.stop="cancelMessage"
            >
              <span class="loading loading-xs"></span>Stop
            </button>

            <!-- Core actions -->
            <!-- Rendered inline only on wide panels (@lg = 512px+). On narrow
                 (mobile) panels all of them live in the ⋯ dropdown below, so the
                 message header keeps a single compact line. -->
            <button
              class="hidden @lg/panel:inline-flex btn btn-xs btn-ghost tooltip tooltip-bottom"
              data-tip="Thread"
              @click.stop="$emit('thread', message)"
            >
              <i class="fa-solid fa-comment-dots"></i>
            </button>
            <button
              v-if="!isChannel"
              class="hidden @lg/panel:inline-flex btn btn-xs btn-ghost tooltip tooltip-bottom"
              data-tip="Mark as answer"
              @click.stop="$emit('answer', message)"
            >
              <i class="fa-solid fa-circle-info text-info/70"></i>
            </button>
            <button
              class="hidden @lg/panel:inline-flex btn btn-xs btn-ghost tooltip tooltip-bottom"
              data-tip="Copy"
              @click.stop="copyMessageToClipboard"
            >
              <i class="fa-solid fa-copy"></i>
            </button>
            <button
              v-if="displayMessage.diffMessage && !isChannel"
              class="hidden @lg/panel:inline-flex btn btn-xs btn-ghost tooltip tooltip-bottom"
              :class="showDiff && 'btn-active'"
              data-tip="Diff"
              @click.stop="toggleShowDiff"
            >
              <i class="fa-regular fa-file-lines"></i>
            </button>
            <button
              v-if="hasCodeBlocksOrFiles && !isChannel"
              class="hidden @lg/panel:inline-flex btn btn-xs btn-ghost tooltip tooltip-bottom"
              :class="showFileView && 'btn-active'"
              data-tip="Files"
              @click.stop="toggleFileView"
            >
              <i class="fa-solid fa-file-code"></i>
            </button>
            <button
              v-if="hasPRViewBlocks && !isChannel"
              class="hidden @lg/panel:inline-flex btn btn-xs btn-ghost tooltip tooltip-bottom"
              :class="showPRView && 'btn-active'"
              data-tip="Review"
              @click.stop="togglePRView"
            >
              <i class="fa-solid fa-code-branch"></i>
            </button>

            <!-- Divider (wide panels only) -->
            <div class="hidden @lg/panel:block w-px h-4 bg-base-300 mx-0.5"></div>

            <!-- More dropdown -->
            <div class="dropdown dropdown-end" @click.stop>
              <button tabindex="0" class="btn btn-xs btn-ghost">
                <i class="fa-solid fa-ellipsis-vertical"></i>
              </button>
              <ul
                tabindex="0"
                class="dropdown-content bg-base-100 menu rounded-box shadow-lg w-44 p-1 z-[200] text-sm"
              >
                <!-- ── Compact (mobile) message actions ──
                     Mirrors the inline icon row that is hidden below @lg/panel,
                     so every action stays reachable without widening the header. -->
                <li class=""><a @click.stop="$emit('thread', message)"><i class="fa-solid fa-comment-dots w-4"></i> Thread</a></li>
                <li v-if="!isChannel" class=""><a @click.stop="$emit('answer', message)"><i class="fa-solid fa-circle-info w-4 text-info/70"></i> {{ displayMessage.is_answer ? 'Unmark answer' : 'Mark as answer' }}</a></li>
                <li class=""><a @click.stop="copyMessageToClipboard"><i class="fa-solid fa-copy w-4"></i> Copy</a></li>
                <li v-if="displayMessage.diffMessage && !isChannel" class=""><a @click.stop="toggleShowDiff" :class="showDiff && 'text-primary'"><i class="fa-regular fa-file-lines w-4"></i> Diff</a></li>
                <li v-if="hasCodeBlocksOrFiles && !isChannel" class=""><a @click.stop="toggleFileView" :class="showFileView && 'text-primary'"><i class="fa-solid fa-file-code w-4"></i> Files</a></li>
                <li v-if="hasPRViewBlocks && !isChannel" class=""><a @click.stop="togglePRView" :class="showPRView && 'text-primary'"><i class="fa-solid fa-code-branch w-4"></i> Review</a></li>

                <!-- Inline Events & Tools — the desktop trigger is hidden on
                     mobile (*), so it lives here for narrow panels. -->
                <li v-if="isAssistant && !isChannel" class=""><a @click.stop="toggleEventsPanel"><i class="fa-solid fa-stream w-4 text-info"></i> Events & Tools</a></li>
                <li v-if="!isChannel"><a @click.stop="runAgents" class="text-info"><i class="fa-solid fa-people-group w-4"></i> Run agents</a></li>
                <li v-if="isDone && !isChannel"><a @click.stop="toggleSrcView()"><i class="fa-solid fa-code w-4"></i> View source</a></li>
                <li v-if="isDone"><a @click.stop="$emit('edit-message', message)"><i class="fa-solid fa-pen w-4"></i> Edit</a></li>
                <li v-if="isDone"><a @click.stop="toggleUnseenStatus" :class="isMessageSeen && 'text-success'"><i :class="isMessageSeen ? 'fa-solid fa-eye' : 'fa-solid fa-eye-slash'" class="w-4"></i> {{ isMessageSeen ? 'Mark un-seen' : 'Mark seen' }}</a></li>
                <li><a @click.stop="confirmRemove" class="text-error"><i class="fa-solid fa-trash-can w-4"></i> Delete</a></li>
              </ul>
            </div>
          </div>

        </div>

        <!-- ── Tool & run events (collapsible, live-updated while streaming) ──
             Rendered inline, directly under the header so it is discoverable and
             contextual. Driven by the existing `eventsOpen` prop (parent owns the
             open state). The "more details" drawer trigger lives INSIDE this panel
             (see <ChatMessageEvents>), which re-emits `show-events-drawer`.
             Hidden in channels: processing details are developer output. -->
        <ChatMessageEvents
          v-if="eventsOpen && !isChannel"
          :message="displayMessage"
          :drawerOpen="eventsDrawerOpen"
          class="mt-2"
          @show-events-drawer="$emit('show-events-drawer', message)"
        />

        <!-- ── Thread / Reply badge (always visible if exists) ── -->
        <div
          v-if="threadChat"
          class="mb-1 inline-flex"
        >
          <button
            class="flex items-center gap-1 text-[11px] text-info hover:text-info hover:underline cursor-pointer"
            @click.stop="openThread"
          >
            <ChatIcon :mode="threadChat.mode" />
            <span>{{ threadChat.messages?.length || 0 }} replies</span>
          </button>
        </div>

        <!-- ── Loading bar ── -->
        <progress
          v-if="!isDone"
          class="progress progress-xs w-full mb-2 opacity-50"
        ></progress>

        <!-- ── Selection context menu ── -->
        <ChatEntrySelectionMenu
          v-if="showSelectionMenu"
          :selectedText="selectedText"
          :chatProject="chatProject"
          @copy="onSelectionCopy"
          @create-subtask="onSelectionCreateSubtask"
          @search-files="onSelectionSearchFiles"
          @close="onCloseSelectionMenu"
        />

        <!-- ── Skeleton loader ── -->
        <div v-if="!displayMessage.content && !displayMessage.think" class="space-y-2 py-1">
          <div class="skeleton h-4 w-full rounded"></div>
          <div class="skeleton h-4 w-4/5 rounded"></div>
          <div class="skeleton h-4 w-2/3 rounded"></div>
        </div>

        <!-- ── TOC for long documents ── -->
        <DocumentSummary
          v-if="!srcView && isDone && messageContent && !showPRView && !showFileView && !hasEvents && !showAttachments"
          :content="messageContent"
          :minHeadings="3"
          :documentId="documentId"
          :scrollContainer="$refs.contentArea"
          class="mb-3"
        />

        <!-- ── Main content area ── -->
        <div
          ref="contentArea"
          @copy.stop="onMessageCopy"
          @mouseup="onContentMouseUp"
          class="min-w-0 w-full notion-content"
          :class="[
            displayMessage.is_answer && 'pl-2 @lg/panel:pl-3 border-l-4 border-info/30',
            isTopic && !isChannel && !displayMessage.is_answer && 'pl-2 @lg/panel:pl-3 border-l-2 border-info/30',
          ]"
        >

          <!-- Source view -->
          <pre v-if="srcView" class="text-xs overflow-auto bg-base-200 p-3 rounded-lg">{{ displayMessage.content }}</pre>

          <!-- Document / Markdown -->
          <Document
            v-if="!showDiff && !srcView && !showPRView && !showFileView && !code_patches && !isWord && !showAttachments"
            :content="messageContent"
            :files="chatFiles"
            :project="chatProject"
            :chat="chat"
            :loading="!message.done"
            :documentId="documentId"
            :message="message"
            @generate-code="onGenerateCode"
            @reload-file="$emit('reload-file', { file: $event, message })"
            @open-file="$emit('open-file', $event)"
            @save-file="$emit('save-file', $event)"
            @add-file="$emit('add-file', $event)"
            @sub-task="$emit('sub-task', $event)"
            @copy-chapter="onCopyChapter"
            @create-task="onCreateTask"
            @block-edited="onBlockEdited"
            :mentionList="mentionList"
          >
            <template #chapter-actions="{ chapter, fullContent }">
              <button class="btn btn-sm btn-ghost gap-1" @click="copyChapterMarkdown(chapter, fullContent)">
                <i class="fa-solid fa-copy"></i> Copy
              </button>
              <button class="btn btn-sm btn-ghost gap-1" @click="createTaskFromChapter(chapter, fullContent)">
                <i class="fa-solid fa-plus"></i> Task
              </button>
            </template>
          </Document>

          <!-- Error -->
          <div class="alert alert-error text-xs mt-2" v-if="displayMessage.error">
            {{ displayMessage.error }}
          </div>

          <!-- Diff view -->
          <CodeDiff
            v-if="showDiff && !showPRView && !showFileView"
            :new-string="displayMessage.diffMessage.content"
            :old-string="messageContent"
            theme="dark"
          />

          <!-- Code patches -->
          <div v-if="code_patches && !showPRView && !showFileView && !showAttachments" class="space-y-3 mt-2">
            <div
              v-for="patch in code_patches"
              :key="patch.file_path"
              class="border border-base-100 rounded-lg p-3 bg-base-200/50"
            >
              <div class="text-xs font-bold text-primary mb-1" :title="patch.file_path">
                {{ patch.file_path.replace($project.abs_project_path, '') }}
              </div>
              <div class="text-xs text-base-content/50 mb-2">{{ patch.description }}</div>
              <Markdown :text="'```diff\n' + patch.patch + '\n```'"></Markdown>
              <div class="flex justify-end mt-2">
                <button
                  class="btn btn-sm btn-warning gap-1"
                  :disabled="patch.working"
                  @click="applyPatch(patch)"
                >
                  <span class="loading loading-spinner" v-if="patch.working"></span>
                  Apply changes
                </button>
              </div>
              <div v-if="patch.res" class="text-xs mt-2">
                <div class="text-error" v-if="patch.res.error">{{ patch.res.error }}</div>
                <div class="text-success" v-else>
                  <i class="fa-solid fa-check"></i> Applied
                </div>
              </div>
            </div>
          </div>

          <!-- ── Bulk save toolbar ──
               Rendered above BOTH the Files view and the Review (PR) view, i.e.
               whenever code blocks are on screen. The per-file checkboxes live
               inside the child views (they own the block list); this bar only
               drives "All" and the single bulk write call. -->
          <div
            v-if="showCodeBlockSelection"
            class="mt-2 mb-2 rounded-lg border border-base-content/10 bg-base-200/40"
          >
            <div class="flex items-center gap-2 px-2 py-1.5 flex-wrap">
              <label
                v-if="selectableCodeBlocks.length > 1"
                class="flex items-center gap-1.5 cursor-pointer select-none"
              >
                <input
                  type="checkbox"
                  class="checkbox checkbox-xs checkbox-primary"
                  :checked="allCodeBlocksSelected"
                  :indeterminate.prop="someCodeBlocksSelected"
                  aria-label="Select all files"
                  @change="toggleSelectAllCodeBlocks($event.target.checked)"
                />
                <span class="text-[11px] text-base-content/60">All</span>
              </label>

              <span class="text-[11px] text-base-content/40 tabular-nums">
                {{ selectedCodeBlockKeys.length }}/{{ selectableCodeBlocks.length }} selected
              </span>

              <span
                v-if="codeBlockSaveStatus"
                class="text-[11px]"
                :class="codeBlockSaveStatus.error ? 'text-error' : 'text-success'"
              >
                {{ codeBlockSaveStatus.text }}
              </span>

              <div class="grow"></div>

              <button
                class="btn btn-xs btn-ghost gap-1"
                :disabled="!selectedCodeBlockKeys.length || savingCodeBlocks"
                @click="clearCodeBlockSelection"
              >
                <i class="fa-solid fa-xmark"></i>Clear
              </button>
              <button
                class="btn btn-xs btn-success gap-1"
                :disabled="!selectedCodeBlockKeys.length || savingCodeBlocks"
                @click="saveSelectedCodeBlocks"
              >
                <span v-if="savingCodeBlocks" class="loading loading-spinner loading-xs"></span>
                <i v-else class="fa-solid fa-floppy-disk"></i>
                Save {{ selectedCodeBlockKeys.length }} file{{ selectedCodeBlockKeys.length > 1 ? 's' : '' }}
              </button>
            </div>
          </div>

          <!-- File View -->
          <MessageFileView
            v-if="showFileView && !srcView && !showDiff && !showPRView && !showAttachments"
            :codeBlocks="prViewCodeBlocks"
            :linkedFiles="displayMessage.files"
            :chat="chat"
            :message="message"
            :selectionKeys="codeBlockKeys"
            :selectedKeys="selectedCodeBlockKeys"
            :savingSelection="savingCodeBlocks"
            @toggle-select="toggleCodeBlockSelection"
            @save-file="$emit('save-file', $event)"
            @add-file="$emit('add-file', $event)"
            @open-file="$emit('open-file', $event)"
            @sub-task="$emit('sub-task', $event)"
            @remove-file="$emit('remove-file', $event)"
          />

          <!-- PR View -->
          <MessagePRView
            v-if="showPRView && !srcView && !showDiff && !showFileView && !showAttachments"
            :codeBlocks="prViewCodeBlocks"
            :chat="chat"
            :message="message"
            :activeBranch="activeBranch"
            :selectionKeys="codeBlockKeys"
            :selectedKeys="selectedCodeBlockKeys"
            @toggle-select="toggleCodeBlockSelection"
            @save-file="$emit('save-file', $event)"
            @add-file="$emit('add-file', $event)"
            @open-file="$emit('open-file', $event)"
            @sub-task="$emit('sub-task', $event)"
          />

          <!-- Images -->
          <div v-if="images && !showPRView && !showFileView && !showAttachments && images?.length" class="mt-3">
            <p class="text-xs text-base-content/40 mb-2">
              <i class="fa-solid fa-images mr-1"></i>Images
            </p>
            <div class="carousel gap-2">
              <div
                class="carousel-item cursor-pointer"
                v-for="image in images"
                :key="image.src"
                @click="$emit('image', image)"
              >
                <div class="flex flex-col gap-1">
                  <div
                    class="bg-cover bg-center border border-base-100 rounded-lg w-20 h-20 hover:border-primary transition-colors"
                    :style="`background-image: url(${image.src})`"
                  ></div>
                  <p class="badge badge-xs" v-if="image.alt">{{ image.alt.slice(0, 12) }}</p>
                </div>
              </div>
            </div>
          </div>

          <!-- Linked files — project file paths belong to developer chats only.
               Channels/DMs share files through attachments (see below). -->
          <div
            v-if="displayMessage.files?.length && !isChannel && !showPRView && !showFileView && !showAttachments"
            class="mt-3 pt-2 border-t border-base-100/50"
          >
            <p class="text-[11px] text-base-content/40 mb-1.5">
              <i class="fa-solid fa-paperclip mr-1"></i>Linked files
            </p>
            <div class="flex flex-wrap gap-1">
              <div
                v-for="file in displayMessage.files"
                :key="file"
                class="flex items-center gap-1 text-xs bg-base-200 hover:bg-base-300 rounded-md px-2 py-0.5 transition-colors group/file"
              >
                <i class="fa-solid fa-file text-primary/60 text-[10px]"></i>
                <a
                  class="hover:underline cursor-pointer max-w-[180px] truncate"
                  @click="openFile(file)"
                  :title="file"
                >
                  {{ file.split('/').reverse()[0] }}
                </a>
                <button
                  class="opacity-0 group-hover/file:opacity-100 ml-0.5 hover:text-error transition-all"
                  @click.stop="$emit('add-file', file)"
                  title="Add to chat"
                >
                  <i class="fa-solid fa-plus text-[10px]"></i>
                </button>
                <button
                  class="opacity-0 group-hover/file:opacity-100 hover:text-error transition-all"
                  @click.stop="$emit('remove-file', file)"
                >
                  <i class="fa-regular fa-circle-xmark text-[10px]"></i>
                </button>
              </div>
            </div>
          </div>

          <!-- Attachments — channels render them as large Discord-style previews -->
          <ChatAttachmentPreview
            v-if="displayMessage.attachments?.length"
            :attachments="displayMessage.attachments"
            :size="isChannel ? 'lg' : 'sm'"
            @update-attachment="onAttachmentUpdated"
          />
        </div>

        <!-- ── Seen timeout progress bar ── -->
        <div
          ref="seenProgressBar"
          class="mt-2 transition-opacity duration-200 min-h-2 bg-base-200"
          :class="isFocused && !isMessageSeen ? 'opacity-100' : 'opacity-0'"
          tabindex="0"
          @focus="onMessageFocus"
          @blur="onMessageBlur"
        >
          <div class="flex gap-2 items-center h-full"
            v-if="!isMyMessage && isDone"
            :class="isFocused && !isMessageSeen ? 'opacity-100' : 'opacity-0'"
          >
            <progress
              class="progress progress-xs flex-1 bg-success/20"
              :value="seenProgressValue"
              max="100"
            ></progress>
            <i class="fa-solid fa-check-double text-sm text-success"></i>
          </div>
        </div>

        <!-- ── Collapsed toggle (for archived messages) ── -->
        <div
          v-if="isCollapsed && displayMessage.hide"
          class="mt-1 text-[11px] text-base-content/30 cursor-pointer hover:text-base-content/60 transition-colors"
          @click="collapsed = false"
        >
          <i class="fa-solid fa-chevron-down mr-1"></i>Show archived content
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  props: ['chat', 'message', 'mentionList', 'menu-less', 'usersList', 'isNewSpeaker', 'eventsOpen', 'eventsDrawerOpen'],
  emits: [
    'generate-code',
    'reload-file',
    'open-file',
    'save-file',
    'add-file',
    'sub-task',
    'thread',
    'hide',
    'remove',
    'answer',
    'enhance',
    'copy',
    'add-file-to-chat',
    'remove-file',
    'image',
    'run-agents',
    'edit-message',
    'search-files',
    'edited',
    'run-edit',
    'code-file-shown',
    'message-changed',
    'show-events',
    'show-events-drawer',
    'preview-file',
    'update-attachment'
  ],
  data() {
    return {
      srcView: false,
      isRemove: false,
      improvementData: null,
      showDiff: false,
      showPRView: false,
      showFileView: false,
      showAttachments: false,
      documentId: 'doc-' + Math.random().toString(36).slice(2, 8),
      activeBranch: null,
      branchLoading: false,
      showSelectionMenu: false,
      selectedText: '',
      selectionPosition: { top: 0, left: 0 },
      collapsed: false,
      hasSeen: false,
      unseenToggling: false,
      isFocused: false,
      seenProgressValue: 0,
      seenDuration: 2500,
      progressInterval: null,
      intersectionObserver: null,
      // Code block selection for bulk save (lives here so CodeViewers stay dumb)
      selectedCodeBlockKeys: [],
      savingCodeBlocks: false,
      codeBlockSaveStatus: null
    }
  },
  created() {
    this.loadThreadChat()
    this.loadActiveBranch()
    this.collapsed = this.displayMessage.hide
  },
  computed: {
    isMobile() {
      return this.$ui?.isMobile
    },
    isDone() {
      return this.displayMessage.done
    },
    // ── Channel / team context ────────────────────────────────────────────
    // Team channels and team DMs are ordinary chats tagged by the team store:
    //   board: `team:<teamId>`  ·  name: `team:<teamId>/<channel>` | `dm:<teamId>/<user>`
    // (see store/teams.js `createChannel` / `openDirectMessage` and
    // store/ui.js `openTeamChannel` / `openTeamDM`).
    // `mode` holds the CHANNEL TYPE ('topic' | 'chat' | 'task'), so it cannot
    // be used to detect a channel — the board/name is the stable marker.
    isTeamChat() {
      const board = this.chat?.board
      if (typeof board === 'string' && board.startsWith('team:')) return true
      const name = this.chat?.name
      return typeof name === 'string' &&
        (name.startsWith('team:') || name.startsWith('dm:'))
    },
    // Explicit channel mode (chats created outside the team store)
    isChannelChat() {
      return this.chat?.mode === 'channel'
    },
    // Any Discord/Slack-like conversation surface: channel or team chat/DM
    isChannel() {
      return this.isChannelChat || this.isTeamChat
    },
    isChannelMessage() {
      return this.isChannel
    },
    // `mode === 'topic'` means "text channel" inside a team, not a knowledge
    // topic: the topic styling (badge + side border) only applies outside.
    isTopic() {
      return this.chat?.mode === 'topic' && !this.isTeamChat
    },
    // Topic chats show the thread's latest reply inline in place of the parent
    // message. A channel must always keep the parent visible (Discord/Slack
    // show a "N replies" badge instead — see the thread badge below).
    isSlackStyle() {
      return this.chat?.mode === 'topic' && !this.isTeamChat
    },
    isWord() {
      return this.chat?.mode === 'word'
    },
    isCollapsed() {
      return this.collapsed !== undefined
        ? this.collapsed
        : this.displayMessage.hide ? true : false
    },
    isMyMessage() {
      return this.displayMessage.user === this.$user.username
    },
    isAssistant() {
      return this.message.role === 'assistant'
    },
    canEditMessage() {
      return !this.isChannelMessage ||
        this.isMyMessage ||
        this.isAssistant
    },
    thinkText() {
      return this.displayMessage.think
    },
    // The entry renders its own message. In slack-like (topic) chats the replies
    // of a message live in a thread chat and the parent shows the latest reply
    // inline — every other mode must never replace the message with a thread
    // reply, that would print the thread content over the original message.
    displayMessage() {
      const threadReply = this.isSlackStyle
        ? this.threadChat?.messages
            ?.filter(m => !m.hide)
            .reverse()[0]
        : null
      return threadReply || this.message
    },
    messageProfiles() {
      let profiles = this.$projects.profiles
        ?.filter(p => this.displayMessage.profiles?.includes(p.name)) || []
      const user = this.$project.users
        .find(({ username }) => username === this.displayMessage.user)
      return [user, ...profiles].filter(u => !!u)
    },
    images() {
      return this.message?.images?.map(i => {
        try {
          return JSON.parse(i)
        } catch {
          return { src: i }
        }
      })
    },
    messageContent() {
      return this.displayMessage.content
    },
    code_changes() {
      return this.improvementData?.code_changes
    },
    code_patches() {
      return this.improvementData?.code_patches
    },
    timeTaken() {
      if (!this.displayMessage.meta_data) return null
      let timeTaken = '--'
      if (this.displayMessage.meta_data?.time_taken) {
        const seconds = Math.floor(this.displayMessage.meta_data.time_taken)
        const baseMoment = moment({ h: 0, m: 0, s: 0, ms: 0 })
        timeTaken = baseMoment.add(seconds, 'seconds').format('mm:ss')
      } else if (this.displayMessage.meta_data?.start_time) {
        timeTaken = moment(this.displayMessage.meta_data?.start_time).fromNow()
      }
      return timeTaken ? `${this.displayMessage.meta_data.model} ${timeTaken}` : null
    },
    chatProject() {
      if (this.chat.project_id) {
        return this.$projects.allProjects.find(p => p.project_id === this.chat.project_id)
      }
      return this.$project
    },
    // Project the chat works in: `project_id` is the working one, falling back
    // to the owner for chats that never overrode it. Baseline a message is
    // compared against (see `isProjectOverridden`).
    chatProjectId() {
      return this.chat?.project_id || this.chat?.owner_project_id || null
    },
    // Project the rendered message is addressed to (Message.project_id).
    // `displayMessage` is used so a topic reply shows the project of the content
    // actually on screen.
    messageProjectId() {
      return this.displayMessage?.project_id || null
    },
    // Resolved project of the rendered message.
    messageProject() {
      const projectId = this.messageProjectId
      if (!projectId) return null
      return this.$projects.allProjectsById?.[projectId]
        || (this.$projects.allProjects || []).find(p => p.project_id === projectId)
        || null
    },
    // Project the code blocks of this message belong to.
    //
    // A message can target another project than the chat (`Message.project_id`)
    // and every block path is relative to THAT project: file writes must be
    // sent through its own API instance, otherwise the request carries the
    // chat's `codx_path` and the write fails.
    codeWriteProject() {
      return this.messageProject || this.chatProject || this.$project
    },
    // A message can target another project than the chat's. Without this the
    // files/code it mentions would be read in the chat's project context.
    isProjectOverridden() {
      const projectId = this.messageProjectId
      return !!projectId && projectId !== this.chatProjectId
    },
    // Tooltip / accessible text of the project badge
    projectLabel() {
      const project = this.messageProject
      if (!project) return 'This message targets another project'
      return project.abs_project_path
        ? `${project.project_name} · ${project.abs_project_path}`
        : project.project_name
    },
    chatFiles() {
      return this.chat.file_list
    },
    // Thread bound to this message. Read from the chats store directly:
    // `$projects.allChats` maps EVERY chat through `createProjectChat()`, so
    // evaluating it per rendered message cloned the whole project chat list
    // (O(messages × chats)) on each render.
    threadChat() {
      const messageId = this.message.doc_id
      if (!messageId) return null
      return this.$chats.allChats.find(c => c.message_id === messageId) || null
    },
    cancellationTokenId() {
      return this.displayMessage.meta_data?.cancellation_token_id
    },
    cancellationTime() {
      return this.displayMessage.meta_data?.cancelled_at
    },
    hasPRViewBlocks() {
      return this.$service.chat.hasCodeBlocksWithFilePaths(this.displayMessage)
    },
    hasCodeBlocksOrFiles() {
      return this.prViewCodeBlocks.length > 0 || this.displayMessage.files?.length > 0
    },
    prViewCodeBlocks() {
      return this.$service.chat.extractCodeBlocksFromMessage(this.displayMessage)
    },
    // Selection keys aligned 1:1 with the rendered code blocks (same order the
    // child views use). `null` marks a block that cannot be written to disk,
    // so the child skips its checkbox instead of shifting every other row.
    codeBlockKeys() {
      return (this.prViewCodeBlocks || []).map((block, index) => {
        const path = this.blockPath(block)
        return path ? `${path}#${index}` : null
      })
    },
    // Only the blocks that can actually be persisted
    selectableCodeBlocks() {
      return (this.prViewCodeBlocks || [])
        .map((block, index) => {
          const path = this.blockPath(block)
          if (!path) return null
          return {
            key: `${path}#${index}`,
            index,
            path,
            name: path.split('/').reverse()[0],
            block
          }
        })
        .filter(Boolean)
    },
    // Toolbar is visible in the Files view AND the Review (PR) view
    showCodeBlockSelection() {
      return (this.showFileView || this.showPRView) &&
        !this.srcView &&
        !this.showDiff &&
        !this.showAttachments &&
        this.selectableCodeBlocks.length > 0
    },
    allCodeBlocksSelected() {
      return this.selectableCodeBlocks.length > 0 &&
        this.selectedCodeBlockKeys.length === this.selectableCodeBlocks.length
    },
    someCodeBlocksSelected() {
      return this.selectedCodeBlockKeys.length > 0 && !this.allCodeBlocksSelected
    },
    toolEventCount() {
      const toolEvents = this.message?.tool_events
      if (Array.isArray(toolEvents)) {
        return toolEvents.length
      }
      return this.message?.tool_event ? 1 : 0
    },
    lifecycleEventCount() {
      const lifecycleEvents = this.message?.lifecycle_events
      if (Array.isArray(lifecycleEvents)) {
        return lifecycleEvents.length
      }
      return this.message?.lifecycle_event ? 1 : 0
    },
    hasEvents() {
      return this.toolEventCount > 0
    },
    attachmentCount() {
      return this.message?.attachments?.length || 0
    },
    hasAttachments() {
      return this.attachmentCount > 0
    },
    eventCount() {
      return this.toolEventCount + this.attachmentCount
    },
    isMessageSeen() {
      const currentUsername = this.$user?.username
      if (!currentUsername) return false
      return (this.message.read_by || []).includes(currentUsername)
    }
  },
  watch: {
    message() {
      this.loadThreadChat()
      this.resetSeenTracking()
    },
    'message.content': function() {
      this.extractImprovementData()
    },
    isDone() {
      if (this.isDone && !this.isMyMessage && this.isFocused && !this.isMessageSeen) {
        this.startSeenTracking()
      } else if (!this.isDone) {
        this.stopProgressTracking()
      }
    },
    // Drop stale selections when the code block set changes (e.g. streaming)
    selectableCodeBlocks() {
      const validKeys = this.selectableCodeBlocks.map(({ key }) => key)
      this.selectedCodeBlockKeys = this.selectedCodeBlockKeys.filter(key => validKeys.includes(key))
    }
  },
  methods: {
    formatDate(date) {
      return moment(date).format('DD/MMM HH:mm')
    },
    extractImprovementData() {
      this.improvementData = null
      if (this.displayMessage.content?.startsWith('```json')) {
        try {
          const lines = this.displayMessage.content.split('\n')
          const jsBlock = lines.slice(1, lines.length - 1).join('\n')
          this.improvementData = JSON.parse(jsBlock)
        } catch (ex) {
          console.error('Failed to parse improvement data', ex)
        }
      }
    },
    copyTextToClipboard(text) {
      this.$ui.copyTextToClipboard(text)
    },
    onMessageCopy(ev) {
      const text = window.getSelection().toString()
      if (text) {
        this.copyTextToClipboard(text)
        ev.preventDefault()
      }
    },
    getSelectionPosition() {
      const selection = window.getSelection()
      if (selection.rangeCount === 0) return { top: 0, left: 0 }
      const range = selection.getRangeAt(0)
      const rect = range.getBoundingClientRect()
      return {
        top: Math.max(10, rect.top + window.scrollY - 60),
        left: rect.left
      }
    },
    onContentMouseUp() {
      function getSelectedHTML() {
        const selection = window.getSelection()
        if (selection.rangeCount > 0) {
          const range = selection.getRangeAt(0)
          const clonedContent = range.cloneContents()
          const div = document.createElement('div')
          div.appendChild(clonedContent)
          return div.innerHTML
        }
        return ""
      }

      const selectedText = getSelectedHTML()
      if (selectedText.length > 0) {
        this.selectedText = selectedText
        this.showSelectionMenu = true
      } else {
        this.showSelectionMenu = false
      }
    },
    onSelectionCopy(text) {
      this.copyTextToClipboard(text)
    },
    onSelectionCreateSubtask(content) {
      this.$emit('sub-task', { content })
    },
    onSelectionSearchFiles({ query }) {
      this.$emit('search-files', { query, fromSelection: true })
    },
    onCloseSelectionMenu() {
      this.showSelectionMenu = false
    },
    toggleSrcView() {
      this.srcView = !this.srcView
      if (this.srcView) {
        this.showDiff = false
        this.showPRView = false
        this.showFileView = false
        this.showAttachments = false
      }
    },
    toggleShowDiff() {
      this.showDiff = !this.showDiff
      if (this.showDiff) {
        this.srcView = false
        this.showPRView = false
        this.showFileView = false
        this.showAttachments = false
      }
    },
    toggleFileView() {
      this.showFileView = !this.showFileView
      if (this.showFileView) {
        this.srcView = false
        this.showDiff = false
        this.showPRView = false
        this.showAttachments = false
      }
    },
    // ─────────────────────────────────────────────────────────────
    // Code block selection / bulk save
    // ─────────────────────────────────────────────────────────────
    // extractCodeBlocks() returns camelCase `filePath`. Keeping the legacy
    // snake_case/path fallbacks makes this resilient to extractor changes.
    blockPath(block) {
      return block?.filePath || block?.file_path || block?.path || null
    },
    isCodeBlockSelected(key) {
      return this.selectedCodeBlockKeys.includes(key)
    },
    toggleCodeBlockSelection(key) {
      if (!key) return
      const index = this.selectedCodeBlockKeys.indexOf(key)
      if (index >= 0) {
        this.selectedCodeBlockKeys.splice(index, 1)
      } else {
        this.selectedCodeBlockKeys.push(key)
      }
      this.codeBlockSaveStatus = null
    },
    // "All" toggle: selects every selectable block of this message at once
    toggleSelectAllCodeBlocks(checked) {
      this.selectedCodeBlockKeys = checked
        ? this.selectableCodeBlocks.map(({ key }) => key)
        : []
      this.codeBlockSaveStatus = null
    },
    clearCodeBlockSelection() {
      this.selectedCodeBlockKeys = []
      this.codeBlockSaveStatus = null
    },
    // Returns { path, content } or null when the block is not self-contained
    resolveCodeBlockFile(block) {
      const path = this.blockPath(block)
      const content = block?.content ?? block?.code
      if (!path || typeof content !== 'string') return null
      return { path, content }
    },
    async saveSelectedCodeBlocks() {
      if (this.savingCodeBlocks) return
      const selected = this.selectableCodeBlocks
        .filter(({ key }) => this.selectedCodeBlockKeys.includes(key))
      if (!selected.length) return

      this.savingCodeBlocks = true
      this.codeBlockSaveStatus = null

      // The blocks belong to the project THIS message targets, not necessarily
      // to the chat's one (see `codeWriteProject`).
      const writeProject = this.codeWriteProject

      try {
        const resolved = selected
          .map(item => item.file || this.resolveCodeBlockFile(item.block))
        const api = writeProject?.$api
        const canBulkWrite = resolved.every(file => !!file) && !!api?.files?.writeMultiple

        if (canBulkWrite) {
          // Two blocks may target the same file — last one wins, as the
          // backend writes them sequentially.
          const byPath = new Map()
          resolved.forEach(file => byPath.set(file.path, file))
          const res = await api.files.writeMultiple([...byPath.values()])
          // Backend contract: { written, failed: [{ path, error }], ... }
          this.applyCodeBlockSaveResult(selected, res?.failed || [])
        } else {
          // No bulk endpoint available (or content not resolvable): replay the
          // existing single-file flow, which expects { file, content }.
          selected.forEach((item, ix) => {
            const file = resolved[ix]
            if (file) {
              this.$emit('save-file', {
                file: file.path,
                content: file.content,
                project: writeProject
              })
            } else {
              this.$emit('save-file', { ...item.block, project: writeProject })
            }
          })
          this.selectedCodeBlockKeys = []
          this.codeBlockSaveStatus = {
            text: `${selected.length} file${selected.length > 1 ? 's' : ''} sent to save`
          }
        }
      } catch (ex) {
        console.error('Failed to save selected code blocks', ex)
        this.codeBlockSaveStatus = { text: 'Error saving selected files', error: true }
      } finally {
        this.savingCodeBlocks = false
      }
    },
    applyCodeBlockSaveResult(selected, failed = []) {
      const failedPaths = failed
        .map(entry => entry?.path)
        .filter(Boolean)
      const savedKeys = selected
        .filter(({ path }) => !failedPaths.includes(path))
        .map(({ key }) => key)

      // Only clear successful ones — failed files stay selected for a retry
      this.selectedCodeBlockKeys = this.selectedCodeBlockKeys
        .filter(key => !savedKeys.includes(key))

      if (failed.length) {
        this.codeBlockSaveStatus = {
          text: `${failed.length} of ${selected.length} failed`,
          error: true
        }
      } else {
        this.codeBlockSaveStatus = {
          text: `${savedKeys.length} file${savedKeys.length > 1 ? 's' : ''} saved`
        }
      }
    },
    togglePRView() {
      this.showPRView = !this.showPRView
      if (this.showPRView) {
        this.srcView = false
        this.showDiff = false
        this.showFileView = false
        this.showAttachments = false
        this.loadActiveBranch()
      }
    },
    toggleAttachmentsView() {
      this.showAttachments = !this.showAttachments
      if (this.showAttachments) {
        this.srcView = false
        this.showDiff = false
        this.showFileView = false
        this.showPRView = false
      }
    },
    onRemove() {
      if (this.isRemove) {
        this.$emit('remove')
      } else {
        this.isRemove = true
      }
    },
    confirmRemove() {
      this.isRemove = true
      this.$emit('remove')
    },
    copyMessageToClipboard() {
      this.copyTextToClipboard(this.displayMessage.content)
    },
    async applyPatch(patch) {
      patch.working = true
      try {
        const code_changes = this.code_changes.filter(cc => cc.file_path === patch.file_path)
        await this.$projects.codeImprovePatch({
          chat: this.chat,
          code_generator: { code_changes, code_patches: [patch] }
        })
        patch.res = { info: 'Patch sent' }
      } catch {
        patch.res = { error: 'Error applying patch' }
      }
      delete patch.working
    },
    onGenerateCode(codeBlockInfo) {
      this.$emit('generate-code', codeBlockInfo)
    },
    openFile(file) {
      this.$emit('preview-file', file)
    },
    onAttachmentUpdated({ index, attachment }) {
      const message = this.displayMessage
      if (!message?.attachments) return
      message.attachments.splice(index, 1, attachment)
      this.$emit('update-attachment', { message, index, attachment })
    },
    openThread() {
      this.$chats.setActiveChat(this.threadChat)
    },
    // Hydrate the thread chat behind this message.
    //
    // This runs on every render of the entry (created + message watcher), so it
    // must NOT write to the store once the thread is loaded: `reloadChat()`
    // always replaced the chat object, and a chat write re-derives every board
    // column, card and unread badge — opening a chat with N threaded messages
    // therefore produced N full rebuilds of the sprint board.
    //
    // `loadUninitialized()` is the correct call here: it fetches the thread only
    // when its history is not loaded yet (chats list/search returns summaries)
    // and is a plain no-op afterwards.
    loadThreadChat() {
      if (!this.threadChat) return null
      return this.$storex.chats.loadUninitialized(this.threadChat)
    },
    runAgents() {
      this.$emit('run-agents', this.message)
    },
    async cancelMessage() {
      const tokenId = this.cancellationTokenId
      if (!tokenId) return
      try {
        await this.$storex.api.chats.cancelMessage(tokenId)
      } catch (ex) {
        console.error('Failed to cancel message', ex)
      }
    },
    async loadActiveBranch() {
      if (this.branchLoading) return
      this.branchLoading = true
      try {
        const repoInfo = await this.chatProject.$api.repo.info()
        this.activeBranch = repoInfo?.active_branch
      } catch (ex) {
        console.error('Failed to load active branch', ex)
        this.activeBranch = null
      } finally {
        this.branchLoading = false
      }
    },
    copyChapterMarkdown(chapter, fullContent) {
      this.copyTextToClipboard(fullContent)
    },
    createTaskFromChapter(chapter, fullContent) {
      this.$emit('sub-task', { content: fullContent, title: chapter.title })
    },
    onCopyChapter(chapterData) {
      this.copyTextToClipboard(chapterData.content)
    },
    onCreateTask(taskData) {
      this.$emit('sub-task', { content: taskData.content, title: taskData.title })
    },
    // The events/tools panel is rendered INLINE inside this component (see the
    // <ChatMessageEvents> block under the header). We still notify the parent
    // which message was toggled so it can own the `eventsOpen` flag.
    toggleEventsPanel() {
      this.$emit('show-events', this.message)
    },
    onBlockEdited(data) {
      const { blockHash, originalContent, newContent, block } = data
      const updatedContent = this.replaceBlockInContent(
        this.displayMessage.content,
        originalContent,
        newContent
      )

      this.$emit('edited', {
        ...this.message,
        content: updatedContent
      })
    },
    replaceBlockInContent(fullContent, originalBlock, newBlock) {
      return fullContent.replace(originalBlock, newBlock)
    },
    setupIntersectionObserver() {
      if (!this.$refs.seenProgressBar || this.intersectionObserver) return

      const options = {
        root: null,
        rootMargin: '0px',
        threshold: 0.5
      }

      this.intersectionObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            this.onMessageFocus()
          } else {
            this.onMessageBlur()
          }
        })
      }, options)

      this.intersectionObserver.observe(this.$refs.seenProgressBar)
    },
    onMessageFocus() {
      if (!this.isMyMessage && this.isDone) {
        this.isFocused = true
        if (this.isDone && !this.isMyMessage && !this.isMessageSeen) {
          this.startSeenTracking()
        }
      }
    },
    onMessageBlur() {
      if (!this.isMyMessage && this.isDone) {
        this.isFocused = false
        this.stopProgressTracking()
      }
    },
    startSeenTracking() {
      if (this.hasSeen || this.isMessageSeen || !this.isDone) return
      this.seenProgressValue = 0

      const startTime = Date.now()

      this.progressInterval = setInterval(() => {
        const elapsed = Date.now() - startTime
        this.seenProgressValue = (elapsed / this.seenDuration) * 100

        if (elapsed >= this.seenDuration) {
          this.stopProgressTracking()
          this.submitMessageSeen()
        }
      }, 30)
    },
    stopProgressTracking() {
      if (this.progressInterval) {
        clearInterval(this.progressInterval)
        this.progressInterval = null
      }
      this.seenProgressValue = 0
    },
    async submitMessageSeen() {
      try {
        const currentUsername = this.$user?.username
        if (!currentUsername) return

        const chatId = this.chat?.doc_id || this.chat?.id
        const messageId = this.message?.doc_id || this.message?.id

        if (!chatId || !messageId) {
          console.error('Missing chat_id or message_id', { chatId, messageId })
          return
        }

        const readByList = this.message.read_by || []
        if (readByList.includes(currentUsername)) {
          this.hasSeen = true
          return
        }

        await this.$storex.api.chats.markMessageAsSeen({
          chat_id: chatId,
          message_id: messageId,
          username: currentUsername
        })
        this.hasSeen = true
        this.message.read_by = [...(this.message.read_by || []), currentUsername]
      } catch (ex) {
        console.error('Failed to mark message as seen', ex)
      }
    },
    resetSeenTracking() {
      this.hasSeen = false
      this.isFocused = false
      this.stopProgressTracking()
    },
    async toggleUnseenStatus() {
      if (this.unseenToggling) return
      this.unseenToggling = true

      try {
        const chatId = this.chat?.doc_id || this.chat?.id
        const messageId = this.message?.doc_id || this.message?.id
        const currentUsername = this.$user?.username

        if (!chatId || !messageId || !currentUsername) {
          console.error('Missing required IDs', { chatId, messageId, currentUsername })
          return
        }

        if (this.isMessageSeen) {
          await this.$storex.api.chats.unmarkMessageAsSeen({
            chat_id: chatId,
            message_id: messageId,
            username: currentUsername
          })
          this.message.read_by = this.message.read_by.filter(u => u !== currentUsername)
          this.hasSeen = false
          this.stopProgressTracking()
        } else {
          await this.$storex.api.chats.markMessageAsSeen({
            chat_id: chatId,
            message_id: messageId,
            username: currentUsername
          })
          this.message.read_by = [...(this.message.read_by || []), currentUsername]
          this.hasSeen = true
        }
      } catch (ex) {
        console.error('Failed to toggle message seen status', ex)
      } finally {
        this.unseenToggling = false
      }
    }
  },
  mounted() {
    this.collapsed = this.isCollapsed || this.displayMessage.hide
    this.extractImprovementData()
    this.resetSeenTracking()
    this.setupIntersectionObserver()
  },
  beforeUnmount() {
    this.stopProgressTracking()
    if (this.intersectionObserver) {
      this.intersectionObserver.disconnect()
    }
  }
}
</script>