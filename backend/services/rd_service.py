"""
rd_service.py — Serviço de Coleta de Dados da RD Station Marketing
-------------------------------------------------------------------
Este módulo é responsável por buscar todos os dados relevantes da API
da RD Station Marketing. Ele consome os seguintes endpoints:

  1. /marketing/automations          → Lista todos os fluxos de automação
  2. /marketing/automations/{id}     → Detalha etapas de um fluxo específico
  3. /marketing/email_marketing      → Campanhas de e-mail (disparos manuais)
  4. /platform/conversions           → Eventos de conversão dos leads
  5. /platform/events                → Eventos gerais (inclui WhatsApp)

Cada método busca os dados, trata erros e retorna os resultados
de forma padronizada para o processamento posterior.
"""

from loguru import logger
from datetime import date
from config import get_settings
from services.auth_service import auth_service

settings = get_settings()


class RDService:
    """
    Serviço centralizado para todas as chamadas à API da RD Station.
    Usa o auth_service para autenticação automática com renovação de token.
    """

    def __init__(self):
        self.date_from = settings.default_date_from
        self.date_to = date.today().isoformat()

    # ----------------------------------------------------------------
    # 1. FLUXOS DE AUTOMAÇÃO
    # ----------------------------------------------------------------

    async def get_automations(self) -> list:
        """
        Busca todos os fluxos de automação da conta.
        Retorna uma lista com nome, status e ID de cada fluxo.

        Endpoint: GET /marketing/automations
        """
        logger.info("📋 Buscando fluxos de automação...")
        try:
            data = await auth_service.make_api_request("GET", "/marketing/automations")
            automations = data if isinstance(data, list) else data.get("automations", [])
            logger.info(f"✅ {len(automations)} fluxos encontrados")
            return automations
        except Exception as e:
            logger.error(f"❌ Erro ao buscar automações: {e}")
            return []

    async def get_automation_detail(self, automation_id: str) -> dict:
        """
        Busca os detalhes e etapas de um fluxo específico.
        Retorna as etapas do fluxo com contagem de leads em cada uma.

        Endpoint: GET /marketing/automations/{id}
        """
        logger.info(f"🔍 Buscando detalhes do fluxo {automation_id}...")
        try:
            data = await auth_service.make_api_request(
                "GET", f"/marketing/automations/{automation_id}"
            )
            return data
        except Exception as e:
            logger.error(f"❌ Erro ao buscar detalhes do fluxo {automation_id}: {e}")
            return {}

    async def get_all_automations_with_details(self) -> list:
        """
        Busca todos os fluxos e seus detalhes em sequência.
        Retorna lista completa com etapas de cada fluxo.
        Respeita o rate limit da API (240 req/min) com pausas entre chamadas.
        """
        import asyncio
        automations = await self.get_automations()
        detailed = []

        for automation in automations:
            automation_id = automation.get("id") or automation.get("uuid")
            if automation_id:
                detail = await self.get_automation_detail(str(automation_id))
                if detail:
                    detailed.append({**automation, **detail})
                # Pequena pausa para respeitar o rate limit da API (240 req/min)
                await asyncio.sleep(0.3)

        logger.info(f"✅ Detalhes carregados para {len(detailed)} fluxos")
        return detailed

    # ----------------------------------------------------------------
    # 2. CAMPANHAS DE E-MAIL (disparos manuais e automáticos)
    # ----------------------------------------------------------------

    async def get_email_campaigns(self) -> list:
        """
        Busca todas as campanhas de e-mail (disparos manuais e automáticos).
        Inclui: nome da campanha, data de envio, status.

        Endpoint: GET /marketing/email_marketing
        """
        logger.info("📧 Buscando campanhas de e-mail...")
        try:
            params = {
                "page": 1,
                "per_page": 100,
            }
            data = await auth_service.make_api_request(
                "GET", "/marketing/email_marketing", params=params
            )
            campaigns = data if isinstance(data, list) else data.get("email_marketing", [])
            logger.info(f"✅ {len(campaigns)} campanhas de e-mail encontradas")
            return campaigns
        except Exception as e:
            logger.error(f"❌ Erro ao buscar campanhas de e-mail: {e}")
            return []

    async def get_email_campaign_report(self, campaign_id: str) -> dict:
        """
        Busca o relatório detalhado de uma campanha de e-mail específica.
        Retorna: enviados, entregues, abertos, clicados, descadastros, bounces.

        Endpoint: GET /marketing/email_marketing/{id}/report
        """
        logger.info(f"📊 Buscando relatório da campanha {campaign_id}...")
        try:
            data = await auth_service.make_api_request(
                "GET", f"/marketing/email_marketing/{campaign_id}/report"
            )
            return data
        except Exception as e:
            logger.error(f"❌ Erro ao buscar relatório da campanha {campaign_id}: {e}")
            return {}

    async def get_all_email_reports(self) -> list:
        """
        Busca relatórios de todas as campanhas de e-mail.
        Combina dados da campanha com métricas de desempenho.
        """
        import asyncio
        campaigns = await self.get_email_campaigns()
        reports = []

        for campaign in campaigns:
            campaign_id = campaign.get("id") or campaign.get("uuid")
            if campaign_id:
                report = await self.get_email_campaign_report(str(campaign_id))
                if report:
                    reports.append({**campaign, "report": report})
                await asyncio.sleep(0.3)  # respeita rate limit

        logger.info(f"✅ Relatórios carregados para {len(reports)} campanhas")
        return reports

    # ----------------------------------------------------------------
    # 3. CONVERSÕES
    # ----------------------------------------------------------------

    async def get_conversions(self, page: int = 1, per_page: int = 100) -> dict:
        """
        Busca eventos de conversão dos leads no período configurado.
        Conversões são ações importantes que os leads realizaram
        (ex: preencheu formulário, clicou em link, comprou).

        Endpoint: GET /platform/conversions
        """
        logger.info(f"🎯 Buscando conversões (página {page})...")
        try:
            params = {
                "page": page,
                "per_page": per_page,
            }
            data = await auth_service.make_api_request(
                "GET", "/platform/conversions", params=params
            )
            return data
        except Exception as e:
            logger.error(f"❌ Erro ao buscar conversões: {e}")
            return {"conversions": [], "total": 0}

    async def get_all_conversions(self) -> list:
        """
        Busca todas as conversões paginando automaticamente.
        Continua buscando páginas até não haver mais resultados.
        """
        all_conversions = []
        page = 1

        while True:
            data = await self.get_conversions(page=page, per_page=100)
            items = data if isinstance(data, list) else data.get("conversions", [])

            if not items:
                break

            all_conversions.extend(items)
            logger.info(f"   → Página {page}: {len(items)} conversões carregadas")

            # Se retornou menos que o máximo, chegamos na última página
            if len(items) < 100:
                break

            page += 1

        logger.info(f"✅ Total de conversões carregadas: {len(all_conversions)}")
        return all_conversions

    # ----------------------------------------------------------------
    # 4. EVENTOS (WhatsApp e outros)
    # ----------------------------------------------------------------

    async def get_whatsapp_events(self, page: int = 1, per_page: int = 100) -> dict:
        """
        Busca eventos de WhatsApp dos leads.
        Inclui: disparos, visualizações, respostas e cliques.

        Endpoint: GET /platform/events?event_type=whatsapp
        """
        logger.info(f"💬 Buscando eventos de WhatsApp (página {page})...")
        try:
            params = {
                "event_type": "whatsapp",
                "page": page,
                "per_page": per_page,
            }
            data = await auth_service.make_api_request(
                "GET", "/platform/events", params=params
            )
            return data
        except Exception as e:
            logger.error(f"❌ Erro ao buscar eventos de WhatsApp: {e}")
            return {"events": [], "total": 0}

    async def get_all_whatsapp_events(self) -> list:
        """
        Busca todos os eventos de WhatsApp paginando automaticamente.
        """
        all_events = []
        page = 1

        while True:
            data = await self.get_whatsapp_events(page=page, per_page=100)
            items = data if isinstance(data, list) else data.get("events", [])

            if not items:
                break

            all_events.extend(items)
            logger.info(f"   → Página {page}: {len(items)} eventos WhatsApp carregados")

            if len(items) < 100:
                break

            page += 1

        logger.info(f"✅ Total de eventos WhatsApp: {len(all_events)}")
        return all_events

    async def get_general_events(
        self, event_type: str = None, page: int = 1, per_page: int = 100
    ) -> dict:
        """
        Busca eventos gerais da plataforma RD Station.
        Pode filtrar por tipo de evento (ex: 'Sale', 'PageVisit', etc.)

        Endpoint: GET /platform/events
        """
        logger.info(f"📡 Buscando eventos gerais (tipo: {event_type or 'todos'}, página {page})...")
        try:
            params = {"page": page, "per_page": per_page}
            if event_type:
                params["event_type"] = event_type

            data = await auth_service.make_api_request(
                "GET", "/platform/events", params=params
            )
            return data
        except Exception as e:
            logger.error(f"❌ Erro ao buscar eventos gerais: {e}")
            return {"events": [], "total": 0}

    # ----------------------------------------------------------------
    # 5. CONTATOS
    # ----------------------------------------------------------------

    async def get_contacts(
        self,
        page: int = 1,
        per_page: int = 100,
        email: str = None,
    ) -> dict:
        """
        Busca contatos da base da RD Station.
        Pode filtrar por e-mail para cruzar com dados da NuvemShop.

        Endpoint: GET /platform/contacts
        """
        logger.info(f"👤 Buscando contatos (página {page})...")
        try:
            params = {"page": page, "per_page": per_page}
            if email:
                params["email"] = email

            data = await auth_service.make_api_request(
                "GET", "/platform/contacts", params=params
            )
            return data
        except Exception as e:
            logger.error(f"❌ Erro ao buscar contatos: {e}")
            return {"contacts": [], "total": 0}


# Instância global do serviço RD Station
rd_service = RDService()
