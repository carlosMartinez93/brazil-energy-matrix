-- ============================================================
-- queries_energia.sql
-- Análise da Matriz Energética Brasileira
-- Autor: Carlos Henrique
-- Fonte dos dados: ONS (ons.org.br) e ANEEL (aneel.gov.br)
-- ============================================================


-- ============================================================
-- 1. VISÃO GERAL — Geração total por fonte e ano
-- ============================================================
SELECT
    ano,
    fonte,
    tipo_fonte,
    grupo_fonte,
    ROUND(SUM(geracao_total_gwh), 0)                         AS geracao_gwh,
    ROUND(
        SUM(geracao_total_gwh) * 100.0 /
        SUM(SUM(geracao_total_gwh)) OVER (PARTITION BY ano),
        2
    )                                                         AS participacao_pct
FROM geracao_anual_por_fonte
GROUP BY ano, fonte, tipo_fonte, grupo_fonte
ORDER BY ano, geracao_gwh DESC;


-- ============================================================
-- 2. EVOLUÇÃO DO MIX RENOVÁVEL (% da matriz)
-- ============================================================
WITH total_por_ano AS (
    SELECT ano, SUM(geracao_total_gwh) AS total_gwh
    FROM geracao_anual_por_fonte
    GROUP BY ano
),
renovavel_por_ano AS (
    SELECT ano, SUM(geracao_total_gwh) AS gwh_renovavel
    FROM geracao_anual_por_fonte
    WHERE tipo_fonte = 'Renovável'
    GROUP BY ano
)
SELECT
    t.ano,
    ROUND(t.total_gwh, 0)                                          AS geracao_total_gwh,
    ROUND(r.gwh_renovavel, 0)                                      AS geracao_renovavel_gwh,
    ROUND(r.gwh_renovavel * 100.0 / t.total_gwh, 2)               AS pct_renovavel,
    ROUND(t.total_gwh - r.gwh_renovavel, 0)                       AS geracao_nao_renovavel_gwh,
    ROUND((t.total_gwh - r.gwh_renovavel) * 100.0 / t.total_gwh, 2) AS pct_nao_renovavel
FROM total_por_ano t
JOIN renovavel_por_ano r USING (ano)
ORDER BY ano;


-- ============================================================
-- 3. CRESCIMENTO ANUAL (YoY) POR FONTE
-- ============================================================
WITH geracao_anual AS (
    SELECT ano, fonte, SUM(geracao_total_gwh) AS gwh
    FROM geracao_anual_por_fonte
    GROUP BY ano, fonte
),
com_lag AS (
    SELECT
        ano,
        fonte,
        gwh,
        LAG(gwh) OVER (PARTITION BY fonte ORDER BY ano) AS gwh_ano_anterior
    FROM geracao_anual
)
SELECT
    ano,
    fonte,
    ROUND(gwh, 0)                                                    AS geracao_gwh,
    ROUND(gwh_ano_anterior, 0)                                       AS geracao_gwh_ano_ant,
    ROUND((gwh - gwh_ano_anterior) * 100.0 / NULLIF(gwh_ano_anterior, 0), 1) AS crescimento_yoy_pct
FROM com_lag
WHERE gwh_ano_anterior IS NOT NULL
ORDER BY ano, crescimento_yoy_pct DESC;


-- ============================================================
-- 4. NOVAS RENOVÁVEIS — Solar e Eólica em destaque
-- ============================================================
SELECT
    ano,
    fonte,
    ROUND(SUM(geracao_total_gwh), 0)    AS geracao_gwh,
    ROUND(
        SUM(geracao_total_gwh) * 100.0 /
        SUM(SUM(geracao_total_gwh)) OVER (PARTITION BY ano),
        3
    )                                    AS participacao_pct_total
FROM geracao_anual_por_fonte
WHERE fonte IN ('Solar', 'Eólica')
GROUP BY ano, fonte
ORDER BY ano, fonte;


-- ============================================================
-- 5. RANKING DE FONTES — Último ano disponível
-- ============================================================
WITH ultimo_ano AS (
    SELECT MAX(ano) AS ano FROM geracao_anual_por_fonte
)
SELECT
    g.fonte,
    g.tipo_fonte,
    ROUND(SUM(g.geracao_total_gwh), 0)                              AS geracao_gwh,
    ROUND(
        SUM(g.geracao_total_gwh) * 100.0 /
        SUM(SUM(g.geracao_total_gwh)) OVER (),
        2
    )                                                                AS participacao_pct,
    RANK() OVER (ORDER BY SUM(g.geracao_total_gwh) DESC)           AS ranking
FROM geracao_anual_por_fonte g
INNER JOIN ultimo_ano u ON g.ano = u.ano
GROUP BY g.fonte, g.tipo_fonte
ORDER BY ranking;


-- ============================================================
-- 6. HÍDRICA vs NOVAS RENOVÁVEIS — Inversão de tendência
-- ============================================================
WITH grupos AS (
    SELECT
        ano,
        CASE
            WHEN fonte = 'Hidráulica' THEN 'Hídrica tradicional'
            WHEN fonte IN ('Solar', 'Eólica') THEN 'Novas renováveis'
            ELSE 'Outras'
        END AS categoria,
        geracao_total_gwh
    FROM geracao_anual_por_fonte
),
agg AS (
    SELECT ano, categoria, ROUND(SUM(geracao_total_gwh), 0) AS gwh
    FROM grupos
    GROUP BY ano, categoria
)
SELECT
    ano,
    MAX(CASE WHEN categoria = 'Hídrica tradicional' THEN gwh END) AS gwh_hidrica,
    MAX(CASE WHEN categoria = 'Novas renováveis'    THEN gwh END) AS gwh_novas_renovaveis,
    ROUND(
        MAX(CASE WHEN categoria = 'Novas renováveis' THEN gwh END) * 100.0 /
        NULLIF(MAX(CASE WHEN categoria = 'Hídrica tradicional' THEN gwh END), 0),
        1
    ) AS razao_novas_vs_hidrica_pct
FROM agg
GROUP BY ano
ORDER BY ano;


-- ============================================================
-- 7. ANÁLISE DE SAZONALIDADE — Geração mensal por fonte
-- (usar com tabela geracao_completa que tem granularidade mensal)
-- ============================================================
SELECT
    mes,
    fonte,
    ROUND(AVG(geracao_gwh), 0) AS media_mensal_gwh,
    ROUND(MAX(geracao_gwh), 0) AS max_mensal_gwh,
    ROUND(MIN(geracao_gwh), 0) AS min_mensal_gwh,
    ROUND(STDDEV(geracao_gwh), 0) AS desvio_padrao_gwh
FROM geracao_completa
WHERE fonte IN ('Hidráulica', 'Eólica', 'Solar')
GROUP BY mes, fonte
ORDER BY fonte, mes;
