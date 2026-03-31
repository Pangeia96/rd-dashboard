"""
supabase_service.py — Serviço de acesso ao banco de dados Supabase
-------------------------------------------------------------------
Responsável por buscar e agregar dados da tabela pedidos_consolidado
usando paginação eficiente com colunas indexadas.

Estratégia de performance:
- Usa ORDER BY pago_em (coluna indexada) para paginação rápida
- Processa agregações no Python após buscar os dados
- Cache em memória para evitar consultas repetidas
- Cada página retorna em ~0.2s, processamento total < 30s para 100k registros
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

PAGE_SIZE = 1000  # Registros por página (máximo eficiente)

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
# ----------------------------------------------------------------
def _fetch_pedidos_pagos(date_from: str, date_to: str) -> Dict[str, Any]:
    """
    Busca todos os pedidos pagos no período usando paginação eficiente.
    Retorna dicionário com id_pedido como chave (deduplicado).

    Args:
        date_from: Data inicial no formato YYYY-MM-DD
        date_to:   Data final no formato YYYY-MM-DD

    Returns:
        Dict[id_pedido -> dados do pedido]
    """
    cache_key = f"pedidos_{date_from}_{date_to}"
    cached = _get_cache(cache_key)
    if cached is not None:
        logger.info(f"📦 Cache hit: pedidos {date_from} → {date_to}")
        return cached

    logger.info(f"🔍 Buscando pedidos pagos: {date_from} → {date_to}")
    pedidos = {}
    offset = 0
    total_rows = 0
    start = time.time()

    while True:
        try:
            r = requests.get(
                f"{_get_supabase_url()}/rest/v1/pedidos_consolidado"
                f"?select=id_pedido,total,total_pago,email_contato,origem_pedido,"
                f"metodo_pagamento,pago_em,estado_entrega,cidade_entrega,"
                f"nome_contato,codigo_cupom,tipo_cupom,desconto"
                f"&status_pagamento=eq.paid"
                f"&pago_em=gte.{date_from}T00:00:00"
                f"&pago_em=lte.{date_to}T23:59:59"
                f"&order=pago_em.asc"
                f"&limit={PAGE_SIZE}&offset={offset}",
                headers=_get_headers(),
                timeout=15
            )

            if r.status_code != 200:
                logger.error(f"Erro ao buscar pedidos (offset={offset}): {r.text[:200]}")
                break

            data = r.json()
            if not data:
                break

            total_rows += len(data)

            for row in data:
                pid = row['id_pedido']
                if pid not in pedidos:
                    pedidos[pid] = {
                        'total': float(row.get('total') or row.get('total_pago') or 0),
                        'email': (row.get('email_contato') or '').lower().strip(),
                        'nome': row.get('nome_contato', ''),
                        'origem': row.get('origem_pedido') or 'unknown',
                        'metodo': row.get('metodo_pagamento') or 'unknown',
                        'pago_em': (row.get('pago_em') or '')[:10],
                        'estado': row.get('estado_entrega') or 'Desconhecido',
                        'cidade': row.get('cidade_entrega') or '',
                        'cupom': row.get('codigo_cupom') or '',
                        'desconto': float(row.get('desconto') or 0),
                    }

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
    logger.info(f"✅ {len(pedidos)} pedidos únicos ({total_rows} linhas) em {elapsed:.1f}s")

    _set_cache(cache_key, pedidos)
    return pedidos


def _fetch_produtos_pedidos(date_from: str, date_to: str) -> List[Dict]:
    """
    Busca todos os produtos dos pedidos pagos no período.
    Usado para análise de top produtos.
    """
    cache_key = f"produtos_{date_from}_{date_to}"
    cached = _get_cache(cache_key)
    if cached is not None:
        return cached

    logger.info(f"🛍️ Buscando produtos: {date_from} → {date_to}")
    produtos = []
    offset = 0

    while True:
        try:
            r = requests.get(
                f"{_get_supabase_url()}/rest/v1/pedidos_consolidado"
                f"?select=id_pedido,nome_produto,nome_produto_simples,sku_produto,quantidade,preco"
                f"&status_pagamento=eq.paid"
                f"&pago_em=gte.{date_from}T00:00:00"
                f"&pago_em=lte.{date_to}T23:59:59"
                f"&order=pago_em.asc"
                f"&limit={PAGE_SIZE}&offset={offset}",
                headers=_get_headers(),
                timeout=15
            )

            if r.status_code != 200:
                break

            data = r.json()
            if not data:
                break

            produtos.extend(data)
            offset += PAGE_SIZE

            if len(data) < PAGE_SIZE:
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

    receita_total = sum(p['total'] for p in pedidos.values())
    total_pedidos = len(pedidos)
    clientes_unicos = len(set(p['email'] for p in pedidos.values() if p['email']))

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

    for p in pedidos.values():
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

    for p in pedidos.values():
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

    for p in pedidos.values():
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

    # Busca os dados base uma única vez
    pedidos = _fetch_pedidos_pagos(date_from, date_to)

    # Calcula todas as métricas a partir dos dados em memória
    receita_total = sum(p['total'] for p in pedidos.values())
    total_pedidos = len(pedidos)
    clientes_unicos = len(set(p['email'] for p in pedidos.values() if p['email']))

    # Timeline
    timeline_data = defaultdict(lambda: {"pedidos": 0, "receita": 0.0})
    por_origem = defaultdict(lambda: {"pedidos": 0, "receita": 0.0})
    por_metodo = defaultdict(lambda: {"pedidos": 0, "receita": 0.0})
    por_estado = defaultdict(lambda: {"pedidos": 0, "receita": 0.0})

    for p in pedidos.values():
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

    # Top produtos (busca separada)
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
