"""
nuvemshop_service.py — Serviço de Coleta de Dados da NuvemShop
---------------------------------------------------------------
Este módulo busca os dados de pedidos (vendas) diretamente da API
da NuvemShop. Os dados são cruzados com os da RD Station pelo
e-mail do cliente, permitindo calcular receita por campanha/fluxo.

Endpoints utilizados:
  GET /orders          → Lista todos os pedidos com valor, status e cliente
  GET /orders/{id}     → Detalhes de um pedido específico
  GET /customers/{id}  → Dados do cliente (inclui e-mail para cruzamento)

Documentação da API NuvemShop:
  https://tiendanube.github.io/api-documentation/resources/order
"""

import httpx
from loguru import logger
from config import get_settings
from datetime import date

settings = get_settings()

# URL base da API NuvemShop com o User ID da loja
NUVEMSHOP_BASE_URL = f"{settings.nuvemshop_api_base}/{settings.nuvemshop_user_id}"


class NuvemShopService:
    """
    Serviço para buscar dados de vendas da NuvemShop.
    Usa autenticação via Bearer Token (access_token).
    """

    def __init__(self):
        # Headers padrão para todas as requisições à NuvemShop
        self.headers = {
            "Authentication": f"bearer {settings.nuvemshop_access_token}",
            "Content-Type": "application/json",
            # User-Agent obrigatório pela NuvemShop para identificar o app
            "User-Agent": "RD-Dashboard/1.0 (pangeia96@gmail.com)",
        }
        self.date_from = settings.default_date_from
        self.date_to = date.today().isoformat()

    async def _request(self, endpoint: str, params: dict = None) -> dict:
        """
        Método interno para fazer requisições autenticadas à NuvemShop.
        Trata erros de forma padronizada e registra no log.
        """
        url = f"{NUVEMSHOP_BASE_URL}{endpoint}"
        logger.debug(f"📡 NuvemShop GET {url}")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=self.headers, params=params)

        if response.status_code == 401:
            logger.error("❌ NuvemShop: Token inválido ou expirado (401)")
            raise Exception("Token da NuvemShop inválido. Verifique o NUVEMSHOP_ACCESS_TOKEN no .env")

        if response.status_code == 429:
            logger.warning("⚠️  NuvemShop: Rate limit atingido (429). Aguardando...")
            import asyncio
            await asyncio.sleep(5)
            return await self._request(endpoint, params)

        if response.status_code >= 400:
            logger.error(f"❌ NuvemShop [{response.status_code}]: {response.text[:200]}")
            response.raise_for_status()

        return response.json()

    # ----------------------------------------------------------------
    # 1. PEDIDOS (VENDAS)
    # ----------------------------------------------------------------

    async def get_orders(
        self,
        page: int = 1,
        per_page: int = 50,
        created_at_min: str = None,
        created_at_max: str = None,
        status: str = None,
    ) -> list:
        """
        Busca pedidos da loja NuvemShop com filtros de data e status.

        Parâmetros:
          page           — número da página (paginação)
          per_page       — quantidade de pedidos por página (máx: 200)
          created_at_min — data mínima de criação (formato: YYYY-MM-DDTHH:MM:SS-03:00)
          created_at_max — data máxima de criação
          status         — filtro de status: "open", "closed", "cancelled"

        Retorna lista de pedidos com: id, número, valor total, status,
        data de criação, e-mail do cliente, produtos comprados.
        """
        logger.info(f"🛒 Buscando pedidos NuvemShop (página {page})...")

        params = {
            "page": page,
            "per_page": per_page,
        }

        # Aplica filtro de data de início (padrão: setembro/2025)
        if created_at_min:
            params["created_at_min"] = created_at_min
        elif self.date_from:
            params["created_at_min"] = f"{self.date_from}T00:00:00-03:00"

        # Aplica filtro de data de fim (padrão: hoje)
        if created_at_max:
            params["created_at_max"] = created_at_max
        else:
            params["created_at_max"] = f"{self.date_to}T23:59:59-03:00"

        # Filtra apenas pedidos fechados (vendas confirmadas) por padrão
        if status:
            params["payment_status"] = status

        try:
            data = await self._request("/orders", params=params)
            orders = data if isinstance(data, list) else []
            logger.info(f"✅ {len(orders)} pedidos encontrados na página {page}")
            return orders
        except Exception as e:
            logger.error(f"❌ Erro ao buscar pedidos: {e}")
            return []

    async def get_all_orders(self, max_pages: int = 20) -> list:
        """
        Busca TODOS os pedidos do período configurado, paginando automaticamente.
        Retorna lista completa com dados normalizados para cruzamento com a RD Station.
        O parâmetro max_pages limita o número de páginas para evitar timeout.
        """
        all_orders = []
        page = 1

        while True:
            orders = await self.get_orders(page=page, per_page=200)

            if not orders:
                break

            all_orders.extend(orders)
            logger.info(f"   → Página {page}: {len(orders)} pedidos | Total acumulado: {len(all_orders)}")

            # Se retornou menos que o máximo, chegamos na última página
            if len(orders) < 200:
                break

            # Limite de segurança para evitar timeout
            if page >= max_pages:
                logger.warning(f"⚠️  Limite de {max_pages} páginas atingido. Carregados {len(all_orders)} pedidos.")
                break

            page += 1

            # Pequena pausa para respeitar o rate limit da NuvemShop
            import asyncio
            await asyncio.sleep(0.3)

        logger.info(f"✅ Total de pedidos carregados: {len(all_orders)}")
        return all_orders

    def normalize_order(self, order: dict) -> dict:
        """
        Normaliza um pedido da NuvemShop para o formato padrão do dashboard.
        Extrai apenas os campos relevantes para análise.

        Campos retornados:
          order_id      — ID único do pedido
          order_number  — Número do pedido (ex: #1234)
          email         — E-mail do cliente (chave para cruzar com RD Station)
          total         — Valor total do pedido em R$
          status        — Status do pedido
          payment_status — Status do pagamento
          created_at    — Data e hora do pedido
          products      — Lista de produtos comprados
        """
        # Extrai e-mail do cliente (pode estar em diferentes estruturas)
        customer = order.get("customer") or {}
        email = (
            order.get("contact_email")
            or customer.get("email")
            or ""
        ).lower().strip()

        # Extrai valor total (NuvemShop retorna como string)
        total_raw = order.get("total") or "0"
        try:
            total = float(str(total_raw).replace(",", "."))
        except (ValueError, TypeError):
            total = 0.0

        # Extrai produtos do pedido
        products = []
        for item in order.get("products", []):
            products.append({
                "name": item.get("name", ""),
                "quantity": item.get("quantity", 0),
                "price": float(str(item.get("price", "0")).replace(",", ".")),
            })

        return {
            "order_id": str(order.get("id", "")),
            "order_number": order.get("number", ""),
            "email": email,
            "total": total,
            "status": order.get("status", ""),
            "payment_status": order.get("payment_status", ""),
            "created_at": order.get("created_at", ""),
            "products": products,
            "raw": order,  # mantém o dado original para referência
        }

    async def get_all_orders_normalized(self) -> list:
        """
        Busca todos os pedidos e retorna já normalizados.
        Filtra apenas pedidos com e-mail válido (necessário para cruzamento).
        """
        raw_orders = await self.get_all_orders()
        normalized = [self.normalize_order(o) for o in raw_orders]

        # Filtra pedidos sem e-mail (não podem ser cruzados com a RD Station)
        valid = [o for o in normalized if o["email"]]
        skipped = len(normalized) - len(valid)

        if skipped > 0:
            logger.warning(f"⚠️  {skipped} pedidos ignorados por não terem e-mail do cliente")

        logger.info(f"✅ {len(valid)} pedidos normalizados e prontos para cruzamento")
        return valid

    # ----------------------------------------------------------------
    # 2. RESUMO DE VENDAS (para o dashboard)
    # ----------------------------------------------------------------

    def calculate_sales_summary(self, orders: list) -> dict:
        """
        Calcula um resumo das vendas a partir da lista de pedidos normalizados.
        Retorna métricas agregadas para exibição no dashboard.
        """
        if not orders:
            return {
                "total_orders": 0,
                "total_revenue": 0.0,
                "average_ticket": 0.0,
                "unique_customers": 0,
            }

        total_revenue = sum(o["total"] for o in orders)
        unique_emails = set(o["email"] for o in orders if o["email"])

        return {
            "total_orders": len(orders),
            "total_revenue": round(total_revenue, 2),
            "average_ticket": round(total_revenue / len(orders), 2) if orders else 0.0,
            "unique_customers": len(unique_emails),
        }


# Instância global do serviço NuvemShop
nuvemshop_service = NuvemShopService()
