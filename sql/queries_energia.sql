-- ============================================================
-- queries_energia.sql
-- Analysis of the Brazilian Energy Matrix
-- Author: Carlos Henrique
-- Data source: ONS open data, "Balanço de Energia nos Subsistemas" (dados.ons.org.br)
-- ============================================================


-- ============================================================
-- 1. OVERVIEW — Total generation by source and year
-- ============================================================
SELECT
    ano,
    fonte,
    tipo_fonte,
    grupo_fonte,
    ROUND(SUM(geracao_total_gwh), 0)                         AS generation_gwh,
    ROUND(
        SUM(geracao_total_gwh) * 100.0 /
        SUM(SUM(geracao_total_gwh)) OVER (PARTITION BY ano),
        2
    )                                                         AS share_pct
FROM geracao_anual_por_fonte
GROUP BY ano, fonte, tipo_fonte, grupo_fonte
ORDER BY ano, generation_gwh DESC;


-- ============================================================
-- 2. HYDRO + WIND + SOLAR SHARE (% of generation - biomass and nuclear sit inside thermal in the ONS dataset)
-- Reading note: shares before and after the 2023 solar series break are not directly comparable.
-- ============================================================
WITH total_by_year AS (
    SELECT ano, SUM(geracao_total_gwh) AS total_gwh
    FROM geracao_anual_por_fonte
    GROUP BY ano
),
hydro_wind_solar_by_year AS (
    SELECT ano, SUM(geracao_total_gwh) AS gwh_hydro_wind_solar
    FROM geracao_anual_por_fonte
    WHERE tipo_fonte = 'Hidro+Eólica+Solar'
    GROUP BY ano
)
SELECT
    t.ano,
    ROUND(t.total_gwh, 0)                                          AS total_generation_gwh,
    ROUND(r.gwh_hydro_wind_solar, 0)                                      AS hydro_wind_solar_generation_gwh,
    ROUND(r.gwh_hydro_wind_solar * 100.0 / t.total_gwh, 2)               AS pct_hydro_wind_solar,
    ROUND(t.total_gwh - r.gwh_hydro_wind_solar, 0)                       AS thermal_generation_gwh,
    ROUND((t.total_gwh - r.gwh_hydro_wind_solar) * 100.0 / t.total_gwh, 2) AS pct_thermal
FROM total_by_year t
JOIN hydro_wind_solar_by_year r USING (ano)
ORDER BY ano;


-- ============================================================
-- 3. ANNUAL GROWTH (YoY) BY SOURCE
-- Series break: the ONS solar series jumps in May 2023 (likely distributed generation
-- being added - cause not confirmed). Solar YoY for 2023 and 2024 compares across the break,
-- so it is returned as NULL instead of a number. See src/regimes.py.
-- ============================================================
WITH annual_generation AS (
    SELECT ano, fonte, SUM(geracao_total_gwh) AS gwh
    FROM geracao_anual_por_fonte
    GROUP BY ano, fonte
),
with_lag AS (
    SELECT
        ano,
        fonte,
        gwh,
        LAG(gwh) OVER (PARTITION BY fonte ORDER BY ano) AS gwh_prev_year
    FROM annual_generation
)
SELECT
    ano,
    fonte,
    ROUND(gwh, 0)                                                    AS generation_gwh,
    ROUND(gwh_prev_year, 0)                                          AS generation_gwh_prev_year,
    CASE
        WHEN fonte = 'Solar' AND ano IN (2023, 2024) THEN NULL
        ELSE ROUND((gwh - gwh_prev_year) * 100.0 / NULLIF(gwh_prev_year, 0), 1)
    END                                                              AS yoy_growth_pct
FROM with_lag
WHERE gwh_prev_year IS NOT NULL
ORDER BY ano, yoy_growth_pct DESC;


-- ============================================================
-- 4. NEW RENEWABLES — Solar and Wind highlighted
-- ============================================================
SELECT
    ano,
    fonte,
    ROUND(SUM(geracao_total_gwh), 0)    AS generation_gwh,
    ROUND(
        SUM(geracao_total_gwh) * 100.0 /
        SUM(SUM(geracao_total_gwh)) OVER (PARTITION BY ano),
        3
    )                                    AS total_share_pct
FROM geracao_anual_por_fonte
WHERE fonte IN ('Solar', 'Eólica')
GROUP BY ano, fonte
ORDER BY ano, fonte;


-- ============================================================
-- 5. SOURCE RANKING — Last available year
-- ============================================================
WITH last_year AS (
    SELECT MAX(ano) AS ano FROM geracao_anual_por_fonte
)
SELECT
    g.fonte,
    g.tipo_fonte,
    ROUND(SUM(g.geracao_total_gwh), 0)                              AS generation_gwh,
    ROUND(
        SUM(g.geracao_total_gwh) * 100.0 /
        SUM(SUM(g.geracao_total_gwh)) OVER (),
        2
    )                                                                AS share_pct,
    RANK() OVER (ORDER BY SUM(g.geracao_total_gwh) DESC)           AS ranking
FROM geracao_anual_por_fonte g
INNER JOIN last_year u ON g.ano = u.ano
GROUP BY g.fonte, g.tipo_fonte
ORDER BY ranking;


-- ============================================================
-- 6. HYDRO vs NEW RENEWABLES — Trend reversal
-- Reading note: "new renewables" includes solar, so the level crosses the 2023 series break.
-- ============================================================
WITH groups AS (
    SELECT
        ano,
        CASE
            WHEN fonte = 'Hidráulica' THEN 'Traditional Hydro'
            WHEN fonte IN ('Solar', 'Eólica') THEN 'New Renewables'
            ELSE 'Others'
        END AS category,
        geracao_total_gwh
    FROM geracao_anual_por_fonte
),
agg AS (
    SELECT ano, category, ROUND(SUM(geracao_total_gwh), 0) AS gwh
    FROM groups
    GROUP BY ano, category
)
SELECT
    ano,
    MAX(CASE WHEN category = 'Traditional Hydro' THEN gwh END) AS gwh_hydro,
    MAX(CASE WHEN category = 'New Renewables'    THEN gwh END) AS gwh_new_renewables,
    ROUND(
        MAX(CASE WHEN category = 'New Renewables' THEN gwh END) * 100.0 /
        NULLIF(MAX(CASE WHEN category = 'Traditional Hydro' THEN gwh END), 0),
        1
    ) AS ratio_new_vs_hydro_pct
FROM agg
GROUP BY ano
ORDER BY ano;


-- ============================================================
-- 7. SEASONALITY ANALYSIS — Monthly generation by source
-- (use with geracao_completa table which has monthly granularity)
-- ============================================================
SELECT
    mes,
    fonte,
    ROUND(AVG(geracao_gwh), 0) AS monthly_avg_gwh,
    ROUND(MAX(geracao_gwh), 0) AS monthly_max_gwh,
    ROUND(MIN(geracao_gwh), 0) AS monthly_min_gwh,
    ROUND(STDDEV(geracao_gwh), 0) AS std_dev_gwh
FROM geracao_completa
WHERE fonte IN ('Hidráulica', 'Eólica', 'Solar')
GROUP BY mes, fonte
ORDER BY fonte, mes;
