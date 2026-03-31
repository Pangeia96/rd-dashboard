"""
auth_router.py — Rotas de Autenticação OAuth 2.0
-------------------------------------------------
Este arquivo define os endpoints HTTP relacionados à autenticação.
São apenas 2 rotas simples:

  GET /auth/login    → Redireciona o usuário para a página de autorização da RD Station
  GET /auth/callback → Recebe o código de autorização e troca pelos tokens

Fluxo completo (em linguagem simples):
  1. Usuário acessa o dashboard pela primeira vez
  2. Sistema detecta que não há token → redireciona para /auth/login
  3. Usuário é levado à página da RD Station para autorizar o acesso
  4. RD Station redireciona de volta para /auth/callback?code=XXXX
  5. Sistema troca o código pelos tokens e salva
  6. Usuário é redirecionado para o dashboard — agora autenticado!
"""

from fastapi import APIRouter
from fastapi.responses import RedirectResponse, JSONResponse
from services.auth_service import auth_service
from loguru import logger

# Cria o roteador de autenticação
router = APIRouter(prefix="/auth", tags=["Autenticação"])


@router.get("/login", summary="Iniciar autenticação com RD Station")
async def login():
    """
    Redireciona o usuário para a página de autorização da RD Station.
    Acesse este endpoint no navegador para iniciar o processo de login.
    """
    url = auth_service.get_authorization_url()
    logger.info("🚀 Iniciando fluxo de autenticação OAuth...")
    return RedirectResponse(url=url)


@router.get("/callback", summary="Callback OAuth — recebe o código de autorização")
async def callback(code: str = None, error: str = None):
    """
    Endpoint chamado automaticamente pela RD Station após o usuário autorizar.
    Recebe o código temporário e o troca pelos tokens de acesso.

    Parâmetros (enviados automaticamente pela RD Station na URL):
      code  — código temporário de autorização
      error — mensagem de erro, se o usuário negou o acesso
    """
    # Usuário negou o acesso
    if error:
        logger.error(f"❌ Usuário negou o acesso: {error}")
        return JSONResponse(
            status_code=400,
            content={"status": "erro", "mensagem": f"Acesso negado: {error}"},
        )

    # Código não recebido
    if not code:
        logger.error("❌ Código de autorização não recebido no callback")
        return JSONResponse(
            status_code=400,
            content={"status": "erro", "mensagem": "Código de autorização não encontrado na URL"},
        )

    try:
        # Troca o código pelos tokens
        await auth_service.exchange_code_for_tokens(code)
        logger.info("✅ Autenticação concluída com sucesso!")

        # Redireciona para o dashboard após autenticação bem-sucedida
        return RedirectResponse(url="/")

    except Exception as e:
        logger.error(f"❌ Falha ao processar callback: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"status": "erro", "mensagem": str(e)},
        )


@router.get("/status", summary="Verificar status da autenticação")
async def auth_status():
    """
    Retorna se o sistema está autenticado com a RD Station.
    Útil para o frontend verificar se precisa redirecionar para o login.
    """
    return {
        "autenticado": auth_service.is_authenticated,
        "mensagem": (
            "✅ Conectado à RD Station" if auth_service.is_authenticated
            else "⚠️  Não autenticado. Acesse /auth/login para conectar."
        ),
    }


@router.post("/refresh", summary="Renovar token manualmente")
async def refresh_token():
    """
    Força a renovação do access_token usando o refresh_token.
    Normalmente isso acontece automaticamente, mas este endpoint
    permite forçar a renovação manualmente se necessário.
    """
    try:
        await auth_service.refresh_access_token()
        return {"status": "sucesso", "mensagem": "Token renovado com sucesso!"}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "erro", "mensagem": str(e)},
        )
