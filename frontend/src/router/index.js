// router/index.js — Configuração das rotas do dashboard
import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Dashboard',
    component: () => import('@/views/DashboardView.vue'),
    meta: { title: 'Visão Geral' },
  },
  {
    path: '/automacoes',
    name: 'Automacoes',
    component: () => import('@/views/AutomacoesView.vue'),
    meta: { title: 'Fluxos de Automação' },
  },
  {
    path: '/emails',
    name: 'Emails',
    component: () => import('@/views/EmailsView.vue'),
    meta: { title: 'Campanhas de E-mail' },
  },
  {
    path: '/whatsapp',
    name: 'WhatsApp',
    component: () => import('@/views/WhatsAppView.vue'),
    meta: { title: 'WhatsApp' },
  },
  {
    path: '/receita',
    name: 'Receita',
    component: () => import('@/views/ReceitaView.vue'),
    meta: { title: 'Receita e Vendas' },
  },
  {
    path: '/comparativo',
    name: 'Comparativo',
    component: () => import('@/views/ComparativoView.vue'),
    meta: { title: 'Comparativo de Canais' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// Atualiza o título da página ao navegar
router.afterEach((to) => {
  document.title = `${to.meta.title || 'Dashboard'} — Pangeia 96`
})

export default router
