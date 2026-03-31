"""
data_router.py — Rotas de Coleta e Exposição de Dados
------------------------------------------------------
Este arquivo define os endpoints que o frontend Vue.js vai consumir
para exibir os dados no dashboard. Cada rota busca os dados da
RD Station e/ou NuvemShop e retorna em formato JSON padronizado.

Rotas disponíveis:
  GET /data/automations          → Todos os fluxos de automação
  GET /data/automations/{id}     → Detalhes de um fluxo específico
  GET /data/emails               → Campanhas de e-mail com métricas
  GET /data/whatsapp             → Eventos de WhatsApp
  GET /data/conversions          → Conversões de leads
  GET /data/orders               → Pedidos da NuvemShop (vendas)
  GET /data/summary              → Resumo geral para o painel principal
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from loguru import logger
from datetime import date

from services.rd_service import rd_service
from services.nuvemshop_service import nuvemshop_service
from services.auth_service import auth_service

# Cria o roteador de dados
router = APIRouter(prefix="/data", tags=["Dados do Dashboard"])


def check_auth():
    """Verifica se o sistema está autenticado antes de buscar dados."""
    if not auth_service.is_authenticated:
        raise HTTPException(
            status_code=401,
            detail="Não autenticado com a RD Station. Acesse /auth/login primeiro.",
        )


# ----------------------------------------------------------------
# FLUXOS DE AUTOMAÇÃO
# ----------------------------------------------------------------

@router.get("/automations", summary="Listar todos os fluxos de automação")
async def get_automations():
    """
    Retorna todos os fluxos de automação configurados na RD Station.
    Inclui: nome, status (ativo/inativo), número de contatos em cada etapa.
    """
    check_auth()
    logger.info("🔄 Requisição: GET /data/automations")
    try:
        data = await rd_service.get_automations()
        return {"status": "ok", "total": len(data), "automations": data}
    except Exception as e:
        logger.error(f"❌ Erro em /data/automations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/automations/{automation_id}", summary="Detalhes de um fluxo de automação")
async def get_automation_detail(automation_id: str):
    """
    Retorna os detalhes e etapas de um fluxo de automação específico.
    Inclui: cada etapa do fluxo, quantos leads estão em cada etapa,
    taxa de avanço entre etapas.
    """
    check_auth()
    logger.info(f"🔄 Requisição: GET /data/automations/{automation_id}")
    try:
        data = await rd_service.get_automation_detail(automation_id)
        if not data:
            raise HTTPException(status_code=404, detail=f"Fluxo {automation_id} não encontrado")
        return {"status": "ok", "automation": data}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro em /data/automations/{automation_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ----------------------------------------------------------------
# CAMPANHAS DE E-MAIL
# ----------------------------------------------------------------

@router.get("/emails", summary="Campanhas de e-mail com métricas de desempenho")
async def get_email_campaigns():
    """
    Retorna todas as campanhas de e-mail (manuais e automáticas) com métricas:
    - Enviados, Entregues, Abertos, Clicados
    - Taxa de abertura (%)
    - Taxa de clique (%)
    - Descadastros e bounces
    """
    check_auth()
    logger.info("🔄 Requisição: GET /data/emails")
    try:
        data = await rd_service.get_all_email_reports()
        return {"status": "ok", "total": len(data), "campaigns": data}
    except Exception as e:
        logger.error(f"❌ Erro em /data/emails: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ----------------------------------------------------------------
# EVENTOS DE WHATSAPP
# ----------------------------------------------------------------

@router.get("/whatsapp", summary="Eventos de WhatsApp (disparos, visualizações, respostas)")
async def get_whatsapp_events():
    """
    Retorna todos os eventos de WhatsApp registrados na RD Station.
    Inclui: disparos, visualizações, respostas e cliques em links.
    """
    check_auth()
    logger.info("🔄 Requisição: GET /data/whatsapp")
    try:
        data = await rd_service.get_all_whatsapp_events()
        return {"status": "ok", "total": len(data), "events": data}
    except Exception as e:
        logger.error(f"❌ Erro em /data/whatsapp: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ----------------------------------------------------------------
# CONVERSÕES
# ----------------------------------------------------------------

@router.get("/conversions", summary="Eventos de conversão dos leads")
async def get_conversions():
    """
    Retorna todos os eventos de conversão dos leads.
    Conversões são ações importantes como: preenchimento de formulário,
    clique em link de compra, conclusão de compra, etc.
    """
    check_auth()
    logger.info("🔄 Requisição: GET /data/conversions")
    try:
        data = await rd_service.get_all_conversions()
        return {"status": "ok", "total": len(data), "conversions": data}
    except Exception as e:
        logger.error(f"❌ Erro em /data/conversions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ----------------------------------------------------------------
# PEDIDOS NUVEMSHOP (VENDAS)
# ----------------------------------------------------------------

@router.get("/orders", summary="Pedidos da NuvemShop (vendas do e-commerce)")
async def get_orders(
    date_from: str = Query(
        default=None,
        description="Data de início (YYYY-MM-DD). Padrão: setembro/2025",
        example="2025-09-01",
    ),
    date_to: str = Query(
        default=None,
        description="Data de fim (YYYY-MM-DD). Padrão: hoje",
        example="2026-03-31",
    ),
):
    """
    Retorna todos os pedidos (vendas) da loja NuvemShop no período.
    Inclui: valor total, e-mail do cliente, produtos, status do pagamento.
    Esses dados são cruzados com a RD Station para calcular receita por campanha.
    """
    logger.info("🔄 Requisição: GET /data/orders")
    try:
        # Aplica filtros de data se fornecidos
        if date_from:
            nuvemshop_service.date_from = date_from
        if date_to:
            nuvemshop_service.date_to = date_to

        data = await nuvemshop_service.get_all_orders_normalized()
        summary = nuvemshop_service.calculate_sales_summary(data)

        return {
            "status": "ok",
            "period": {
                "from": nuvemshop_service.date_from,
                "to": nuvemshop_service.date_to,
            },
            "summary": summary,
            "orders": data,
        }
    except Exception as e:
        logger.error(f"❌ Erro em /data/orders: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ----------------------------------------------------------------
# RESUMO GERAL (painel principal do dashboard)
# ----------------------------------------------------------------

@router.get("/summary", summary="Resumo geral para o painel principal")
async def get_summary():
    """
    Retorna um resumo consolidado de todas as fontes de dados.
    Este é o endpoint principal consumido pela tela inicial do dashboard.
    Inclui:
    - Total de fluxos ativos
    - Total de campanhas de e-mail
    - Total de conversões
    - Total de pedidos e receita (NuvemShop)
    - Status da autenticação
    """
    logger.info("🔄 Requisição: GET /data/summary")

    summary = {
        "status": "ok",
        "generated_at": date.today().isoformat(),
        "authenticated_rd": auth_service.is_authenticated,
        "automations": {"total": 0, "error": None},
        "emails": {"total": 0, "error": None},
        "whatsapp": {"total": 0, "error": None},
        "conversions": {"total": 0, "error": None},
        "orders": {"total": 0, "total_revenue": 0.0, "error": None},
    }

    # Busca dados em paralelo para ser mais rápido
    if auth_service.is_authenticated:
        try:
            automations = await rd_service.get_automations()
            summary["automations"]["total"] = len(automations)
        except Exception as e:
            summary["automations"]["error"] = str(e)

        try:
            campaigns = await rd_service.get_email_campaigns()
            summary["emails"]["total"] = len(campaigns)
        except Exception as e:
            summary["emails"]["error"] = str(e)

    # Pedidos NuvemShop (não precisa de autenticação RD)
    try:
        orders = await nuvemshop_service.get_all_orders_normalized()
        sales = nuvemshop_service.calculate_sales_summary(orders)
        summary["orders"]["total"] = sales["total_orders"]
        summary["orders"]["total_revenue"] = sales["total_revenue"]
        summary["orders"]["average_ticket"] = sales["average_ticket"]
        summary["orders"]["unique_customers"] = sales["unique_customers"]
    except Exception as e:
        summary["orders"]["error"] = str(e)

    return summary
