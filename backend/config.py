"""
config.py — Configurações centrais do projeto
----------------------------------------------
Este arquivo carrega todas as variáveis do arquivo .env e as disponibiliza
para o restante da aplicação de forma organizada e segura.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """
    Classe de configurações — cada atributo corresponde a uma variável no .env.
    O Pydantic valida automaticamente os tipos e avisa se algo estiver faltando.
    """

    # --- Credenciais da RD Station ---
    rd_client_id: str
    rd_client_secret: str
    rd_redirect_uri: str

    # --- Tokens OAuth (podem estar vazios inicialmente) ---
    rd_access_token: str = ""
    rd_refresh_token: str = ""

    # --- Configurações do servidor ---
    backend_port: int = 8000
    secret_key: str = "chave_padrao_insegura"

    # --- Cache ---
    cache_ttl_seconds: int = 3600  # padrão: 1 hora

    # --- NuvemShop ---
    nuvemshop_user_id: str = ""
    nuvemshop_access_token: str = ""
    nuvemshop_api_base: str = "https://api.tiendanube.com/v1"

    # --- Período padrão ---
    default_date_from: str = "2025-09-01"

    # --- Supabase ---
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_key: str = ""

    # --- Ambiente ---
    environment: str = "development"

    class Config:
        # Indica ao Pydantic onde encontrar o arquivo de variáveis
        env_file = ".env"
        env_file_encoding = "utf-8"
        # Permite que variáveis extras no .env não causem erro
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """
    Retorna as configurações carregadas do .env.
    O @lru_cache garante que o arquivo .env seja lido apenas uma vez,
    evitando leituras repetidas em cada requisição.
    """
    return Settings()
