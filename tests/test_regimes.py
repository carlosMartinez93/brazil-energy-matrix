"""Regra de comparabilidade entre anos (quebra da série solar em 2023)."""

import pytest

from src.regimes import comparacao_valida, janela_comparavel, regime


def test_regimes_por_ano():
    assert [regime(a) for a in (2016, 2022, 2023, 2024, 2025)] == ["A", "A", "T", "B", "B"]


@pytest.mark.parametrize("ini,fim,esperado", [
    (2016, 2022, True),    # mesmo regime A
    (2024, 2025, True),    # mesmo regime B
    (2022, 2024, False),   # cruza a quebra
    (2016, 2025, False),
    (2022, 2023, False),   # 2023 é transição
    (2023, 2024, False),
    (2023, 2023, False),
])
def test_solar_so_compara_dentro_do_regime(ini, fim, esperado):
    assert comparacao_valida(ini, fim, "Solar") is esperado
    assert comparacao_valida(ini, fim, None) is esperado  # total e participações seguem a mesma regra


@pytest.mark.parametrize("fonte", ["Eólica", "Hidráulica", "Termelétrica"])
def test_outras_fontes_comparam_em_nivel_sempre(fonte):
    assert comparacao_valida(2016, 2025, fonte) is True
    assert comparacao_valida(2022, 2024, fonte) is True


def test_janela_devolve_o_proprio_intervalo_quando_valido():
    assert janela_comparavel(2016, 2022, "Solar") == (2016, 2022)
    assert janela_comparavel(2024, 2025, None) == (2024, 2025)


def test_janela_encurta_o_inicio_para_2024_quando_o_fim_esta_no_regime_b():
    assert janela_comparavel(2016, 2025, "Solar") == (2024, 2025)
    assert janela_comparavel(2023, 2025, None) == (2024, 2025)


def test_janela_vazia_quando_nao_ha_comparacao_legitima():
    assert janela_comparavel(2016, 2023, "Solar") is None   # termina na transição
    assert janela_comparavel(2025, 2025, "Solar") is None   # um ano só
    assert janela_comparavel(2025, 2024, "Solar") is None   # invertido
    assert janela_comparavel(2016, 2025, "Eólica") == (2016, 2025)
