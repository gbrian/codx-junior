<script setup>
</script>
<template>
  <div class="w-full h-full flex flex-col gap-2 p-4">
    <h1 class="text-2xl font-bold mb-4">OAuth Settings</h1>
    <div class="grid grid-cols-1 grid-cols-1 gap-4">
      <div
        v-for="provider in computedProviders"
        :key="provider.name"
        class="click card border border-slate-300 bg-slate-800 text-white/80 p-4 shadow-sm flex flex-col justify-between"
        @click="editProvider(provider)"
      >
        <div class="overflow-hidden">
          <h2 class="font-bold text-lg text-primary">
            {{ provider.name }}
          </h2>
          <table class="w-full">
            <tr>
              <td>Client ID:</td>
              <td>{{ provider.client_id }}</td>
            </tr>
            <tr>
              <td>Secret:</td>
              <td>{{ provider.secret }}</td>
            </tr>
            <tr>
              <td>Callback URL:</td>
              <td>{{ location.origin + '/auth/' + provider.name }}</td>
            </tr>
          </table>
        </div>
        <div class="flex gap-2 mt-4">
          <button class="btn btn-xs btn-circle btn-outline" @click.stop="editProvider(provider)">
            <i class="fa-solid fa-pen-to-square"></i>
          </button>
          <button class="btn btn-xs btn-circle btn-outline text-error" @click.stop="confirmDelete(provider)">
            <i class="fa-solid fa-trash-can"></i>
          </button>
        </div>
      </div>
      <div class="card border-2 border-dashed border-base-300 p-4 flex justify-center items-center cursor-pointer" @click="editProvider(null)">
        <span class="text-gray-500">Add New Provider</span>
      </div>
    </div>

    <modal close="true" @close="showDialog = false" v-if="showDialog">
      <form class="flex flex-col gap-2" @submit.prevent="saveProvider">
        <div class="form-control">
          <span class="label">Provider Name</span>
          <input v-model="currentProvider.name" class="input input-bordered" placeholder="Provider Name" />
        </div>
        <div class="form-control">
          <span class="label">Client ID</span>
          <input v-model="currentProvider.client_id" class="input input-bordered" placeholder="Client ID" />
        </div>
        <div class="form-control">
          <span class="label">Secret</span>
          <input v-model="currentProvider.secret" class="input input-bordered" placeholder="Secret" />
        </div>
        <div class="form-control">
          <span class="label">Callback URL</span>
          <span>{{ location.origin + '/auth/' + currentProvider.name }}</span>
        </div>
        <div class="flex gap-2 justify-end">
          <button class="btn btn-primary" type="submit">Save</button>
          <button class="btn" @click="showDialog = false">Cancel</button>
        </div>
      </form>
    </modal>

    <modal close="true" @close="showDeleteDialog = true" v-if="showDeleteDialog">
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
</template>

<script>
export default {
  props: ['settings'],
  data() {
    return {
      showDialog: false,
      showDeleteDialog: false,
      currentProvider: { name: '', client_id: '', secret: '' },
      providerToDelete: null
    }
  },
  computed: {
    computedProviders() {
      return this.settings.oauth_providers;
    },
    location() {
      return window.location
    }
  },
  methods: {
    editProvider(provider) {
      if (!provider) {
        provider = {};
        this.computedProviders.push(provider);
      }
      this.currentProvider = provider;
      this.showDialog = true;
    },
    saveProvider() {
      this.showDialog = false;
    },
    confirmDelete(provider) {
      this.providerToDelete = provider;
      this.showDeleteDialog = true;
    },
    deleteProvider() {
      const index = this.computedProviders.findIndex(p => p.name === this.providerToDelete.name);
      if (index !== -1) {
        this.computedProviders.splice(index, 1);
      }
      this.showDeleteDialog = false;
    }
  }
}
</script>
