"""
transformacao.py
----------------
Transforma a geração mensal por subsistema (saída de ingestao.py) nos arquivos usados
pelo dashboard e pelas queries SQL.

Regras que o código impõe (e falha se violadas):
  - só lê dado com manifest de procedência e origem "ons_bigquery"
    (com --synthetic, só lê origem "synthetic" e grava em data/dev/, nunca em data/processed/);
  - totais anuais usam apenas ANOS COMPLETOS (12 meses, horas conferindo com o calendário,
    nos 4 subsistemas). Ano parcial é listado no manifest e fica fora, para não distorcer
    totais nem taxas de crescimento;
  - o total nacional é a soma dos 4 subsistemas; o total "SIN" publicado pela ONS entra só
    como conferência (reconciliacao_sin.parquet).

Uso:
    python src/transformacao.py
    python src/transformacao.py --synthetic     # DEV apenas
"""

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

try:
    from src.proveniencia import (
        ORIGEM_REAL, ORIGEM_SINTETICA, ProvenienciaError, ler_manifest, escrever_manifest, sha256_arquivo,
    )
except ImportError:  # execução como script
    from proveniencia import (
        ORIGEM_REAL, ORIGEM_SINTETICA, ProvenienciaError, ler_manifest, escrever_manifest, sha256_arquivo,
    )

RAIZ = Path(__file__).resolve().parent.parent
ARQ_REAL = RAIZ / "data" / "raw" / "ons_geracao_mensal.parquet"
ARQ_SINT = RAIZ / "data" / "dev" / "ons_geracao_mensal__SYNTHETIC.parquet"
SAIDA_REAL = RAIZ / "data" / "processed"
SAIDA_SINT = RAIZ / "data" / "dev" / "processed__SYNTHETIC"

SUBSISTEMAS = ["N", "NE", "SE", "S"]
COLUNA_PARA_FONTE = {
    "hydro_gwh": "Hidráulica",
    "thermal_gwh": "Termelétrica",
    "wind_gwh": "Eólica",
    "solar_gwh": "Solar",
}

# O dataset da ONS separa só hidráulica, térmica, eólica e solar. A térmica não é aberta
# por combustível, então biomassa e nuclear NÃO aparecem separadas. Por isso o agrupamento
# abaixo se chama "Hidro+Eólica+Solar" e não "renovável".
TIPO_FONTE = {
    "Hidráulica": "Hidro+Eólica+Solar",
    "Eólica": "Hidro+Eólica+Solar",
    "Solar": "Hidro+Eólica+Solar",
    "Termelétrica": "Térmica",
}
GRUPO_FONTE = {
    "Hidráulica": "Hídrica",
    "Eólica": "Novas renováveis",
    "Solar": "Novas renováveis",
    "Termelétrica": "Térmica",
}
DEFINICOES = {
    "geracao_gwh": "soma das leituras horárias em MWmed (= MWh) do mês, dividida por 1000",
    "total_nacional": "soma dos 4 subsistemas (N, NE, SE, S); a linha SIN da ONS é usada só na reconciliação",
    "hidro_eolica_solar": "hidráulica + eólica + solar; biomassa e nuclear estão dentro de 'Termelétrica' no dataset da ONS",
}


class TransformacaoError(RuntimeError):
    pass


def carregar_bruto(sintetico: bool):
    arquivo = ARQ_SINT if sintetico else ARQ_REAL
    origem = ORIGEM_SINTETICA if sintetico else ORIGEM_REAL
    if not arquivo.exists():
        comando = "python src/ingestao.py --synthetic" if sintetico else "python src/ingestao.py"
        raise TransformacaoError(f"{arquivo.relative_to(RAIZ)} não existe. Rode: {comando}")
    manifest = ler_manifest(arquivo, origem)
    if sha256_arquivo(arquivo) != manifest.get("sha256_parquet"):
        raise TransformacaoError(f"{arquivo.name} foi alterado depois da ingestão (sha256 difere do manifest).")
    df = pd.read_parquet(arquivo)
    df["reference_month"] = pd.to_datetime(df["reference_month"])
    return df, manifest, arquivo


def marcar_meses_completos(df: pd.DataFrame) -> pd.DataFrame:
    """Mês completo = horas lidas batem com dias*24 (tolerância de 1h por horário de verão)."""
    df = df.copy()
    esperado = df["reference_month"].dt.days_in_month * 24
    df["mes_completo"] = (df["hours_count"] - esperado).abs() <= 1
    return df


def selecionar_anos_completos(sub: pd.DataFrame):
    """Retorna (anos_incluidos, anos_excluidos[{ano, motivo}]) olhando só os 4 subsistemas."""
    incluidos, excluidos = [], []
    for ano, g in sub.groupby(sub["reference_month"].dt.year):
        meses_por_sub = g.groupby("subsystem_code")["reference_month"].nunique()
        if set(meses_por_sub.index) != set(SUBSISTEMAS) or (meses_por_sub != 12).any():
            excluidos.append({"ano": int(ano), "motivo": "menos de 12 meses em algum subsistema"})
        elif not g["mes_completo"].all():
            excluidos.append({"ano": int(ano), "motivo": "mês com horas incompletas"})
        else:
            incluidos.append(int(ano))
    if not incluidos:
        raise TransformacaoError("Nenhum ano completo na extração. Nada para publicar.")
    return incluidos, excluidos


def para_formato_longo(sub: pd.DataFrame) -> pd.DataFrame:
    longo = sub.melt(
        id_vars=["subsystem_code", "reference_month"],
        value_vars=list(COLUNA_PARA_FONTE),
        var_name="coluna", value_name="geracao_gwh",
    )
    longo["fonte"] = longo["coluna"].map(COLUNA_PARA_FONTE)
    longo = longo.rename(columns={"subsystem_code": "subsistema", "reference_month": "data"})
    return longo.drop(columns="coluna")


def enriquecer(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["ano"] = df["data"].dt.year
    df["mes"] = df["data"].dt.month
    df["trimestre"] = df["data"].dt.quarter
    df["semestre"] = (df["mes"] > 6).astype(int) + 1
    df["ano_mes"] = df["data"].dt.strftime("%Y-%m")
    df["tipo_fonte"] = df["fonte"].map(TIPO_FONTE)
    df["grupo_fonte"] = df["fonte"].map(GRUPO_FONTE)
    df["renovavel"] = df["tipo_fonte"] == "Hidro+Eólica+Solar"
    return df


def calcular_anual(nacional: pd.DataFrame) -> pd.DataFrame:
    anual = (
        nacional.groupby(["ano", "fonte", "tipo_fonte", "grupo_fonte"])["geracao_gwh"]
        .sum().reset_index().rename(columns={"geracao_gwh": "geracao_total_gwh"})
    )
    total = anual.groupby("ano")["geracao_total_gwh"].transform("sum")
    anual["participacao_pct"] = (anual["geracao_total_gwh"] / total * 100).round(2)
    anual["renovavel"] = anual["tipo_fonte"] == "Hidro+Eólica+Solar"
    return anual


def calcular_mix(nacional: pd.DataFrame) -> pd.DataFrame:
    por_ano = nacional.groupby(["ano", "renovavel"])["geracao_gwh"].sum().reset_index()
    total = por_ano.groupby("ano")["geracao_gwh"].transform("sum")
    por_ano["pct"] = (por_ano["geracao_gwh"] / total * 100).round(2)
    mix = por_ano[por_ano["renovavel"]][["ano", "geracao_gwh", "pct"]]
    return mix.rename(columns={"geracao_gwh": "gwh_hidro_eolica_solar", "pct": "pct_hidro_eolica_solar"})


def calcular_crescimento(nacional: pd.DataFrame) -> pd.DataFrame:
    novas = nacional[nacional["grupo_fonte"] == "Novas renováveis"]
    mensal = novas.groupby(["ano_mes", "ano", "mes", "fonte"])["geracao_gwh"].sum().reset_index()
    mensal = mensal.sort_values(["fonte", "ano_mes"])
    mensal["variacao_yoy_pct"] = (mensal.groupby("fonte")["geracao_gwh"].pct_change(periods=12) * 100).round(2)
    return mensal


def reconciliar_sin(df: pd.DataFrame) -> pd.DataFrame:
    """Soma dos 4 subsistemas x linha SIN publicada pela ONS, mês a mês (todos os meses)."""
    soma = df[~df["is_national_aggregate"]].groupby("reference_month")["total_generation_gwh"].sum()
    sin = df[df["is_national_aggregate"]].set_index("reference_month")["total_generation_gwh"]
    r = pd.DataFrame({"soma_subsistemas_gwh": soma, "sin_ons_gwh": sin}).dropna().reset_index()
    r["diferenca_pct"] = ((r["soma_subsistemas_gwh"] - r["sin_ons_gwh"]) / r["sin_ons_gwh"] * 100).round(4)
    return r


def transformar(sintetico: bool = False) -> Path:
    df, manifest_raw, arquivo_raw = carregar_bruto(sintetico)
    df = marcar_meses_completos(df)
    sub = df[~df["is_national_aggregate"]]
    anos_ok, anos_fora = selecionar_anos_completos(sub)

    sub_ok = sub[sub["reference_month"].dt.year.isin(anos_ok)]
    por_subsistema = enriquecer(para_formato_longo(sub_ok))
    nacional = (
        por_subsistema.groupby(
            ["data", "ano", "mes", "trimestre", "semestre", "ano_mes", "fonte", "tipo_fonte", "grupo_fonte", "renovavel"],
            as_index=False,
        )["geracao_gwh"].sum()
    )
    anual = calcular_anual(nacional)
    mix = calcular_mix(nacional)
    crescimento = calcular_crescimento(nacional)
    recon = reconciliar_sin(df)

    destino = SAIDA_SINT if sintetico else SAIDA_REAL
    destino.mkdir(parents=True, exist_ok=True)
    nacional.to_parquet(destino / "geracao_completa.parquet", index=False)
    por_subsistema.to_parquet(destino / "geracao_mensal_subsistema.parquet", index=False)
    anual.to_parquet(destino / "geracao_anual_por_fonte.parquet", index=False)
    anual.to_csv(destino / "geracao_anual_por_fonte.csv", index=False)
    mix.to_parquet(destino / "mix_hidro_eolica_solar_anual.parquet", index=False)
    mix.to_csv(destino / "mix_hidro_eolica_solar_anual.csv", index=False)
    crescimento.to_parquet(destino / "crescimento_solar_eolica.parquet", index=False)
    recon.to_parquet(destino / "reconciliacao_sin.parquet", index=False)

    principal = destino / "geracao_completa.parquet"
    escrever_manifest(principal, {
        **{k: manifest_raw[k] for k in manifest_raw if k not in ("sha256_parquet",)},
        "sha256_raw": manifest_raw["sha256_parquet"],
        "arquivo_raw": arquivo_raw.name,
        "anos_incluidos": anos_ok,
        "anos_excluidos": anos_fora,
        "reconciliacao_sin": {
            "meses_comparados": int(len(recon)),
            "desvio_abs_max_pct": float(recon["diferenca_pct"].abs().max()),
            "desvio_abs_medio_pct": float(recon["diferenca_pct"].abs().mean()),
        },
        "definicoes": DEFINICOES,
        "transformado_em_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sha256_parquet": sha256_arquivo(principal),
    })
    return destino


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--synthetic", action="store_true", help="SÓ DEV: lê data/dev/ e grava em data/dev/processed__SYNTHETIC/")
    args = parser.parse_args()
    try:
        destino = transformar(args.synthetic)
    except (TransformacaoError, ProvenienciaError) as exc:
        print(f"ERRO DE TRANSFORMAÇÃO: {exc}", file=sys.stderr)
        return 2
    print(f"OK: arquivos em {destino}")
    if args.synthetic:
        print("[AVISO] saída SINTÉTICA. O dashboard não lê esta pasta.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
