"""
main.py — Ponto de entrada do servidor backend
-----------------------------------------------
Este é o arquivo principal que inicia o servidor FastAPI.
Ao rodar este arquivo, o servidor sobe e fica aguardando requisições
do frontend (dashboard Vue.js) e do callback OAuth da RD Station.

Para iniciar o servidor:
  cd backend
  uvicorn main:app --reload --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from config import get_settings
from utils.logger import setup_logger
from routers.auth_router import router as auth_router
from routers.data_router import router as data_router
from routers.metrics_router import router as metrics_router
from routers.supabase_router import router as supabase_router

# Inicializa o sistema de logs
logger = setup_logger()
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Executado na inicialização e encerramento do servidor.
    Aqui podemos carregar dados iniciais, verificar conexões, etc.
    """
    logger.info("🚀 Iniciando RD Station Dashboard Backend...")
    logger.info(f"🌍 Ambiente: {settings.environment}")
    logger.info(f"🔗 Redirect URI configurada: {settings.rd_redirect_uri}")
    yield
    logger.info("🛑 Servidor encerrado.")


# Criação da aplicação FastAPI
app = FastAPI(
    title="RD Station Dashboard — API Backend",
    description=(
        "Backend do dashboard de análise de fluxos de automação da RD Station Marketing. "
        "Fornece dados processados de e-mail, WhatsApp e conversões para o frontend Vue.js."
    ),
    version="1.0.0",
    lifespan=lifespan,
    # Documentação automática disponível em /docs
    docs_url="/docs",
    redoc_url="/redoc",
)

# -------------------------------------------------------
# Configuração de CORS (Cross-Origin Resource Sharing)
# Permite que o frontend Vue.js (em outro domínio/porta)
# faça requisições para este backend sem ser bloqueado.
# -------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",        # Vue.js em desenvolvimento local
        "http://localhost:5173",        # Vite dev server padrão
        "http://localhost:5174",        # Vite dev server alternativo
        "https://www.pangeia96.com.br", # Domínio principal da Pangeia 96
        "https://pangeia96.com.br",     # Sem www
        "https://*.vercel.app",         # Deploy na Vercel
        "https://rd-dashboard-frontend.vercel.app",  # Frontend em produção
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------------
# Registro dos roteadores (grupos de endpoints)
# -------------------------------------------------------
app.include_router(auth_router)
app.include_router(data_router)
app.include_router(metrics_router)
app.include_router(supabase_router)


# -------------------------------------------------------
# Endpoint raiz — verifica se o servidor está no ar
# -------------------------------------------------------
@app.get("/", summary="Health check — verifica se o servidor está rodando")
async def root():
    """
    Endpoint de verificação de saúde do servidor.
    Retorna informações básicas sobre o status do sistema.
    """
    from services.auth_service import auth_service
    return {
        "status": "online",
        "servico": "RD Station Dashboard Backend",
        "versao": "1.0.0",
        "autenticado_rd_station": auth_service.is_authenticated,
        "documentacao": "/docs",
        "ambiente": settings.environment,
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """
    Captura erros não tratados e retorna uma resposta amigável.
    O erro completo é registrado no arquivo de log para diagnóstico.
    """
    logger.error(f"❌ Erro não tratado: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "status": "erro",
            "mensagem": "Ocorreu um erro interno. Verifique o arquivo logs/app.log para detalhes.",
            "detalhe": str(exc),
        },
    )


# -------------------------------------------------------
# Permite rodar diretamente com: python main.py
# -------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.backend_port,
        reload=settings.environment == "development",
    )
