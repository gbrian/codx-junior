<script setup>
import Iframe from '../Iframe.vue';
</script>

<template>
  <div class="w-full h-full ">
    <Iframe :url="adminUrl" v-if="adminUrl">

    </Iframe>
    <div class="flex flex-col gap-2 p-4" v-else>
      <h1 class="text-2xl font-bold mb-4">AI Settings</h1>
      <div class="overflow-x-auto">
        <table class="table w-full">
          <thead>
            <tr>
              <th>Name</th>
              <th>Provider</th>
              <th>API URL</th>
              <th>API Key</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr class="click" @click="editProvider(provider)" v-for="provider in aiProviders" :key="provider.name">
              <td>
                <button class="btn btn-xs btn-circle btn-ghost text-info"
                  @click.stop="navigateAdmin(provider)"
                  v-if="provider.admin_url"  
                >
                  <i class="fa-solid fa-link"></i>
                </button>
                {{ provider.name }}
              </td>
              <td>{{ provider.provider }}</td>
              <td class="w-20 overflow-hidden whitespace-nowrap text-ellipsis" :title="provider.api_url">{{ provider.api_url?.slice(0, 30) }}</td>
              <td class="w-20 overflow-hidden whitespace-nowrap text-ellipsis" :title="provider.api_key">{{ provider.api_key?.slice(0, 30) }}</td>
              <td class="flex gap-2">
                <button class="btn btn-xs btn-circle btn-ghost" @click.stop="editProvider(provider)">
                  <i class="fa-solid fa-pen-to-square"></i>
                </button>
                <button class="btn btn-xs btn-circle btn-ghost text-error" @click.stop="confirmDelete(provider)">
                  <i class="fa-solid fa-trash-can"></i>
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="flex justify-end">
        <button class="btn btn-sm mt-2" @click="editProvider({})">
          Add New
        </button>
      </div>

      <modal v-if="showDialog">
        <div>
          <div class="form-control">
            <label class="label">Provider Name</label>
            <input
              class="input input-bordered"
              v-model="currentProvider.name"
              placeholder="Provider Name"
            />
          </div>
          <div class="form-control">
            <label class="label">Provider Protocol</label>
            <input
              class="input input-bordered"
              v-model="currentProvider.provider"
              placeholder="Provider Protocol"
            />
          </div>
          <div class="form-control">
            <label class="label">API URL</label>
            <input
              class="input input-bordered overflow-hidden whitespace-nowrap text-ellipsis"
              v-model="currentProvider.api_url"
              placeholder="API URL"
            />
          </div>
          <div class="form-control">
            <label class="label">API Key</label>
            <input
              class="input input-bordered overflow-hidden whitespace-nowrap text-ellipsis"
              v-model="currentProvider.api_key"
              placeholder="API Key"
            />
          </div>
          <div class="form-control">
            <label class="label">Admin url</label>
            <input
              class="input input-bordered overflow-hidden whitespace-nowrap text-ellipsis"
              v-model="currentProvider.admin_url"
              placeholder="Admin url"
            />
          </div>
          <div class="modal-action">
            <button class="btn btn-primary" @click="saveProvider">
              Save
            </button>
            <button class="btn" @click="showDialog = false">
              Cancel
            </button>
          </div>
        </div>
      </modal>

      <modal v-if="showDeleteDialog">
        <div>
          <p>Are you sure you want to delete {{ providerToDelete.name }}?</p>
          <div class="modal-action">
            <button class="btn btn-error" @click="deleteProvider">
              Confirm
            </button>
            <button class="btn" @click="showDeleteDialog = false">Cancel</button>
          </div>
        </div>
      </modal>
    </div>
  </div>
</template>

<script>
export default {
  props: ['settings'],
  data() {
    return {
      showDialog: false,
      showDeleteDialog: false,
      currentProvider: {},
      providerToDelete: null,
      adminUrl: null
    }
  },
  computed: {
    aiProviders() {
      return this.settings.ai_providers
    }
  },
  methods: {
    editProvider(provider) {
      this.currentProvider = provider
      this.showDialog = true
    },
    saveProvider() {
      if (!this.aiProviders.find(p => p.name === this.currentProvider.name)) {
        this.aiProviders.push(this.currentProvider)
      }
      this.showDialog = false
      this.currentProvider = null
    },
    confirmDelete(provider) {
      this.providerToDelete = provider
      this.showDeleteDialog = true
    },
    deleteProvider() {
      const index = this.aiProviders.findIndex(
        p => p.name === this.providerToDelete.name
      )
      if (index !== -1) {
        this.aiProviders.splice(index, 1)
      }
      this.showDeleteDialog = false
    },
    navigateAdmin(provider) {
      this.adminUrl = provider.admin_url
    }
  }
}
</script>