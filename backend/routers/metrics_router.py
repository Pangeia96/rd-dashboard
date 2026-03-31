"""
metrics_router.py — Rotas de Métricas Processadas
--------------------------------------------------
Este arquivo expõe os endpoints com dados já processados e prontos
para exibição no dashboard Vue.js. Ao contrário do data_router
(que retorna dados brutos), este router retorna métricas calculadas:
taxas, percentuais, rankings e cruzamentos.

Rotas disponíveis:
  GET /metrics/emails          → Métricas processadas de e-mail
  GET /metrics/whatsapp        → Métricas processadas de WhatsApp
  GET /metrics/automations     → Funil de cada fluxo de automação
  GET /metrics/sales           → Receita cruzada RD Station × NuvemShop
  GET /metrics/timeline        → Timeline de vendas por dia
  GET /metrics/dashboard       → Resumo consolidado para o painel principal
"""

from fastapi import APIRouter, HTTPException, Query
from loguru import logger
from datetime import date, datetime
import asyncio

from services.rd_service import rd_service
from services.nuvemshop_service import nuvemshop_service, NuvemShopService
from services.metrics_service import metrics_service
from services.auth_service import auth_service

# Cache simples em memória para o endpoint /dashboard
# Evita buscar todos os pedidos a cada requisição
_dashboard_cache: dict = {}
_CACHE_TTL_SECONDS = 300  # 5 minutos

router = APIRouter(prefix="/metrics", tags=["Métricas Processadas"])


def check_auth():
    if not auth_service.is_authenticated:
        raise HTTPException(
            status_code=401,
            detail="Não autenticado com a RD Station. Acesse /auth/login primeiro.",
        )


# ----------------------------------------------------------------
# MÉTRICAS DE E-MAIL
# ----------------------------------------------------------------

@router.get("/emails", summary="Métricas processadas de campanhas de e-mail")
async def get_email_metrics():
    """
    Retorna todas as campanhas de e-mail com métricas calculadas:
    taxa de abertura, clique, conversão e classificação de desempenho.
    """
    check_auth()
    logger.info("📊 Calculando métricas de e-mail...")
    try:
        campaigns_raw = await rd_service.get_all_email_reports()
        processed = metrics_service.process_email_metrics(campaigns_raw)
        return {
            "status": "ok",
            "total": len(processed),
            "campaigns": processed,
            "summary": {
                "avg_open_rate": round(
                    sum(c["open_rate"] for c in processed) / len(processed), 1
                ) if processed else 0,
                "avg_click_rate": round(
                    sum(c["click_rate"] for c in processed) / len(processed), 1
                ) if processed else 0,
                "best_campaign": max(processed, key=lambda x: x["open_rate"])
                if processed else None,
            },
        }
    except Exception as e:
        logger.error(f"❌ Erro em /metrics/emails: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ----------------------------------------------------------------
# MÉTRICAS DE WHATSAPP
# ----------------------------------------------------------------

@router.get("/whatsapp", summary="Métricas processadas de WhatsApp")
async def get_whatsapp_metrics():
    """
    Retorna métricas agregadas de WhatsApp:
    taxa de entrega, leitura, resposta e engajamento geral.
    """
    check_auth()
    logger.info("📊 Calculando métricas de WhatsApp...")
    try:
        events_raw = await rd_service.get_all_whatsapp_events()
        processed = metrics_service.process_whatsapp_metrics(events_raw)
        return {"status": "ok", "metrics": processed}
    except Exception as e:
        logger.error(f"❌ Erro em /metrics/whatsapp: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ----------------------------------------------------------------
# FUNIL DE AUTOMAÇÃO
# ----------------------------------------------------------------

@router.get("/automations", summary="Funil de cada fluxo de automação")
async def get_automation_funnels():
    """
    Retorna o funil de cada fluxo de automação:
    leads por etapa, taxa de avanço e taxa de abandono.
    """
    check_auth()
    logger.info("📊 Calculando funis de automação...")
    try:
        automations_raw = await rd_service.get_all_automations_with_details()
        processed = metrics_service.process_automation_funnel(automations_raw)
        return {
            "status": "ok",
            "total": len(processed),
            "automations": processed,
        }
    except Exception as e:
        logger.error(f"❌ Erro em /metrics/automations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ----------------------------------------------------------------
# RECEITA CRUZADA (RD Station × NuvemShop)
# ----------------------------------------------------------------

@router.get("/sales", summary="Receita por fluxo, etapa e canal")
async def get_sales_metrics(
    date_from: str = Query(default=None, description="Data de início (YYYY-MM-DD)"),
    date_to: str = Query(default=None, description="Data de fim (YYYY-MM-DD)"),
):
    """
    Cruza os pedidos pagos da NuvemShop com os dados da RD Station.
    Retorna receita atribuída por fluxo de automação, etapa e canal
    (e-mail vs WhatsApp).
    """
    logger.info("📊 Calculando receita cruzada RD Station × NuvemShop...")
    try:
        # Cria instância fresca para aplicar filtros de data
        ns = NuvemShopService()
        if date_from:
            ns.date_from = date_from
        if date_to:
            ns.date_to = date_to

        # Busca dados em paralelo
        orders = await ns.get_all_orders_normalized()

        contacts = []
        automations = []
        email_campaigns = []

        if auth_service.is_authenticated:
            try:
                contacts_raw = await rd_service.get_contacts()
                contacts = contacts_raw if isinstance(contacts_raw, list) else \
                    contacts_raw.get("contacts", [])
            except Exception as e:
                logger.warning(f"⚠️  Não foi possível buscar contatos RD: {e}")

            try:
                automations = await rd_service.get_automations()
            except Exception as e:
                logger.warning(f"⚠️  Não foi possível buscar automações: {e}")

            try:
                email_campaigns = await rd_service.get_email_campaigns()
            except Exception as e:
                logger.warning(f"⚠️  Não foi possível buscar campanhas: {e}")

        # Calcula cruzamento
        cross = metrics_service.cross_reference_sales(
            orders=orders,
            contacts=contacts,
            automations=automations,
            email_campaigns=email_campaigns,
        )

        # Resumo de vendas NuvemShop
        sales_summary = nuvemshop_service.calculate_sales_summary(orders)

        return {
            "status": "ok",
            "period": {
                "from": ns.date_from,
                "to": ns.date_to,
            },
            "nuvemshop_summary": sales_summary,
            "attribution": cross,
        }
    except Exception as e:
        logger.error(f"❌ Erro em /metrics/sales: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ----------------------------------------------------------------
# TIMELINE DE VENDAS
# ----------------------------------------------------------------

@router.get("/timeline", summary="Timeline de vendas por dia")
async def get_sales_timeline(
    date_from: str = Query(default=None, description="Data de início (YYYY-MM-DD)"),
    date_to: str = Query(default=None, description="Data de fim (YYYY-MM-DD)"),
):
    """
    Retorna a evolução diária de vendas e receita.
    Usado para construir o gráfico de linha temporal no dashboard.
    """
    logger.info("📊 Construindo timeline de vendas...")
    try:
        ns = NuvemShopService()
        if date_from:
            ns.date_from = date_from
        if date_to:
            ns.date_to = date_to

        orders = await ns.get_all_orders_normalized()
        timeline = metrics_service.build_sales_timeline(orders)

        return {
            "status": "ok",
            "period": {"from": ns.date_from, "to": ns.date_to},
            "total_days": len(timeline),
            "timeline": timeline,
        }
    except Exception as e:
        logger.error(f"❌ Erro em /metrics/timeline: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ----------------------------------------------------------------
# RESUMO CONSOLIDADO — PAINEL PRINCIPAL
# ----------------------------------------------------------------

@router.get("/dashboard", summary="Resumo consolidado para o painel principal")
async def get_dashboard_metrics(
    quick: bool = Query(default=False, description="Se true, retorna apenas dados recentes (rápido)")
):
    """
    Endpoint principal do dashboard. Retorna todas as métricas
    consolidadas em um único objeto para alimentar o painel inicial.

    - quick=true: retorna dados dos últimos 30 dias imediatamente (< 5s)
    - quick=false: retorna dados completos do período configurado (pode demorar)
    Usa cache de 5 minutos para evitar chamadas repetidas à API.
    """
    global _dashboard_cache

    # Verifica se existe cache válido
    cache_key = f"dashboard_{'quick' if quick else 'full'}"
    now = datetime.now().timestamp()
    if cache_key in _dashboard_cache:
        cached = _dashboard_cache[cache_key]
        if now - cached["timestamp"] < _CACHE_TTL_SECONDS:
            logger.info(f"⚡ Retornando dashboard do cache [{cache_key}] (TTL: 5min)")
            return cached["data"]

    logger.info(f"📊 Gerando resumo consolidado do dashboard [quick={quick}]...")
    try:
        # Para modo rápido, usa apenas últimos 30 dias (1 página)
        if quick:
            from datetime import timedelta
            quick_service = NuvemShopService()
            quick_service.date_from = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            orders = await quick_service.get_all_orders_normalized()
        else:
            # Coleta dados de todas as fontes
            orders = await nuvemshop_service.get_all_orders_normalized()
        timeline = metrics_service.build_sales_timeline(orders)

        automations_processed = []
        email_metrics = []
        whatsapp_metrics = metrics_service.process_whatsapp_metrics([])
        sales_cross = metrics_service.cross_reference_sales(orders, [], [], [])

        if auth_service.is_authenticated:
            try:
                automations_raw = await rd_service.get_automations()
                automations_processed = metrics_service.process_automation_funnel(automations_raw)
            except Exception as e:
                logger.warning(f"⚠️  Automações não disponíveis: {e}")

            try:
                campaigns_raw = await rd_service.get_email_campaigns()
                email_metrics = metrics_service.process_email_metrics(campaigns_raw)
            except Exception as e:
                logger.warning(f"⚠️  E-mails não disponíveis: {e}")

            try:
                wpp_events = await rd_service.get_all_whatsapp_events()
                whatsapp_metrics = metrics_service.process_whatsapp_metrics(wpp_events)
            except Exception as e:
                logger.warning(f"⚠️  WhatsApp não disponível: {e}")

            try:
                contacts_raw = await rd_service.get_contacts()
                contacts = contacts_raw if isinstance(contacts_raw, list) else \
                    contacts_raw.get("contacts", [])
                automations_list = await rd_service.get_automations()
                campaigns_list = await rd_service.get_email_campaigns()
                sales_cross = metrics_service.cross_reference_sales(
                    orders, contacts, automations_list, campaigns_list
                )
            except Exception as e:
                logger.warning(f"⚠️  Cruzamento parcial: {e}")

        summary = metrics_service.build_dashboard_summary(
            automations_processed=automations_processed,
            email_metrics=email_metrics,
            whatsapp_metrics=whatsapp_metrics,
            sales_cross=sales_cross,
            timeline=timeline,
        )

        result = {"status": "ok", **summary}

        # Armazena no cache
        _dashboard_cache[cache_key] = {
            "timestamp": datetime.now().timestamp(),
            "data": result,
        }
        logger.info("✅ Dashboard gerado e armazenado em cache por 5 minutos")
        return result

    except Exception as e:
        logger.error(f"❌ Erro em /metrics/dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))
