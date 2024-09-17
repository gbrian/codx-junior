<template>
    <div class="flex flex-col items-center justify-center h-screen p-4">
      <h1 class="text-3xl font-bold mb-4">Welcome to GPT Engineer</h1>
      <p class="mb-6">Please select a directory or clone a GitHub repository to get started.</p>
      
      <div class="mb-4 w-full max-w-md">
        <input 
          type="text" 
          v-model="directory" 
          placeholder="Enter directory path" 
          class="input input-bordered w-full mb-2"
        />
        <button 
          @click="selectDirectory" 
          class="btn btn-primary w-full"
        >
          Select Directory
        </button>
      </div>
      
      <div class="mb-4 w-full max-w-md">
        <input 
          type="text" 
          v-model="repoUrl" 
          placeholder="Enter GitHub repository URL" 
          class="input input-bordered w-full mb-2"
        />
        <button 
          @click="cloneRepo" 
          class="btn btn-primary w-full"
        >
          Clone Repository
        </button>
      </div>
      
      <div v-if="errorMessage" class="text-red-500 mt-4">{{ errorMessage }}</div>
    </div>
  </template>
  
  <script setup>
  import { ref } from 'vue';
  
  const directory = ref('');
  const repoUrl = ref('');
  const errorMessage = ref('');
  
  const selectDirectory = () => {
    if (!directory.value) {
      errorMessage.value = 'Please enter a valid directory path.';
    } else {
      errorMessage.value = '';
      // Logic to initialize the project in the selected directory
      console.log(`Selected directory: ${directory.value}`);
    }
  };
  
  const cloneRepo = () => {
    if (!repoUrl.value) {
      errorMessage.value = 'Please enter a valid GitHub repository URL.';
    } else {
      errorMessage.value = '';
      // Logic to clone the repository
      console.log(`Cloning repository: ${repoUrl.value}`);
    }
  };
  </script>