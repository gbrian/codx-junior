<script setup>
import Markdown from './Markdown.vue'
import moment from 'moment'
import { CodeDiff } from 'v-code-diff'
import ChatIcon from './chat/ChatIcon.vue'
import Document from './document/Document.vue'
import ProfileAvatar from './profile/ProfileAvatar.vue'
import Editor from './monaco/Editor.vue'
</script>

<template>
  <div
    class="group chat-entry relative"
    :class="[
      displayMessage.hide ? 'opacity-60 border-l-2 border-warning' : '',
      editting ? 'border border-dashed border-warning' : '',
      !isDone ? 'border border-dashed border-sky-800' : '',
      displayMessage.is_answer ? 'bg-success/10 border border-dashed border-success' : '',
      isTopic ? 'border-l bg-info/5 border-info/50' : ''
    ]"
  >
    <!-- Mobile header -->
    <div class="flex items-center gap-2">
      <div class="flex -space-x-1 shrink-0">
        <div
          v-for="profile in messageProfiles"
          :key="profile.name"
          class="tooltip tooltip-right"
          :data-tip="profile.name || profile.username"
        >
          <ProfileAvatar :profile="profile" width="7" />
        </div>
      </div>

      <div class="flex flex-col min-w-0 flex-1">
        <div class="flex items-center gap-1 flex-wrap">
          <span class="text-xs font-bold truncate">
            {{ messageProfiles[0]?.name || messageProfiles[0]?.username || 'Unknown' }}
          </span>
          <span class="badge badge-xs badge-warning" v-if="displayMessage.hide">
            <i class="fa-solid fa-box-archive mr-1"></i>Archived
          </span>
          <span class="badge badge-xs badge-error" v-if="cancellationTime">Cancelled</span>
          <div class="badge badge-xs badge-success gap-1" v-if="displayMessage.is_answer">
            <ChatIcon mode="answer" />Knowledge
          </div>
          <div class="badge badge-xs badge-info badge-outline gap-1" v-if="isTopic">
            <ChatIcon mode="topic" />Topic
          </div>
        </div>
        <div class="flex items-center gap-1 text-xs text-base-content/50">
          <span>{{ formatDate(displayMessage.updated_at) }}</span>
          <span v-if="timeTaken" class="truncate">· {{ timeTaken }}</span>
        </div>
      </div>

      <!-- Ellipsis menu trigger -->
      <button
        class="btn btn-circle btn-xs btn-ghost shrink-0"
        @click="mobileActionsOpen = true"
        v-if="menuLess !== true"
      >
        <i class="fa-solid fa-ellipsis-vertical"></i>
      </button>
    </div>

    <!-- Progress -->
    <progress class="progress w-full h-1" v-if="!isDone"></progress>

    <!-- Think block -->
    <div v-if="displayMessage.think" class="mx-3 mb-1">
      <div
        class="alert alert-info py-2 text-xs click flex gap-2 items-start"
        @click="displayMessage.full_think = !displayMessage.full_think"
      >
        <i class="fa-solid fa-brain mt-0.5 shrink-0"></i>
        <span class="line-clamp-2">{{ thinkText }}</span>
      </div>
    </div>

    <!-- Skeleton -->
    <div
      class="mx-3 mb-2 flex flex-col gap-3 bg-base-100 rounded-xl p-3"
      v-if="!displayMessage.content && !displayMessage.think"
    >
      <div class="flex items-center gap-3">
        <div class="skeleton h-8 w-8 rounded-full shrink-0"></div>
        <div class="skeleton h-4 w-24"></div>
      </div>
      <div class="skeleton h-24 w-full rounded-lg"></div>
    </div>

    <!-- Content -->
    <div
      class=""
      :class="isCollapsed ? 'h-12 overflow-hidden' : 'h-fit'"
      @copy.stop="onMessageCopy"
    >
      <!-- Editor: model-value + emit to keep editing state in ChatEntry -->
      <div v-if="editting" class="mb-2">
        <Editor
          class="h-64 overflow-auto rounded-xl"
          language="markdown"
          :model-value="editting"
          @update:modelValue="$emit('update:editting', $event)"
        />
        <div class="flex gap-2 mt-2 justify-end">
          <button class="btn btn-sm btn-success" @click="$emit('save-editting')">
            <i class="fa-solid fa-check"></i> Save
          </button>
          <button class="btn btn-sm btn-error" @click="$emit('cancel-editting')">
            <i class="fa-solid fa-xmark"></i> Cancel
          </button>
        </div>
      </div>

      <pre v-if="srcView" class="text-xs overflow-auto rounded-lg bg-base-200 p-2">{{ displayMessage.content }}</pre>

      <Document
        v-if="!showDiff && !editting && !srcView && !code_patches && !isWord"
        :content="messageContent"
        :files="chatFiles"
        :project="chatProject"
        :chat="chat"
        :loading="!message.done"
        :mentionList="mentionList"
        @generate-code="$emit('generate-code', $event)"
        @reload-file="$emit('reload-file', { file: $event, message })"
        @open-file="$emit('open-file', $event)"
        @save-file="$emit('save-file', $event)"
        @add-file="$emit('add-file', $event)"
        @edit-message="$emit('edit-message', $event)"
        @sub-task="$emit('sub-task', $event)"
      />

      <div class="alert alert-error text-xs mt-1" v-if="displayMessage.error">
        {{ displayMessage.error }}
      </div>

      <CodeDiff
        v-if="showDiff"
        :new-string="displayMessage.diffMessage.content"
        :old-string="messageContent"
        theme="dark"
      />

      <div v-if="code_patches" class="flex flex-col gap-2 mt-2">
        <div
          class="rounded-xl bg-base-200 p-3 flex flex-col gap-1"
          v-for="patch in code_patches"
          :key="patch.file_path"
        >
          <div class="text-xs font-bold text-primary truncate">
            {{ patch.file_path.replace($project.abs_project_path, '') }}
          </div>
          <div class="text-xs">{{ patch.description }}</div>
          <Markdown :text="'```diff\n' + patch.patch + '\n```'" />
          <div class="flex justify-end">
            <button class="btn btn-sm btn-warning" :disabled="patch.working" @click="$emit('apply-patch', patch)">
              <span class="loading loading-spinner loading-xs" v-if="patch.working"></span>
              Apply changes
            </button>
          </div>
          <div v-if="patch.res">
            <div class="text-xs text-error" v-if="patch.res.error">{{ patch.res.error }}</div>
            <div class="text-xs text-success" v-else>Patch applied</div>
          </div>
        </div>
      </div>

      <div v-if="images?.length" class="flex gap-2 mt-2 overflow-x-auto pb-1">
        <div
          v-for="image in images"
          :key="image.src"
          class="shrink-0 flex flex-col items-center click"
          @click="$emit('image', image)"
        >
          <div
            class="w-16 h-16 rounded-lg border bg-contain bg-no-repeat bg-center"
            :style="`background-image: url(${image.src})`"
          ></div>
          <p class="badge badge-xs mt-1" v-if="image.alt">{{ image.alt.slice(0, 10) }}</p>
        </div>
      </div>

      <div class="flex flex-col gap-1 mt-2" v-if="displayMessage.files?.length">
        <div class="text-xs font-bold text-base-content/60">Linked files</div>
        <div
          v-for="file in displayMessage.files"
          :key="file"
          class="flex items-center gap-2 rounded-lg bg-base-200 px-2 py-1"
        >
          <i class="fa-solid fa-file-arrow-up text-primary click" @click.stop="$emit('add-file-to-chat', file)"></i>
          <span class="text-xs flex-1 truncate click hover:underline" @click="$emit('open-file', file)">
            {{ file.split('/').reverse()[0] }}
          </span>
          <i class="fa-regular fa-circle-xmark text-error click" @click.stop="$emit('remove-file', file)"></i>
        </div>
      </div>
    </div>

    <!-- Thread link -->
    <div
      v-if="threadChat"
      class="mx-3 mb-2 flex items-center gap-1 text-xs text-info click"
      @click="$emit('open-thread')"
    >
      <ChatIcon :mode="threadChat.mode" />
      <span class="underline">View thread</span>
    </div>

    <!-- Mobile Bottom Sheet -->
    <Teleport to="body">
      <div
        v-if="mobileActionsOpen"
        class="fixed inset-0 z-50 flex flex-col justify-end"
      >
        <div class="absolute inset-0 bg-black/50" @click="mobileActionsOpen = false"></div>
        <div class="relative bg-base-200 rounded-t-2xl shadow-2xl max-h-[80vh] overflow-y-auto">
          <!-- Handle -->
          <div class="flex justify-center pt-3 pb-1 sticky top-0 bg-base-200">
            <div class="w-10 h-1 rounded-full bg-base-content/30"></div>
          </div>

          <!-- Sheet header -->
          <div class="px-4 pb-3 border-b border-base-300 flex items-center gap-2">
            <div class="flex -space-x-1">
              <ProfileAvatar v-for="p in messageProfiles" :key="p.name" :profile="p" width="7" />
            </div>
            <div class="flex-1 min-w-0">
              <div class="text-sm font-bold truncate">
                {{ messageProfiles[0]?.name || messageProfiles[0]?.username }}
              </div>
              <div class="text-xs text-base-content/50">{{ formatDate(displayMessage.updated_at) }}</div>
            </div>
          </div>

          <!-- Actions list -->
          <div class="flex flex-col divide-y divide-base-300 pb-8">
            <button
              v-if="!isDone && cancellationTokenId"
              class="flex items-center gap-3 px-5 py-4 text-error active:bg-base-300 w-full text-left"
              @click="$emit('cancel-message'); mobileActionsOpen = false"
            >
              <span class="loading loading-spinner loading-sm"></span>
              <span class="font-medium">Stop generation</span>
            </button>
            <button
              v-if="!editting"
              class="flex items-center gap-3 px-5 py-4 active:bg-base-300 w-full text-left"
              @click="$emit('thread', message); mobileActionsOpen = false"
            >
              <i class="fa-solid fa-comment-dots w-5 text-center"></i>
              <span class="font-medium">Open Thread</span>
            </button>
            <button
              v-if="!editting"
              class="flex items-center gap-3 px-5 py-4 active:bg-base-300 w-full text-left"
              @click="$emit('copy-message'); mobileActionsOpen = false"
            >
              <i class="fa-solid fa-copy w-5 text-center"></i>
              <span class="font-medium">Copy message</span>
            </button>
            <button
              v-if="!editting"
              class="flex items-center gap-3 px-5 py-4 text-success active:bg-base-300 w-full text-left"
              @click="$emit('answer', message); mobileActionsOpen = false"
            >
              <i class="fa-solid fa-check-double w-5 text-center"></i>
              <span class="font-medium">Mark as answer</span>
            </button>
            <button
              v-if="!editting"
              class="flex items-center gap-3 px-5 py-4 active:bg-base-300 w-full text-left"
              @click="$emit('run-agents', message); mobileActionsOpen = false"
            >
              <i class="fa-solid fa-people-group w-5 text-center"></i>
              <span class="font-medium">Run agents</span>
            </button>
            <button
              v-if="canEditMessage && !editting"
              class="flex items-center gap-3 px-5 py-4 active:bg-base-300 w-full text-left"
              @click="$emit('edit-message-click'); mobileActionsOpen = false"
            >
              <i class="fa-solid fa-pencil w-5 text-center"></i>
              <span class="font-medium">Edit message</span>
            </button>
            <button
              v-if="displayMessage.diffMessage && !editting"
              class="flex items-center gap-3 px-5 py-4 active:bg-base-300 w-full text-left"
              @click="$emit('toggle-show-diff'); mobileActionsOpen = false"
            >
              <i class="fa-regular fa-file-lines w-5 text-center"></i>
              <span class="font-medium">View diff</span>
            </button>
            <button
              v-if="isDone"
              class="flex items-center gap-3 px-5 py-4 active:bg-base-300 w-full text-left"
              @click="$emit('toggle-src-view'); mobileActionsOpen = false"
            >
              <i class="fa-solid fa-code w-5 text-center"></i>
              <span class="font-medium">View source</span>
            </button>
            <button
              v-if="isDone"
              class="flex items-center gap-3 px-5 py-4 text-warning active:bg-base-300 w-full text-left"
              @click="$emit('hide', message); mobileActionsOpen = false"
            >
              <i class="fa-solid fa-box-archive w-5 text-center"></i>
              <span class="font-medium">{{ displayMessage.hide ? 'Show' : 'Archive' }}</span>
            </button>
            <button
              class="flex items-center gap-3 px-5 py-4 text-error active:bg-base-300 w-full text-left"
              @click="$emit('confirm-remove'); mobileActionsOpen = false"
            >
              <i class="fa-solid fa-trash-can w-5 text-center"></i>
              <span class="font-medium">Delete</span>
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script>
export default {
  props: [
    'chat', 'message', 'mentionList', 'menu-less', 'usersList',
    'displayMessage', 'messageProfiles', 'chatFiles', 'chatProject',
    'messageContent', 'isDone', 'editting', 'srcView', 'showDiff',
    'timeTaken', 'thinkText', 'cancellationTokenId', 'cancellationTime',
    'canEditMessage', 'threadChat', 'isTopic', 'isWord', 'isCollapsed',
    'images', 'code_patches', 'menuLess'
  ],
  emits: [
    'generate-code', 'reload-file', 'open-file', 'save-file',
    'add-file', 'edit-message', 'sub-task', 'thread', 'hide',
    'remove', 'confirm-remove', 'answer', 'copy', 'add-file-to-chat',
    'remove-file', 'image', 'run-agents', 'edited',
    'cancel-message', 'copy-message', 'edit-message-click',
    'save-editting', 'cancel-editting', 'toggle-src-view',
    'toggle-show-diff', 'open-thread', 'message-copy', 'apply-patch',
    'update:editting'
  ],
  data() {
    return {
      mobileActionsOpen: false
    }
  },
  methods: {
    formatDate(date) {
      return moment(date).format('DD/MMM HH:mm:ss')
    },
    onMessageCopy(ev) {
      const text = window.getSelection().toString()
      if (text) {
        this.$emit('message-copy', ev)
        ev.preventDefault()
      }
    }
  }
}
</script>