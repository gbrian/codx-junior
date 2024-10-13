import './assets/main.css'

import { createApp } from 'vue'
import store, { $storex } from "./store";

import App from './App.vue'
import Modal from './components/Modal.vue'
import router from './router'

const app = createApp(App)

app.provide('$storex', $storex)
app.use(router)
app.component('modal', Modal)
app.mount('#app')

store.app = app;
$storex.app = app;
$storex.init()
