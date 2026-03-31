-- ============================================================
-- FUNÇÕES SQL PARA O DASHBOARD — Pangeia 96
-- ============================================================
-- Estas funções fazem toda a agregação DENTRO do banco,
-- retornando apenas o resultado final para o dashboard.
-- Isso resolve o problema de 25k+ pedidos por mês:
-- em vez de trazer todos os registros, o banco calcula
-- e retorna apenas os números prontos.
--
-- Instruções:
--   1. Acesse supabase.com → seu projeto → SQL Editor
--   2. Cole TODO este conteúdo e clique em "Run"
-- ============================================================


-- ============================================================
-- FUNÇÃO 1: Resumo de KPIs (receita, pedidos, ticket médio)
-- ============================================================
CREATE OR REPLACE FUNCTION get_pedidos_resumo(
    p_date_from TEXT DEFAULT '2025-09-01',
    p_date_to   TEXT DEFAULT NULL
)
RETURNS JSON
LANGUAGE plpgsql
AS $$
DECLARE
    v_date_to TEXT;
    resultado JSON;
BEGIN
    v_date_to := COALESCE(p_date_to, TO_CHAR(NOW(), 'YYYY-MM-DD'));

    SELECT json_build_object(
        'total_pedidos',   COUNT(DISTINCT id_pedido),
        'receita_total',   ROUND(SUM(DISTINCT_TOTAL), 2),
        'ticket_medio',    ROUND(AVG(DISTINCT_TOTAL), 2),
        'total_clientes',  COUNT(DISTINCT email_contato),
        'periodo',         json_build_object('de', p_date_from, 'ate', v_date_to)
    ) INTO resultado
    FROM (
        SELECT DISTINCT ON (id_pedido)
            id_pedido,
            total AS DISTINCT_TOTAL,
            email_contato
        FROM pedidos_consolidado
        WHERE status_pagamento = 'paid'
          AND pago_em >= (p_date_from || 'T00:00:00')::TIMESTAMPTZ
          AND pago_em <= (v_date_to || 'T23:59:59')::TIMESTAMPTZ
    ) sub;

    RETURN resultado;
END;
$$;


-- ============================================================
-- FUNÇÃO 2: Timeline de vendas por dia
-- ============================================================
CREATE OR REPLACE FUNCTION get_pedidos_timeline(
    p_date_from  TEXT DEFAULT '2025-09-01',
    p_date_to    TEXT DEFAULT NULL,
    p_granularity TEXT DEFAULT 'day'
)
RETURNS JSON
LANGUAGE plpgsql
AS $$
DECLARE
    v_date_to TEXT;
    resultado JSON;
BEGIN
    v_date_to := COALESCE(p_date_to, TO_CHAR(NOW(), 'YYYY-MM-DD'));

    SELECT json_agg(
        json_build_object(
            'data',    periodo,
            'pedidos', total_pedidos,
            'receita', total_receita
        ) ORDER BY periodo
    ) INTO resultado
    FROM (
        SELECT
            CASE p_granularity
                WHEN 'month' THEN TO_CHAR(pago_em, 'YYYY-MM')
                WHEN 'week'  THEN TO_CHAR(DATE_TRUNC('week', pago_em), 'YYYY-MM-DD')
                ELSE              TO_CHAR(pago_em, 'YYYY-MM-DD')
            END AS periodo,
            COUNT(DISTINCT id_pedido) AS total_pedidos,
            ROUND(SUM(total_unico), 2) AS total_receita
        FROM (
            SELECT DISTINCT ON (id_pedido)
                id_pedido,
                pago_em,
                total AS total_unico
            FROM pedidos_consolidado
            WHERE status_pagamento = 'paid'
              AND pago_em >= (p_date_from || 'T00:00:00')::TIMESTAMPTZ
              AND pago_em <= (v_date_to || 'T23:59:59')::TIMESTAMPTZ
        ) sub
        GROUP BY periodo
    ) agg;

    RETURN COALESCE(resultado, '[]'::JSON);
END;
$$;


-- ============================================================
-- FUNÇÃO 3: Receita por canal de origem
-- ============================================================
CREATE OR REPLACE FUNCTION get_pedidos_por_canal(
    p_date_from TEXT DEFAULT '2025-09-01',
    p_date_to   TEXT DEFAULT NULL
)
RETURNS JSON
LANGUAGE plpgsql
AS $$
DECLARE
    v_date_to TEXT;
    resultado JSON;
BEGIN
    v_date_to := COALESCE(p_date_to, TO_CHAR(NOW(), 'YYYY-MM-DD'));

    SELECT json_build_object(
        'por_origem',    (
            SELECT json_agg(json_build_object(
                'canal',    COALESCE(origem_pedido, 'unknown'),
                'pedidos',  total_pedidos,
                'receita',  total_receita
            ) ORDER BY total_receita DESC)
            FROM (
                SELECT
                    origem_pedido,
                    COUNT(DISTINCT id_pedido) AS total_pedidos,
                    ROUND(SUM(total_unico), 2) AS total_receita
                FROM (
                    SELECT DISTINCT ON (id_pedido)
                        id_pedido, origem_pedido, total AS total_unico
                    FROM pedidos_consolidado
                    WHERE status_pagamento = 'paid'
                      AND pago_em >= (p_date_from || 'T00:00:00')::TIMESTAMPTZ
                      AND pago_em <= (v_date_to || 'T23:59:59')::TIMESTAMPTZ
                ) sub
                GROUP BY origem_pedido
            ) agg
        ),
        'por_pagamento', (
            SELECT json_agg(json_build_object(
                'metodo',   COALESCE(metodo_pagamento, 'unknown'),
                'pedidos',  total_pedidos,
                'receita',  total_receita
            ) ORDER BY total_receita DESC)
            FROM (
                SELECT
                    metodo_pagamento,
                    COUNT(DISTINCT id_pedido) AS total_pedidos,
                    ROUND(SUM(total_unico), 2) AS total_receita
                FROM (
                    SELECT DISTINCT ON (id_pedido)
                        id_pedido, metodo_pagamento, total AS total_unico
                    FROM pedidos_consolidado
                    WHERE status_pagamento = 'paid'
                      AND pago_em >= (p_date_from || 'T00:00:00')::TIMESTAMPTZ
                      AND pago_em <= (v_date_to || 'T23:59:59')::TIMESTAMPTZ
                ) sub
                GROUP BY metodo_pagamento
            ) agg
        )
    ) INTO resultado;

    RETURN resultado;
END;
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
LANGUAGE plpgsql
AS $$
DECLARE
    v_date_to TEXT;
    resultado JSON;
BEGIN
    v_date_to := COALESCE(p_date_to, TO_CHAR(NOW(), 'YYYY-MM-DD'));

    SELECT json_agg(
        json_build_object(
            'nome',       nome,
            'sku',        sku_produto,
            'quantidade', total_quantidade,
            'receita',    total_receita
        ) ORDER BY total_receita DESC
    ) INTO resultado
    FROM (
        SELECT
            COALESCE(nome_produto_simples, nome_produto, 'Desconhecido') AS nome,
            sku_produto,
            SUM(quantidade) AS total_quantidade,
            ROUND(SUM(preco * quantidade), 2) AS total_receita
        FROM pedidos_consolidado
        WHERE status_pagamento = 'paid'
          AND pago_em >= (p_date_from || 'T00:00:00')::TIMESTAMPTZ
          AND pago_em <= (v_date_to || 'T23:59:59')::TIMESTAMPTZ
        GROUP BY COALESCE(nome_produto_simples, nome_produto, 'Desconhecido'), sku_produto
        ORDER BY total_receita DESC
        LIMIT p_limit
    ) sub;

    RETURN COALESCE(resultado, '[]'::JSON);
END;
$$;


-- ============================================================
-- FUNÇÃO 5: Receita por estado (UF)
-- ============================================================
CREATE OR REPLACE FUNCTION get_pedidos_por_estado(
    p_date_from TEXT DEFAULT '2025-09-01',
    p_date_to   TEXT DEFAULT NULL
)
RETURNS JSON
LANGUAGE plpgsql
AS $$
DECLARE
    v_date_to TEXT;
    resultado JSON;
BEGIN
    v_date_to := COALESCE(p_date_to, TO_CHAR(NOW(), 'YYYY-MM-DD'));

    SELECT json_agg(
        json_build_object(
            'estado',   COALESCE(estado_entrega, 'Desconhecido'),
            'pedidos',  total_pedidos,
            'receita',  total_receita
        ) ORDER BY total_receita DESC
    ) INTO resultado
    FROM (
        SELECT
            estado_entrega,
            COUNT(DISTINCT id_pedido) AS total_pedidos,
            ROUND(SUM(total_unico), 2) AS total_receita
        FROM (
            SELECT DISTINCT ON (id_pedido)
                id_pedido, estado_entrega, total AS total_unico
            FROM pedidos_consolidado
            WHERE status_pagamento = 'paid'
              AND pago_em >= (p_date_from || 'T00:00:00')::TIMESTAMPTZ
              AND pago_em <= (v_date_to || 'T23:59:59')::TIMESTAMPTZ
        ) sub
        GROUP BY estado_entrega
    ) agg;

    RETURN COALESCE(resultado, '[]'::JSON);
END;
$$;


-- ============================================================
-- FUNÇÃO 6: Dashboard completo (todas as métricas em 1 chamada)
-- ============================================================
CREATE OR REPLACE FUNCTION get_dashboard_completo(
    p_date_from TEXT DEFAULT '2025-09-01',
    p_date_to   TEXT DEFAULT NULL
)
RETURNS JSON
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN json_build_object(
        'kpis',        get_pedidos_resumo(p_date_from, p_date_to),
        'timeline',    get_pedidos_timeline(p_date_from, p_date_to, 'day'),
        'canais',      get_pedidos_por_canal(p_date_from, p_date_to),
        'top_produtos', get_top_produtos(p_date_from, p_date_to, 10),
        'por_estado',  get_pedidos_por_estado(p_date_from, p_date_to),
        'gerado_em',   NOW()::TEXT
    );
END;
$$;
