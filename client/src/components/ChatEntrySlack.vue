<script setup>
import ChatIcon from './chat/ChatIcon.vue'
import Document from './document/Document.vue'
import ProfileAvatar from './profile/ProfileAvatar.vue'
import Editor from './monaco/Editor.vue'
</script>

<template>
  <div
    class="group chat-entry flex gap-2 items-start relative px-3 py-1 hover:bg-base-200/50 rounded-md"
    :class="[
      displayMessage.hide ? 'opacity-50 hover:opacity-100 border-l-2 border-warning' : '',
      !isDone && 'border border-dashed border-sky-800',
      editting && 'border border-dashed border-warning',
    ]"
  >
    <!-- Avatar column -->
    <div class="flex-shrink-0 pt-0.5 flex flex-col -space-y-1">
      <div class="avatar placeholder" v-for="profile in messageProfiles" :key="profile.name || profile.username">
        <ProfileAvatar :profile="profile" width="6" class="rounded-full" />
      </div>
    </div>

    <!-- Content column -->
    <div class="flex flex-col flex-1 min-w-0">
      <!-- Header row -->
      <div class="flex items-baseline gap-2 text-xs">
        <span class="font-bold text-base-content">
          {{ displayMessage.user }}
        </span>
        <span class="text-base-content/50 text-[10px]">
          {{ formatDate(displayMessage.updated_at) }}
        </span>
        <span v-if="timeTaken" class="text-base-content/40 text-[10px]">({{ timeTaken }})</span>
        <span class="badge badge-xs badge-error" v-if="cancellationTime">Cancelled</span>

        <!-- Action buttons, visible on hover -->
        <div class="opacity-0 group-hover:opacity-100 flex gap-1 items-center ml-auto" v-if="menuLess !== true">
          <button
            class="btn btn-xs btn-error tooltip tooltip-bottom"
            data-tip="Stop generation"
            @click="$emit('cancel-message')"
            v-if="!isDone && cancellationTokenId"
          >
            <span class="loading loading-xs"></span> Cancel...
          </button>
          <button class="btn btn-xs hover:btn-outline tooltip tooltip-bottom" data-tip="Thread"
            @click="$emit('thread', message)" v-if="!editting">
            <i class="fa-solid fa-comment-dots"></i>
          </button>
          <button class="btn btn-xs hover:btn-outline tooltip tooltip-bottom" data-tip="Copy message"
            @click="$emit('copy-message')" v-if="!editting">
            <i class="fa-solid fa-copy"></i>
          </button>
          <button v-if="canEditMessage && !editting" class="btn btn-xs hover:btn-outline tooltip tooltip-bottom"
            data-tip="Edit message" @click="$emit('edit-message-click')">
            <i class="fa-solid fa-pencil"></i>
          </button>
          <button v-if="editting" class="btn btn-xs btn-success" @click="$emit('save-editting')">Save</button>
          <button v-if="editting" class="btn btn-xs btn-error" @click="$emit('cancel-editting')">Cancel</button>
          <div class="dropdown dropdown-hover dropdown-end" v-if="!editting">
            <button tabindex="0" class="btn hover:btn-error btn-xs" @click="$emit('remove')">
              <i class="fa-solid fa-bars"></i>
            </button>
            <ul tabindex="0" class="dropdown-content menu rounded-box shadow w-32 p-2 bg-base-300 z-50">
              <li class="text-error">
                <a class="hover:underline" @click="$emit('confirm-remove')">
                  <i class="fa-solid fa-trash-can"></i> Delete
                </a>
              </li>
              <li class="text-warning" v-if="isDone">
                <a @click.stop="$emit('hide', message)" class="text-left tooltip tooltip-bottom click"
                  :data-tip="displayMessage.hide ? 'Click to add message to conversation' : 'Click to archive message from the conversation'">
                  <i class="fa-solid fa-box-archive"></i> {{ displayMessage.hide ? 'Show' : 'Archive' }}
                </a>
              </li>
              <li @click="$emit('toggle-src-view')" v-if="isDone">
                <a><i class="fa-solid fa-code"></i> Source</a>
              </li>
            </ul>
          </div>
        </div>
      </div>

      <!-- Progress bar while loading -->
      <progress class="progress w-full" v-if="!isDone"></progress>

      <!-- Think block -->
      <div v-if="displayMessage.think">
        <div class="alert click items-start text-xs" @click="displayMessage.full_think = !displayMessage.full_think">
          <i class="fa-solid fa-brain"></i>
          {{ thinkText }}
        </div>
      </div>

      <!-- Message body -->
      <div @copy.stop="$emit('message-copy', $event)" class="max-w-full text-sm text-base-content">
        <Editor class="h-[1024px] overflow-auto" language="markdown" v-model="edittingModel" v-if="editting" />
        <pre v-if="srcView">{{ displayMessage.content }}</pre>
        <Document
          :content="messageContent"
          :files="chatFiles"
          :project="chatProject"
          :chat="chat"
          :loading="!message.done"
          @generate-code="$emit('generate-code', $event)"
          @reload-file="$emit('reload-file', { file: $event, message })"
          @open-file="$emit('open-file', $event)"
          @save-file="$emit('save-file', $event)"
          @add-file="$emit('add-file', $event)"
          @edit-message="$emit('edit-message', $event)"
          @sub-task="$emit('sub-task', $event)"
          :mentionList="mentionList"
          v-if="!editting && !srcView"
        />
        <div class="alert alert-error text-xs" v-if="displayMessage.error">
          {{ displayMessage.error }}
        </div>
      </div>

      <!-- Thread badge -->
      <div class="mt-1" v-if="threadChat">
        <div class="badge badge-sm border-dashed badge-outline flex gap-1 cursor-pointer w-fit"
          @click="$emit('open-thread')">
          <ChatIcon :mode="threadChat.mode" /> Thread
        </div>
      </div>

      <!-- Linked files -->
      <div class="font-bold text-xs flex flex-col gap-2 mt-2" v-if="displayMessage.files?.length">
        Linked files:
        <div v-for="file in displayMessage.files" :key="file" :title="file" class="flex gap-2 items-center click">
          <div class="flex gap-2 click hover:underline" @click="$emit('open-file', file)">
            <div class="click tooltip tooltip-right" data-tip="Attach file" @click.stop="$emit('add-file-to-chat', file)">
              <i class="fa-solid fa-file-arrow-up"></i>
            </div>
            <div class="overflow-hidden">{{ file.split('/').reverse()[0] }}</div>
          </div>
          <div class="click hover:text-error" @click.stop="$emit('remove-file', file)">
            <i class="fa-regular fa-circle-xmark"></i>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  props: [
    'chat', 'message', 'displayMessage', 'messageProfiles', 'mentionList',
    'menuLess', 'threadChat', 'chatFiles', 'chatProject', 'messageContent',
    'isDone', 'editting', 'srcView', 'timeTaken', 'thinkText',
    'cancellationTokenId', 'cancellationTime', 'canEditMessage'
  ],
  emits: [
    'thread', 'hide', 'remove', 'confirm-remove', 'toggle-src-view',
    'cancel-message', 'copy-message', 'edit-message-click', 'save-editting',
    'cancel-editting', 'generate-code', 'reload-file', 'open-file',
    'save-file', 'add-file', 'edit-message', 'sub-task', 'open-thread',
    'add-file-to-chat', 'remove-file', 'message-copy'
  ],
  computed: {
    edittingModel: {
      get() { return this.editting },
      set(val) { this.$emit('update:editting', val) }
    },
    formatDate() {
      return (date) => this.$parent.formatDate ? this.$parent.formatDate(date) : date
    }
  },
  methods: {
    formatDate(date) {
      const moment = this.$parent?.formatDate
        ? { format: () => this.$parent.formatDate(date) }
        : null
      return moment?.format() || date
    }
  }
}
</script>