// store/dashboard.js — Estado global do dashboard Pangeia 96
// Gerencia os dados carregados da API e os filtros ativos

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_URL || 'https://rd-dashboard-backend.onrender.com'

export const useDashboardStore = defineStore('dashboard', () => {
  // ── Estado ──────────────────────────────────────────────────────────
  const loading = ref(false)
  const loadingKpis = ref(false)
  const loadingTimeline = ref(false)
  const loadingCanais = ref(false)
  const loadingProdutos = ref(false)
  const error = ref(null)

  // Filtros de data (padrão: setembro 2025 até hoje)
  const dateFrom = ref('2025-09-01')
  const dateTo = ref(new Date().toISOString().split('T')[0])

  // Dados carregados da API Supabase
  const kpisData = ref(null)
  const timelineData = ref([])
  const canaisData = ref(null)
  const estadosData = ref([])
  const produtosData = ref([])

  // Dados RD Station (carregados após autenticação OAuth)
  const automacoes = ref([])
  const emailMetrics = ref([])
  const whatsappMetrics = ref(null)

  // ── Getters ─────────────────────────────────────────────────────────

  const totalPedidos = computed(() => kpisData.value?.total_pedidos || 0)
  const receitaTotal = computed(() => kpisData.value?.receita_total || 0)
  const ticketMedio = computed(() => kpisData.value?.ticket_medio || 0)
  const totalClientes = computed(() => kpisData.value?.total_clientes || 0)

  const receitaFormatada = computed(() =>
    new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' })
      .format(receitaTotal.value)
  )

  const ticketFormatado = computed(() =>
    new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' })
      .format(ticketMedio.value)
  )

  // Top canal por receita
  const topCanal = computed(() => {
    const origens = canaisData.value?.por_origem || []
    return origens[0] || null
  })

  // Top método de pagamento
  const topMetodo = computed(() => {
    const metodos = canaisData.value?.por_pagamento || []
    return metodos[0] || null
  })

  // ── Ações ────────────────────────────────────────────────────────────

  async function fetchKpis() {
    loadingKpis.value = true
    error.value = null
    try {
      const res = await axios.get(`${API_BASE}/db/kpis`, {
        params: { date_from: dateFrom.value, date_to: dateTo.value },
        timeout: 120000
      })
      kpisData.value = res.data
    } catch (e) {
      error.value = 'Erro ao carregar KPIs. Verifique a conexão com o servidor.'
      console.error('fetchKpis error:', e)
    } finally {
      loadingKpis.value = false
    }
  }

  async function fetchTimeline(granularity = 'day') {
    loadingTimeline.value = true
    try {
      const res = await axios.get(`${API_BASE}/db/timeline`, {
        params: { date_from: dateFrom.value, date_to: dateTo.value, granularity },
        timeout: 120000
      })
      timelineData.value = res.data || []
    } catch (e) {
      console.error('fetchTimeline error:', e)
    } finally {
      loadingTimeline.value = false
    }
  }

  async function fetchCanais() {
    loadingCanais.value = true
    try {
      const res = await axios.get(`${API_BASE}/db/canais`, {
        params: { date_from: dateFrom.value, date_to: dateTo.value },
        timeout: 120000
      })
      canaisData.value = res.data
    } catch (e) {
      console.error('fetchCanais error:', e)
    } finally {
      loadingCanais.value = false
    }
  }

  async function fetchEstados() {
    try {
      const res = await axios.get(`${API_BASE}/db/estados`, {
        params: { date_from: dateFrom.value, date_to: dateTo.value },
        timeout: 120000
      })
      estadosData.value = res.data || []
    } catch (e) {
      console.error('fetchEstados error:', e)
    }
  }

  async function fetchProdutos(limit = 10) {
    loadingProdutos.value = true
    try {
      const res = await axios.get(`${API_BASE}/db/top-produtos`, {
        params: { date_from: dateFrom.value, date_to: dateTo.value, limit },
        timeout: 120000
      })
      produtosData.value = res.data || []
    } catch (e) {
      console.error('fetchProdutos error:', e)
    } finally {
      loadingProdutos.value = false
    }
  }

  async function fetchDashboardCompleto() {
    loading.value = true
    error.value = null
    try {
      const res = await axios.get(`${API_BASE}/db/dashboard`, {
        params: { date_from: dateFrom.value, date_to: dateTo.value },
        timeout: 180000
      })
      const data = res.data
      kpisData.value = data.kpis
      timelineData.value = data.timeline || []
      canaisData.value = data.canais
      estadosData.value = data.por_estado || []
      produtosData.value = data.top_produtos || []
    } catch (e) {
      error.value = 'Erro ao carregar dashboard. Verifique a conexão com o servidor.'
      console.error('fetchDashboardCompleto error:', e)
    } finally {
      loading.value = false
    }
  }

  // Carrega todos os dados em uma única chamada ao endpoint /db/dashboard
  async function fetchTudo() {
    await fetchDashboardCompleto()
  }

  function setDateRange(from, to) {
    dateFrom.value = from
    dateTo.value = to
  }

  async function aplicarFiltros() {
    await fetchTudo()
  }

  return {
    // Estado
    loading, loadingKpis, loadingTimeline, loadingCanais, loadingProdutos,
    error, dateFrom, dateTo,
    kpisData, timelineData, canaisData, estadosData, produtosData,
    automacoes, emailMetrics, whatsappMetrics,
    // Getters
    totalPedidos, receitaTotal, ticketMedio, totalClientes,
    receitaFormatada, ticketFormatado, topCanal, topMetodo,
    // Ações
    fetchKpis, fetchTimeline, fetchCanais, fetchEstados, fetchProdutos,
    fetchDashboardCompleto, fetchTudo, setDateRange, aplicarFiltros,
  }
})
