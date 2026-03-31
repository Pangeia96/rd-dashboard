-- ============================================================
-- create_rd_tables.sql — Criação das tabelas RD Station
-- ============================================================
-- Este script cria todas as tabelas necessárias para armazenar
-- os dados da RD Station Marketing no Supabase (PostgreSQL).
--
-- Tabelas criadas:
--   rd_automacoes          → Fluxos de automação
--   rd_etapas_automacao    → Etapas de cada fluxo
--   rd_campanhas_email     → Campanhas de e-mail disparadas
--   rd_metricas_email      → Métricas de cada campanha (abertura, clique, etc.)
--   rd_eventos_whatsapp    → Eventos de WhatsApp (disparos, leituras, respostas)
--   rd_contatos            → Contatos/leads da RD Station
--   rd_conversoes          → Eventos de conversão dos contatos
--   rd_sync_log            → Log de sincronizações (controle incremental)
-- ============================================================

-- ----------------------------------------------------------------
-- 1. FLUXOS DE AUTOMAÇÃO
-- ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS rd_automacoes (
    id                  TEXT PRIMARY KEY,          -- ID único da automação na RD Station
    nome                TEXT NOT NULL,             -- Nome do fluxo de automação
    status              TEXT DEFAULT 'active',     -- Status: active, paused, archived
    total_contatos      INTEGER DEFAULT 0,         -- Total de contatos no fluxo
    criado_em           TIMESTAMPTZ,               -- Data de criação na RD Station
    atualizado_em       TIMESTAMPTZ,               -- Última atualização
    sincronizado_em     TIMESTAMPTZ DEFAULT NOW()  -- Última sincronização com nosso banco
);

-- ----------------------------------------------------------------
-- 2. ETAPAS DE CADA FLUXO
-- ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS rd_etapas_automacao (
    id                  TEXT PRIMARY KEY,          -- ID único da etapa
    automacao_id        TEXT REFERENCES rd_automacoes(id) ON DELETE CASCADE,
    nome                TEXT NOT NULL,             -- Nome da etapa (ex: "E-mail de boas-vindas")
    tipo                TEXT,                      -- Tipo: email, whatsapp, wait, condition, etc.
    ordem               INTEGER DEFAULT 0,         -- Posição da etapa no fluxo
    total_contatos      INTEGER DEFAULT 0,         -- Contatos que passaram por esta etapa
    total_saidas        INTEGER DEFAULT 0,         -- Contatos que saíram (avançaram ou abandonaram)
    sincronizado_em     TIMESTAMPTZ DEFAULT NOW()
);

-- ----------------------------------------------------------------
-- 3. CAMPANHAS DE E-MAIL
-- ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS rd_campanhas_email (
    id                  TEXT PRIMARY KEY,          -- ID único da campanha
    nome                TEXT NOT NULL,             -- Nome da campanha
    assunto             TEXT,                      -- Assunto do e-mail
    status              TEXT,                      -- Status: sent, scheduled, draft
    tipo                TEXT DEFAULT 'broadcast',  -- broadcast (disparo manual) ou automation
    automacao_id        TEXT,                      -- ID da automação (se for de um fluxo)
    etapa_id            TEXT,                      -- ID da etapa (se for de um fluxo)
    enviado_em          TIMESTAMPTZ,               -- Data/hora do envio
    sincronizado_em     TIMESTAMPTZ DEFAULT NOW()
);

-- ----------------------------------------------------------------
-- 4. MÉTRICAS DE E-MAIL (por campanha)
-- ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS rd_metricas_email (
    id                  SERIAL PRIMARY KEY,
    campanha_id         TEXT REFERENCES rd_campanhas_email(id) ON DELETE CASCADE,
    total_enviados      INTEGER DEFAULT 0,         -- Total de e-mails enviados
    total_entregues     INTEGER DEFAULT 0,         -- E-mails entregues (não bounced)
    total_abertos       INTEGER DEFAULT 0,         -- E-mails abertos (unique opens)
    total_clicados      INTEGER DEFAULT 0,         -- E-mails com clique (unique clicks)
    total_bounces       INTEGER DEFAULT 0,         -- E-mails com bounce (hard + soft)
    total_descadastros  INTEGER DEFAULT 0,         -- Descadastros gerados por esta campanha
    total_spam          INTEGER DEFAULT 0,         -- Marcados como spam
    taxa_abertura       DECIMAL(5,2) DEFAULT 0,    -- % de abertura (calculado)
    taxa_clique         DECIMAL(5,2) DEFAULT 0,    -- % de clique (calculado)
    taxa_bounce         DECIMAL(5,2) DEFAULT 0,    -- % de bounce (calculado)
    sincronizado_em     TIMESTAMPTZ DEFAULT NOW()
);

-- ----------------------------------------------------------------
-- 5. EVENTOS DE WHATSAPP
-- ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS rd_eventos_whatsapp (
    id                  TEXT PRIMARY KEY,          -- ID único do evento
    campanha_id         TEXT,                      -- ID da campanha/disparo
    nome_campanha       TEXT,                      -- Nome do disparo
    automacao_id        TEXT,                      -- ID da automação (se for de fluxo)
    etapa_id            TEXT,                      -- ID da etapa (se for de fluxo)
    tipo_evento         TEXT,                      -- sent, delivered, read, replied, failed
    contato_email       TEXT,                      -- E-mail do contato (para cruzamento)
    contato_telefone    TEXT,                      -- Telefone do contato
    ocorrido_em         TIMESTAMPTZ,               -- Data/hora do evento
    sincronizado_em     TIMESTAMPTZ DEFAULT NOW()
);

-- ----------------------------------------------------------------
-- 6. CONTATOS / LEADS
-- ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS rd_contatos (
    id                  TEXT PRIMARY KEY,          -- ID único do contato na RD Station
    email               TEXT UNIQUE,               -- E-mail (chave de cruzamento com NuvemShop)
    nome                TEXT,                      -- Nome completo
    telefone            TEXT,                      -- Telefone
    empresa             TEXT,                      -- Empresa (se B2B)
    cargo               TEXT,                      -- Cargo
    tags                TEXT[],                    -- Tags do contato
    lead_scoring        INTEGER DEFAULT 0,         -- Pontuação de lead scoring
    lifecycle_stage     TEXT,                      -- Etapa do funil: lead, qualified, customer
    criado_em           TIMESTAMPTZ,
    atualizado_em       TIMESTAMPTZ,
    sincronizado_em     TIMESTAMPTZ DEFAULT NOW()
);

-- ----------------------------------------------------------------
-- 7. CONVERSÕES
-- ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS rd_conversoes (
    id                  SERIAL PRIMARY KEY,
    contato_id          TEXT REFERENCES rd_contatos(id) ON DELETE CASCADE,
    contato_email       TEXT,                      -- E-mail duplicado para consultas rápidas
    tipo_conversao      TEXT,                      -- Tipo: form_submission, landing_page, etc.
    nome_conversao      TEXT,                      -- Nome da conversão (ex: "Comprou produto")
    automacao_id        TEXT,                      -- Fluxo ativo no momento da conversão
    etapa_id            TEXT,                      -- Etapa ativa no momento da conversão
    campanha_email_id   TEXT,                      -- Campanha de e-mail que gerou a conversão
    ocorrido_em         TIMESTAMPTZ,
    sincronizado_em     TIMESTAMPTZ DEFAULT NOW()
);

-- ----------------------------------------------------------------
-- 8. LOG DE SINCRONIZAÇÃO (controle incremental)
-- ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS rd_sync_log (
    id                  SERIAL PRIMARY KEY,
    tabela              TEXT NOT NULL,             -- Nome da tabela sincronizada
    ultima_sincronizacao TIMESTAMPTZ DEFAULT NOW(),-- Quando foi a última sincronização
    total_registros     INTEGER DEFAULT 0,         -- Quantos registros foram sincronizados
    status              TEXT DEFAULT 'success',    -- success, error, partial
    mensagem            TEXT                       -- Detalhes ou mensagem de erro
);

-- ----------------------------------------------------------------
-- ÍNDICES para performance nas consultas do dashboard
-- ----------------------------------------------------------------

-- Índices em rd_contatos (busca por email é muito frequente)
CREATE INDEX IF NOT EXISTS idx_rd_contatos_email ON rd_contatos(email);

-- Índices em rd_conversoes (busca por email e automação)
CREATE INDEX IF NOT EXISTS idx_rd_conversoes_email ON rd_conversoes(contato_email);
CREATE INDEX IF NOT EXISTS idx_rd_conversoes_automacao ON rd_conversoes(automacao_id);
CREATE INDEX IF NOT EXISTS idx_rd_conversoes_data ON rd_conversoes(ocorrido_em);

-- Índices em rd_metricas_email
CREATE INDEX IF NOT EXISTS idx_rd_metricas_campanha ON rd_metricas_email(campanha_id);

-- Índices em rd_eventos_whatsapp
CREATE INDEX IF NOT EXISTS idx_rd_wpp_email ON rd_eventos_whatsapp(contato_email);
CREATE INDEX IF NOT EXISTS idx_rd_wpp_data ON rd_eventos_whatsapp(ocorrido_em);
CREATE INDEX IF NOT EXISTS idx_rd_wpp_campanha ON rd_eventos_whatsapp(campanha_id);

-- Índices em rd_etapas_automacao
CREATE INDEX IF NOT EXISTS idx_rd_etapas_automacao ON rd_etapas_automacao(automacao_id);

-- ----------------------------------------------------------------
-- INSERÇÃO INICIAL NO LOG DE SINCRONIZAÇÃO
-- ----------------------------------------------------------------
INSERT INTO rd_sync_log (tabela, status, mensagem, total_registros)
VALUES
    ('rd_automacoes', 'pending', 'Aguardando primeira sincronização', 0),
    ('rd_campanhas_email', 'pending', 'Aguardando primeira sincronização', 0),
    ('rd_metricas_email', 'pending', 'Aguardando primeira sincronização', 0),
    ('rd_eventos_whatsapp', 'pending', 'Aguardando primeira sincronização', 0),
    ('rd_contatos', 'pending', 'Aguardando primeira sincronização', 0),
    ('rd_conversoes', 'pending', 'Aguardando primeira sincronização', 0)
ON CONFLICT DO NOTHING;

-- ----------------------------------------------------------------
-- COMENTÁRIO FINAL
-- ----------------------------------------------------------------
-- Após executar este script, rode o backend e acesse:
--   POST /sync/rd-station  → inicia sincronização completa
--   GET  /sync/status      → verifica status da sincronização
-- ============================================================
