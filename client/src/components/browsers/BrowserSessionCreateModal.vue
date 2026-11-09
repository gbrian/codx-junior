<script setup>
import BrowserFolderPicker from './BrowserFolderPicker.vue'
import ComputerImageLibrary from './ComputerImageLibrary.vue'
</script>

<template>
  <!--
    New computer session settings.

    One dialog creates every kind of shared machine: a Linux desktop container,
    a Windows/macOS VM, a remote VNC/SSH machine or the original Chromium
    browser session. Container kinds decide their project mounts here because
    they become bind mounts; VMs see the project root at /shared (Z: on
    Windows) and remote machines have no mounts.
  -->
  <modal close title="New computer session" @close="close">
    <div class="flex flex-col gap-5 md:w-[34rem]">

      <!-- ── Machine ──────────────────────────────────────────────────── -->
      <section class="flex flex-col gap-2">
        <h3 class="text-[11px] font-semibold uppercase tracking-wide text-base-content/40">
          Machine
        </h3>
        <fieldset class="grid grid-cols-1 gap-1.5 sm:grid-cols-2">
          <legend class="sr-only">What kind of computer should the AI share?</legend>
          <label
            v-for="option in kindOptions"
            :key="option.value"
            class="flex cursor-pointer items-start gap-2 rounded-lg border p-2.5 transition-colors duration-150"
            :class="form.kind === option.value
              ? 'border-primary/50 bg-primary/5'
              : 'border-base-content/10 hover:border-base-content/20 hover:bg-base-200/50'"
          >
            <input
              v-model="form.kind"
              type="radio"
              name="computer-kind"
              :value="option.value"
              class="radio radio-xs radio-primary mt-0.5"
            />
            <span class="min-w-0 flex-1">
              <span class="flex items-center gap-1.5 text-xs font-semibold">
                <i :class="option.icon" aria-hidden="true"></i>
                {{ option.label }}
              </span>
              <span class="mt-0.5 block text-[11px] leading-snug text-base-content/50">
                {{ option.description }}
              </span>
            </span>
          </label>
        </fieldset>
        <p
          v-if="isVm"
          class="flex items-start gap-1.5 rounded-lg bg-warning/10 px-2 py-1.5 text-[11px] text-warning"
        >
          <i class="fa-solid fa-triangle-exclamation mt-0.5" aria-hidden="true"></i>
          <span>VMs need KVM (/dev/kvm) on the Docker host. The first boot installs the OS (several GB and minutes).</span>
        </p>
        <p
          v-else-if="isRemote"
          class="flex items-start gap-1.5 rounded-lg bg-info/10 px-2 py-1.5 text-[11px] text-info"
        >
          <i class="fa-solid fa-circle-info mt-0.5" aria-hidden="true"></i>
          <span>Enable VNC/Screen Sharing on the remote machine. Add SSH to let the AI run shell commands (builds, tests, adb).</span>
        </p>
      </section>

      <!-- ── Session ──────────────────────────────────────────────────── -->
      <section class="flex flex-col gap-3">
        <h3 class="text-[11px] font-semibold uppercase tracking-wide text-base-content/40">
          Session
        </h3>

        <label class="flex flex-col gap-1">
          <span class="text-xs font-semibold">
            Name
            <span class="text-error" aria-hidden="true">*</span>
          </span>
          <input
            ref="nameInput"
            v-model="form.name"
            type="text"
            class="input input-sm input-bordered w-full"
            :placeholder="namePlaceholder"
            aria-required="true"
            @keyup.enter="create"
          />
        </label>

        <label v-if="isBrowser" class="flex flex-col gap-1">
          <span class="text-xs font-semibold">Start URL</span>
          <input
            v-model="form.url"
            type="url"
            class="input input-sm input-bordered w-full"
            placeholder="https://example.com"
            @keyup.enter="create"
          />
        </label>

        <label v-if="isVm" class="flex flex-col gap-1">
          <span class="text-xs font-semibold">OS release</span>
          <select v-model="form.osVersion" class="select select-sm select-bordered w-full">
            <option v-for="option in osVersions" :key="option.value" :value="option.value">
              {{ option.label }}
            </option>
          </select>
        </label>
      </section>

      <!-- ── VM resources ────────────────────────────────────────────── -->
      <section v-if="isVm" class="flex flex-col gap-2">
        <h3 class="text-[11px] font-semibold uppercase tracking-wide text-base-content/40">
          VM resources
        </h3>

        <div class="grid grid-cols-2 gap-2">
          <label class="flex flex-col gap-1">
            <span class="text-xs font-semibold">vCPUs</span>
            <input
              v-model.number="form.cpuCores"
              type="number"
              min="1"
              max="128"
              step="1"
              class="input input-sm input-bordered w-full"
              placeholder="default (4)"
            />
          </label>
          <label class="flex flex-col gap-1">
            <span class="text-xs font-semibold">RAM</span>
            <input
              v-model="form.ramSize"
              type="text"
              class="input input-sm input-bordered w-full font-mono text-[11px]"
              placeholder="default (8G)"
              spellcheck="false"
            />
          </label>
        </div>

        <label class="flex flex-col gap-1">
          <span class="text-xs font-semibold">Disk size</span>
          <input
            v-model="form.diskSize"
            type="text"
            class="input input-sm input-bordered w-full font-mono text-[11px]"
            :placeholder="form.kind === 'macos' ? 'default (128G)' : 'default (64G)'"
            spellcheck="false"
          />
        </label>
        <div class="flex flex-wrap items-center gap-1">
          <span class="text-[11px] text-base-content/50">Presets:</span>
          <button
            v-for="preset in ['64G', '128G', '256G']"
            :key="preset"
            type="button"
            class="btn btn-xs"
            :class="form.diskSize === preset ? 'btn-primary' : 'btn-ghost'"
            @click="form.diskSize = preset"
          >{{ preset }}</button>
        </div>

        <p
          v-if="form.kind === 'macos'"
          class="flex items-start gap-1.5 rounded-lg bg-info/10 px-2 py-1.5 text-[11px] text-info"
        >
          <i class="fa-solid fa-circle-info mt-0.5 flex-shrink-0" aria-hidden="true"></i>
          <span>
            macOS installs need room for the system plus your tools. The default is
            128G; 64G can work for a minimal install, and 256G is safer for
            Xcode/Simulator. The disk can be expanded later from the session settings
            and a restart. On first boot, erase the VirtIO disk in Disk Utility before
            reinstalling macOS.
          </span>
        </p>
      </section>

      <!-- ── Desktop image library ───────────────────────────────────── -->
      <section v-if="isLinux" class="flex flex-col gap-2">
        <div class="flex items-center gap-2">
          <h3 class="flex-1 text-[11px] font-semibold uppercase tracking-wide text-base-content/40">
            Desktop image
          </h3>
          <button
            v-if="form.image || selectedLibraryImage"
            type="button"
            class="btn btn-ghost btn-xs gap-1 text-base-content/50"
            @click="clearLibraryImage"
          >
            <i class="fa-solid fa-eraser"></i> Use default
          </button>
        </div>
        <button
          type="button"
          class="flex w-full items-center gap-2.5 rounded-xl border border-base-content/10 bg-base-100 p-2 text-left transition-colors hover:border-primary/40 hover:bg-base-200/50"
          @click="showImageLibrary = true"
        >
          <span class="flex h-14 w-20 flex-shrink-0 items-center justify-center overflow-hidden rounded-lg bg-base-300/50">
            <img
              v-if="imageSelectionPreview"
              :src="imageSelectionPreview"
              alt=""
              class="h-full w-full object-cover"
            />
            <i v-else class="fa-solid fa-desktop text-lg text-base-content/30"></i>
          </span>
          <span class="min-w-0 flex-1">
            <span class="block truncate text-xs font-semibold">{{ imageSelectionTitle }}</span>
            <span class="block truncate text-[11px] text-base-content/50">{{ imageSelectionMeta }}</span>
            <span class="mt-0.5 flex items-center gap-1 text-[10px] text-primary">
              <i class="fa-solid fa-images"></i> Browse Kasmweb and LinuxServer images
            </span>
          </span>
          <i class="fa-solid fa-chevron-right text-[10px] text-base-content/30"></i>
        </button>
      </section>

      <!-- ── Remote machine ──────────────────────────────────────────── -->
      <section v-if="isRemote" class="flex flex-col gap-3">
        <h3 class="text-[11px] font-semibold uppercase tracking-wide text-base-content/40">
          Remote connection
        </h3>
        <div class="grid grid-cols-[1fr_6rem] gap-2">
          <label class="flex flex-col gap-1">
            <span class="text-xs font-semibold">VNC host <span class="text-error">*</span></span>
            <input v-model="form.vncHost" type="text" class="input input-sm input-bordered w-full"
              placeholder="mac-mini.local or 192.168.1.20" />
          </label>
          <label class="flex flex-col gap-1">
            <span class="text-xs font-semibold">VNC port</span>
            <input v-model.number="form.vncPort" type="number" class="input input-sm input-bordered w-full" />
          </label>
        </div>
        <label class="flex flex-col gap-1">
          <span class="text-xs font-semibold">VNC password</span>
          <input v-model="form.vncPassword" type="password" autocomplete="new-password"
            class="input input-sm input-bordered w-full" placeholder="optional, stored server-side" />
        </label>
        <div class="grid grid-cols-[1fr_1fr] gap-2">
          <label class="flex flex-col gap-1">
            <span class="text-xs font-semibold">SSH host</span>
            <input v-model="form.sshHost" type="text" class="input input-sm input-bordered w-full"
              placeholder="same host by default" />
          </label>
          <label class="flex flex-col gap-1">
            <span class="text-xs font-semibold">SSH user</span>
            <input v-model="form.sshUser" type="text" class="input input-sm input-bordered w-full"
              placeholder="osx" />
          </label>
        </div>
        <div class="grid grid-cols-[6rem_1fr] gap-2">
          <label class="flex flex-col gap-1">
            <span class="text-xs font-semibold">SSH port</span>
            <input v-model.number="form.sshPort" type="number" class="input input-sm input-bordered w-full" />
          </label>
          <label class="flex flex-col gap-1">
            <span class="text-xs font-semibold">SSH key path (API host)</span>
            <input v-model="form.sshKeyPath" type="text" class="input input-sm input-bordered w-full"
              placeholder="~/.ssh/id_ed25519" />
          </label>
        </div>
        <label class="flex flex-col gap-1">
          <span class="text-xs font-semibold">SSH password (alternative to a key)</span>
          <input v-model="form.sshPassword" type="password" autocomplete="new-password"
            class="input input-sm input-bordered w-full" placeholder="requires sshpass in the API image" />
        </label>
      </section>

      <!-- ── Project folders ─────────────────────────────────────────── -->
      <section v-if="!isRemote" class="flex flex-col gap-2">
        <div class="flex items-center gap-2">
          <h3 class="flex-1 text-[11px] font-semibold uppercase tracking-wide text-base-content/40">
            Project files
          </h3>
          <span
            class="badge badge-sm"
            :class="mounts.length ? 'badge-primary badge-outline' : 'badge-ghost'"
          >
            {{ mounts.length }} mounted
          </span>
        </div>

        <p
          v-if="isVm"
          class="flex items-start gap-1.5 rounded-lg bg-base-200/60 px-2 py-1.5 text-[11px] text-base-content/60"
        >
          <i class="fa-solid fa-folder-tree mt-0.5" aria-hidden="true"></i>
          <span>
            The project root is shared as
            <code class="font-mono">{{ form.kind === 'windows' ? 'Z:\\' : '/shared' }}</code>.
            Files saved there appear in the project on the host.
          </span>
        </p>

        <fieldset v-if="!isVm" class="flex flex-col gap-1.5">
          <legend class="sr-only">What can the computer see of this project?</legend>

          <label
            v-for="option in modeOptions"
            :key="option.value"
            class="flex cursor-pointer items-start gap-2.5 rounded-lg border p-2.5 transition-colors duration-150"
            :class="form.mode === option.value
              ? 'border-primary/50 bg-primary/5'
              : 'border-base-content/10 hover:border-base-content/20 hover:bg-base-200/50'"
          >
            <input
              v-model="form.mode"
              type="radio"
              name="browser-share-mode"
              :value="option.value"
              class="radio radio-xs radio-primary mt-0.5"
            />
            <span class="min-w-0 flex-1">
              <span class="block text-xs font-semibold">{{ option.label }}</span>
              <span class="block text-[11px] leading-snug text-base-content/50">
                {{ option.description }}
              </span>
              <span
                v-if="option.path"
                class="mt-0.5 block truncate font-mono text-[10px] text-base-content/40"
                :title="option.path"
              >{{ option.path }}</span>
            </span>
          </label>
        </fieldset>

        <!-- Read-only: applies to every mounted folder -->
        <label
          v-if="!isVm && form.mode !== 'none'"
          class="flex cursor-pointer items-start gap-2.5 rounded-lg border border-base-content/10 p-2.5 transition-colors duration-150 hover:bg-base-200/50"
        >
          <input v-model="form.readonly" type="checkbox" class="toggle toggle-sm toggle-primary mt-0.5" />
          <span class="min-w-0 flex-1">
            <span class="block text-xs font-semibold">Read-only mounts</span>
            <span class="block text-[11px] leading-snug text-base-content/50">
              The browser can open the folders but cannot change them. Downloads then
              get their own folder instead of being written inside them.
            </span>
          </span>
        </label>

        <!-- Selected folders -->
        <div
          v-if="!isVm && form.mode === 'selected'"
          class="flex flex-col gap-2 rounded-lg border border-base-content/10 p-2"
        >
          <p
            v-if="!form.folders.length"
            class="flex items-start gap-1.5 rounded-md bg-warning/10 px-2 py-1.5 text-[11px] text-warning"
          >
            <i class="fa-solid fa-triangle-exclamation mt-0.5" aria-hidden="true"></i>
            <span>No folder selected: the browser will not see any project file.</span>
          </p>

          <ul v-else class="flex flex-col gap-1">
            <li
              v-for="folder in form.folders"
              :key="folder"
              class="flex items-center gap-2 rounded-md bg-base-200/70 px-2 py-1"
            >
              <i class="fa-solid fa-folder text-warning text-[11px]" aria-hidden="true"></i>
              <span class="min-w-0 flex-1 truncate font-mono text-[11px]" :title="folder">
                {{ folder }}
              </span>
              <button
                type="button"
                class="btn btn-ghost btn-xs btn-circle text-base-content/40 hover:text-error"
                :aria-label="`Remove folder ${folder}`"
                @click="removeFolder(folder)"
              >
                <i class="fa-solid fa-xmark text-[10px]"></i>
              </button>
            </li>
          </ul>

          <button
            type="button"
            class="btn btn-outline btn-sm justify-start gap-2"
            @click="picker = 'folders'"
          >
            <i class="fa-solid fa-folder-plus"></i>
            Add folders
          </button>
        </div>

        <!-- Resolved mapping: what the browser will actually see -->
        <div
          v-if="mounts.length"
          class="flex flex-col gap-0.5 rounded-lg border border-base-content/10 bg-base-200/40 p-2"
        >
          <span class="text-[10px] font-semibold uppercase tracking-wide text-base-content/40">
            Mounts inside the browser
          </span>
          <code
            v-for="mount in mounts"
            :key="mount.mount"
            class="truncate font-mono text-[10px] text-base-content/60"
            :title="`file://${mount.mount}`"
          >file://{{ mount.mount }}</code>
        </div>
      </section>

      <!-- ── Downloads ───────────────────────────────────────────────── -->
      <section v-if="!isRemote" class="flex flex-col gap-2">
        <h3 class="text-[11px] font-semibold uppercase tracking-wide text-base-content/40">
          Downloads
        </h3>

        <fieldset class="flex flex-col gap-1.5">
          <legend class="sr-only">Where are the browser downloads saved?</legend>

          <label
            class="flex cursor-pointer items-start gap-2.5 rounded-lg border p-2.5 transition-colors duration-150"
            :class="form.downloads === 'default'
              ? 'border-primary/50 bg-primary/5'
              : 'border-base-content/10 hover:border-base-content/20 hover:bg-base-200/50'"
          >
            <input
              v-model="form.downloads"
              type="radio"
              name="browser-downloads-mode"
              value="default"
              class="radio radio-xs radio-primary mt-0.5"
            />
            <span class="min-w-0 flex-1">
              <span class="block text-xs font-semibold">Session folder</span>
              <span class="block font-mono text-[10px] text-base-content/50">
                {{ isVm ? '.codx/computer_downloads/<session id>' : '.codx/browser_downloads/<session id>' }}
              </span>
            </span>
          </label>

          <label
            class="flex cursor-pointer items-start gap-2.5 rounded-lg border p-2.5 transition-colors duration-150"
            :class="[
              form.downloads === 'custom'
                ? 'border-primary/50 bg-primary/5'
                : 'border-base-content/10 hover:border-base-content/20 hover:bg-base-200/50',
              form.mode === 'none' ? 'cursor-not-allowed opacity-50' : ''
            ]"
          >
            <input
              v-model="form.downloads"
              type="radio"
              name="browser-downloads-mode"
              value="custom"
              class="radio radio-xs radio-primary mt-0.5"
              :disabled="form.mode === 'none'"
            />
            <span class="min-w-0 flex-1">
              <span class="block text-xs font-semibold">Project folder</span>
              <span class="block text-[11px] leading-snug text-base-content/50">
                {{ form.mode === 'none'
                  ? 'Needs a project folder to be mounted first.'
                  : 'Pick any project folder: downloads become project files.' }}
              </span>
            </span>
          </label>
        </fieldset>

        <div v-if="form.downloads === 'custom'" class="flex items-center gap-2">
          <button
            type="button"
            class="btn btn-sm flex-1 justify-start gap-2 overflow-hidden"
            :aria-label="form.downloadsFolder
              ? `Change downloads folder (${form.downloadsFolder})`
              : 'Choose downloads folder'"
            @click="picker = 'downloads'"
          >
            <i class="fa-solid fa-folder-open flex-shrink-0"></i>
            <span class="truncate font-mono text-[11px]">
              {{ form.downloadsFolder || 'Choose a folder…' }}
            </span>
          </button>
          <button
            v-if="form.downloadsFolder"
            type="button"
            class="btn btn-ghost btn-sm btn-circle text-base-content/50"
            aria-label="Clear downloads folder"
            @click="form.downloadsFolder = ''"
          >
            <i class="fa-solid fa-eraser"></i>
          </button>
        </div>

        <!-- Resolved downloads location -->
        <p
          class="flex items-start gap-1.5 rounded-lg bg-base-200/60 px-2 py-1.5 text-[10px] text-base-content/60"
        >
          <i class="fa-solid fa-hard-drive mt-0.5 flex-shrink-0" aria-hidden="true"></i>
          <span class="min-w-0 break-all">
            <span class="font-mono">{{ downloads.path }}</span>
            <span class="block text-base-content/40">{{ downloads.note }}</span>
          </span>
        </p>
      </section>

      <!-- ── Advanced settings ───────────────────────────────────────── -->
      <section v-if="!isRemote" class="flex flex-col gap-2">
        <details
          ref="advancedDetails"
          class="group rounded-lg border border-base-content/10 bg-base-200/30"
        >
          <summary class="flex cursor-pointer list-none items-center gap-2 p-2.5">
            <i class="fa-solid fa-sliders text-[11px] text-base-content/50" aria-hidden="true"></i>
            <span class="flex-1 text-[11px] font-semibold uppercase tracking-wide text-base-content/40">
              Advanced settings
            </span>
            <span class="badge badge-sm badge-ghost max-w-[11rem] truncate">{{ advancedSummary }}</span>
            <i
              class="fa-solid fa-chevron-down text-[9px] text-base-content/40 transition-transform duration-150 group-open:rotate-180"
              aria-hidden="true"
            ></i>
          </summary>

          <div class="flex flex-col gap-3 border-t border-base-content/10 p-2.5">
            <!-- Image -->
            <label class="flex flex-col gap-1">
              <span class="text-xs font-semibold">Custom image override</span>
              <input
                v-model="form.image"
                type="text"
                class="input input-sm input-bordered w-full font-mono text-[11px]"
                :placeholder="defaultImage"
                spellcheck="false"
              />
              <span class="text-[10px] leading-snug text-base-content/50">
                Leave empty to use the Desktop image selection above, or
                <code class="font-mono">{{ defaultImage }}</code>. A custom image must
                keep a live view and the X11/control channel of this machine kind.
              </span>
            </label>

            <!-- CPU + RAM (browser/Linux; VMs have a dedicated section) -->
            <div v-if="!isVm" class="grid grid-cols-2 gap-2">
              <label class="flex flex-col gap-1">
                <span class="text-xs font-semibold">vCPUs</span>
                <input
                  v-model.number="form.cpuCores"
                  type="number"
                  min="1"
                  max="128"
                  step="1"
                  class="input input-sm input-bordered w-full"
                  placeholder="host default"
                />
              </label>
              <label class="flex flex-col gap-1">
                <span class="text-xs font-semibold">RAM</span>
                <input
                  v-model="form.ramSize"
                  type="text"
                  class="input input-sm input-bordered w-full font-mono text-[11px]"
                  placeholder="e.g. 2G"
                  spellcheck="false"
                />
              </label>
            </div>

            <!-- Desktop size (browser/Linux) -->
            <div v-if="!isVm" class="grid grid-cols-2 gap-2">
              <label class="flex flex-col gap-1">
                <span class="text-xs font-semibold">Desktop width</span>
                <input
                  v-model.number="form.desktopWidth"
                  type="number"
                  min="640"
                  max="7680"
                  step="1"
                  class="input input-sm input-bordered w-full"
                  placeholder="1920"
                />
              </label>
              <label class="flex flex-col gap-1">
                <span class="text-xs font-semibold">Desktop height</span>
                <input
                  v-model.number="form.desktopHeight"
                  type="number"
                  min="480"
                  max="4320"
                  step="1"
                  class="input input-sm input-bordered w-full"
                  placeholder="1080"
                />
              </label>
            </div>

            <!-- Shared memory (browser/Linux) -->
            <label v-if="!isVm" class="flex flex-col gap-1">
              <span class="text-xs font-semibold">Shared memory</span>
              <input
                v-model="form.shmSize"
                type="text"
                class="input input-sm input-bordered w-full font-mono text-[11px]"
                placeholder="default (2G)"
                spellcheck="false"
              />
              <span class="text-[10px] leading-snug text-base-content/50">
                Docker <code class="font-mono">/dev/shm</code> size. Browsers and desktop apps
                may crash with the default when many tabs/apps are open.
              </span>
            </label>

            <!-- Extra image environment -->
            <label class="flex flex-col gap-1">
              <span class="text-xs font-semibold">Environment variables</span>
              <textarea
                v-model="form.env"
                rows="3"
                class="textarea textarea-bordered textarea-sm w-full font-mono text-[11px]"
                placeholder="KEY=VALUE (one per line)&#10;e.g. LC_ALL=en_US.UTF-8"
                spellcheck="false"
              ></textarea>
              <span class="text-[10px] leading-snug text-base-content/50">
                Passed to the image. Names managed by codx-junior (SUBFOLDER, VERSION,
                RAM_SIZE, USERNAME…) cannot be overridden.
              </span>
            </label>

            <button
              type="button"
              class="btn btn-ghost btn-xs self-start gap-1 text-base-content/50"
              @click="resetAdvanced"
            >
              <i class="fa-solid fa-rotate-left" aria-hidden="true"></i>
              Reset advanced settings
            </button>
          </div>
        </details>
      </section>

      <!-- Error -->
      <p
        v-if="error"
        role="alert"
        class="flex items-start gap-1.5 rounded-lg bg-error/10 px-2.5 py-2 text-[11px] text-error"
      >
        <i class="fa-solid fa-circle-exclamation mt-0.5 flex-shrink-0" aria-hidden="true"></i>
        <span class="min-w-0 break-words">{{ error }}</span>
      </p>
    </div>

    <!-- ── Actions ──────────────────────────────────────────────────── -->
    <template #footer>
      <button type="button" class="btn btn-sm btn-ghost" :disabled="creating" @click="close">
        Cancel
      </button>
      <button
        type="button"
        class="btn btn-sm btn-primary gap-1"
        :disabled="!canCreate"
        @click="create"
      >
        <i
          class="fa-solid"
          :class="creating ? 'fa-spinner animate-spin' : 'fa-plus'"
          aria-hidden="true"
        ></i>
        {{ creating ? 'Creating…' : 'Create session' }}
      </button>
    </template>

    <Teleport to="body">
      <ComputerImageLibrary
        v-if="showImageLibrary"
        :kind="form.kind"
        :model-value="form.image"
        @select="onImageSelected"
        @close="showImageLibrary = false"
      />
    </Teleport>

    <!--
      The folder browser is teleported to <body>: the dialog box carries an
      `animate-in` transform, which would otherwise become the containing block
      of the picker's `position: fixed` overlay and clip it inside the dialog.
    -->
    <Teleport to="body">
      <BrowserFolderPicker
        v-if="picker"
        :mode="picker === 'downloads' ? 'single' : 'multiple'"
        :model-value="picker === 'downloads'
          ? (form.downloadsFolder ? [form.downloadsFolder] : [])
          : form.folders"
        :title="picker === 'downloads' ? 'Downloads folder' : 'Project folders'"
        @select="onPickerSelect"
        @close="picker = null"
      />
    </Teleport>
  </modal>
</template>

<script>
// Fresh form state. A function (not an object) so every open starts clean even
// when the component instance is reused.
const emptyForm = () => ({
  name: '',
  url: 'http://example.com',
  // `linux` | `windows` | `macos` | `remote` | `browser`
  kind: 'linux',
  osVersion: '11',
  // Remote machine connection (VNC for the screen, SSH for the shell)
  vncHost: '',
  vncPort: 5900,
  vncPassword: '',
  sshHost: '',
  sshPort: 22,
  sshUser: '',
  sshKeyPath: '',
  sshPassword: '',
  // `whole` | `selected` | `none` — mirrors share_project + share_folders
  mode: 'whole',
  folders: [],
  readonly: false,
  // `default` | `custom` — mirrors downloads_folder
  downloads: 'default',
  downloadsFolder: '',
  // Advanced settings: image + resources + extra image environment.
  image: '',
  cpuCores: '',
  ramSize: '',
  diskSize: '',
  shmSize: '',
  desktopWidth: '',
  desktopHeight: '',
  // One KEY=VALUE per line
  env: ''
})

//: Project folder holding the downloads when no specific folder is chosen.
const DOWNLOADS_FOLDER = '.codx/browser_downloads'
const COMPUTER_DOWNLOADS_FOLDER = '.codx/computer_downloads'

export default {
  name: 'BrowserSessionCreateModal',
  components: { BrowserFolderPicker, ComputerImageLibrary },
  data() {
    return {
      form: emptyForm(),
      creating: false,
      error: null,
      // Open folder picker: null | 'folders' | 'downloads'
      picker: null,
      showImageLibrary: false,
      selectedLibraryImage: null
    }
  },
  watch: {
    'form.kind'(kind, oldKind) {
      if (kind === 'windows') this.form.osVersion = '11'
      if (kind === 'macos') this.form.osVersion = '15'
      if (oldKind && oldKind !== kind) {
        // An image selected for one machine kind must never leak into another
        // (e.g. a VM image into a Linux desktop). Advanced users can still type
        // a custom image after switching.
        this.selectedLibraryImage = null
        this.form.image = ''
      }
    },
    'form.image'(value) {
      // A manual edit in Advanced settings invalidates the library selection.
      if (this.selectedLibraryImage && value !== this.selectedLibraryImage.image) {
        this.selectedLibraryImage = null
      }
    }
  },
  computed: {
    isBrowser() {
      return this.form.kind === 'browser'
    },
    isLinux() {
      return this.form.kind === 'linux'
    },
    isVm() {
      return this.form.kind === 'windows' || this.form.kind === 'macos'
    },
    isRemote() {
      return this.form.kind === 'remote'
    },
    /** Image the backend uses when the advanced override stays empty. */
    defaultImage() {
      return {
        browser: 'lscr.io/linuxserver/chromium:latest',
        linux: 'lscr.io/linuxserver/webtop:debian-kde',
        windows: 'dockurr/windows',
        macos: 'dockurr/macos'
      }[this.form.kind] || ''
    },
    /** Library selection (or the default image) shown in the main dialog. */
    imageSelectionTitle() {
      if (this.selectedLibraryImage) return this.selectedLibraryImage.name
      if (this.form.image.trim()) return 'Custom image'
      return 'Default LinuxServer webtop'
    },
    imageSelectionMeta() {
      if (this.selectedLibraryImage) {
        const image = this.selectedLibraryImage
        if (image.provider === 'saved') {
          const transport = {
            kasmvnc: 'KasmVNC',
            selkies: 'Selkies',
            screenshot: 'Screenshot'
          }[image.live_view] || 'Screenshot'
          const author = image.created_by ? ` · by ${image.created_by}` : ''
          return `Saved computer · ${transport}${author}`
        }
        const provider = {
          kasmweb: 'Kasmweb',
          linuxserver: 'LinuxServer.io',
          custom: 'Custom image'
        }[image.provider] || image.provider || 'Custom image'
        const transport = {
          kasmvnc: 'KasmVNC',
          selkies: 'Selkies',
          screenshot: 'Screenshot'
        }[image.live_view] || 'Screenshot'
        return `${provider} · ${transport} · ${image.tag || 'latest'}`
      }
      if (this.form.image.trim()) return this.form.image.trim()
      return `${this.defaultImage} · Selkies`
    },
    imageSelectionPreview() {
      return this.selectedLibraryImage?.screenshot_url || this.selectedLibraryImage?.icon_url || ''
    },
    /** Short "what changed" badge shown while the section is collapsed. */
    advancedSummary() {
      const parts = []
      if (this.form.cpuCores) parts.push(`${this.form.cpuCores} vCPU`)
      if (this.form.ramSize.trim()) parts.push(`${this.form.ramSize.trim()} RAM`)
      if (this.isVm && this.form.diskSize.trim()) parts.push(`${this.form.diskSize.trim()} disk`)
      if (this.selectedLibraryImage) parts.push(this.selectedLibraryImage.name)
      else if (this.form.image.trim()) parts.push('custom image')
      const envCount = String(this.form.env || '')
        .split('\n')
        .filter(line => line.trim() && !line.trim().startsWith('#'))
        .length
      if (envCount) parts.push(`${envCount} env`)
      return parts.length ? parts.join(' · ') : 'defaults'
    },
    kindOptions() {
      return [
        {
          value: 'linux',
          icon: 'fa-brands fa-linux',
          label: 'Linux desktop',
          description: 'A full Ubuntu/KDE desktop in a container. Best default: shell + apps work out of the box.'
        },
        {
          value: 'windows',
          icon: 'fa-brands fa-windows',
          label: 'Windows VM',
          description: 'Windows 11/10 in a KVM VM. Needs /dev/kvm on the Docker host; first boot installs Windows.'
        },
        {
          value: 'macos',
          icon: 'fa-brands fa-apple',
          label: 'macOS VM',
          description: 'macOS in a KVM VM (Apple hardware only, per Apple EULA). Xcode/Simulator need a real Mac.'
        },
        {
          value: 'remote',
          icon: 'fa-solid fa-network-wired',
          label: 'Remote machine',
          description: 'An existing Mac/Windows/Linux box reachable over VNC, with optional SSH for shell commands.'
        },
        {
          value: 'browser',
          icon: 'fa-solid fa-compass',
          label: 'Browser only',
          description: 'The original Chromium co-browsing session (DOM tools, downloads, scripts).'
        }
      ]
    },
    osVersions() {
      return this.form.kind === 'windows'
        ? [
            { value: '11', label: 'Windows 11 Pro' },
            { value: '10', label: 'Windows 10 Pro' },
            { value: '11l', label: 'Windows 11 LTSC (smaller)' },
            { value: '2022', label: 'Windows Server 2022' }
          ]
        : [
            { value: '15', label: 'macOS 15 Sequoia' },
            { value: '14', label: 'macOS 14 Sonoma' },
            { value: '13', label: 'macOS 13 Ventura' }
          ]
    },
    namePlaceholder() {
      return {
        linux: 'Linux dev box',
        windows: 'Windows test machine',
        macos: 'Mac build machine',
        remote: 'Office Mac mini',
        browser: 'Invoice hunt'
      }[this.form.kind] || 'Computer session'
    },
    projectName() {
      return this.$project?.project_name ||
        this.$storex.projects.activeProject?.project_name ||
        'project'
    },
    /** Mirror of the backend rule that builds `/home/<project_name>`. */
    projectFolderName() {
      const name = String(this.projectName || '')
        .replace(/[^A-Za-z0-9._-]+/g, '-')
        .replace(/^[-._]+|[-._]+$/g, '')
      return name || 'project'
    },
    homePath() {
      return `/home/${this.projectFolderName}`
    },
    /** Container mounts the backend will create for the current selection. */
    mounts() {
      if (this.isRemote) return []
      if (this.isVm) {
        return [{ folder: '', mount: '/shared' }]
      }
      if (this.form.mode === 'none') return []
      if (this.form.mode === 'whole') {
        return [{ folder: '', mount: this.homePath }]
      }
      return this.form.folders.map(folder => ({
        folder,
        mount: `${this.homePath}/${folder}`
      }))
    },
    modeOptions() {
      return [
        {
          value: 'whole',
          label: 'Whole project',
          description: 'Every file of the project is visible to the browser.',
          path: this.homePath
        },
        {
          value: 'selected',
          label: 'Selected folders',
          description: 'Mount only the folders the browser needs.',
          path: ''
        },
        {
          value: 'none',
          label: 'No project access',
          description: 'Isolated browser: no project file can be read or written.',
          path: ''
        }
      ]
    },
    /** Project-relative folder receiving the downloads ('' = default). */
    downloadsFolderPath() {
      if (this.form.downloads !== 'custom') return ''
      return this.normalizeFolder(this.form.downloadsFolder)
    },
    /**
     * Where the downloads end up inside the container.
     *
     * Same rule as the backend: the folder is used through an existing mount
     * when it is inside a *writable* one, otherwise it gets its own bind and
     * is exposed at `/downloads`.
     */
    downloads() {
      if (this.isVm) {
        const folder = this.downloadsFolderPath || `${COMPUTER_DOWNLOADS_FOLDER}/<session id>`
        const relative = folder.replace(/^\/+|\/+$/g, '')
        return {
          path: this.form.kind === 'windows'
            ? `Z:\\${relative.replace(/\//g, '\\')}`
            : `/shared/${relative}`,
          note: 'The project root is shared with the VM; files saved here are project files.'
        }
      }
      if (this.form.mode === 'none') {
        return {
          path: '/downloads',
          note: 'Stored in the session folder on the server: no project file is created.'
        }
      }

      const folder = this.downloadsFolderPath || `${DOWNLOADS_FOLDER}/<session id>`
      if (this.form.readonly) {
        return {
          path: '/downloads',
          note: `Saved at ${folder}: the mounted folders are read-only.`
        }
      }

      const covering = this.coveringMount(this.downloadsFolderPath)
      if (!covering) {
        return {
          path: '/downloads',
          note: `Saved at ${folder}: outside the mounted folders.`
        }
      }
      const rest = this.downloadsFolderPath.slice(this.normalizeFolder(covering.folder).length)
      const suffix = rest.replace(/^\/+/, '')
      return {
        path: suffix ? `${covering.mount}/${suffix}` : covering.mount,
        note: 'Saved inside a mounted folder: the files are project files.'
      }
    },
    canCreate() {
      if (!this.form.name.trim() || this.creating) return false
      if (this.isRemote && !this.form.vncHost.trim()) return false
      return true
    }
  },
  methods: {
    normalizeFolder(value) {
      return String(value || '')
        .replace(/\\/g, '/')
        .replace(/\/{2,}/g, '/')
        .replace(/^\/+|\/+$/g, '')
    },
    /** True when *folder* is *parent* or lives inside it. */
    isInside(folder, parent) {
      const path = this.normalizeFolder(folder)
      const base = this.normalizeFolder(parent)
      if (!base) return true
      return path === base || path.startsWith(`${base}/`)
    },
    /** Innermost mount holding *folder* (null when nothing covers it). */
    coveringMount(folder) {
      const path = this.normalizeFolder(folder)
      let best = null
      this.mounts.forEach((mount) => {
        if (!this.isInside(path, mount.folder)) return
        if (!best || this.normalizeFolder(mount.folder).length > this.normalizeFolder(best.folder).length) {
          best = mount
        }
      })
      return best
    },
    removeFolder(folder) {
      this.form.folders = this.form.folders.filter(item => item !== folder)
    },
    /** Merge a picker selection, dropping folders already covered by a parent. */
    mergeFolders(selection) {
      const merged = [...new Set([...this.form.folders, ...selection])]
        .map(folder => this.normalizeFolder(folder))
        .filter(Boolean)
      const kept = merged.filter(folder =>
        !merged.some(other => other !== folder && this.isInside(folder, other))
      )
      this.form.folders = kept.sort((a, b) => a.localeCompare(b))
    },
    onPickerSelect(selection) {
      if (this.picker === 'downloads') {
        const chosen = (selection || [])[0] || ''
        this.form.downloadsFolder = this.normalizeFolder(chosen)
        this.form.downloads = 'custom'
      } else if ((selection || []).includes('')) {
        // Picking the project root is the "whole project" mode
        this.form.mode = 'whole'
        this.form.folders = []
      } else {
        this.mergeFolders(selection || [])
      }
      this.picker = null
    },
    /** Parse the advanced environment textarea into an object. */
    parseEnv() {
      const env = {}
      const lines = String(this.form.env || '').split('\n')
      lines.forEach((raw, index) => {
        const line = raw.trim()
        if (!line || line.startsWith('#')) return
        const separator = line.indexOf('=')
        if (separator <= 0) {
          throw new Error(`Environment variable on line ${index + 1} must use KEY=VALUE`)
        }
        const key = line.slice(0, separator).trim()
        if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(key)) {
          throw new Error(`Invalid environment variable name '${key}' (line ${index + 1})`)
        }
        env[key] = line.slice(separator + 1).trim()
      })
      return env
    },
    /** Validate the advanced form; returns an error message or null. */
    validateAdvanced() {
      if (this.isRemote) return null
      const sizePattern = /^\d+(?:\.\d+)?\s*[KMGT](?:i?b)?$/i
      const sizeError = (label, value, example) => {
        const text = String(value || '').trim()
        if (!text) return null
        return sizePattern.test(text)
          ? null
          : `${label} must be a number with a unit, for example ${example}.`
      }
      const errors = [
        sizeError('RAM', this.form.ramSize, '8G'),
        sizeError('Disk size', this.isVm ? this.form.diskSize : '', '64G'),
        sizeError('Shared memory', this.isVm ? '' : this.form.shmSize, '2G')
      ].filter(Boolean)
      if (errors.length) return errors[0]

      if (this.form.cpuCores) {
        const cpus = Number(this.form.cpuCores)
        if (!Number.isInteger(cpus) || cpus < 1 || cpus > 128) {
          return 'vCPUs must be a whole number between 1 and 128.'
        }
      }
      if (!this.isVm) {
        const width = Number(this.form.desktopWidth)
        const height = Number(this.form.desktopHeight)
        if (this.form.desktopWidth && (!Number.isInteger(width) || width < 640 || width > 7680)) {
          return 'Desktop width must be a whole number between 640 and 7680.'
        }
        if (this.form.desktopHeight && (!Number.isInteger(height) || height < 480 || height > 4320)) {
          return 'Desktop height must be a whole number between 480 and 4320.'
        }
      }
      let env = {}
      try {
        env = this.parseEnv()
      } catch (error) {
        return error.message
      }
      if (Object.keys(env).length > 50) {
        return 'Use at most 50 environment variables.'
      }
      return null
    },
    onImageSelected(image) {
      this.selectedLibraryImage = image
      this.form.image = image?.image || ''
      this.showImageLibrary = false
    },
    clearLibraryImage() {
      this.selectedLibraryImage = null
      this.form.image = ''
    },
    resetAdvanced() {
      // The image is also edited by the library section above, but the reset
      // button sits next to the advanced override; clear it there.
      this.form.image = ''
      this.selectedLibraryImage = null
      this.form.shmSize = ''
      this.form.desktopWidth = ''
      this.form.desktopHeight = ''
      this.form.env = ''
      // VM CPU/RAM/disk have their own top-level section now: do not reset
      // them from the advanced panel. Browser/Linux CPU/RAM are still advanced.
      if (!this.isVm) {
        this.form.cpuCores = ''
        this.form.ramSize = ''
      }
    },
    /** Advanced fields sent to the backend (empty values stay null). */
    advancedPayload() {
      if (this.isRemote) return {}
      return {
        image: this.form.image.trim() || null,
        image_provider: this.selectedLibraryImage?.image_provider ||
          this.selectedLibraryImage?.provider || null,
        library_item_id: this.selectedLibraryImage?.library_item_id || null,
        cpu_cores: Number(this.form.cpuCores) || null,
        ram_size: this.form.ramSize.trim() || null,
        disk_size: this.isVm ? (this.form.diskSize.trim() || null) : null,
        shm_size: this.isVm ? null : (this.form.shmSize.trim() || null),
        extra_env: this.parseEnv(),
        desktop_width: this.isVm ? null : (Number(this.form.desktopWidth) || null),
        desktop_height: this.isVm ? null : (Number(this.form.desktopHeight) || null)
      }
    },
    errorMessage(error) {
      return error?.response?.data?.detail ||
        error?.message ||
        'Could not create the computer session'
    },
    async create() {
      if (!this.canCreate) return
      const advancedError = this.validateAdvanced()
      if (advancedError) {
        this.error = advancedError
        // VM CPU/RAM/disk live in their own section; only open the advanced
        // panel for errors in fields that are actually inside it.
        const vmResourceError = this.isVm && /(RAM|vCPUs|Disk size)/.test(advancedError)
        if (!vmResourceError && this.$refs.advancedDetails) {
          this.$refs.advancedDetails.open = true
        }
        return
      }
      this.creating = true
      this.error = null
      try {
        const session = await this.$storex.browsers.createSession({
          name: this.form.name.trim(),
          kind: this.form.kind,
          os_version: this.isVm ? this.form.osVersion : null,
          initial_url: this.isBrowser ? (this.form.url.trim() || null) : null,
          share_project: this.isRemote
            ? null
            : (this.isVm ? true : this.form.mode === 'whole'),
          share_folders: this.isVm || this.isRemote
            ? []
            : (this.form.mode === 'selected' ? [...this.form.folders] : []),
          readonly: this.isRemote ? null : !!this.form.readonly,
          downloads_folder: this.isRemote
            ? null
            : (this.form.downloads === 'custom' ? (this.form.downloadsFolder || null) : null),
          vnc_host: this.isRemote ? (this.form.vncHost.trim() || null) : null,
          vnc_port: this.isRemote ? Number(this.form.vncPort) || 5900 : null,
          vnc_password: this.isRemote ? (this.form.vncPassword || null) : null,
          ssh_host: this.isRemote ? (this.form.sshHost.trim() || null) : null,
          ssh_port: this.isRemote ? Number(this.form.sshPort) || 22 : null,
          ssh_user: this.isRemote ? (this.form.sshUser.trim() || null) : null,
          ssh_key_path: this.isRemote ? (this.form.sshKeyPath.trim() || null) : null,
          ssh_password: this.isRemote ? (this.form.sshPassword || null) : null,
          ...this.advancedPayload()
        })
        this.close()
        return session
      } catch (error) {
        console.error('[BrowserSessionCreateModal] Create failed:', error)
        this.error = this.errorMessage(error)
      } finally {
        this.creating = false
      }
    },
    /** ESC / backdrop: an open folder picker closes first, never both. */
    close() {
      if (this.picker) {
        this.picker = null
        return
      }
      this.$storex.browsers.toggleNewSessionForm(false)
    }
  },
  mounted() {
    // The standalone library browser can open this dialog with a card already
    // picked; apply it once so the form shows the image before the user types.
    const pendingImage = this.$storex.browsers.pendingLibraryImage
    if (pendingImage) {
      this.onImageSelected(pendingImage)
      this.$storex.browsers.clearPendingLibraryImage()
    }
    this.$nextTick(() => this.$refs.nameInput?.focus())
  }
}
</script>