<template>
  <div class="space-y-6">
    <div>
      <h1 class="text-2xl font-bold text-pangeia-roxo-profundo">Fluxos de Automação</h1>
      <p class="text-sm text-gray-400 mt-0.5">Funil de leads por etapa e taxa de avanço</p>
    </div>

    <LoadingState v-if="loading" message="Carregando fluxos de automação..." />

    <template v-else>
      <!-- Resumo geral -->
      <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard label="Total de Fluxos" :value="automations.length" icon="🔄" />
        <KpiCard label="Fluxos Ativos" :value="activeCount" icon="✅" icon-bg="bg-apoio-verde-claro" />
        <KpiCard label="Total de Leads" :value="totalLeads" icon="👥" icon-bg="bg-pangeia-lilas-claro" />
        <KpiCard label="Melhor Conversão" :value="bestConversionRate" format="percent" icon="🏆" icon-bg="bg-apoio-laranja-claro" />
      </div>

      <!-- Lista de fluxos -->
      <div v-if="automations.length" class="space-y-4">
        <div
          v-for="auto in automations"
          :key="auto.id"
          class="card"
        >
          <!-- Cabeçalho do fluxo -->
          <div class="flex items-start justify-between mb-4 cursor-pointer" @click="toggle(auto.id)">
            <div class="flex items-center gap-3">
              <span class="text-2xl">🔄</span>
              <div>
                <h3 class="font-semibold text-pangeia-roxo-profundo">{{ auto.name }}</h3>
                <p class="text-xs text-gray-400 mt-0.5">
                  {{ auto.steps_count }} etapas ·
                  {{ (auto.total_contacts || 0).toLocaleString('pt-BR') }} leads no total
                </p>
              </div>
            </div>
            <div class="flex items-center gap-3">
              <span class="badge" :class="auto.status === 'active' ? 'badge-success' : 'badge-info'">
                {{ auto.status === 'active' ? 'Ativo' : auto.status || 'Desconhecido' }}
              </span>
              <span class="text-gray-400 text-sm">{{ expanded.has(auto.id) ? '▲' : '▼' }}</span>
            </div>
          </div>

          <!-- Funil expandido -->
          <div v-if="expanded.has(auto.id)">
            <div class="border-t border-pangeia-lilas-claro/30 pt-4">
              <FunnelChart :steps="auto.steps || []" />
            </div>
          </div>

          <!-- Preview colapsado -->
          <div v-else class="flex gap-2 overflow-x-auto pb-1">
            <div
              v-for="(step, i) in (auto.steps || []).slice(0, 5)"
              :key="i"
              class="flex-shrink-0 bg-pangeia-lilas-claro/30 rounded-lg px-3 py-2 text-center min-w-[90px]"
            >
              <p class="text-xs text-gray-500 truncate">{{ step.name }}</p>
              <p class="text-sm font-bold text-pangeia-roxo-medio mt-0.5">
                {{ (step.contacts || 0).toLocaleString('pt-BR') }}
              </p>
            </div>
            <div v-if="(auto.steps || []).length > 5" class="flex-shrink-0 flex items-center px-3 text-xs text-gray-400">
              +{{ auto.steps.length - 5 }} etapas
            </div>
          </div>
        </div>
      </div>

      <EmptyState
        v-else
        icon="🔄"
        title="Nenhum fluxo encontrado"
        subtitle="Autentique-se com a RD Station para carregar os fluxos de automação."
      />
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useDashboardStore } from '@/store/dashboard'
import KpiCard from '@/components/KpiCard.vue'
import FunnelChart from '@/components/FunnelChart.vue'
import LoadingState from '@/components/LoadingState.vue'
import EmptyState from '@/components/EmptyState.vue'

const store = useDashboardStore()
const loading = ref(false)
const expanded = ref(new Set())

onMounted(async () => {
  if (!store.automations.length) {
    loading.value = true
    await store.fetchDashboard()
    loading.value = false
  }
})

const automations = computed(() => store.automations || [])
const activeCount = computed(() => automations.value.filter(a => a.status === 'active').length)
const totalLeads = computed(() => automations.value.reduce((s, a) => s + (a.total_contacts || 0), 0))
const bestConversionRate = computed(() => {
  const rates = automations.value.flatMap(a =>
    (a.steps || []).map(s => s.advance_rate || 0)
  )
  return rates.length ? Math.max(...rates) : 0
})

function toggle(id) {
  if (expanded.value.has(id)) {
    expanded.value.delete(id)
  } else {
    expanded.value.add(id)
  }
}
</script>
