# Dashboard RD Station Marketing — Pangeia 96

Dashboard interativo de análise de fluxos de automação integrado à API da RD Station Marketing e NuvemShop.

## Visão Geral

Este projeto permite que a equipe de marketing da Pangeia 96 visualize, em tempo real, o desempenho de cada etapa das automações — com foco em conversões e vendas geradas por e-mail e WhatsApp.

## Arquitetura

```
Frontend (Vue.js)          Backend (FastAPI/Python)       Banco de Dados
┌─────────────────┐        ┌──────────────────────┐       ┌─────────────┐
│  Vercel         │ ──────▶│  Render.com          │──────▶│  Supabase   │
│  Vue 3 + Vite   │        │  FastAPI + Python     │       │  PostgreSQL │
│  Chart.js       │        │  OAuth 2.0 RD Station │       │             │
│  Pinia          │        │  NuvemShop API        │       │ pedidos_    │
└─────────────────┘        └──────────────────────┘       │ consolidado │
                                                           │ rd_*        │
                                                           └─────────────┘
```

## Pré-requisitos

- Python 3.11+
- Node.js 18+
- pnpm (gerenciador de pacotes)
- Conta no Supabase com projeto configurado
- Credenciais da API RD Station (client_id + client_secret)
- Token de acesso NuvemShop com escopos: `read_orders,read_customers,read_products`

## Instalação Local

### 1. Clone o repositório

```bash
git clone https://github.com/Pangeia96/rd-dashboard.git
cd rd-dashboard
```

### 2. Configure o backend

```bash
cd backend
cp .env.example .env
# Edite o .env com suas credenciais reais
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 3. Configure o frontend

```bash
cd frontend
pnpm install
pnpm dev
```

O dashboard estará disponível em `http://localhost:5173`

## Deploy em Produção

### Backend — Render.com

1. Acesse [render.com](https://render.com) e crie uma conta
2. Clique em **New → Web Service**
3. Conecte ao repositório `Pangeia96/rd-dashboard`
4. Configure:
   - **Root Directory:** `backend`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Adicione as variáveis de ambiente (veja `.env.example`)
6. Clique em **Deploy**

### Frontend — Vercel

1. Acesse [vercel.com](https://vercel.com) e crie uma conta
2. Clique em **New Project**
3. Importe o repositório `Pangeia96/rd-dashboard`
4. Configure:
   - **Root Directory:** `frontend`
   - **Framework Preset:** Vite
5. Adicione a variável de ambiente:
   - `VITE_API_URL` = URL do backend no Render (ex: `https://rd-dashboard-backend.onrender.com`)
6. Clique em **Deploy**

## Autenticação com a RD Station

Após o deploy, acesse `https://SEU_BACKEND.onrender.com/auth/login` para autorizar o acesso à RD Station. O sistema salvará os tokens automaticamente e iniciará a sincronização dos dados.

## Estrutura do Projeto

```
rd-dashboard/
├── backend/
│   ├── main.py                    # Ponto de entrada do servidor
│   ├── config.py                  # Configurações e variáveis de ambiente
│   ├── requirements.txt           # Dependências Python
│   ├── .env.example               # Modelo de variáveis de ambiente
│   ├── routers/
│   │   ├── auth_router.py         # Endpoints de autenticação OAuth
│   │   ├── data_router.py         # Endpoints de coleta de dados
│   │   ├── metrics_router.py      # Endpoints de métricas processadas
│   │   └── supabase_router.py     # Endpoints do banco de dados
│   ├── services/
│   │   ├── auth_service.py        # Lógica OAuth 2.0 RD Station
│   │   ├── rd_service.py          # Coleta de dados da RD Station
│   │   ├── nuvemshop_service.py   # Coleta de dados da NuvemShop
│   │   ├── metrics_service.py     # Processamento de métricas
│   │   └── supabase_service.py    # Acesso ao banco de dados
│   ├── utils/
│   │   ├── logger.py              # Sistema de logs
│   │   └── token_store.py         # Persistência de tokens OAuth
│   └── scripts/
│       ├── criar_tabelas_rd_station.sql    # SQL para criar tabelas RD
│       ├── criar_indices_concurrently.sql  # SQL para criar índices
│       └── criar_funcoes_otimizadas.sql    # SQL para funções agregadas
└── frontend/
    ├── src/
    │   ├── views/                 # Páginas do dashboard
    │   ├── components/            # Componentes reutilizáveis
    │   ├── store/                 # Estado global (Pinia)
    │   └── router/                # Rotas da aplicação
    ├── package.json
    └── vercel.json                # Configuração de deploy na Vercel
```

## Endpoints da API

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/` | Health check |
| GET | `/auth/login` | Inicia autenticação OAuth com RD Station |
| GET | `/auth/callback` | Callback OAuth (recebe token da RD Station) |
| GET | `/auth/status` | Verifica se está autenticado |
| GET | `/db/kpis` | KPIs principais (receita, pedidos, ticket médio) |
| GET | `/db/timeline` | Evolução de vendas por período |
| GET | `/db/canais` | Receita por canal e método de pagamento |
| GET | `/db/estados` | Receita por estado |
| GET | `/db/top-produtos` | Top produtos mais vendidos |
| GET | `/db/dashboard` | Todos os dados em uma chamada |
| POST | `/db/cache/invalidar` | Limpa o cache de dados |

Documentação completa disponível em `/docs` (Swagger UI).

## Suporte

Em caso de dúvidas ou problemas, consulte os logs em `backend/logs/app.log`.
