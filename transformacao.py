"""
transformacao.py
----------------
Limpeza, enriquecimento e preparação dos dados brutos para análise.
Gera os arquivos processados usados pelo dashboard e pelas queries SQL.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

RAW_DIR = Path(__file__).parent.parent / "data" / "raw"
PROC_DIR = Path(__file__).parent.parent / "data" / "processed"
PROC_DIR.mkdir(parents=True, exist_ok=True)


TIPO_FONTE = {
    "Hidráulica":   "Renovável",
    "Eólica":       "Renovável",
    "Solar":        "Renovável",
    "Biomassa":     "Renovável",
    "Nuclear":      "Baixo carbono",
    "Termelétrica": "Não renovável",
}

GRUPO_FONTE = {
    "Hidráulica":   "Hídrica",
    "Eólica":       "Novas renováveis",
    "Solar":        "Novas renováveis",
    "Biomassa":     "Biomassa",
    "Nuclear":      "Nuclear",
    "Termelétrica": "Fóssil",
}


def carregar_dados_brutos() -> pd.DataFrame:
    """Carrega dados de geração (reais ou sintéticos)."""
    caminhos = [
        RAW_DIR / "geracao_sintetica.parquet",
        RAW_DIR / "ons_geracao_historico.parquet",
    ]
    for caminho in caminhos:
        if caminho.exists():
            df = pd.read_parquet(caminho)
            logger.info(f"Dados carregados de {caminho.name} — {len(df):,} linhas")
            return df
    raise FileNotFoundError("Nenhum arquivo de geração encontrado. Execute src/ingestao.py primeiro.")


def limpar_e_enriquecer(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aplica limpeza e adiciona colunas derivadas para análise.
    """
    logger.info("Iniciando limpeza e enriquecimento...")

    # Garante tipos corretos
    df["data"] = pd.to_datetime(df["data"])
    df["geracao_mwmed"] = pd.to_numeric(df["geracao_mwmed"], errors="coerce")
    df = df.dropna(subset=["geracao_mwmed", "fonte"])
    df = df[df["geracao_mwmed"] >= 0]

    # Colunas temporais
    df["ano"] = df["data"].dt.year
    df["mes"] = df["data"].dt.month
    df["trimestre"] = df["data"].dt.quarter
    df["ano_mes"] = df["data"].dt.to_period("M").astype(str)
    df["semestre"] = df["mes"].apply(lambda m: 1 if m <= 6 else 2)

    # Classificação da fonte
    df["tipo_fonte"] = df["fonte"].map(TIPO_FONTE).fillna("Outro")
    df["grupo_fonte"] = df["fonte"].map(GRUPO_FONTE).fillna("Outro")
    df["renovavel"] = df["tipo_fonte"] == "Renovável"

    # Conversão de unidade: MWmed → GWh mensal (MWmed × 24h × 30 dias ÷ 1000)
    df["geracao_gwh"] = (df["geracao_mwmed"] * 24 * 30 / 1000).round(2)

    logger.info(f"Dados limpos: {len(df):,} registros válidos")
    return df


def calcular_metricas_anuais(df: pd.DataFrame) -> pd.DataFrame:
    """Agrega geração anual por fonte e calcula participação percentual."""
    anual = (
        df.groupby(["ano", "fonte", "tipo_fonte", "grupo_fonte"])
        ["geracao_gwh"]
        .sum()
        .reset_index()
        .rename(columns={"geracao_gwh": "geracao_total_gwh"})
    )
    total_ano = anual.groupby("ano")["geracao_total_gwh"].transform("sum")
    anual["participacao_pct"] = (anual["geracao_total_gwh"] / total_ano * 100).round(2)
    anual["renovavel"] = anual["tipo_fonte"] == "Renovável"
    return anual


def calcular_crescimento_novas_renovaveis(df: pd.DataFrame) -> pd.DataFrame:
    """Foca em solar e eólica — as de maior crescimento no período."""
    novas = df[df["grupo_fonte"] == "Novas renováveis"].copy()
    mensal = (
        novas.groupby(["ano_mes", "ano", "mes", "fonte"])
        ["geracao_gwh"]
        .sum()
        .reset_index()
    )
    mensal = mensal.sort_values(["fonte", "ano_mes"])
    mensal["variacao_yoy_pct"] = (
        mensal.groupby("fonte")["geracao_gwh"]
        .pct_change(periods=12) * 100
    ).round(2)
    return mensal


def calcular_mix_renovavel_por_ano(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula percentual renovável da matriz por ano."""
    anual = df.groupby(["ano", "renovavel"])["geracao_gwh"].sum().reset_index()
    total = anual.groupby("ano")["geracao_gwh"].transform("sum")
    anual["pct"] = (anual["geracao_gwh"] / total * 100).round(2)
    return anual[anual["renovavel"] == True][["ano", "geracao_gwh", "pct"]].rename(
        columns={"geracao_gwh": "gwh_renovavel", "pct": "pct_renovavel"}
    )


def salvar_processados(df_base, df_anual, df_novas, df_mix):
    """Salva todos os datasets processados."""
    df_base.to_parquet(PROC_DIR / "geracao_completa.parquet", index=False)
    df_anual.to_parquet(PROC_DIR / "geracao_anual_por_fonte.parquet", index=False)
    df_novas.to_parquet(PROC_DIR / "crescimento_solar_eolica.parquet", index=False)
    df_mix.to_parquet(PROC_DIR / "mix_renovavel_anual.parquet", index=False)

    # CSV também para facilitar uso em SQL e Power BI
    df_anual.to_csv(PROC_DIR / "geracao_anual_por_fonte.csv", index=False)
    df_mix.to_csv(PROC_DIR / "mix_renovavel_anual.csv", index=False)

    logger.info(f"Arquivos salvos em {PROC_DIR}")


if __name__ == "__main__":
    df_bruto = carregar_dados_brutos()
    df_limpo = limpar_e_enriquecer(df_bruto)
    df_anual = calcular_metricas_anuais(df_limpo)
    df_novas = calcular_crescimento_novas_renovaveis(df_limpo)
    df_mix = calcular_mix_renovavel_por_ano(df_limpo)
    salvar_processados(df_limpo, df_anual, df_novas, df_mix)
    logger.info("=== Transformação concluída ===")
