"""
Testes sobre os arquivos REAIS versionados em data/ (saída de ingestao.py + transformacao.py).
Não inventam número: conferem coerência interna e a procedência. Se os arquivos não existirem
(clone sem dados), os testes são pulados.
"""

import json
from pathlib import Path

import pandas as pd
import pytest

from src.proveniencia import ORIGEM_REAL, ler_manifest, sha256_arquivo

RAIZ = Path(__file__).resolve().parent.parent
RAW = RAIZ / "data" / "raw" / "ons_geracao_mensal.parquet"
PROC = RAIZ / "data" / "processed"

pytestmark = pytest.mark.skipif(not (RAW.exists() and (PROC / "geracao_completa.parquet").exists()),
                                reason="dados versionados ausentes")


@pytest.fixture(scope="module")
def nacional():
    return pd.read_parquet(PROC / "geracao_completa.parquet")


@pytest.fixture(scope="module")
def anual():
    return pd.read_parquet(PROC / "geracao_anual_por_fonte.parquet")


@pytest.fixture(scope="module")
def manifest():
    return json.loads((PROC / "geracao_completa.manifest.json").read_text(encoding="utf-8"))


def test_procedencia_real_e_hash_confere():
    assert ler_manifest(RAW, ORIGEM_REAL)["origem"] == ORIGEM_REAL
    assert sha256_arquivo(RAW) == ler_manifest(RAW, ORIGEM_REAL)["sha256_parquet"]
    m = ler_manifest(PROC / "geracao_completa.parquet", ORIGEM_REAL)
    assert m["sha256_parquet"] == sha256_arquivo(PROC / "geracao_completa.parquet")
    assert m["sha256_raw"] == sha256_arquivo(RAW)


def test_nenhum_ano_faltando(anual, manifest):
    anos = sorted(anual["ano"].unique())
    assert anos == manifest["anos_incluidos"]
    assert anos == list(range(anos[0], anos[-1] + 1))


def test_so_anos_completos_nos_totais(nacional):
    meses_por_ano = nacional.groupby("ano")["mes"].nunique()
    assert (meses_por_ano == 12).all()


def test_percentuais_somam_100_por_ano(anual):
    soma = anual.groupby("ano")["participacao_pct"].sum()
    assert soma.sub(100).abs().max() < 0.05


def test_total_anual_bate_com_a_soma_dos_meses(nacional, anual):
    por_ano_mensal = nacional.groupby("ano")["geracao_gwh"].sum()
    por_ano_anual = anual.groupby("ano")["geracao_total_gwh"].sum()
    pd.testing.assert_series_equal(por_ano_mensal, por_ano_anual, check_names=False, rtol=1e-9)


def test_total_nacional_e_a_soma_dos_subsistemas(nacional):
    sub = pd.read_parquet(PROC / "geracao_mensal_subsistema.parquet")
    assert set(sub["subsistema"].unique()) == {"N", "NE", "SE", "S"}
    assert sub["geracao_gwh"].sum() == pytest.approx(nacional["geracao_gwh"].sum(), rel=1e-9)


def test_reconciliacao_com_a_linha_sin_dentro_de_1_por_cento(manifest):
    assert manifest["reconciliacao_sin"]["desvio_abs_max_pct"] < 1.0


def test_yoy_solar_nao_existe_nos_anos_que_cruzam_a_quebra():
    c = pd.read_parquet(PROC / "crescimento_solar_eolica.parquet")
    solar = c[c["fonte"] == "Solar"]
    assert solar[solar["ano"].isin([2023, 2024])]["variacao_yoy_pct"].isna().all()
    assert solar[solar["ano"].isin([2017, 2022, 2025])]["variacao_yoy_pct"].notna().any()


def test_manifest_registra_a_quebra_de_serie(manifest):
    q = manifest["quebra_de_serie"]
    assert q["fonte"] == "Solar" and q["mes"] == "2023-05"
    assert "NÃO confirmada" in q["hipotese_causa"]
