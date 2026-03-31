-- ============================================================
-- FUNÇÕES SQL OTIMIZADAS — Pangeia 96 Dashboard
-- ============================================================
-- Versão otimizada: usa MIN() para deduplicar pedidos
-- em vez de DISTINCT ON, que é mais eficiente com índices.
--
-- Instruções:
--   1. Acesse supabase.com → SQL Editor → New query
--   2. Cole TODO este conteúdo e clique em "Run"
-- ============================================================


-- ============================================================
-- FUNÇÃO 1: Resumo de KPIs
-- ============================================================
CREATE OR REPLACE FUNCTION get_pedidos_resumo(
    p_date_from TEXT DEFAULT '2025-09-01',
    p_date_to   TEXT DEFAULT NULL
)
RETURNS JSON
LANGUAGE sql
STABLE
AS $$
    SELECT json_build_object(
        'total_pedidos',  COUNT(DISTINCT id_pedido),
        'receita_total',  ROUND(SUM(total_unico)::NUMERIC, 2),
        'ticket_medio',   ROUND(AVG(total_unico)::NUMERIC, 2),
        'total_clientes', COUNT(DISTINCT email_contato),
        'periodo',        json_build_object(
                            'de',  p_date_from,
                            'ate', COALESCE(p_date_to, TO_CHAR(NOW(), 'YYYY-MM-DD'))
                          )
    )
    FROM (
        SELECT id_pedido, MIN(total) AS total_unico, MIN(email_contato) AS email_contato
        FROM pedidos_consolidado
        WHERE status_pagamento = 'paid'
          AND pago_em >= (p_date_from || 'T00:00:00')::TIMESTAMPTZ
          AND pago_em <= (COALESCE(p_date_to, TO_CHAR(NOW(), 'YYYY-MM-DD')) || 'T23:59:59')::TIMESTAMPTZ
        GROUP BY id_pedido
    ) sub;
$$;


-- ============================================================
-- FUNÇÃO 2: Timeline de vendas por dia/semana/mês
-- ============================================================
CREATE OR REPLACE FUNCTION get_pedidos_timeline(
    p_date_from   TEXT DEFAULT '2025-09-01',
    p_date_to     TEXT DEFAULT NULL,
    p_granularity TEXT DEFAULT 'day'
)
RETURNS JSON
LANGUAGE sql
STABLE
AS $$
    SELECT COALESCE(json_agg(row ORDER BY row.periodo), '[]'::JSON)
    FROM (
        SELECT
            CASE p_granularity
                WHEN 'month' THEN TO_CHAR(MIN(pago_em), 'YYYY-MM')
                WHEN 'week'  THEN TO_CHAR(DATE_TRUNC('week', MIN(pago_em)), 'YYYY-MM-DD')
                ELSE              TO_CHAR(MIN(pago_em), 'YYYY-MM-DD')
            END AS periodo,
            COUNT(DISTINCT id_pedido) AS pedidos,
            ROUND(SUM(total_unico)::NUMERIC, 2) AS receita
        FROM (
            SELECT id_pedido, MIN(pago_em) AS pago_em, MIN(total) AS total_unico
            FROM pedidos_consolidado
            WHERE status_pagamento = 'paid'
              AND pago_em >= (p_date_from || 'T00:00:00')::TIMESTAMPTZ
              AND pago_em <= (COALESCE(p_date_to, TO_CHAR(NOW(), 'YYYY-MM-DD')) || 'T23:59:59')::TIMESTAMPTZ
            GROUP BY id_pedido
        ) sub
        GROUP BY
            CASE p_granularity
                WHEN 'month' THEN TO_CHAR(pago_em, 'YYYY-MM')
                WHEN 'week'  THEN TO_CHAR(DATE_TRUNC('week', pago_em), 'YYYY-MM-DD')
                ELSE              TO_CHAR(pago_em, 'YYYY-MM-DD')
            END
    ) row;
$$;


-- ============================================================
-- FUNÇÃO 3: Receita por canal de origem e método de pagamento
-- ============================================================
CREATE OR REPLACE FUNCTION get_pedidos_por_canal(
    p_date_from TEXT DEFAULT '2025-09-01',
    p_date_to   TEXT DEFAULT NULL
)
RETURNS JSON
LANGUAGE sql
STABLE
AS $$
    SELECT json_build_object(
        'por_origem', (
            SELECT COALESCE(json_agg(r ORDER BY r.receita DESC), '[]'::JSON)
            FROM (
                SELECT
                    COALESCE(origem_pedido, 'unknown') AS canal,
                    COUNT(DISTINCT id_pedido) AS pedidos,
                    ROUND(SUM(total_unico)::NUMERIC, 2) AS receita
                FROM (
                    SELECT id_pedido, MIN(origem_pedido) AS origem_pedido, MIN(total) AS total_unico
                    FROM pedidos_consolidado
                    WHERE status_pagamento = 'paid'
                      AND pago_em >= (p_date_from || 'T00:00:00')::TIMESTAMPTZ
                      AND pago_em <= (COALESCE(p_date_to, TO_CHAR(NOW(), 'YYYY-MM-DD')) || 'T23:59:59')::TIMESTAMPTZ
                    GROUP BY id_pedido
                ) sub
                GROUP BY COALESCE(origem_pedido, 'unknown')
            ) r
        ),
        'por_pagamento', (
            SELECT COALESCE(json_agg(r ORDER BY r.receita DESC), '[]'::JSON)
            FROM (
                SELECT
                    COALESCE(metodo_pagamento, 'unknown') AS metodo,
                    COUNT(DISTINCT id_pedido) AS pedidos,
                    ROUND(SUM(total_unico)::NUMERIC, 2) AS receita
                FROM (
                    SELECT id_pedido, MIN(metodo_pagamento) AS metodo_pagamento, MIN(total) AS total_unico
                    FROM pedidos_consolidado
                    WHERE status_pagamento = 'paid'
                      AND pago_em >= (p_date_from || 'T00:00:00')::TIMESTAMPTZ
                      AND pago_em <= (COALESCE(p_date_to, TO_CHAR(NOW(), 'YYYY-MM-DD')) || 'T23:59:59')::TIMESTAMPTZ
                    GROUP BY id_pedido
                ) sub
                GROUP BY COALESCE(metodo_pagamento, 'unknown')
            ) r
        )
    );
$$;


-- ============================================================
-- FUNÇÃO 4: Top produtos mais vendidos
-- ============================================================
CREATE OR REPLACE FUNCTION get_top_produtos(
    p_date_from TEXT DEFAULT '2025-09-01',
    p_date_to   TEXT DEFAULT NULL,
    p_limit     INT  DEFAULT 10
)
RETURNS JSON
LANGUAGE sql
STABLE
AS $$
    SELECT COALESCE(json_agg(r ORDER BY r.receita DESC), '[]'::JSON)
    FROM (
        SELECT
            COALESCE(nome_produto_simples, nome_produto, 'Desconhecido') AS nome,
            sku_produto,
            SUM(quantidade) AS quantidade,
            ROUND(SUM(preco * quantidade)::NUMERIC, 2) AS receita
        FROM pedidos_consolidado
        WHERE status_pagamento = 'paid'
          AND pago_em >= (p_date_from || 'T00:00:00')::TIMESTAMPTZ
          AND pago_em <= (COALESCE(p_date_to, TO_CHAR(NOW(), 'YYYY-MM-DD')) || 'T23:59:59')::TIMESTAMPTZ
        GROUP BY COALESCE(nome_produto_simples, nome_produto, 'Desconhecido'), sku_produto
        ORDER BY receita DESC
        LIMIT p_limit
    ) r;
$$;


-- ============================================================
-- FUNÇÃO 5: Receita por estado (UF)
-- ============================================================
CREATE OR REPLACE FUNCTION get_pedidos_por_estado(
    p_date_from TEXT DEFAULT '2025-09-01',
    p_date_to   TEXT DEFAULT NULL
)
RETURNS JSON
LANGUAGE sql
STABLE
AS $$
    SELECT COALESCE(json_agg(r ORDER BY r.receita DESC), '[]'::JSON)
    FROM (
        SELECT
            COALESCE(estado_entrega, 'Desconhecido') AS estado,
            COUNT(DISTINCT id_pedido) AS pedidos,
            ROUND(SUM(total_unico)::NUMERIC, 2) AS receita
        FROM (
            SELECT id_pedido, MIN(estado_entrega) AS estado_entrega, MIN(total) AS total_unico
            FROM pedidos_consolidado
            WHERE status_pagamento = 'paid'
              AND pago_em >= (p_date_from || 'T00:00:00')::TIMESTAMPTZ
              AND pago_em <= (COALESCE(p_date_to, TO_CHAR(NOW(), 'YYYY-MM-DD')) || 'T23:59:59')::TIMESTAMPTZ
            GROUP BY id_pedido
        ) sub
        GROUP BY COALESCE(estado_entrega, 'Desconhecido')
    ) r;
$$;


-- ============================================================
-- FUNÇÃO 6: Dashboard completo (todas as métricas em 1 chamada)
-- ============================================================
CREATE OR REPLACE FUNCTION get_dashboard_completo(
    p_date_from TEXT DEFAULT '2025-09-01',
    p_date_to   TEXT DEFAULT NULL
)
RETURNS JSON
LANGUAGE sql
STABLE
AS $$
    SELECT json_build_object(
        'kpis',         get_pedidos_resumo(p_date_from, p_date_to),
        'timeline',     get_pedidos_timeline(p_date_from, p_date_to, 'day'),
        'canais',       get_pedidos_por_canal(p_date_from, p_date_to),
        'top_produtos', get_top_produtos(p_date_from, p_date_to, 10),
        'por_estado',   get_pedidos_por_estado(p_date_from, p_date_to),
        'gerado_em',    NOW()::TEXT
    );
$$;
