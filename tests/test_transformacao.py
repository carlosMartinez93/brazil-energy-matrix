"""
Testes de src/transformacao.py com dados FABRICADOS (ver conftest.py).
Cobrem o que o projeto promete: totais corretos, percentuais fechando em 100%, nenhum ano
faltando e nenhum ano parcial entrando nos totais.
"""

import json

import pandas as pd
import pytest

from src import transformacao as t
from src.proveniencia import ORIGEM_REAL, escrever_manifest, sha256_arquivo
from tests.conftest import EOLICA, HIDRO, SOLAR, TERMICA, TOTAL_SUB, montar_bruto


def nacional_de(bruto):
    df = t.marcar_meses_completos(bruto)
    sub = df[~df["is_national_aggregate"]]
    anos_ok, _ = t.selecionar_anos_completos(sub)
    sub_ok = sub[sub["reference_month"].dt.year.isin(anos_ok)]
    por_sub = t.enriquecer(t.para_formato_longo(sub_ok))
    chaves = ["data", "ano", "mes", "trimestre", "semestre", "ano_mes", "fonte", "tipo_fonte", "grupo_fonte", "renovavel"]
    return por_sub.groupby(chaves, as_index=False)["geracao_gwh"].sum()


# --- anos completos -----------------------------------------------------------------------------

def test_ano_completo_entra_e_ano_parcial_sai():
    bruto = pd.concat([montar_bruto([2020, 2021]), montar_bruto([2022], meses=range(1, 7))])
    df = t.marcar_meses_completos(bruto)
    incluidos, excluidos = t.selecionar_anos_completos(df[~df["is_national_aggregate"]])
    assert incluidos == [2020, 2021]
    assert excluidos == [{"ano": 2022, "motivo": "menos de 12 meses em algum subsistema"}]


def test_mes_com_horas_faltando_exclui_o_ano_inteiro():
    # Norte com 1 dia a menos em abril de 2021: o ano todo sai (caso real de 2015 nos dados da ONS)
    bruto = montar_bruto([2020, 2021], horas_fora={(2021, 4, "N"): 30 * 24 - 24})
    df = t.marcar_meses_completos(bruto)
    incluidos, excluidos = t.selecionar_anos_completos(df[~df["is_national_aggregate"]])
    assert incluidos == [2020]
    assert excluidos[0]["ano"] == 2021 and "horas" in excluidos[0]["motivo"]


def test_tolerancia_de_uma_hora_para_horario_de_verao():
    bruto = montar_bruto([2020], horas_fora={(2020, 11, "SE"): 30 * 24 - 1})
    df = t.marcar_meses_completos(bruto)
    incluidos, _ = t.selecionar_anos_completos(df[~df["is_national_aggregate"]])
    assert incluidos == [2020]


def test_sem_nenhum_ano_completo_falha_em_vez_de_publicar_vazio():
    bruto = montar_bruto([2020], meses=range(1, 6))
    df = t.marcar_meses_completos(bruto)
    with pytest.raises(t.TransformacaoError):
        t.selecionar_anos_completos(df[~df["is_national_aggregate"]])


def test_ano_sem_um_dos_subsistemas_nao_e_completo():
    bruto = montar_bruto([2020, 2021])
    bruto = bruto[~((bruto["subsystem_code"] == "S") & (bruto["reference_month"].dt.year == 2021))]
    df = t.marcar_meses_completos(bruto)
    incluidos, _ = t.selecionar_anos_completos(df[~df["is_national_aggregate"]])
    assert incluidos == [2020]


# --- totais e percentuais -----------------------------------------------------------------------

def test_total_nacional_e_a_soma_dos_4_subsistemas():
    anual = t.calcular_anual(nacional_de(montar_bruto([2020, 2021])))
    hidro_2020 = anual[(anual["ano"] == 2020) & (anual["fonte"] == "Hidráulica")]["geracao_total_gwh"].iloc[0]
    assert hidro_2020 == HIDRO * 4 * 12
    total_2020 = anual[anual["ano"] == 2020]["geracao_total_gwh"].sum()
    assert total_2020 == TOTAL_SUB * 4 * 12


def test_percentuais_somam_100_por_ano():
    anual = t.calcular_anual(nacional_de(montar_bruto([2020, 2021, 2022])))
    soma = anual.groupby("ano")["participacao_pct"].sum()
    assert len(soma) == 3
    assert soma.sub(100).abs().max() < 0.05  # só arredondamento a 2 casas


def test_participacao_bate_com_valor_conhecido():
    anual = t.calcular_anual(nacional_de(montar_bruto([2020])))
    eolica = anual[anual["fonte"] == "Eólica"]["participacao_pct"].iloc[0]
    assert eolica == pytest.approx(EOLICA / TOTAL_SUB * 100, abs=0.01)


def test_mix_hidro_eolica_solar_exclui_termica():
    mix = t.calcular_mix(nacional_de(montar_bruto([2020, 2021])))
    esperado = (HIDRO + EOLICA + SOLAR) / TOTAL_SUB * 100
    assert mix["pct_hidro_eolica_solar"].tolist() == pytest.approx([esperado, esperado], abs=0.01)
    assert TERMICA / TOTAL_SUB * 100 + esperado == pytest.approx(100, abs=0.01)


def test_nenhum_ano_falta_entre_o_primeiro_e_o_ultimo():
    anual = t.calcular_anual(nacional_de(montar_bruto([2019, 2020, 2021, 2022])))
    anos = sorted(anual["ano"].unique())
    assert anos == list(range(anos[0], anos[-1] + 1))


# --- reconciliação com a linha SIN --------------------------------------------------------------

def test_reconciliacao_sin_zero_quando_soma_bate():
    r = t.reconciliar_sin(montar_bruto([2020]))
    assert len(r) == 12
    assert r["diferenca_pct"].abs().max() == 0


def test_reconciliacao_sin_acusa_divergencia():
    bruto = montar_bruto([2020])
    idx = bruto[(bruto["is_national_aggregate"]) & (bruto["reference_month"].dt.month == 3)].index
    bruto.loc[idx, "total_generation_gwh"] *= 1.10
    r = t.reconciliar_sin(bruto)
    marco = r[r["reference_month"].dt.month == 3]["diferenca_pct"].iloc[0]
    assert marco == pytest.approx(-100 * (1 - 1 / 1.10), abs=0.01)


# --- quebra de série solar ----------------------------------------------------------------------

def solar_com_quebra(ano, mes):
    return SOLAR * 3 if (ano, mes) >= (2023, 5) else SOLAR


def test_yoy_solar_fica_vazio_quando_cruza_2023_e_eolica_nao():
    nac = nacional_de(montar_bruto([2021, 2022, 2023, 2024, 2025], solar=solar_com_quebra))
    c = t.calcular_crescimento(nac)
    solar = c[c["fonte"] == "Solar"].groupby("ano")["variacao_yoy_pct"].apply(lambda s: s.notna().sum())
    eolica = c[c["fonte"] == "Eólica"].groupby("ano")["variacao_yoy_pct"].apply(lambda s: s.notna().sum())
    assert solar.to_dict() == {2021: 0, 2022: 12, 2023: 0, 2024: 0, 2025: 12}  # 2021 é o 1º ano: sem base
    assert eolica.to_dict() == {2021: 0, 2022: 12, 2023: 12, 2024: 12, 2025: 12}


def test_evidencia_da_quebra_e_calculada_dos_dados():
    nac = nacional_de(montar_bruto([2021, 2022, 2023, 2024], solar=solar_com_quebra))
    ev = t.evidencia_quebra(nac)
    assert ev["mes"] == "2023-05"
    assert ev["variacao_mm_pct"] == pytest.approx(200.0)  # 5 -> 15 GWh por subsistema
    razoes = ev["razao_mes_sobre_anterior_por_ano"]
    assert razoes["2023"] == pytest.approx(3.0)
    assert all(v == pytest.approx(1.0) for k, v in razoes.items() if k != "2023")


def test_evidencia_da_quebra_e_none_sem_o_mes_na_serie():
    assert t.evidencia_quebra(nacional_de(montar_bruto([2020, 2021]))) is None


# --- pipeline completo com manifest -------------------------------------------------------------

@pytest.fixture
def ambiente(tmp_path, monkeypatch):
    bruto = montar_bruto([2020, 2021])
    arquivo = tmp_path / "raw" / "ons_geracao_mensal.parquet"
    arquivo.parent.mkdir()
    bruto.to_parquet(arquivo, index=False)
    escrever_manifest(arquivo, {"origem": ORIGEM_REAL, "sha256_parquet": sha256_arquivo(arquivo)})
    monkeypatch.setattr(t, "ARQ_REAL", arquivo)
    monkeypatch.setattr(t, "SAIDA_REAL", tmp_path / "processed")
    return tmp_path


def test_transformar_grava_saidas_e_manifest(ambiente):
    destino = t.transformar(sintetico=False)
    for nome in ("geracao_completa.parquet", "geracao_anual_por_fonte.parquet", "reconciliacao_sin.parquet"):
        assert (destino / nome).exists()
    manifest = json.loads((destino / "geracao_completa.manifest.json").read_text(encoding="utf-8"))
    assert manifest["origem"] == ORIGEM_REAL
    assert manifest["anos_incluidos"] == [2020, 2021]
    assert manifest["sha256_parquet"] == sha256_arquivo(destino / "geracao_completa.parquet")


def test_transformar_recusa_arquivo_alterado_depois_da_ingestao(ambiente):
    arquivo = t.ARQ_REAL
    df = pd.read_parquet(arquivo)
    df.loc[0, "hydro_gwh"] += 1
    df.to_parquet(arquivo, index=False)
    with pytest.raises(t.TransformacaoError, match="sha256"):
        t.transformar(sintetico=False)


def test_transformar_recusa_dado_sem_manifest(ambiente):
    (t.ARQ_REAL.parent / "ons_geracao_mensal.manifest.json").unlink()
    with pytest.raises(t.ProvenienciaError):
        t.transformar(sintetico=False)
