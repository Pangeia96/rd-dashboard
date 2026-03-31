<template>
  <div class="flex min-h-screen bg-[#f8f5ff]">
    <!-- Sidebar de navegação -->
    <aside class="sidebar fixed left-0 top-0 h-screen z-30 hidden lg:flex flex-col">
      <!-- Logo -->
      <div class="px-6 py-6 border-b border-white/10">
        <div class="flex items-center gap-3">
          <div class="w-9 h-9 rounded-xl bg-pangeia-roxo flex items-center justify-center">
            <span class="text-white font-bold text-lg">P</span>
          </div>
          <div>
            <p class="text-white font-bold text-sm leading-tight">Pangeia 96</p>
            <p class="text-pangeia-lilas-claro/60 text-xs">Dashboard de Automações</p>
          </div>
        </div>
      </div>

      <!-- Links de navegação -->
      <nav class="flex-1 py-4 space-y-1">
        <router-link
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          class="sidebar-link"
          :class="{ active: $route.path === item.path }"
        >
          <span class="text-lg">{{ item.icon }}</span>
          <span>{{ item.label }}</span>
        </router-link>
      </nav>

      <!-- Rodapé da sidebar -->
      <div class="px-5 py-4 border-t border-white/10">
        <p class="text-pangeia-lilas-claro/40 text-xs">
          Dados atualizados a cada hora
        </p>
      </div>
    </aside>

    <!-- Conteúdo principal -->
    <main class="flex-1 lg:ml-64 min-h-screen">
      <!-- Header mobile -->
      <header class="lg:hidden bg-pangeia-roxo-profundo text-white px-4 py-3 flex items-center gap-3 sticky top-0 z-20">
        <div class="w-8 h-8 rounded-lg bg-pangeia-roxo flex items-center justify-center">
          <span class="text-white font-bold">P</span>
        </div>
        <span class="font-semibold text-sm">Pangeia 96 — Dashboard</span>
      </header>

      <!-- Conteúdo da rota atual -->
      <div class="p-4 lg:p-8">
        <router-view />
      </div>
    </main>
  </div>
</template>

<script setup>
const navItems = [
  { path: '/',            icon: '📊', label: 'Visão Geral' },
  { path: '/automacoes',  icon: '🔄', label: 'Fluxos de Automação' },
  { path: '/receita',     icon: '💰', label: 'Receita e Vendas' },
  { path: '/emails',      icon: '📧', label: 'Campanhas de E-mail' },
  { path: '/whatsapp',    icon: '💬', label: 'WhatsApp' },
  { path: '/comparativo', icon: '⚖️',  label: 'Comparativo de Canais' },
]
</script>
