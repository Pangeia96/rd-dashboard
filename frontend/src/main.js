// main.js — Ponto de entrada da aplicação Vue.js
// Inicializa o app, registra plugins e monta no DOM

import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import './assets/main.css'

const app = createApp(App)

// Pinia — gerenciamento de estado global (dados do dashboard)
app.use(createPinia())

// Vue Router — navegação entre páginas do dashboard
app.use(router)

app.mount('#app')
