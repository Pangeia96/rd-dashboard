"""
token_store.py — Armazenamento persistente dos tokens OAuth
------------------------------------------------------------
Este módulo salva e lê os tokens de acesso (access_token e refresh_token)
em um arquivo local (tokens.json). Isso garante que, ao reiniciar o servidor,
o sistema não precise pedir autorização novamente ao usuário.
"""

import json
import os
from pathlib import Path
from loguru import logger

# Caminho onde os tokens serão salvos (na pasta backend/)
TOKEN_FILE = Path(__file__).parent.parent / "tokens.json"


def save_tokens(access_token: str, refresh_token: str) -> None:
    """
    Salva os tokens no arquivo tokens.json.
    Chamado automaticamente após cada autenticação ou renovação.
    """
    data = {
        "access_token": access_token,
        "refresh_token": refresh_token,
    }
    with open(TOKEN_FILE, "w") as f:
        json.dump(data, f, indent=2)
    logger.info("✅ Tokens salvos com sucesso em tokens.json")


def load_tokens() -> dict:
    """
    Lê os tokens salvos anteriormente.
    Retorna um dicionário com 'access_token' e 'refresh_token',
    ou strings vazias se o arquivo não existir ainda.
    """
    if not TOKEN_FILE.exists():
        logger.warning("⚠️  Arquivo tokens.json não encontrado. Autenticação necessária.")
        return {"access_token": "", "refresh_token": ""}

    with open(TOKEN_FILE, "r") as f:
        data = json.load(f)
    logger.info("🔑 Tokens carregados do arquivo tokens.json")
    return data


def clear_tokens() -> None:
    """
    Remove os tokens salvos (útil para forçar uma nova autenticação).
    """
    if TOKEN_FILE.exists():
        os.remove(TOKEN_FILE)
        logger.info("🗑️  Tokens removidos. Nova autenticação será necessária.")
