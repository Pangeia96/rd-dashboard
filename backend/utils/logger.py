"""
logger.py — Configuração centralizada de logs
----------------------------------------------
Este módulo configura o sistema de logs da aplicação.
Todos os eventos importantes (autenticações, erros, chamadas à API)
são registrados em arquivo e exibidos no terminal com cores.
"""

import sys
from loguru import logger
from pathlib import Path

# Pasta onde os arquivos de log serão salvos
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)


def setup_logger():
    """
    Configura o logger com dois destinos:
    1. Terminal (stdout) — para visualização em tempo real
    2. Arquivo logs/app.log — para histórico e diagnóstico de erros
    """
    # Remove o handler padrão do loguru
    logger.remove()

    # Handler para o terminal com cores
    logger.add(
        sys.stdout,
        level="INFO",
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> — {message}",
        colorize=True,
    )

    # Handler para arquivo de log (rotaciona a cada 10MB, mantém 30 dias)
    logger.add(
        LOG_DIR / "app.log",
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name} — {message}",
        rotation="10 MB",
        retention="30 days",
        encoding="utf-8",
    )

    logger.info("📋 Sistema de logs inicializado")
    return logger
