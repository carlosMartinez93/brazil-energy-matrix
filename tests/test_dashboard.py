"""Smoke test do dashboard com os dados reais versionados: sobe, responde ao callback e respeita a regra de comparabilidade."""

import importlib.util
from pathlib import Path

import pytest
from dash.development.base_component import Component

RAIZ = Path(__file__).resolve().parent.parent
pytestmark = pytest.mark.skipif(not (RAIZ / "data" / "processed" / "geracao_completa.parquet").exists(),
                                reason="dados versionados ausentes")


def textos(no):
    saida = []

    def visitar(x):
        if isinstance(x, (list, tuple)):
            for i in x:
                visitar(i)
        elif isinstance(x, Component):
            visitar(getattr(x, "children", None))
        elif isinstance(x, str):
            saida.append(x)

    visitar(no)
    return saida


@pytest.fixture(scope="module")
def app():
    spec = importlib.util.spec_from_file_location("dashboard_app", RAIZ / "dashboard" / "app.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def chamar(app, intervalo):
    meses = [str(m) for m in range(1, 13)]
    return app.atualizar(intervalo, meses, list(app.fontes_disp))


def test_periodo_padrao_e_o_intervalo_completo(app):
    slider = next(c for c in app.app.layout._traverse() if getattr(c, "id", None) == "filtro-ano")
    assert slider.value == [app.anos_disp[0], app.anos_disp[-1]]


def test_callback_responde_para_o_periodo_completo(app):
    kpis, *figuras, insights = chamar(app, [app.anos_disp[0], app.anos_disp[-1]])
    assert len(kpis) == 4 and len(figuras) == 5
    assert textos(insights)


def test_solar_nao_mostra_variacao_que_cruza_2023(app):
    kpis, *_ = chamar(app, [2016, 2025])
    solar = textos(kpis[2])
    assert "+660%" not in solar
    assert "2024→2025" in solar  # usa só a janela válida e diz qual é


def test_os_4_cards_comparam_a_mesma_janela(app):
    kpis, *_ = chamar(app, [2016, 2025])
    total, hes, solar, eolica = (" ".join(textos(k)) for k in kpis)
    assert "em 2024" in total and "em 2024" in hes
    assert "2024→2025" in solar and "2024→2025" in eolica
    assert "2016" not in solar + eolica  # a Eólica não usa janela mais longa que a Solar nos cards


def test_insights_mantem_o_historico_longo_da_eolica_com_os_anos_escritos(app):
    *_, insights = chamar(app, [2016, 2025])
    assert any("Eólica" in t and "entre 2016 e 2025" in t for t in textos(insights))


def test_janela_dos_cards_acompanha_o_slider_dentro_do_mesmo_regime(app):
    kpis, *_ = chamar(app, [2016, 2022])
    assert "2016→2022" in " ".join(textos(kpis[2])) and "2016→2022" in " ".join(textos(kpis[3]))


def test_solar_n_d_quando_so_ha_transicao(app):
    kpis, *_ = chamar(app, [2016, 2023])
    assert textos(kpis[2])[1] == "n/d"


def test_eixo_x_com_anos_inteiros(app):
    _, fig_ev, *_ = chamar(app, [2016, 2025])
    assert fig_ev.layout.xaxis.dtick == 1 and fig_ev.layout.xaxis.tickformat == "d"
