"""
metrics_service.py — Motor de Processamento e Cálculo de Métricas
-----------------------------------------------------------------
Este módulo é o cérebro analítico do dashboard. Ele recebe os dados
brutos da RD Station e da NuvemShop e os transforma em métricas
prontas para exibição no painel visual.

Métricas calculadas:
  1. Funil por fluxo de automação (leads por etapa, taxa de avanço)
  2. Métricas de e-mail (taxa de abertura, clique, conversão)
  3. Métricas de WhatsApp (disparos, visualizações, respostas, engajamento)
  4. Cruzamento RD Station × NuvemShop (receita por fluxo/etapa/canal)
  5. Timeline de vendas ao longo do tempo
  6. Ranking de fluxos por receita gerada

Como funciona o cruzamento (em linguagem simples):
  → Pegamos todos os pedidos PAGOS da NuvemShop
  → Para cada pedido, temos o e-mail do cliente
  → Buscamos esse e-mail na RD Station para saber:
      - Em qual fluxo de automação esse lead estava
      - Qual etapa do fluxo ele havia recebido antes de comprar
      - Qual canal (e-mail ou WhatsApp) foi o último contato antes da compra
  → Com isso, calculamos: receita por fluxo, receita por etapa, receita por canal
"""

from collections import defaultdict
from datetime import datetime, date
from typing import List, Dict, Any, Optional
from loguru import logger


class MetricsService:
    """
    Serviço de processamento e cálculo de métricas do dashboard.
    Recebe dados brutos e retorna métricas estruturadas.
    """

    # ----------------------------------------------------------------
    # 1. MÉTRICAS DE E-MAIL
    # ----------------------------------------------------------------

    def process_email_metrics(self, campaigns: List[Dict]) -> List[Dict]:
        """
        Processa as campanhas de e-mail e calcula as métricas de desempenho.

        Para cada campanha, calcula:
          - Taxa de entrega = (entregues / enviados) × 100
          - Taxa de abertura = (abertos / entregues) × 100
          - Taxa de clique = (clicados / entregues) × 100
          - Taxa de conversão = (convertidos / entregues) × 100

        Em linguagem simples:
          "De cada 100 e-mails entregues, quantos foram abertos?
           Quantos clicaram no link? Quantos compraram?"
        """
        processed = []

        for campaign in campaigns:
            # Extrai o relatório (pode estar aninhado ou no nível raiz)
            report = campaign.get("report", campaign)

            # Extrai os contadores principais
            sent = self._to_int(report.get("sent") or report.get("total_sent", 0))
            delivered = self._to_int(
                report.get("delivered") or report.get("total_delivered", sent)
            )
            opened = self._to_int(
                report.get("opened")
                or report.get("unique_opens")
                or report.get("total_opened", 0)
            )
            clicked = self._to_int(
                report.get("clicked")
                or report.get("unique_clicks")
                or report.get("total_clicked", 0)
            )
            bounced = self._to_int(
                report.get("bounced") or report.get("total_bounced", 0)
            )
            unsubscribed = self._to_int(
                report.get("unsubscribed") or report.get("total_unsubscribed", 0)
            )

            # Calcula as taxas (evita divisão por zero)
            base = delivered if delivered > 0 else sent
            delivery_rate = self._pct(delivered, sent)
            open_rate = self._pct(opened, base)
            click_rate = self._pct(clicked, base)
            click_to_open_rate = self._pct(clicked, opened)  # CTOR
            bounce_rate = self._pct(bounced, sent)
            unsubscribe_rate = self._pct(unsubscribed, base)

            processed.append({
                "id": campaign.get("id") or campaign.get("uuid", ""),
                "name": campaign.get("name") or campaign.get("subject", "Sem nome"),
                "type": campaign.get("type", "email"),
                "status": campaign.get("status", ""),
                "sent_at": campaign.get("sent_at") or campaign.get("scheduled_at", ""),
                "automation_id": campaign.get("automation_id", None),
                # Contadores absolutos
                "sent": sent,
                "delivered": delivered,
                "opened": opened,
                "clicked": clicked,
                "bounced": bounced,
                "unsubscribed": unsubscribed,
                # Taxas percentuais
                "delivery_rate": delivery_rate,
                "open_rate": open_rate,
                "click_rate": click_rate,
                "click_to_open_rate": click_to_open_rate,
                "bounce_rate": bounce_rate,
                "unsubscribe_rate": unsubscribe_rate,
                # Classificação de desempenho
                "performance": self._classify_email_performance(open_rate, click_rate),
            })

        # Ordena por data de envio (mais recente primeiro)
        processed.sort(key=lambda x: x.get("sent_at", ""), reverse=True)
        logger.info(f"✅ {len(processed)} campanhas de e-mail processadas")
        return processed

    def _classify_email_performance(self, open_rate: float, click_rate: float) -> str:
        """
        Classifica o desempenho de uma campanha de e-mail.
        Baseado em benchmarks do setor de e-commerce brasileiro.
        """
        if open_rate >= 25 and click_rate >= 3:
            return "excelente"
        elif open_rate >= 15 and click_rate >= 1.5:
            return "bom"
        elif open_rate >= 10:
            return "regular"
        else:
            return "abaixo_da_media"

    # ----------------------------------------------------------------
    # 2. MÉTRICAS DE WHATSAPP
    # ----------------------------------------------------------------

    def process_whatsapp_metrics(self, events: List[Dict]) -> Dict:
        """
        Processa os eventos de WhatsApp e calcula métricas de engajamento.

        Tipos de eventos esperados:
          - sent/dispatched: mensagem enviada
          - delivered: mensagem entregue
          - read/viewed: mensagem visualizada
          - replied: lead respondeu
          - clicked: lead clicou em link

        Retorna métricas agregadas e por dia.
        """
        if not events:
            return {
                "total_sent": 0,
                "total_delivered": 0,
                "total_read": 0,
                "total_replied": 0,
                "total_clicked": 0,
                "delivery_rate": 0.0,
                "read_rate": 0.0,
                "reply_rate": 0.0,
                "engagement_rate": 0.0,
                "by_day": [],
            }

        # Contadores por tipo de evento
        counters = defaultdict(int)
        by_day = defaultdict(lambda: defaultdict(int))

        for event in events:
            event_type = (
                event.get("event_type")
                or event.get("type")
                or event.get("name", "")
            ).lower()

            # Normaliza o tipo de evento
            if any(k in event_type for k in ["sent", "dispatch", "enviado"]):
                counters["sent"] += 1
            elif any(k in event_type for k in ["delivered", "entregue"]):
                counters["delivered"] += 1
            elif any(k in event_type for k in ["read", "viewed", "visualiz", "lido"]):
                counters["read"] += 1
            elif any(k in event_type for k in ["replied", "resposta", "respondeu"]):
                counters["replied"] += 1
            elif any(k in event_type for k in ["clicked", "clicou", "click"]):
                counters["clicked"] += 1

            # Agrupa por dia
            event_date = self._extract_date(event)
            if event_date:
                by_day[event_date][event_type] += 1

        sent = counters["sent"] or len(events)
        delivered = counters["delivered"] or sent
        read = counters["read"]
        replied = counters["replied"]
        clicked = counters["clicked"]

        # Converte by_day para lista ordenada
        daily_list = [
            {"date": d, **dict(counts)}
            for d, counts in sorted(by_day.items())
        ]

        result = {
            "total_sent": sent,
            "total_delivered": delivered,
            "total_read": read,
            "total_replied": replied,
            "total_clicked": clicked,
            "delivery_rate": self._pct(delivered, sent),
            "read_rate": self._pct(read, delivered),
            "reply_rate": self._pct(replied, delivered),
            "engagement_rate": self._pct(read + replied + clicked, sent),
            "by_day": daily_list,
        }

        logger.info(
            f"✅ WhatsApp processado: {sent} disparos | "
            f"{result['read_rate']}% lidos | {result['reply_rate']}% respondidos"
        )
        return result

    # ----------------------------------------------------------------
    # 3. FUNIL DE AUTOMAÇÃO
    # ----------------------------------------------------------------

    def process_automation_funnel(self, automations: List[Dict]) -> List[Dict]:
        """
        Processa os fluxos de automação e monta o funil de cada um.

        Para cada fluxo, calcula:
          - Quantos leads entraram no fluxo
          - Quantos estão em cada etapa
          - Taxa de avanço entre etapas (quantos % passaram para a próxima)
          - Taxa de abandono em cada etapa

        Em linguagem simples:
          "De 1000 leads que entraram no fluxo, 800 abriram o primeiro e-mail,
           500 clicaram, 200 foram para a etapa 2, e 50 compraram."
        """
        processed = []

        for automation in automations:
            steps = (
                automation.get("steps")
                or automation.get("stages")
                or automation.get("actions")
                or []
            )

            total_contacts = self._to_int(
                automation.get("total_contacts")
                or automation.get("contacts_count", 0)
            )

            # Processa cada etapa do fluxo
            processed_steps = []
            prev_count = total_contacts

            for i, step in enumerate(steps):
                step_contacts = self._to_int(
                    step.get("contacts_count")
                    or step.get("total_contacts")
                    or step.get("count", 0)
                )

                # Taxa de avanço em relação à etapa anterior
                advance_rate = self._pct(step_contacts, prev_count) if prev_count > 0 else 0
                # Taxa de abandono nesta etapa
                drop_rate = 100 - advance_rate if advance_rate > 0 else 0

                processed_steps.append({
                    "position": i + 1,
                    "name": (
                        step.get("name")
                        or step.get("title")
                        or step.get("action_type")
                        or f"Etapa {i + 1}"
                    ),
                    "type": step.get("type") or step.get("action_type", ""),
                    "contacts": step_contacts,
                    "advance_rate": advance_rate,
                    "drop_rate": drop_rate,
                })

                if step_contacts > 0:
                    prev_count = step_contacts

            processed.append({
                "id": str(automation.get("id") or automation.get("uuid", "")),
                "name": automation.get("name", "Fluxo sem nome"),
                "status": automation.get("status", ""),
                "total_contacts": total_contacts,
                "steps_count": len(steps),
                "steps": processed_steps,
                "created_at": automation.get("created_at", ""),
                "updated_at": automation.get("updated_at", ""),
            })

        logger.info(f"✅ {len(processed)} fluxos de automação processados")
        return processed

    # ----------------------------------------------------------------
    # 4. CRUZAMENTO RD STATION × NUVEMSHOP (receita por fluxo/etapa)
    # ----------------------------------------------------------------

    def cross_reference_sales(
        self,
        orders: List[Dict],
        contacts: List[Dict],
        automations: List[Dict],
        email_campaigns: List[Dict],
    ) -> Dict:
        """
        Cruza os pedidos pagos da NuvemShop com os dados da RD Station
        para calcular receita por fluxo de automação, por etapa e por canal.

        Lógica do cruzamento:
          1. Filtra apenas pedidos PAGOS
          2. Para cada pedido, busca o e-mail do cliente na RD Station
          3. Verifica em qual fluxo/etapa esse contato estava
          4. Acumula a receita por fluxo, etapa e canal

        Retorna:
          - revenue_by_automation: receita total por fluxo
          - revenue_by_channel: receita por canal (e-mail vs WhatsApp)
          - revenue_by_step: receita por etapa de cada fluxo
          - top_automations: ranking dos fluxos mais rentáveis
          - unattributed_revenue: receita de clientes não encontrados na RD Station
        """
        logger.info("🔄 Iniciando cruzamento RD Station × NuvemShop...")

        # Filtra apenas pedidos pagos
        paid_orders = [o for o in orders if o.get("payment_status") == "paid"]
        logger.info(f"   → {len(paid_orders)} pedidos pagos de {len(orders)} total")

        # Cria índice de contatos por e-mail para busca rápida
        contacts_by_email = {}
        for contact in contacts:
            email = (contact.get("email") or "").lower().strip()
            if email:
                contacts_by_email[email] = contact

        # Acumuladores de receita
        revenue_by_automation = defaultdict(lambda: {
            "automation_id": "",
            "automation_name": "Desconhecido",
            "revenue": 0.0,
            "orders_count": 0,
            "customers_count": set(),
        })
        revenue_by_channel = defaultdict(lambda: {"revenue": 0.0, "orders_count": 0})
        revenue_by_step = defaultdict(lambda: defaultdict(lambda: {
            "step_name": "",
            "revenue": 0.0,
            "orders_count": 0,
        }))
        unattributed_revenue = 0.0
        unattributed_count = 0

        for order in paid_orders:
            email = order.get("email", "").lower().strip()
            total = order.get("total", 0.0)

            # Busca o contato na RD Station pelo e-mail
            contact = contacts_by_email.get(email)

            if not contact:
                # Cliente não encontrado na RD Station
                unattributed_revenue += total
                unattributed_count += 1
                continue

            # Identifica o fluxo de automação do contato
            automation_id = (
                contact.get("automation_id")
                or contact.get("current_automation_id")
                or "sem_fluxo"
            )
            automation_name = self._find_automation_name(automation_id, automations)
            current_step = (
                contact.get("current_step")
                or contact.get("automation_step")
                or "Etapa desconhecida"
            )

            # Identifica o canal do último contato
            channel = self._identify_last_channel(contact, email_campaigns)

            # Acumula receita por fluxo
            revenue_by_automation[automation_id]["automation_id"] = automation_id
            revenue_by_automation[automation_id]["automation_name"] = automation_name
            revenue_by_automation[automation_id]["revenue"] += total
            revenue_by_automation[automation_id]["orders_count"] += 1
            revenue_by_automation[automation_id]["customers_count"].add(email)

            # Acumula receita por canal
            revenue_by_channel[channel]["revenue"] += total
            revenue_by_channel[channel]["orders_count"] += 1

            # Acumula receita por etapa
            revenue_by_step[automation_id][current_step]["step_name"] = current_step
            revenue_by_step[automation_id][current_step]["revenue"] += total
            revenue_by_step[automation_id][current_step]["orders_count"] += 1

        # Converte sets para contagens
        automation_list = []
        for auto_id, data in revenue_by_automation.items():
            automation_list.append({
                **data,
                "customers_count": len(data["customers_count"]),
                "average_ticket": round(
                    data["revenue"] / data["orders_count"], 2
                ) if data["orders_count"] > 0 else 0,
            })

        # Ordena por receita (maior primeiro)
        automation_list.sort(key=lambda x: x["revenue"], reverse=True)

        # Calcula totais gerais
        total_attributed_revenue = sum(a["revenue"] for a in automation_list)
        total_revenue = total_attributed_revenue + unattributed_revenue

        result = {
            "total_paid_orders": len(paid_orders),
            "total_revenue": round(total_revenue, 2),
            "attributed_revenue": round(total_attributed_revenue, 2),
            "unattributed_revenue": round(unattributed_revenue, 2),
            "attribution_rate": self._pct(total_attributed_revenue, total_revenue),
            "revenue_by_automation": automation_list,
            "revenue_by_channel": {
                k: {**v, "revenue": round(v["revenue"], 2)}
                for k, v in revenue_by_channel.items()
            },
            "revenue_by_step": {
                auto_id: list(steps.values())
                for auto_id, steps in revenue_by_step.items()
            },
            "top_automations": automation_list[:5],  # top 5
        }

        logger.info(
            f"✅ Cruzamento concluído: R$ {result['total_revenue']} total | "
            f"{result['attribution_rate']}% atribuído a fluxos"
        )
        return result

    def _find_automation_name(self, automation_id: str, automations: List[Dict]) -> str:
        """Busca o nome de um fluxo pelo ID."""
        for auto in automations:
            if str(auto.get("id") or auto.get("uuid", "")) == str(automation_id):
                return auto.get("name", f"Fluxo {automation_id}")
        return f"Fluxo {automation_id}"

    def _identify_last_channel(self, contact: Dict, email_campaigns: List[Dict]) -> str:
        """
        Identifica o último canal de contato antes da compra.
        Retorna 'email', 'whatsapp' ou 'organico'.
        """
        last_interaction = contact.get("last_interaction") or {}
        channel = last_interaction.get("channel", "").lower()

        if "whatsapp" in channel:
            return "whatsapp"
        elif "email" in channel:
            return "email"

        # Tenta identificar pelo histórico de conversões
        conversions = contact.get("conversions", [])
        for conv in reversed(conversions):
            source = (conv.get("source") or "").lower()
            if "whatsapp" in source:
                return "whatsapp"
            elif "email" in source:
                return "email"

        return "organico"

    # ----------------------------------------------------------------
    # 5. TIMELINE DE VENDAS
    # ----------------------------------------------------------------

    def build_sales_timeline(self, orders: List[Dict]) -> List[Dict]:
        """
        Agrupa as vendas por dia para construir o gráfico de timeline.
        Retorna lista ordenada por data com receita e quantidade diária.

        Filtra apenas pedidos pagos.
        """
        paid_orders = [o for o in orders if o.get("payment_status") == "paid"]

        daily = defaultdict(lambda: {"revenue": 0.0, "orders": 0, "customers": set()})

        for order in paid_orders:
            date_str = self._extract_date(order, field="created_at")
            if date_str:
                daily[date_str]["revenue"] += order.get("total", 0.0)
                daily[date_str]["orders"] += 1
                daily[date_str]["customers"].add(order.get("email", ""))

        timeline = [
            {
                "date": d,
                "revenue": round(data["revenue"], 2),
                "orders": data["orders"],
                "unique_customers": len(data["customers"]),
            }
            for d, data in sorted(daily.items())
        ]

        logger.info(f"✅ Timeline gerada: {len(timeline)} dias com vendas")
        return timeline

    # ----------------------------------------------------------------
    # 6. RESUMO CONSOLIDADO PARA O DASHBOARD
    # ----------------------------------------------------------------

    def build_dashboard_summary(
        self,
        automations_processed: List[Dict],
        email_metrics: List[Dict],
        whatsapp_metrics: Dict,
        sales_cross: Dict,
        timeline: List[Dict],
    ) -> Dict:
        """
        Consolida todas as métricas em um único objeto para o painel principal.
        Este é o dado que alimenta os cards de resumo no topo do dashboard.
        """
        # Médias de e-mail
        avg_open_rate = 0.0
        avg_click_rate = 0.0
        if email_metrics:
            avg_open_rate = round(
                sum(e["open_rate"] for e in email_metrics) / len(email_metrics), 1
            )
            avg_click_rate = round(
                sum(e["click_rate"] for e in email_metrics) / len(email_metrics), 1
            )

        return {
            "generated_at": datetime.now().isoformat(),
            "period": {
                "from": timeline[0]["date"] if timeline else "",
                "to": timeline[-1]["date"] if timeline else "",
            },
            # Cards principais
            "kpis": {
                "total_revenue": sales_cross.get("total_revenue", 0.0),
                "total_paid_orders": sales_cross.get("total_paid_orders", 0),
                "active_automations": len([a for a in automations_processed if a.get("status") == "active"]),
                "total_automations": len(automations_processed),
                "email_campaigns": len(email_metrics),
                "avg_email_open_rate": avg_open_rate,
                "avg_email_click_rate": avg_click_rate,
                "whatsapp_sent": whatsapp_metrics.get("total_sent", 0),
                "whatsapp_read_rate": whatsapp_metrics.get("read_rate", 0.0),
                "whatsapp_reply_rate": whatsapp_metrics.get("reply_rate", 0.0),
            },
            # Dados para gráficos
            "charts": {
                "sales_timeline": timeline,
                "revenue_by_channel": sales_cross.get("revenue_by_channel", {}),
                "top_automations": sales_cross.get("top_automations", []),
                "email_performance": email_metrics[:10],  # top 10 campanhas
                "whatsapp_by_day": whatsapp_metrics.get("by_day", []),
            },
            # Dados detalhados
            "automations": automations_processed,
            "sales": sales_cross,
        }

    # ----------------------------------------------------------------
    # UTILITÁRIOS INTERNOS
    # ----------------------------------------------------------------

    @staticmethod
    def _to_int(value) -> int:
        """Converte qualquer valor para inteiro de forma segura."""
        try:
            return int(value or 0)
        except (ValueError, TypeError):
            return 0

    @staticmethod
    def _pct(part, total) -> float:
        """Calcula percentual com 1 casa decimal. Retorna 0 se total for 0."""
        if not total or total == 0:
            return 0.0
        return round((part / total) * 100, 1)

    @staticmethod
    def _extract_date(obj: Dict, field: str = "created_at") -> Optional[str]:
        """Extrai a data de um objeto e retorna no formato YYYY-MM-DD."""
        value = obj.get(field) or obj.get("date") or obj.get("timestamp", "")
        if not value:
            return None
        try:
            # Tenta parsear diferentes formatos de data
            if "T" in str(value):
                return str(value)[:10]
            return str(value)[:10]
        except Exception:
            return None


# Instância global do serviço de métricas
metrics_service = MetricsService()
