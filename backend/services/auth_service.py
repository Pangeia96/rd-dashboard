"""
auth_service.py — Serviço de Autenticação OAuth 2.0 com a RD Station
----------------------------------------------------------------------
Este módulo é o coração da autenticação do sistema. Ele é responsável por:

1. Gerar o link de autorização (onde o usuário clica para permitir acesso)
2. Trocar o código de autorização por tokens de acesso
3. Renovar automaticamente o access_token quando ele expirar
4. Fazer todas as requisições à API com o token correto

Como funciona o OAuth 2.0 da RD Station (em linguagem simples):
  → Você clica em "Conectar com RD Station"
  → A RD Station pergunta: "Você permite que este app acesse seus dados?"
  → Você clica em "Autorizar"
  → A RD Station envia um "código temporário" para nossa URL de callback
  → Nosso sistema troca esse código por um "token de acesso" (válido por tempo limitado)
  → Quando o token expira, usamos o "refresh_token" para pegar um novo automaticamente
"""

import httpx
from loguru import logger
from config import get_settings
from utils.token_store import save_tokens, load_tokens

# URLs oficiais da API da RD Station
RD_AUTH_URL = "https://api.rd.services/auth/dialog"
RD_TOKEN_URL = "https://api.rd.services/auth/token"
RD_API_BASE = "https://api.rd.services"


class AuthService:
    """
    Classe que gerencia todo o ciclo de autenticação OAuth 2.0.
    """

    def __init__(self):
        self.settings = get_settings()
        # Carrega tokens salvos anteriormente (se existirem)
        tokens = load_tokens()
        self._access_token: str = tokens.get("access_token", "")
        self._refresh_token: str = tokens.get("refresh_token", "")

    def get_authorization_url(self) -> str:
        """
        Gera a URL que o usuário deve acessar para autorizar o app.
        Exemplo de retorno:
        https://api.rd.services/auth/dialog?client_id=...&redirect_uri=...&response_type=code
        """
        params = {
            "client_id": self.settings.rd_client_id,
            "redirect_uri": self.settings.rd_redirect_uri,
            "response_type": "code",
        }
        # Monta a URL com os parâmetros
        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"{RD_AUTH_URL}?{query_string}"
        logger.info(f"🔗 URL de autorização gerada: {url}")
        return url

    async def exchange_code_for_tokens(self, code: str) -> dict:
        """
        Troca o código temporário (recebido no callback) pelos tokens de acesso.
        Este método é chamado automaticamente quando a RD Station redireciona
        o usuário de volta para nossa URL de callback com o parâmetro ?code=...
        """
        logger.info("🔄 Trocando código de autorização por tokens...")

        payload = {
            "client_id": self.settings.rd_client_id,
            "client_secret": self.settings.rd_client_secret,
            "redirect_uri": self.settings.rd_redirect_uri,
            "code": code,
            "grant_type": "authorization_code",
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(RD_TOKEN_URL, json=payload)

        if response.status_code != 200:
            logger.error(f"❌ Erro ao obter tokens: {response.status_code} — {response.text}")
            raise Exception(f"Falha na autenticação: {response.text}")

        data = response.json()
        self._access_token = data["access_token"]
        self._refresh_token = data["refresh_token"]

        # Salva os tokens em disco para persistência
        save_tokens(self._access_token, self._refresh_token)
        logger.info("✅ Tokens obtidos e salvos com sucesso!")

        return data

    async def refresh_access_token(self) -> str:
        """
        Renova o access_token usando o refresh_token.
        Chamado automaticamente quando a API retorna erro 401 (token expirado).
        O usuário NÃO precisa fazer nada — isso acontece nos bastidores.
        """
        if not self._refresh_token:
            logger.error("❌ Sem refresh_token disponível. Autenticação manual necessária.")
            raise Exception("Refresh token não disponível. Acesse /auth/login para autenticar.")

        logger.info("🔄 Renovando access_token automaticamente...")

        payload = {
            "client_id": self.settings.rd_client_id,
            "client_secret": self.settings.rd_client_secret,
            "refresh_token": self._refresh_token,
            "grant_type": "refresh_token",
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(RD_TOKEN_URL, json=payload)

        if response.status_code != 200:
            logger.error(f"❌ Erro ao renovar token: {response.status_code} — {response.text}")
            raise Exception(f"Falha ao renovar token: {response.text}")

        data = response.json()
        self._access_token = data["access_token"]
        # Alguns fluxos OAuth retornam um novo refresh_token também
        if "refresh_token" in data:
            self._refresh_token = data["refresh_token"]

        save_tokens(self._access_token, self._refresh_token)
        logger.info("✅ Access token renovado com sucesso!")

        return self._access_token

    async def get_valid_token(self) -> str:
        """
        Retorna um token válido.
        Se não houver token, lança exceção pedindo autenticação.
        """
        if not self._access_token:
            raise Exception("Não autenticado. Acesse /auth/login para iniciar a autenticação.")
        return self._access_token

    async def make_api_request(
        self,
        method: str,
        endpoint: str,
        params: dict = None,
        json_body: dict = None,
        retry: bool = True,
    ) -> dict:
        """
        Faz uma requisição autenticada à API da RD Station.
        Se receber erro 401 (token expirado), renova o token automaticamente
        e tenta novamente — sem intervenção do usuário.

        Parâmetros:
          method   — "GET", "POST", etc.
          endpoint — caminho da API, ex: "/marketing/automations"
          params   — parâmetros de query string (ex: filtros)
          json_body — corpo da requisição para POST/PUT
          retry    — se True, tenta renovar o token em caso de 401
        """
        token = await self.get_valid_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        url = f"{RD_API_BASE}{endpoint}"

        logger.debug(f"📡 {method} {url}")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=json_body,
            )

        # Token expirado — tenta renovar e repetir a requisição uma vez
        if response.status_code == 401 and retry:
            logger.warning("⚠️  Token expirado. Renovando automaticamente...")
            await self.refresh_access_token()
            return await self.make_api_request(method, endpoint, params, json_body, retry=False)

        # Outros erros da API
        if response.status_code >= 400:
            logger.error(
                f"❌ Erro na API [{response.status_code}]: {endpoint} — {response.text[:200]}"
            )
            response.raise_for_status()

        return response.json()

    @property
    def is_authenticated(self) -> bool:
        """Retorna True se há um token de acesso disponível."""
        return bool(self._access_token)


# Instância global do serviço de autenticação
# Importada pelos outros módulos do projeto
auth_service = AuthService()
