"""
Fixtures dos testes.

ATENÇÃO: os dados daqui são FABRICADOS, pequenos e de valores conhecidos, só para testar a lógica
de transformacao.py. Nada disto é dado da ONS e nada disto chega ao dashboard.
Os testes em test_dados_reais.py são os que olham para os arquivos reais versionados em data/.
"""

import calendar
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

SUBS = ["N", "NE", "SE", "S"]
# GWh por mês, por subsistema, nos dados fabricados
HIDRO, TERMICA, EOLICA, SOLAR = 100.0, 20.0, 10.0, 5.0
TOTAL_SUB = HIDRO + TERMICA + EOLICA + SOLAR  # 135


def montar_bruto(anos, meses=range(1, 13), horas_fora=None, solar=SOLAR):
    """
    Tabela no formato de data/raw/ons_geracao_mensal.parquet (mesmas colunas).
    horas_fora: {(ano, mes, subsistema): horas_lidas} para simular mês incompleto.
    solar: número, ou função (ano, mes) -> GWh por subsistema.
    """
    horas_fora = horas_fora or {}
    linhas = []
    for ano in anos:
        for mes in meses:
            h = calendar.monthrange(ano, mes)[1] * 24
            s = solar(ano, mes) if callable(solar) else solar
            total_sub = HIDRO + TERMICA + EOLICA + s
            for sub in SUBS:
                linhas.append({
                    "subsystem_code": sub, "subsystem_name": sub, "is_national_aggregate": False,
                    "reference_month": pd.Timestamp(ano, mes, 1),
                    "hours_count": horas_fora.get((ano, mes, sub), h), "hours_with_null_generation": 0,
                    "hydro_gwh": HIDRO, "thermal_gwh": TERMICA, "wind_gwh": EOLICA, "solar_gwh": s,
                    "load_gwh": total_sub, "total_generation_gwh": total_sub,
                })
            linhas.append({
                "subsystem_code": "SIN", "subsystem_name": "SIN", "is_national_aggregate": True,
                "reference_month": pd.Timestamp(ano, mes, 1),
                "hours_count": h, "hours_with_null_generation": 0,
                "hydro_gwh": HIDRO * 4, "thermal_gwh": TERMICA * 4, "wind_gwh": EOLICA * 4, "solar_gwh": s * 4,
                "load_gwh": total_sub * 4, "total_generation_gwh": total_sub * 4,
            })
    return pd.DataFrame(linhas)


@pytest.fixture
def bruto_2_anos():
    return montar_bruto([2020, 2021])
