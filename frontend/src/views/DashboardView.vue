<template>
  <div class="space-y-6">

    <!-- Cabeçalho com filtro de data -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
      <div>
        <h1 class="text-2xl font-bold text-pangeia-roxo-profundo">Visão Geral</h1>
        <p class="text-sm text-gray-400 mt-0.5">
          {{ store.dateFrom }} → {{ store.dateTo }}
        </p>
      </div>
      <DateRangeFilter @change="onDateChange" />
    </div>

    <!-- Loading global -->
    <LoadingState v-if="store.loading" message="Carregando dados do dashboard..." />

    <template v-else>
      <!-- KPI Cards principais -->
      <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          label="Receita Total"
          :value="store.receitaTotal"
          format="currency"
          icon="💰"
          icon-bg="bg-apoio-laranja-claro"
          :loading="store.loadingKpis"
        />
        <KpiCard
          label="Pedidos Pagos"
          :value="store.totalPedidos"
          icon="📦"
          icon-bg="bg-apoio-verde-claro"
          :loading="store.loadingKpis"
        />
        <KpiCard
          label="Ticket Médio"
          :value="store.ticketMedio"
          format="currency"
          icon="🎯"
          icon-bg="bg-pangeia-lilas-claro"
          :loading="store.loadingKpis"
        />
        <KpiCard
          label="Clientes Únicos"
          :value="store.totalClientes"
          icon="👥"
          icon-bg="bg-apoio-azul-claro"
          :loading="store.loadingKpis"
        />
      </div>

      <!-- Gráfico de timeline + Origem dos pedidos -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">

        <!-- Timeline de receita (ocupa 2/3) -->
        <div class="card lg:col-span-2">
          <div class="flex items-center justify-between mb-4">
            <h2 class="font-semibold text-pangeia-roxo-profundo">Receita ao Longo do Tempo</h2>
            <div class="flex gap-2">
              <button
                v-for="g in granularidades"
                :key="g.value"
                @click="mudarGranularidade(g.value)"
                :class="[
                  'px-3 py-1 text-xs rounded-full font-medium transition-colors',
                  granularidade === g.value
                    ? 'bg-pangeia-roxo text-white'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                ]"
              >{{ g.label }}</button>
            </div>
          </div>
          <div class="h-64">
            <LoadingState v-if="store.loadingTimeline" message="" />
            <LineChart
              v-else-if="timelineLabels.length"
              :labels="timelineLabels"
              :datasets="timelineDatasets"
              y-prefix="R$ "
            />
            <EmptyState
              v-else
              icon="📈"
              title="Sem dados de vendas no período"
              subtitle="Ajuste o filtro de data para ver a evolução de receita."
            />
          </div>
        </div>

        <!-- Origem dos pedidos (ocupa 1/3) -->
        <div class="card">
          <h2 class="font-semibold text-pangeia-roxo-profundo mb-4">Origem dos Pedidos</h2>
          <LoadingState v-if="store.loadingCanais" message="" />
          <template v-else-if="store.canaisData?.por_origem?.length">
            <DoughnutChart
              :labels="origemLabels"
              :values="origemValues"
              :center-label="store.receitaFormatada"
              center-sub="receita total"
              format="currency"
            />
            <div class="mt-4 space-y-2">
              <div
                v-for="item in store.canaisData.por_origem"
                :key="item.canal"
                class="flex items-center justify-between text-sm"
              >
                <span class="text-gray-600">{{ traduzirCanal(item.canal) }}</span>
                <div class="text-right">
                  <span class="font-semibold text-gray-900">{{ formatCurrency(item.receita) }}</span>
                  <span class="text-xs text-gray-400 ml-1">{{ item.pedidos.toLocaleString('pt-BR') }} ped.</span>
                </div>
              </div>
            </div>
          </template>
          <EmptyState v-else icon="📊" title="Sem dados de origem" subtitle="" />
        </div>
      </div>

      <!-- Método de Pagamento + Top Produtos -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">

        <!-- Método de Pagamento -->
        <div class="card">
          <h2 class="font-semibold text-pangeia-roxo-profundo mb-4">Método de Pagamento</h2>
          <LoadingState v-if="store.loadingCanais" message="" />
          <template v-else-if="store.canaisData?.por_pagamento?.length">
            <div class="space-y-3">
              <div
                v-for="item in store.canaisData.por_pagamento"
                :key="item.metodo"
                class="flex items-center gap-3"
              >
                <span class="text-xl w-8 text-center">{{ iconeMetodo(item.metodo) }}</span>
                <div class="flex-1">
                  <div class="flex justify-between text-sm mb-1">
                    <span class="text-gray-700 font-medium">{{ traduzirMetodo(item.metodo) }}</span>
                    <span class="font-bold text-gray-900">{{ formatCurrency(item.receita) }}</span>
                  </div>
                  <div class="w-full bg-gray-100 rounded-full h-2">
                    <div
                      class="h-2 rounded-full bg-pangeia-roxo"
                      :style="{ width: calcPct(item.receita, store.receitaTotal) + '%' }"
                    ></div>
                  </div>
                  <p class="text-xs text-gray-400 mt-1">{{ item.pedidos.toLocaleString('pt-BR') }} pedidos · {{ calcPct(item.receita, store.receitaTotal) }}%</p>
                </div>
              </div>
            </div>
          </template>
          <EmptyState v-else icon="💳" title="Sem dados de pagamento" subtitle="" />
        </div>

        <!-- Top 10 Produtos -->
        <div class="card">
          <h2 class="font-semibold text-pangeia-roxo-profundo mb-4">Top 10 Produtos</h2>
          <LoadingState v-if="store.loadingProdutos" message="" />
          <div v-else-if="store.produtosData.length" class="space-y-2 max-h-72 overflow-y-auto pr-1">
            <div
              v-for="(produto, idx) in store.produtosData.slice(0, 10)"
              :key="produto.sku || idx"
              class="flex items-center gap-3 py-2 border-b border-gray-50 last:border-0"
            >
              <span class="text-sm font-bold text-gray-300 w-5 text-center flex-shrink-0">{{ idx + 1 }}</span>
              <div class="flex-1 min-w-0">
                <p class="text-sm font-medium text-gray-800 truncate">{{ produto.nome }}</p>
                <p class="text-xs text-gray-400">{{ produto.quantidade.toLocaleString('pt-BR') }} un.</p>
              </div>
              <span class="text-sm font-bold text-pangeia-roxo-medio whitespace-nowrap">
                {{ formatCurrency(produto.receita) }}
              </span>
            </div>
          </div>
          <EmptyState v-else icon="🛍️" title="Sem dados de produtos" subtitle="" />
        </div>
      </div>

      <!-- Top Estados -->
      <div class="card">
        <h2 class="font-semibold text-pangeia-roxo-profundo mb-4">Receita por Estado</h2>
        <div v-if="store.estadosData.length" class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
          <div
            v-for="estado in store.estadosData.slice(0, 10)"
            :key="estado.estado"
            class="bg-pangeia-lilas-claro/30 rounded-xl p-3 text-center"
          >
            <p class="text-xs text-gray-500 mb-1 font-medium">{{ estado.estado }}</p>
            <p class="text-sm font-bold text-pangeia-roxo-profundo">{{ formatCurrency(estado.receita) }}</p>
            <p class="text-xs text-gray-400">{{ estado.pedidos.toLocaleString('pt-BR') }} ped.</p>
          </div>
        </div>
        <EmptyState v-else icon="🗺️" title="Sem dados de estados" subtitle="" />
      </div>

      <!-- Aviso sobre RD Station -->
      <div class="bg-apoio-laranja-claro/40 border border-apoio-laranja rounded-xl px-5 py-4 flex items-start gap-3">
        <span class="text-2xl flex-shrink-0">⚠️</span>
        <div>
          <p class="font-semibold text-yellow-800 text-sm">Dados de Automação RD Station</p>
          <p class="text-xs text-yellow-700 mt-1">
            Os dados de fluxos de automação, e-mail e WhatsApp serão exibidos após a
            <a href="http://localhost:8000/auth/login" target="_blank" class="underline font-semibold">autenticação OAuth</a>
            ser concluída. Os dados de vendas acima são carregados diretamente do Supabase.
          </p>
        </div>
      </div>

    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useDashboardStore } from '@/store/dashboard'
import KpiCard from '@/components/KpiCard.vue'
import DateRangeFilter from '@/components/DateRangeFilter.vue'
import LineChart from '@/components/LineChart.vue'
import DoughnutChart from '@/components/DoughnutChart.vue'
import LoadingState from '@/components/LoadingState.vue'
import EmptyState from '@/components/EmptyState.vue'

const store = useDashboardStore()
const granularidade = ref('day')
const granularidades = [
  { label: 'Dia', value: 'day' },
  { label: 'Semana', value: 'week' },
  { label: 'Mês', value: 'month' },
]

onMounted(async () => {
  await store.fetchTudo()
})

async function onDateChange({ from, to }) {
  store.setDateRange(from, to)
  await store.aplicarFiltros()
}

async function mudarGranularidade(g) {
  granularidade.value = g
  await store.fetchTimeline(g)
}

// Timeline
const timelineLabels = computed(() =>
  (store.timelineData || []).map(d => {
    try {
      const dt = new Date(d.data + 'T12:00:00')
      if (granularidade.value === 'month') return dt.toLocaleDateString('pt-BR', { month: 'short', year: '2-digit' })
      return dt.toLocaleDateString('pt-BR', { day: '2-digit', month: 'short' })
    } catch { return d.data }
  })
)
const timelineDatasets = computed(() => [{
  label: 'Receita (R$)',
  data: (store.timelineData || []).map(d => d.receita),
  fill: true,
}])

// Origem dos pedidos para DoughnutChart
const origemLabels = computed(() =>
  (store.canaisData?.por_origem || []).map(i => traduzirCanal(i.canal))
)
const origemValues = computed(() =>
  (store.canaisData?.por_origem || []).map(i => i.receita)
)

function formatCurrency(v) {
  return Number(v || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
}

function calcPct(valor, total) {
  if (!total) return 0
  return Math.round((valor / total) * 100)
}

function traduzirCanal(canal) {
  const mapa = { mobile: '📱 Mobile', desktop: '🖥️ Desktop', store: '🏪 Loja', form: '📝 Formulário', unknown: '❓ Desconhecido' }
  return mapa[canal] || canal
}

function traduzirMetodo(metodo) {
  const mapa = { credit_card: 'Cartão de Crédito', pix: 'PIX', boleto: 'Boleto', debit_card: 'Débito', unknown: 'Desconhecido' }
  return mapa[metodo] || metodo
}

function iconeMetodo(metodo) {
  const mapa = { credit_card: '💳', pix: '⚡', boleto: '📄', debit_card: '💳', unknown: '❓' }
  return mapa[metodo] || '💰'
}
</script>
