-- ============================================================
-- ÍNDICES para a tabela pedidos_consolidado
-- ============================================================
-- Estes índices são ESSENCIAIS para que as consultas do dashboard
-- respondam em < 1 segundo com 100k+ registros.
--
-- Instruções:
--   1. Acesse supabase.com → seu projeto → SQL Editor
--   2. Cole TODO este conteúdo e clique em "Run"
--   ⚠️  Pode demorar alguns minutos para criar os índices
--      (normal para tabelas grandes — só precisa fazer uma vez)
-- ============================================================

-- Índice na data de pagamento (filtro mais usado no dashboard)
CREATE INDEX IF NOT EXISTS idx_pedidos_pago_em
    ON pedidos_consolidado(pago_em);

-- Índice no status de pagamento (filtramos sempre por "paid")
CREATE INDEX IF NOT EXISTS idx_pedidos_status_pagamento
    ON pedidos_consolidado(status_pagamento);

-- Índice composto: status + data (consulta mais comum do dashboard)
CREATE INDEX IF NOT EXISTS idx_pedidos_status_data
    ON pedidos_consolidado(status_pagamento, pago_em);

-- Índice no email do contato (para cruzamento com RD Station)
CREATE INDEX IF NOT EXISTS idx_pedidos_email
    ON pedidos_consolidado(email_contato);

-- Índice no id do pedido (para deduplicação)
CREATE INDEX IF NOT EXISTS idx_pedidos_id_pedido
    ON pedidos_consolidado(id_pedido);

-- Índice no estado de entrega (para análise geográfica)
CREATE INDEX IF NOT EXISTS idx_pedidos_estado
    ON pedidos_consolidado(estado_entrega);

-- Índice na origem do pedido (mobile, desktop, etc.)
CREATE INDEX IF NOT EXISTS idx_pedidos_origem
    ON pedidos_consolidado(origem_pedido);

-- ============================================================
-- Após criar os índices, as consultas do dashboard vão
-- responder em < 1 segundo mesmo com 100k+ registros.
-- ============================================================
