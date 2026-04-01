"""
supabase_service.py — Serviço de acesso ao banco de dados Supabase
-------------------------------------------------------------------
Usa funções SQL criadas diretamente no banco (via RPC) para agregar
os dados de pedidos. Isso elimina paginação e resolve timeouts:
o banco calcula tudo internamente e retorna apenas o resultado final.

Funções disponíveis no Supabase:
  - get_pedidos_resumo(date_from, date_to)     → KPIs principais
  - get_pedidos_timeline(date_from, date_to)   → Evolução diária
  - get_pedidos_por_canal(date_from, date_to)  → Por origem/pagamento
  - get_pedidos_por_estado(date_from, date_to) → Por UF
  - get_top_produtos(date_from, date_to, limit)→ Top 10 produtos
  - get_dashboard_completo(date_from, date_to) → Tudo em 1 chamada

Tabela base: pedidos_resumo (1 linha por pedido, com concluido_em)
"""

import requests
import time
from datetime import datetime
from typing import Optional, Dict, Any, List
import os

from config import get_settings
from loguru import logger


# ----------------------------------------------------------------
# Configuração da conexão — lida diretamente do ambiente
# para garantir que os valores do Render sejam sempre usados
# ----------------------------------------------------------------
def _get_supabase_url() -> str:
    return os.environ.get("SUPABASE_URL") or get_settings().supabase_url


def _get_service_key() -> str:
    return os.environ.get("SUPABASE_SERVICE_KEY") or get_settings().supabase_service_key


def _get_headers() -> Dict[str, str]:
    key = _get_service_key()
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }


# ----------------------------------------------------------------
# Cache em memória — evita re-buscar dados já calculados
# ----------------------------------------------------------------
_cache: Dict[str, Any] = {}
_cache_ttl: Dict[str, float] = {}
CACHE_DURATION = 1800  # 30 minutos


def _get_cache(key: str) -> Optional[Any]:
    """Retorna dado do cache se ainda válido."""
    if key in _cache and time.time() < _cache_ttl.get(key, 0):
        return _cache[key]
    return None


def _set_cache(key: str, value: Any):
    """Armazena dado no cache com TTL de 30 minutos."""
    _cache[key] = value
    _cache_ttl[key] = time.time() + CACHE_DURATION


# ----------------------------------------------------------------
# Função base: chama uma função SQL via RPC do Supabase
# ----------------------------------------------------------------
def _call_rpc(function_name: str, params: Dict[str, Any], timeout: int = 25) -> Any:
    """
    Chama uma função SQL do Supabase via RPC (Remote Procedure Call).
    O banco executa a função internamente e retorna apenas o resultado.

    Args:
        function_name: Nome da função SQL (ex: 'get_pedidos_resumo')
        params: Parâmetros da função (ex: {'p_date_from': '2026-03-01'})
        timeout: Timeout em segundos

    Returns:
        Resultado da função (dict, list ou None)
    """
    url = f"{_get_supabase_url()}/rest/v1/rpc/{function_name}"
    try:
        r = requests.post(url, json=params, headers=_get_headers(), timeout=timeout)
        if r.status_code == 200:
            return r.json()
        else:
            logger.error(f"❌ RPC {function_name} falhou [{r.status_code}]: {r.text[:300]}")
            return None
    except requests.Timeout:
        logger.error(f"⏱️ Timeout ao chamar {function_name}")
        return None
    except Exception as e:
        logger.error(f"❌ Erro ao chamar {function_name}: {e}")
        return None


# ----------------------------------------------------------------
# Funções públicas do serviço
# ----------------------------------------------------------------

def get_kpis(date_from: str, date_to: Optional[str] = None) -> Dict[str, Any]:
    """
    Retorna os KPIs principais do período:
    - Total de pedidos únicos
    - Receita total
    - Ticket médio
    - Clientes únicos

    Usa a função SQL get_pedidos_resumo() que agrega no banco.
    """
    if not date_to:
        date_to = datetime.now().strftime('%Y-%m-%d')

    cache_key = f"kpis_{date_from}_{date_to}"
    cached = _get_cache(cache_key)
    if cached is not None:
        logger.info(f"📦 Cache hit: KPIs {date_from} → {date_to}")
        return cached

    logger.info(f"🔍 Buscando KPIs via RPC: {date_from} → {date_to}")
    start = time.time()

    result = _call_rpc("get_pedidos_resumo", {
        "p_date_from": date_from,
        "p_date_to": date_to
    })

    elapsed = time.time() - start
    logger.info(f"✅ KPIs obtidos em {elapsed:.2f}s")

    if not result:
        result = {
            "total_pedidos": 0,
            "receita_total": 0.0,
            "ticket_medio": 0.0,
            "total_clientes": 0,
            "periodo": {"de": date_from, "ate": date_to}
        }

    _set_cache(cache_key, result)
    return result


def get_timeline(
    date_from: str,
    date_to: Optional[str] = None,
    granularity: str = "day"
) -> List[Dict]:
    """
    Retorna a evolução de vendas ao longo do tempo.

    Args:
        granularity: 'day', 'week' ou 'month'
    """
    if not date_to:
        date_to = datetime.now().strftime('%Y-%m-%d')

    cache_key = f"timeline_{date_from}_{date_to}_{granularity}"
    cached = _get_cache(cache_key)
    if cached is not None:
        return cached

    logger.info(f"📈 Buscando timeline via RPC: {date_from} → {date_to} ({granularity})")

    result = _call_rpc("get_pedidos_timeline", {
        "p_date_from": date_from,
        "p_date_to": date_to,
        "p_granularity": granularity
    })

    if not result:
        result = []

    _set_cache(cache_key, result)
    return result


def get_por_canal(date_from: str, date_to: Optional[str] = None) -> Dict[str, Any]:
    """
    Retorna métricas agrupadas por canal de origem e método de pagamento.
    """
    if not date_to:
        date_to = datetime.now().strftime('%Y-%m-%d')

    cache_key = f"canal_{date_from}_{date_to}"
    cached = _get_cache(cache_key)
    if cached is not None:
        return cached

    logger.info(f"📊 Buscando canais via RPC: {date_from} → {date_to}")

    result = _call_rpc("get_pedidos_por_canal", {
        "p_date_from": date_from,
        "p_date_to": date_to
    })

    if not result:
        result = {"por_origem": [], "por_pagamento": []}

    _set_cache(cache_key, result)
    return result


def get_por_estado(date_from: str, date_to: Optional[str] = None) -> List[Dict]:
    """
    Retorna métricas agrupadas por estado (UF).
    """
    if not date_to:
        date_to = datetime.now().strftime('%Y-%m-%d')

    cache_key = f"estado_{date_from}_{date_to}"
    cached = _get_cache(cache_key)
    if cached is not None:
        return cached

    logger.info(f"🗺️ Buscando estados via RPC: {date_from} → {date_to}")

    result = _call_rpc("get_pedidos_por_estado", {
        "p_date_from": date_from,
        "p_date_to": date_to
    })

    if not result:
        result = []

    _set_cache(cache_key, result)
    return result


def get_top_produtos(
    date_from: str,
    date_to: Optional[str] = None,
    limit: int = 10
) -> List[Dict]:
    """
    Retorna os produtos mais vendidos por receita.
    """
    if not date_to:
        date_to = datetime.now().strftime('%Y-%m-%d')

    cache_key = f"produtos_{date_from}_{date_to}_{limit}"
    cached = _get_cache(cache_key)
    if cached is not None:
        return cached

    logger.info(f"🛍️ Buscando top produtos via RPC: {date_from} → {date_to}")

    result = _call_rpc("get_top_produtos", {
        "p_date_from": date_from,
        "p_date_to": date_to,
        "p_limit": limit
    })

    if not result:
        result = []

    _set_cache(cache_key, result)
    return result


def get_dashboard_completo(
    date_from: str,
    date_to: Optional[str] = None
) -> Dict[str, Any]:
    """
    Retorna todos os dados do dashboard em uma única chamada RPC.
    O banco executa todas as agregações internamente e retorna o resultado.
    """
    if not date_to:
        date_to = datetime.now().strftime('%Y-%m-%d')

    cache_key = f"dashboard_{date_from}_{date_to}"
    cached = _get_cache(cache_key)
    if cached is not None:
        logger.info("📦 Dashboard servido do cache")
        return cached

    logger.info(f"🏗️ Buscando dashboard completo via RPC: {date_from} → {date_to}")
    start = time.time()

    result = _call_rpc("get_dashboard_completo", {
        "p_date_from": date_from,
        "p_date_to": date_to
    })

    elapsed = time.time() - start
    logger.info(f"✅ Dashboard completo obtido em {elapsed:.2f}s")

    if not result:
        result = {
            "kpis": get_kpis(date_from, date_to),
            "timeline": get_timeline(date_from, date_to),
            "canais": get_por_canal(date_from, date_to),
            "top_produtos": get_top_produtos(date_from, date_to),
            "por_estado": get_por_estado(date_from, date_to),
            "gerado_em": datetime.now().isoformat()
        }
    else:
        result["tempo_processamento_s"] = round(elapsed, 2)

    _set_cache(cache_key, result)
    return result


def invalidar_cache():
    """Limpa todo o cache (útil após sincronização de novos dados)."""
    global _cache, _cache_ttl
    _cache = {}
    _cache_ttl = {}
    logger.info("🗑️ Cache invalidado")
