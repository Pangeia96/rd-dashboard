"""
supabase_router.py — Endpoints do banco de dados (Supabase)
-----------------------------------------------------------
Expõe os dados de pedidos processados para o frontend Vue.js.
Todos os endpoints usam cache interno de 30 minutos.
"""

from fastapi import APIRouter, Query, BackgroundTasks
from typing import Optional
from datetime import datetime
from services import supabase_service
from loguru import logger

router = APIRouter(prefix="/db", tags=["Banco de Dados (Supabase)"])

DEFAULT_DATE_FROM = "2025-09-01"


def _default_date_to():
    return datetime.now().strftime('%Y-%m-%d')


# ----------------------------------------------------------------
# KPIs principais
# ----------------------------------------------------------------
@router.get("/kpis", summary="KPIs principais do período")
async def get_kpis(
    date_from: str = Query(DEFAULT_DATE_FROM, description="Data inicial (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Data final (YYYY-MM-DD)")
):
    """
    Retorna os indicadores principais:
    - Total de pedidos pagos
    - Receita total
    - Ticket médio
    - Clientes únicos
    """
    return supabase_service.get_kpis(date_from, date_to or _default_date_to())


# ----------------------------------------------------------------
# Timeline de vendas
# ----------------------------------------------------------------
@router.get("/timeline", summary="Evolução de vendas ao longo do tempo")
async def get_timeline(
    date_from: str = Query(DEFAULT_DATE_FROM, description="Data inicial (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Data final (YYYY-MM-DD)"),
    granularity: str = Query("day", description="Granularidade: day, week ou month")
):
    """
    Retorna a evolução diária/semanal/mensal de pedidos e receita.
    """
    return supabase_service.get_timeline(date_from, date_to or _default_date_to(), granularity)


# ----------------------------------------------------------------
# Por canal de origem
# ----------------------------------------------------------------
@router.get("/canais", summary="Receita por canal de origem e método de pagamento")
async def get_canais(
    date_from: str = Query(DEFAULT_DATE_FROM, description="Data inicial (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Data final (YYYY-MM-DD)")
):
    """
    Retorna pedidos e receita agrupados por:
    - Origem: mobile, desktop, etc.
    - Método de pagamento: pix, credit_card, boleto, etc.
    """
    return supabase_service.get_por_canal(date_from, date_to or _default_date_to())


# ----------------------------------------------------------------
# Por estado
# ----------------------------------------------------------------
@router.get("/estados", summary="Receita por estado (UF)")
async def get_estados(
    date_from: str = Query(DEFAULT_DATE_FROM, description="Data inicial (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Data final (YYYY-MM-DD)")
):
    """
    Retorna pedidos e receita agrupados por estado de entrega.
    """
    return supabase_service.get_por_estado(date_from, date_to or _default_date_to())


# ----------------------------------------------------------------
# Top produtos
# ----------------------------------------------------------------
@router.get("/top-produtos", summary="Top produtos mais vendidos")
async def get_top_produtos(
    date_from: str = Query(DEFAULT_DATE_FROM, description="Data inicial (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Data final (YYYY-MM-DD)"),
    limit: int = Query(10, description="Número de produtos a retornar")
):
    """
    Retorna os produtos mais vendidos por receita.
    """
    return supabase_service.get_top_produtos(date_from, date_to or _default_date_to(), limit)


# ----------------------------------------------------------------
# Dashboard completo (endpoint principal do frontend)
# ----------------------------------------------------------------
@router.get("/dashboard", summary="Dashboard completo — todos os dados em uma chamada")
async def get_dashboard(
    date_from: str = Query(DEFAULT_DATE_FROM, description="Data inicial (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Data final (YYYY-MM-DD)")
):
    """
    Retorna todos os dados do dashboard em uma única chamada.
    Usa cache de 30 minutos para respostas instantâneas.
    """
    return supabase_service.get_dashboard_completo(date_from, date_to or _default_date_to())


# ----------------------------------------------------------------
# Invalidar cache
# ----------------------------------------------------------------
@router.post("/cache/invalidar", summary="Limpa o cache de dados")
async def invalidar_cache():
    """
    Força a re-busca dos dados na próxima requisição.
    Use após sincronizar novos dados.
    """
    supabase_service.invalidar_cache()
    return {"status": "ok", "mensagem": "Cache invalidado com sucesso"}
