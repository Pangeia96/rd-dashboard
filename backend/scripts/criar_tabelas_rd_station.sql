-- ============================================================
-- DASHBOARD RD STATION — Criação das Tabelas no Supabase
-- ============================================================
-- Instruções:
--   1. Acesse supabase.com → seu projeto
--   2. No menu lateral, clique em "SQL Editor"
--   3. Cole TODO este conteúdo e clique em "Run"
-- ============================================================


-- 1. FLUXOS DE AUTOMAÇÃO
CREATE TABLE IF NOT EXISTS rd_automacoes (
    id               TEXT PRIMARY KEY,
    nome             TEXT NOT NULL,
    status           TEXT DEFAULT 'active',
    total_contatos   INTEGER DEFAULT 0,
    criado_em        TIMESTAMPTZ,
    atualizado_em    TIMESTAMPTZ,
    sincronizado_em  TIMESTAMPTZ DEFAULT NOW()
);


-- 2. ETAPAS DE CADA FLUXO
CREATE TABLE IF NOT EXISTS rd_etapas_automacao (
    id               TEXT PRIMARY KEY,
    automacao_id     TEXT REFERENCES rd_automacoes(id) ON DELETE CASCADE,
    nome             TEXT NOT NULL,
    tipo             TEXT,
    ordem            INTEGER DEFAULT 0,
    total_contatos   INTEGER DEFAULT 0,
    total_saidas     INTEGER DEFAULT 0,
    sincronizado_em  TIMESTAMPTZ DEFAULT NOW()
);


-- 3. CAMPANHAS DE E-MAIL
CREATE TABLE IF NOT EXISTS rd_campanhas_email (
    id               TEXT PRIMARY KEY,
    nome             TEXT NOT NULL,
    assunto          TEXT,
    status           TEXT,
    tipo             TEXT DEFAULT 'broadcast',
    automacao_id     TEXT,
    etapa_id         TEXT,
    enviado_em       TIMESTAMPTZ,
    sincronizado_em  TIMESTAMPTZ DEFAULT NOW()
);


-- 4. MÉTRICAS DE E-MAIL (por campanha)
CREATE TABLE IF NOT EXISTS rd_metricas_email (
    id                  SERIAL PRIMARY KEY,
    campanha_id         TEXT REFERENCES rd_campanhas_email(id) ON DELETE CASCADE,
    total_enviados      INTEGER DEFAULT 0,
    total_entregues     INTEGER DEFAULT 0,
    total_abertos       INTEGER DEFAULT 0,
    total_clicados      INTEGER DEFAULT 0,
    total_bounces       INTEGER DEFAULT 0,
    total_descadastros  INTEGER DEFAULT 0,
    total_spam          INTEGER DEFAULT 0,
    taxa_abertura       DECIMAL(5,2) DEFAULT 0,
    taxa_clique         DECIMAL(5,2) DEFAULT 0,
    taxa_bounce         DECIMAL(5,2) DEFAULT 0,
    sincronizado_em     TIMESTAMPTZ DEFAULT NOW()
);


-- 5. EVENTOS DE WHATSAPP
CREATE TABLE IF NOT EXISTS rd_eventos_whatsapp (
    id                TEXT PRIMARY KEY,
    campanha_id       TEXT,
    nome_campanha     TEXT,
    automacao_id      TEXT,
    etapa_id          TEXT,
    tipo_evento       TEXT,
    contato_email     TEXT,
    contato_telefone  TEXT,
    ocorrido_em       TIMESTAMPTZ,
    sincronizado_em   TIMESTAMPTZ DEFAULT NOW()
);


-- 6. CONTATOS / LEADS
CREATE TABLE IF NOT EXISTS rd_contatos (
    id               TEXT PRIMARY KEY,
    email            TEXT UNIQUE,
    nome             TEXT,
    telefone         TEXT,
    empresa          TEXT,
    cargo            TEXT,
    tags             TEXT[],
    lead_scoring     INTEGER DEFAULT 0,
    lifecycle_stage  TEXT,
    criado_em        TIMESTAMPTZ,
    atualizado_em    TIMESTAMPTZ,
    sincronizado_em  TIMESTAMPTZ DEFAULT NOW()
);


-- 7. CONVERSÕES
CREATE TABLE IF NOT EXISTS rd_conversoes (
    id                SERIAL PRIMARY KEY,
    contato_id        TEXT REFERENCES rd_contatos(id) ON DELETE CASCADE,
    contato_email     TEXT,
    tipo_conversao    TEXT,
    nome_conversao    TEXT,
    automacao_id      TEXT,
    etapa_id          TEXT,
    campanha_email_id TEXT,
    ocorrido_em       TIMESTAMPTZ,
    sincronizado_em   TIMESTAMPTZ DEFAULT NOW()
);


-- 8. LOG DE SINCRONIZAÇÃO
CREATE TABLE IF NOT EXISTS rd_sync_log (
    id                    SERIAL PRIMARY KEY,
    tabela                TEXT NOT NULL,
    ultima_sincronizacao  TIMESTAMPTZ DEFAULT NOW(),
    total_registros       INTEGER DEFAULT 0,
    status                TEXT DEFAULT 'success',
    mensagem              TEXT
);


-- ÍNDICES para performance
CREATE INDEX IF NOT EXISTS idx_rd_contatos_email       ON rd_contatos(email);
CREATE INDEX IF NOT EXISTS idx_rd_conversoes_email     ON rd_conversoes(contato_email);
CREATE INDEX IF NOT EXISTS idx_rd_conversoes_automacao ON rd_conversoes(automacao_id);
CREATE INDEX IF NOT EXISTS idx_rd_conversoes_data      ON rd_conversoes(ocorrido_em);
CREATE INDEX IF NOT EXISTS idx_rd_metricas_campanha    ON rd_metricas_email(campanha_id);
CREATE INDEX IF NOT EXISTS idx_rd_wpp_email            ON rd_eventos_whatsapp(contato_email);
CREATE INDEX IF NOT EXISTS idx_rd_wpp_data             ON rd_eventos_whatsapp(ocorrido_em);
CREATE INDEX IF NOT EXISTS idx_rd_wpp_campanha         ON rd_eventos_whatsapp(campanha_id);
CREATE INDEX IF NOT EXISTS idx_rd_etapas_automacao     ON rd_etapas_automacao(automacao_id);


-- Registro inicial no log de sincronização
INSERT INTO rd_sync_log (tabela, status, mensagem, total_registros)
VALUES
    ('rd_automacoes',        'pending', 'Aguardando primeira sincronização', 0),
    ('rd_campanhas_email',   'pending', 'Aguardando primeira sincronização', 0),
    ('rd_metricas_email',    'pending', 'Aguardando primeira sincronização', 0),
    ('rd_eventos_whatsapp',  'pending', 'Aguardando primeira sincronização', 0),
    ('rd_contatos',          'pending', 'Aguardando primeira sincronização', 0),
    ('rd_conversoes',        'pending', 'Aguardando primeira sincronização', 0)
ON CONFLICT DO NOTHING;
