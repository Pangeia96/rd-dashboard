-- ============================================================
-- ÍNDICES PARA pedidos_consolidado — Criação sem bloqueio
-- ============================================================
-- Execute cada comando SEPARADAMENTE no SQL Editor do Supabase.
-- Copie e execute UM de cada vez, aguardando terminar antes do próximo.
-- ⚠️  Cada índice pode demorar 1-3 minutos (normal para tabelas grandes).
-- ============================================================

-- ÍNDICE 1 — Execute primeiro (mais importante)
-- Filtra pedidos pagos por data (consulta mais comum do dashboard)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_pedidos_status_pago_em
ON pedidos_consolidado (status_pagamento, pago_em);

-- ============================================================
-- Após o índice 1 terminar, execute o índice 2:
-- ============================================================

-- ÍNDICE 2 — Para cruzamento com RD Station por e-mail
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_pedidos_email_contato
ON pedidos_consolidado (email_contato);

-- ============================================================
-- Após o índice 2 terminar, execute o índice 3:
-- ============================================================

-- ÍNDICE 3 — Para deduplicação de pedidos
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_pedidos_id_pedido
ON pedidos_consolidado (id_pedido);
