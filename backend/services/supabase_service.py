"""
supabase_service.py — Serviço de acesso ao banco de dados Supabase
-------------------------------------------------------------------
Responsável por buscar e agregar dados da tabela pedidos_unicos.

A tabela pedidos_unicos é uma view materializada que já contém
exatamente 1 registro por pedido (deduplicado), com os campos
mais relevantes para análise. Isso elimina a necessidade de
deduplicação em Python e reduz drasticamente o volume de dados
transferidos.

Colunas disponíveis em pedidos_unicos:
  id_pedido, status_pagamento, pago_em, total, email_contato,
  nome_contato, origem_pedido, metodo_pagamento, estado_entrega,
  cidade_entrega, codigo_cupom, tipo_cupom, desconto

Para top produtos (que precisa de nome_produto/sku), ainda usa
pedidos_consolidado com paginação normal.
"""

import requests
import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from config import get_settings
from loguru import logger

import os

# ----------------------------------------------------------------
# Configuração da conexão
# Lida diretamente das variáveis de ambiente para garantir que
# os valores do Render sejam sempre usados (evita problema de cache)
# ----------------------------------------------------------------
def _get_supabase_url():
    return os.environ.get("SUPABASE_URL") or get_settings().supabase_url

def _get_service_key():
    return os.environ.get("SUPABASE_SERVICE_KEY") or get_settings().supabase_service_key

def _get_headers():
    key = _get_service_key()
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }

# PAGE_SIZE aumentado para 10.000 — pedidos_unicos é leve (13 colunas)
# e responde rápido, então páginas maiores = menos requisições
PAGE_SIZE = 10000

# ----------------------------------------------------------------
# Cache em memória (evita re-buscar dados já calculados)
# ----------------------------------------------------------------
_cache: Dict[str, Any] = {}
_cache_ttl: Dict[str, float] = {}
CACHE_DURATION = 1800  # 30 minutos em segundos


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
# Função base: busca todos os pedidos pagos no período
# Usa pedidos_unicos — já 1 linha por pedido, sem deduplicação
# ----------------------------------------------------------------
def _fetch_pedidos_pagos(date_from: str, date_to: str) -> List[Dict]:
    """
    Busca todos os pedidos pagos no período usando pedidos_unicos.
    Retorna lista de dicionários (1 item = 1 pedido, já deduplicado).

    Args:
        date_from: Data inicial no formato YYYY-MM-DD
        date_to:   Data final no formato YYYY-MM-DD

    Returns:
        List[Dict] — lista de pedidos com campos normalizados
    """
    cache_key = f"pedidos_{date_from}_{date_to}"
    cached = _get_cache(cache_key)
    if cached is not None:
        logger.info(f"📦 Cache hit: pedidos {date_from} → {date_to}")
        return cached

    logger.info(f"🔍 Buscando pedidos pagos (pedidos_unicos): {date_from} → {date_to}")
    pedidos = []
    offset = 0
    start = time.time()

    while True:
        try:
            r = requests.get(
                f"{_get_supabase_url()}/rest/v1/pedidos_unicos"
                f"?select=id_pedido,total,email_contato,nome_contato,"
                f"origem_pedido,metodo_pagamento,pago_em,estado_entrega,"
                f"cidade_entrega,codigo_cupom,tipo_cupom,desconto"
                f"&status_pagamento=eq.paid"
                f"&pago_em=gte.{date_from}T00:00:00"
                f"&pago_em=lte.{date_to}T23:59:59"
                f"&order=pago_em.asc"
                f"&limit={PAGE_SIZE}&offset={offset}",
                headers=_get_headers(),
                timeout=20
            )

            if r.status_code != 200:
                logger.error(f"Erro ao buscar pedidos (offset={offset}): {r.text[:200]}")
                break

            data = r.json()
            if not isinstance(data, list) or not data:
                break

            # Normaliza os campos para uso consistente no restante do serviço
            for row in data:
                pedidos.append({
                    'id_pedido': row['id_pedido'],
                    'total': float(row.get('total') or 0),
                    'email': (row.get('email_contato') or '').lower().strip(),
                    'nome': row.get('nome_contato', ''),
                    'origem': row.get('origem_pedido') or 'unknown',
                    'metodo': row.get('metodo_pagamento') or 'unknown',
                    'pago_em': (row.get('pago_em') or '')[:10],
                    'estado': row.get('estado_entrega') or 'Desconhecido',
                    'cidade': row.get('cidade_entrega') or '',
                    'cupom': row.get('codigo_cupom') or '',
                    'desconto': float(row.get('desconto') or 0),
                })

            offset += PAGE_SIZE
            if len(data) < PAGE_SIZE:
                break

        except requests.Timeout:
            logger.warning(f"Timeout na página offset={offset}, tentando novamente...")
            time.sleep(1)
            continue
        except Exception as e:
            logger.error(f"Erro inesperado: {e}")
            break

    elapsed = time.time() - start
    logger.info(f"✅ {len(pedidos)} pedidos carregados em {elapsed:.1f}s")

    _set_cache(cache_key, pedidos)
    return pedidos


def _fetch_produtos_pedidos(date_from: str, date_to: str) -> List[Dict]:
    """
    Busca todos os produtos dos pedidos pagos no período.
    Ainda usa pedidos_consolidado pois pedidos_unicos não tem nome_produto.
    Usado exclusivamente para análise de top produtos.
    """
    cache_key = f"produtos_{date_from}_{date_to}"
    cached = _get_cache(cache_key)
    if cached is not None:
        return cached

    logger.info(f"🛍️ Buscando produtos (pedidos_consolidado): {date_from} → {date_to}")
    produtos = []
    offset = 0
    PAGE = 5000  # Página menor pois pedidos_consolidado é mais pesada

    while True:
        try:
            r = requests.get(
                f"{_get_supabase_url()}/rest/v1/pedidos_consolidado"
                f"?select=id_pedido,nome_produto,nome_produto_simples,sku_produto,quantidade,preco"
                f"&status_pagamento=eq.paid"
                f"&pago_em=gte.{date_from}T00:00:00"
                f"&pago_em=lte.{date_to}T23:59:59"
                f"&order=pago_em.asc"
                f"&limit={PAGE}&offset={offset}",
                headers=_get_headers(),
                timeout=20
            )

            if r.status_code != 200:
                break

            data = r.json()
            if not isinstance(data, list) or not data:
                break

            produtos.extend(data)
            offset += PAGE

            if len(data) < PAGE:
                break

        except Exception as e:
            logger.error(f"Erro ao buscar produtos: {e}")
            break

    _set_cache(cache_key, produtos)
    return produtos


# ----------------------------------------------------------------
# Funções de métricas
# ----------------------------------------------------------------

def get_kpis(date_from: str, date_to: Optional[str] = None) -> Dict[str, Any]:
    """
    Retorna os KPIs principais do período:
    - Total de pedidos únicos
    - Receita total
    - Ticket médio
    - Clientes únicos
    """
    if not date_to:
        date_to = datetime.now().strftime('%Y-%m-%d')

    pedidos = _fetch_pedidos_pagos(date_from, date_to)

    if not pedidos:
        return {
            "total_pedidos": 0,
            "receita_total": 0.0,
            "ticket_medio": 0.0,
            "total_clientes": 0,
            "periodo": {"de": date_from, "ate": date_to}
        }

    receita_total = sum(p['total'] for p in pedidos)
    total_pedidos = len(pedidos)
    clientes_unicos = len(set(p['email'] for p in pedidos if p['email']))

    return {
        "total_pedidos": total_pedidos,
        "receita_total": round(receita_total, 2),
        "ticket_medio": round(receita_total / total_pedidos, 2) if total_pedidos > 0 else 0.0,
        "total_clientes": clientes_unicos,
        "periodo": {"de": date_from, "ate": date_to}
    }


def get_timeline(date_from: str, date_to: Optional[str] = None, granularity: str = "day") -> List[Dict]:
    """
    Retorna a evolução de vendas ao longo do tempo.

    Args:
        granularity: 'day', 'week' ou 'month'
    """
    if not date_to:
        date_to = datetime.now().strftime('%Y-%m-%d')

    pedidos = _fetch_pedidos_pagos(date_from, date_to)
    timeline = defaultdict(lambda: {"pedidos": 0, "receita": 0.0})

    for p in pedidos:
        data_str = p['pago_em']
        if not data_str:
            continue
        try:
            dt = datetime.strptime(data_str, '%Y-%m-%d')
            if granularity == 'month':
                key = dt.strftime('%Y-%m')
            elif granularity == 'week':
                # Início da semana (segunda-feira)
                inicio_semana = dt - timedelta(days=dt.weekday())
                key = inicio_semana.strftime('%Y-%m-%d')
            else:
                key = data_str
        except:
            key = data_str

        timeline[key]["pedidos"] += 1
        timeline[key]["receita"] += p['total']

    result = [
        {"data": k, "pedidos": v["pedidos"], "receita": round(v["receita"], 2)}
        for k, v in sorted(timeline.items())
    ]
    return result


def get_por_canal(date_from: str, date_to: Optional[str] = None) -> Dict[str, Any]:
    """
    Retorna métricas agrupadas por canal de origem e método de pagamento.
    """
    if not date_to:
        date_to = datetime.now().strftime('%Y-%m-%d')

    pedidos = _fetch_pedidos_pagos(date_from, date_to)

    por_origem = defaultdict(lambda: {"pedidos": 0, "receita": 0.0})
    por_metodo = defaultdict(lambda: {"pedidos": 0, "receita": 0.0})

    for p in pedidos:
        origem = p['origem'] or 'unknown'
        metodo = p['metodo'] or 'unknown'
        por_origem[origem]["pedidos"] += 1
        por_origem[origem]["receita"] += p['total']
        por_metodo[metodo]["pedidos"] += 1
        por_metodo[metodo]["receita"] += p['total']

    return {
        "por_origem": sorted(
            [{"canal": k, "pedidos": v["pedidos"], "receita": round(v["receita"], 2)}
             for k, v in por_origem.items()],
            key=lambda x: -x["receita"]
        ),
        "por_pagamento": sorted(
            [{"metodo": k, "pedidos": v["pedidos"], "receita": round(v["receita"], 2)}
             for k, v in por_metodo.items()],
            key=lambda x: -x["receita"]
        )
    }


def get_por_estado(date_from: str, date_to: Optional[str] = None) -> List[Dict]:
    """
    Retorna métricas agrupadas por estado (UF).
    """
    if not date_to:
        date_to = datetime.now().strftime('%Y-%m-%d')

    pedidos = _fetch_pedidos_pagos(date_from, date_to)
    por_estado = defaultdict(lambda: {"pedidos": 0, "receita": 0.0})

    for p in pedidos:
        estado = p['estado'] or 'Desconhecido'
        por_estado[estado]["pedidos"] += 1
        por_estado[estado]["receita"] += p['total']

    return sorted(
        [{"estado": k, "pedidos": v["pedidos"], "receita": round(v["receita"], 2)}
         for k, v in por_estado.items()],
        key=lambda x: -x["receita"]
    )


def get_top_produtos(date_from: str, date_to: Optional[str] = None, limit: int = 10) -> List[Dict]:
    """
    Retorna os produtos mais vendidos por receita.
    Usa pedidos_consolidado pois pedidos_unicos não tem nome_produto.
    """
    if not date_to:
        date_to = datetime.now().strftime('%Y-%m-%d')

    produtos_raw = _fetch_produtos_pedidos(date_from, date_to)
    por_produto = defaultdict(lambda: {"quantidade": 0, "receita": 0.0, "sku": ""})

    for row in produtos_raw:
        nome = row.get('nome_produto_simples') or row.get('nome_produto') or 'Desconhecido'
        sku = row.get('sku_produto') or ''
        qtd = int(row.get('quantidade') or 0)
        preco = float(row.get('preco') or 0)
        por_produto[nome]["quantidade"] += qtd
        por_produto[nome]["receita"] += preco * qtd
        por_produto[nome]["sku"] = sku

    return sorted(
        [{"nome": k, "sku": v["sku"], "quantidade": v["quantidade"], "receita": round(v["receita"], 2)}
         for k, v in por_produto.items()],
        key=lambda x: -x["receita"]
    )[:limit]


def get_dashboard_completo(date_from: str, date_to: Optional[str] = None) -> Dict[str, Any]:
    """
    Retorna todos os dados do dashboard em uma única chamada.
    Usa cache interno para evitar re-processamento.
    """
    if not date_to:
        date_to = datetime.now().strftime('%Y-%m-%d')

    cache_key = f"dashboard_{date_from}_{date_to}"
    cached = _get_cache(cache_key)
    if cached is not None:
        logger.info("📦 Dashboard servido do cache")
        return cached

    logger.info(f"🏗️ Construindo dashboard: {date_from} → {date_to}")
    start = time.time()

    # Busca os dados base uma única vez (pedidos_unicos — rápido)
    pedidos = _fetch_pedidos_pagos(date_from, date_to)

    # Calcula todas as métricas a partir dos dados em memória
    receita_total = sum(p['total'] for p in pedidos)
    total_pedidos = len(pedidos)
    clientes_unicos = len(set(p['email'] for p in pedidos if p['email']))

    # Agrega por dimensão em uma única passagem
    timeline_data = defaultdict(lambda: {"pedidos": 0, "receita": 0.0})
    por_origem = defaultdict(lambda: {"pedidos": 0, "receita": 0.0})
    por_metodo = defaultdict(lambda: {"pedidos": 0, "receita": 0.0})
    por_estado = defaultdict(lambda: {"pedidos": 0, "receita": 0.0})

    for p in pedidos:
        dia = p['pago_em']
        if dia:
            timeline_data[dia]["pedidos"] += 1
            timeline_data[dia]["receita"] += p['total']

        origem = p['origem'] or 'unknown'
        por_origem[origem]["pedidos"] += 1
        por_origem[origem]["receita"] += p['total']

        metodo = p['metodo'] or 'unknown'
        por_metodo[metodo]["pedidos"] += 1
        por_metodo[metodo]["receita"] += p['total']

        estado = p['estado'] or 'Desconhecido'
        por_estado[estado]["pedidos"] += 1
        por_estado[estado]["receita"] += p['total']

    # Top produtos (busca separada em pedidos_consolidado)
    top_produtos = get_top_produtos(date_from, date_to, 10)

    result = {
        "kpis": {
            "total_pedidos": total_pedidos,
            "receita_total": round(receita_total, 2),
            "ticket_medio": round(receita_total / total_pedidos, 2) if total_pedidos > 0 else 0.0,
            "total_clientes": clientes_unicos,
            "periodo": {"de": date_from, "ate": date_to}
        },
        "timeline": [
            {"data": k, "pedidos": v["pedidos"], "receita": round(v["receita"], 2)}
            for k, v in sorted(timeline_data.items())
        ],
        "canais": {
            "por_origem": sorted(
                [{"canal": k, "pedidos": v["pedidos"], "receita": round(v["receita"], 2)}
                 for k, v in por_origem.items()],
                key=lambda x: -x["receita"]
            ),
            "por_pagamento": sorted(
                [{"metodo": k, "pedidos": v["pedidos"], "receita": round(v["receita"], 2)}
                 for k, v in por_metodo.items()],
                key=lambda x: -x["receita"]
            )
        },
        "por_estado": sorted(
            [{"estado": k, "pedidos": v["pedidos"], "receita": round(v["receita"], 2)}
             for k, v in por_estado.items()],
            key=lambda x: -x["receita"]
        ),
        "top_produtos": top_produtos,
        "gerado_em": datetime.now().isoformat(),
        "tempo_processamento_s": round(time.time() - start, 2)
    }

    _set_cache(cache_key, result)
    return result


def invalidar_cache():
    """Limpa todo o cache (útil após sincronização de novos dados)."""
    global _cache, _cache_ttl
    _cache = {}
    _cache_ttl = {}
    logger.info("🗑️ Cache invalidado")
