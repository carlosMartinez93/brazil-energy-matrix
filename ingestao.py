"""
ingestao.py
-----------
Coleta dados de geração de energia elétrica no Brasil a partir de fontes abertas:
  - ONS: Geração por fonte via API REST dedicada
  - ONS: Carga de energia por subsistema via API REST
  - ANEEL: Capacidade instalada (SIGA) via download direto CSV

Fontes:
  - https://dados.ons.org.br
  - https://dadosabertos.aneel.gov.br
"""

import requests
import pandas as pd
from pathlib import Path
from datetime import date
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

RAW_DIR = Path(__file__).parent.parent / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# 1. ONS — Geração por fonte via API REST (endpoint correto 2025)
# ---------------------------------------------------------------------------

# O ONS disponibiliza API REST dedicada por tipo de dado:
# https://apicarga.ons.org.br/prd/geracaousinascombinadas
# Parâmetros: dat_inicio, dat_fim (formato YYYY-MM-DD)

ONS_GERACAO_URL = "https://apicarga.ons.org.br/prd/geracaousinascombinadas"
ONS_CARGA_URL   = "https://apicarga.ons.org.br/prd/cargaverificada"


def baixar_geracao_ons(ano_inicio: int = 2015, ano_fim: int = 2024) -> pd.DataFrame:
    """
    Baixa dados históricos de geração de energia por fonte do ONS.
    Usa a API REST prd (produção) com janelas anuais para não sobrecarregar.
    Colunas retornadas: din_instante, nom_subsistema, nom_tipousina, val_geracao
    """
    frames = []
    for ano in range(ano_inicio, ano_fim + 1):
        dat_ini = f"{ano}-01-01"
        dat_fim = f"{ano}-12-31"
        logger.info(f"Baixando geração ONS — {dat_ini} a {dat_fim}")
        params = {"dat_inicio": dat_ini, "dat_fim": dat_fim}
        try:
            resp = requests.get(ONS_GERACAO_URL, params=params, timeout=120)
            resp.raise_for_status()
            df = pd.DataFrame(resp.json())
            df["ano"] = ano
            frames.append(df)
            logger.info(f"  → {len(df):,} registros obtidos para {ano}")
        except Exception as e:
            logger.warning(f"Erro ao baixar geração ONS ano {ano}: {e}")

    if not frames:
        logger.error("Nenhum dado obtido do ONS — ativando fallback sintético.")
        return pd.DataFrame()

    df_final = pd.concat(frames, ignore_index=True)
    saida = RAW_DIR / "ons_geracao_historico.parquet"
    df_final.to_parquet(saida, index=False)
    logger.info(f"ONS salvo em {saida} — {len(df_final):,} linhas totais")
    return df_final


# ---------------------------------------------------------------------------
# 2. ONS — Carga de energia por subsistema (demanda verificada)
# ---------------------------------------------------------------------------

def baixar_carga_ons(ano_inicio: int = 2015, ano_fim: int = 2024) -> pd.DataFrame:
    """
    Baixa dados de carga (demanda) verificada por subsistema do ONS.
    Endpoint: https://apicarga.ons.org.br/prd/cargaverificada
    """
    frames = []
    for ano in range(ano_inicio, ano_fim + 1):
        dat_ini = f"{ano}-01-01"
        dat_fim = f"{ano}-12-31"
        logger.info(f"Baixando carga ONS — {dat_ini} a {dat_fim}")
        params = {"dat_inicio": dat_ini, "dat_fim": dat_fim}
        try:
            resp = requests.get(ONS_CARGA_URL, params=params, timeout=120)
            resp.raise_for_status()
            df = pd.DataFrame(resp.json())
            df["ano"] = ano
            frames.append(df)
        except Exception as e:
            logger.warning(f"Erro carga ONS ano {ano}: {e}")

    if not frames:
        return pd.DataFrame()

    df_final = pd.concat(frames, ignore_index=True)
    saida = RAW_DIR / "ons_carga_historico.parquet"
    df_final.to_parquet(saida, index=False)
    logger.info(f"Carga ONS salva em {saida} — {len(df_final):,} linhas")
    return df_final


# ---------------------------------------------------------------------------
# 3. ANEEL — Capacidade instalada (SIGA) — URL corrigida 2025
# ---------------------------------------------------------------------------

# URL correta do SIGA obtida diretamente do portal dados abertos ANEEL
ANEEL_SIGA_URL = (
    "https://dadosabertos.aneel.gov.br/dataset/"
    "b1bd71e7-d0ad-4214-9053-cbd58e9564a7/resource/"
    "b2c4b85b-8097-400e-b6e2-b0a81cf45c03/download/"
    "siga-empreendimentos-geracao.csv"
)

def baixar_capacidade_aneel() -> pd.DataFrame:
    """
    Baixa o SIGA (Sistema de Informações de Geração da ANEEL):
    capacidade instalada por tipo de usina, UF e situação operacional.
    """
    logger.info("Baixando capacidade instalada — ANEEL SIGA...")
    try:
        # O SIGA usa separador ; e encoding latin1
        df = pd.read_csv(
            ANEEL_SIGA_URL,
            sep=";",
            encoding="latin1",
            low_memory=False,
            on_bad_lines="skip",
        )
        saida = RAW_DIR / "aneel_capacidade_instalada.parquet"
        df.to_parquet(saida, index=False)
        logger.info(f"ANEEL SIGA salvo em {saida} — {len(df):,} empreendimentos")
        return df
    except Exception as e:
        logger.error(f"Erro ao baixar ANEEL SIGA: {e}")
        logger.info("Dica: acesse https://dadosabertos.aneel.gov.br e busque 'SIGA' para obter a URL atualizada do CSV.")
        return pd.DataFrame()


# ---------------------------------------------------------------------------
# 4. Geração de dados sintéticos (fallback p/ desenvolvimento offline)
# ---------------------------------------------------------------------------

FONTES = ["Hidráulica", "Eólica", "Solar", "Termelétrica", "Nuclear", "Biomassa"]
SUBSISTEMAS = ["Sudeste/Centro-Oeste", "Sul", "Nordeste", "Norte"]

def gerar_dados_sinteticos(ano_inicio: int = 2015, ano_fim: int = 2024) -> pd.DataFrame:
    """
    Gera dataset sintético realista para desenvolvimento e testes offline.
    Simula tendências reais: crescimento de solar/eólica, redução relativa de hidráulica.
    """
    import numpy as np

    np.random.seed(42)
    datas = pd.date_range(f"{ano_inicio}-01-01", f"{ano_fim}-12-31", freq="MS")
    rows = []

    tendencias = {
        "Hidráulica":    {"base": 45000, "crescimento": -0.008, "sazonalidade": 0.20},
        "Eólica":        {"base":  8000, "crescimento":  0.060, "sazonalidade": 0.15},
        "Solar":         {"base":   500, "crescimento":  0.120, "sazonalidade": 0.25},
        "Termelétrica":  {"base": 12000, "crescimento":  0.010, "sazonalidade": 0.10},
        "Nuclear":       {"base":  2000, "crescimento":  0.001, "sazonalidade": 0.02},
        "Biomassa":      {"base":  4000, "crescimento":  0.020, "sazonalidade": 0.12},
    }

    for data in datas:
        anos_decorridos = (data.year - ano_inicio) + data.month / 12
        for fonte, params in tendencias.items():
            for subsistema in SUBSISTEMAS:
                fator_sub = {"Sudeste/Centro-Oeste": 1.5, "Sul": 0.8, "Nordeste": 0.9, "Norte": 0.6}
                base = params["base"] * fator_sub[subsistema]
                tendencia = base * (1 + params["crescimento"]) ** anos_decorridos
                saz = 1 + params["sazonalidade"] * np.sin(2 * np.pi * data.month / 12)
                ruido = np.random.normal(1, 0.03)
                geracao = tendencia * ruido
                if fonte == "Solar":
                    geracao *= max(0.1, 1 + 0.3 * (data.month in [10, 11, 12, 1, 2, 3]) - 0.2)
                rows.append({
                    "data": data,
                    "ano": data.year,
                    "mes": data.month,
                    "trimestre": data.quarter,
                    "fonte": fonte,
                    "subsistema": subsistema,
                    "geracao_mwmed": round(max(0, geracao), 2),
                })

    df = pd.DataFrame(rows)
    saida = RAW_DIR / "geracao_sintetica.parquet"
    df.to_parquet(saida, index=False)
    logger.info(f"Dados sintéticos gerados em {saida} — {len(df):,} linhas")
    return df


if __name__ == "__main__":
    logger.info("=== Iniciando ingestão de dados de energia ===")

    # Tenta dados reais; se falhar, usa sintéticos
    df_geracao = baixar_geracao_ons(2015, 2024)
    if df_geracao.empty:
        logger.warning("Usando dados sintéticos para desenvolvimento.")
        df_geracao = gerar_dados_sinteticos(2015, 2024)

    baixar_capacidade_aneel()

    logger.info("=== Ingestão concluída ===")
