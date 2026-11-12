"""
ingestao.py
-----------
Extrai a geração MENSAL por subsistema e fonte do BigQuery e grava parquet + manifest
de procedência.

Fonte dos dados: tabela mart_ons__monthly_generation_by_source do projeto
ons-energy-pipeline, que agrega o dataset "Balanço de Energia nos Subsistemas" (horário)
do portal de dados abertos da ONS (dados.ons.org.br).

Uso:
    python src/ingestao.py                 # dado real; ERRO claro se o BigQuery/tabela falhar
    python src/ingestao.py --synthetic     # SÓ PARA DESENVOLVIMENTO. Grava em data/dev/ com
                                           # sufixo __SYNTHETIC; o dashboard nunca lê esse arquivo.

Não existe fallback: se o dado real não estiver disponível, o script para com erro.
"""

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from src.proveniencia import ORIGEM_REAL, ORIGEM_SINTETICA, escrever_manifest, sha256_arquivo
except ImportError:  # execução como script: python src/ingestao.py
    from proveniencia import ORIGEM_REAL, ORIGEM_SINTETICA, escrever_manifest, sha256_arquivo

RAIZ = Path(__file__).resolve().parent.parent
RAW_DIR = RAIZ / "data" / "raw"
DEV_DIR = RAIZ / "data" / "dev"

ARQUIVO_REAL = RAW_DIR / "ons_geracao_mensal.parquet"
ARQUIVO_SINTETICO = DEV_DIR / "ons_geracao_mensal__SYNTHETIC.parquet"

PROJETO_PADRAO = "ons-energy-pipeline"
TABELA_PADRAO = "dbt_dev.mart_ons__monthly_generation_by_source"

COLUNAS = [
    "subsystem_code", "subsystem_name", "is_national_aggregate", "reference_month",
    "hours_count", "hours_with_null_generation",
    "hydro_gwh", "thermal_gwh", "wind_gwh", "solar_gwh", "load_gwh", "total_generation_gwh",
]
COLUNAS_GWH = ["hydro_gwh", "thermal_gwh", "wind_gwh", "solar_gwh", "load_gwh", "total_generation_gwh"]
SUBSISTEMAS = {"N", "NE", "SE", "S"}

QUERY = """
SELECT
    subsystem_code, subsystem_name, is_national_aggregate,
    FORMAT_DATE('%Y-%m-%d', reference_month) AS reference_month,
    hours_count, hours_with_null_generation,
    hydro_gwh, thermal_gwh, wind_gwh, solar_gwh, load_gwh, total_generation_gwh
FROM `{tabela}`
ORDER BY reference_month, subsystem_code
"""


class IngestaoError(RuntimeError):
    """Falha de ingestão. Sempre com mensagem acionável; nunca vira dado sintético."""


# ---------------------------------------------------------------------------
# Dado real
# ---------------------------------------------------------------------------

def consultar_bigquery(projeto: str, tabela: str) -> pd.DataFrame:
    try:
        from google.cloud import bigquery
        from google.auth.exceptions import DefaultCredentialsError
    except ImportError as exc:
        raise IngestaoError(
            "Biblioteca do BigQuery ausente. Rode: pip install google-cloud-bigquery"
        ) from exc

    tabela_completa = f"{projeto}.{tabela}"
    try:
        cliente = bigquery.Client(project=projeto)
        return cliente.query(QUERY.format(tabela=tabela_completa)).to_dataframe(create_bqstorage_client=False)
    except DefaultCredentialsError as exc:
        raise IngestaoError(
            "Sem credenciais do Google Cloud. Rode: gcloud auth application-default login"
        ) from exc
    except Exception as exc:  # NotFound, Forbidden, rede...
        raise IngestaoError(
            f"Falha ao consultar `{tabela_completa}`: {type(exc).__name__}: {exc}\n"
            "Confirme que o mart existe (dbt build no ons-energy-pipeline) e que você tem acesso."
        ) from exc


def validar_extracao(df: pd.DataFrame, aceitar_horas_nulas: bool) -> int:
    """Checagens que travam a ingestão. Nada aqui é corrigido em silêncio.

    Horas com fonte nula travam a ingestão nos 4 subsistemas, que são a base dos totais.
    A linha SIN (agregado pré-calculado pela ONS) só serve de conferência: nulos nela
    não travam, mas são contados, avisados e gravados no manifest. Retorna esse total."""
    faltando = [c for c in COLUNAS if c not in df.columns]
    if faltando:
        raise IngestaoError(f"Colunas ausentes na extração: {faltando}")
    if df.empty:
        raise IngestaoError("A tabela veio vazia. Nada para publicar.")

    codigos = set(df["subsystem_code"].unique())
    esperados = SUBSISTEMAS | {"SIN"}
    if codigos != esperados:
        raise IngestaoError(f"Subsistemas encontrados {sorted(codigos)} != esperados {sorted(esperados)}")

    if (df[COLUNAS_GWH].dropna() < 0).any().any():
        raise IngestaoError("Há geração negativa na extração.")

    meses = pd.to_datetime(df["reference_month"])
    for codigo, grupo in df.assign(_m=meses).groupby("subsystem_code"):
        completo = pd.date_range(grupo["_m"].min(), grupo["_m"].max(), freq="MS")
        ausentes = completo.difference(pd.DatetimeIndex(grupo["_m"]))
        if len(ausentes):
            lista = ", ".join(d.strftime("%Y-%m") for d in ausentes[:12])
            raise IngestaoError(f"{codigo}: meses ausentes na série ({len(ausentes)}): {lista}")
        if grupo["_m"].duplicated().any():
            raise IngestaoError(f"{codigo}: meses duplicados na série.")

    eh_sin = df["subsystem_code"] == "SIN"
    nulas = int(df.loc[~eh_sin, "hours_with_null_generation"].sum())
    if nulas and not aceitar_horas_nulas:
        pior = df.loc[~eh_sin].sort_values("hours_with_null_generation", ascending=False).head(5)[
            ["subsystem_code", "reference_month", "hours_with_null_generation"]
        ]
        raise IngestaoError(
            f"{nulas} horas com geração nula nos subsistemas. Exemplos:\n{pior.to_string(index=False)}\n"
            "Investigue na fonte. Se for esperado (ex.: solar antes de existir no dataset), "
            "reexecute com --aceitar-horas-nulas e documente."
        )

    nulas_sin = int(df.loc[eh_sin, "hours_with_null_generation"].sum())
    if nulas_sin:
        meses_sin = int((df.loc[eh_sin, "hours_with_null_generation"] > 0).sum())
        print(
            f"[AVISO] A linha SIN tem {nulas_sin} horas com alguma fonte nula em {meses_sin} meses. "
            "O total nacional usa a soma dos 4 subsistemas, não a linha SIN; ela entra só na reconciliação.",
            file=sys.stderr,
        )
    return nulas_sin


def ingerir_real(projeto: str, tabela: str, aceitar_horas_nulas: bool) -> Path:
    df = consultar_bigquery(projeto, tabela)
    horas_nulas_sin = validar_extracao(df, aceitar_horas_nulas)

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    df["reference_month"] = pd.to_datetime(df["reference_month"])
    df.to_parquet(ARQUIVO_REAL, index=False)

    escrever_manifest(ARQUIVO_REAL, {
        "origem": ORIGEM_REAL,
        "fonte_original": "ONS - Balanço de Energia nos Subsistemas (horário), dataset balanco_energia_subsistema_ho",
        "portal": "https://dados.ons.org.br",
        "tabela_bigquery": f"{projeto}.{tabela}",
        "query": " ".join(QUERY.format(tabela=f"{projeto}.{tabela}").split()),
        "extraido_em_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "linhas": int(len(df)),
        "mes_inicial": df["reference_month"].min().strftime("%Y-%m"),
        "mes_final": df["reference_month"].max().strftime("%Y-%m"),
        "horas_nulas_aceitas": bool(aceitar_horas_nulas),
        "horas_nulas_linha_sin": horas_nulas_sin,
        "sha256_parquet": sha256_arquivo(ARQUIVO_REAL),
    })
    return ARQUIVO_REAL


# ---------------------------------------------------------------------------
# Modo desenvolvimento (explícito). Nunca alimenta o dashboard.
# ---------------------------------------------------------------------------

def gerar_sintetico() -> Path:
    """Dado ALEATÓRIO com o mesmo schema do dado real. Não representa o Brasil."""
    rng = np.random.default_rng(42)
    meses = pd.date_range("2019-01-01", "2024-12-01", freq="MS")
    base = {"hydro_gwh": 20000, "thermal_gwh": 4000, "wind_gwh": 3000, "solar_gwh": 1500}
    peso = {"N": 0.15, "NE": 0.25, "SE": 0.45, "S": 0.15}
    nomes = {"N": "Norte", "NE": "Nordeste", "SE": "Sudeste/Centro-Oeste", "S": "Sul"}

    linhas = []
    for mes in meses:
        horas = mes.days_in_month * 24
        for codigo, w in peso.items():
            fontes = {k: v * w * rng.uniform(0.8, 1.2) for k, v in base.items()}
            linhas.append({
                "subsystem_code": codigo, "subsystem_name": nomes[codigo], "is_national_aggregate": False,
                "reference_month": mes, "hours_count": horas, "hours_with_null_generation": 0,
                **fontes, "load_gwh": sum(fontes.values()),
            })
    df = pd.DataFrame(linhas)
    sin = df.groupby("reference_month", as_index=False)[
        ["hydro_gwh", "thermal_gwh", "wind_gwh", "solar_gwh", "load_gwh"]
    ].sum()
    sin = sin.assign(subsystem_code="SIN", subsystem_name="Sistema Interligado Nacional",
                     is_national_aggregate=True, hours_count=[m.days_in_month * 24 for m in sin["reference_month"]],
                     hours_with_null_generation=0)
    df = pd.concat([df, sin], ignore_index=True)
    df["total_generation_gwh"] = df[["hydro_gwh", "thermal_gwh", "wind_gwh", "solar_gwh"]].sum(axis=1)
    df = df[COLUNAS].sort_values(["reference_month", "subsystem_code"]).reset_index(drop=True)

    DEV_DIR.mkdir(parents=True, exist_ok=True)
    df.to_parquet(ARQUIVO_SINTETICO, index=False)
    escrever_manifest(ARQUIVO_SINTETICO, {
        "origem": ORIGEM_SINTETICA,
        "aviso": "DADO ALEATÓRIO PARA DESENVOLVIMENTO. Não representa o sistema elétrico brasileiro.",
        "gerado_em_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "linhas": int(len(df)),
        "sha256_parquet": sha256_arquivo(ARQUIVO_SINTETICO),
    })
    return ARQUIVO_SINTETICO


# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--synthetic", action="store_true", help="SÓ DEV: grava dado aleatório em data/dev/")
    parser.add_argument("--project", default=PROJETO_PADRAO)
    parser.add_argument("--table", default=TABELA_PADRAO, help="dataset.tabela do mart mensal")
    parser.add_argument("--aceitar-horas-nulas", action="store_true")
    args = parser.parse_args()

    try:
        if args.synthetic:
            caminho = gerar_sintetico()
            print(f"[AVISO] DADO SINTÉTICO gravado em {caminho}. Não use em análise nem no dashboard.")
        else:
            caminho = ingerir_real(args.project, args.table, args.aceitar_horas_nulas)
            print(f"OK: dado real gravado em {caminho}")
    except IngestaoError as exc:
        print(f"ERRO DE INGESTÃO: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
