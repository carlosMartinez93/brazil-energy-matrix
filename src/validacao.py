"""
validacao.py
------------
Gera o bloco "Validação" do README (estilo relatório de reconciliação):

  1. Reconciliação interna: soma dos 4 subsistemas x total SIN publicado pela ONS,
     e quais anos entraram / ficaram de fora por estarem incompletos.
  2. Reconciliação externa: totais anuais do projeto x valores oficiais que VOCÊ cadastra em
     data/reference/referencia_oficial.csv (EPE/BEN, ONS, etc.), com URL e escopo de cada um.

O script nunca preenche valor oficial por conta própria. Sem o CSV de referência, ele para.

Uso:
    python src/validacao.py            # escreve docs/validacao.md e imprime o bloco
"""

import sys
from pathlib import Path

import pandas as pd

try:
    from src.proveniencia import ORIGEM_REAL, ProvenienciaError, ler_manifest
except ImportError:  # execução como script
    from proveniencia import ORIGEM_REAL, ProvenienciaError, ler_manifest

RAIZ = Path(__file__).resolve().parent.parent
PROCESSED = RAIZ / "data" / "processed"
REFERENCIA = RAIZ / "data" / "reference" / "referencia_oficial.csv"
SAIDA = RAIZ / "docs" / "validacao.md"

COLUNAS_REF = ["fonte_oficial", "url", "ano", "metrica", "valor", "unidade", "escopo_oficial"]
METRICAS = {
    "geracao_total": None,
    "geracao_hidraulica": "Hidráulica",
    "geracao_eolica": "Eólica",
    "geracao_solar": "Solar",
    "geracao_termica": "Termelétrica",
}
PARA_GWH = {"GWh": 1.0, "TWh": 1000.0}


class ValidacaoError(RuntimeError):
    pass


def carregar_referencia() -> pd.DataFrame:
    if not REFERENCIA.exists():
        raise ValidacaoError(
            f"{REFERENCIA.relative_to(RAIZ)} não existe. Cadastre os valores oficiais "
            "(veja data/reference/LEIAME.md). Valor sem fonte e URL não entra."
        )
    ref = pd.read_csv(REFERENCIA, dtype=str).fillna("")
    faltando = [c for c in COLUNAS_REF if c not in ref.columns]
    if faltando:
        raise ValidacaoError(f"Colunas ausentes em {REFERENCIA.name}: {faltando}")
    if ref.empty:
        raise ValidacaoError(f"{REFERENCIA.name} está vazio.")
    vazias = ref[(ref[COLUNAS_REF] == "").any(axis=1)]
    if not vazias.empty:
        raise ValidacaoError(
            f"Linhas com campo vazio em {REFERENCIA.name} (linhas {list(vazias.index + 2)}). "
            "Todo valor precisa de fonte, URL, ano, métrica, unidade e escopo."
        )
    invalidas = set(ref["metrica"]) - set(METRICAS)
    if invalidas:
        raise ValidacaoError(f"Métricas inválidas {sorted(invalidas)}. Use: {sorted(METRICAS)}")
    desconhecidas = set(ref["unidade"]) - set(PARA_GWH)
    if desconhecidas:
        raise ValidacaoError(f"Unidades inválidas {sorted(desconhecidas)}. Use: {sorted(PARA_GWH)}")
    ref["ano"] = ref["ano"].astype(int)
    ref["valor"] = ref["valor"].str.replace(",", ".", regex=False).astype(float)
    return ref


def valor_do_projeto(anual: pd.DataFrame, ano: int, metrica: str):
    do_ano = anual[anual["ano"] == ano]
    if do_ano.empty:
        return None
    fonte = METRICAS[metrica]
    if fonte is None:
        return float(do_ano["geracao_total_gwh"].sum())
    linha = do_ano[do_ano["fonte"] == fonte]
    return float(linha["geracao_total_gwh"].sum()) if not linha.empty else None


def fmt(x_gwh: float) -> str:
    return f"{x_gwh / 1000:,.1f} TWh"


def pct(x: float) -> str:
    return f"{x:+.2f}%"


def gerar_bloco() -> str:
    manifest = ler_manifest(PROCESSED / "geracao_completa.parquet", ORIGEM_REAL)
    anual = pd.read_parquet(PROCESSED / "geracao_anual_por_fonte.parquet")
    ref = carregar_referencia()
    exigidos = ["fonte_original", "tabela_bigquery", "extraido_em_utc", "mes_inicial", "mes_final",
                "reconciliacao_sin", "anos_incluidos", "anos_excluidos"]
    ausentes = [k for k in exigidos if k not in manifest]
    if ausentes:
        raise ValidacaoError(f"Manifest sem os campos {ausentes}. Rode ingestao.py e transformacao.py de novo.")
    rec = manifest["reconciliacao_sin"]

    L = ["## Validation", ""]
    L += [
        f"Project data source: {manifest['fonte_original']} - table `{manifest['tabela_bigquery']}`, "
        f"extracted on {manifest['extraido_em_utc']} (UTC), months {manifest['mes_inicial']} to {manifest['mes_final']}.",
        "",
        "### Internal reconciliation",
        "",
        "| Check | Result |",
        "|---|---|",
        f"| Months compared (sum of the 4 subsystems vs. ONS national total, SIN) | {rec['meses_comparados']} |",
        f"| Maximum absolute deviation | {rec['desvio_abs_max_pct']:.4f}% |",
        f"| Mean absolute deviation | {rec['desvio_abs_medio_pct']:.4f}% |",
        f"| Years included (complete) | {', '.join(map(str, manifest['anos_incluidos']))} |",
    ]
    if manifest["anos_excluidos"]:
        fora = "; ".join(f"{a['ano']} ({a['motivo']})" for a in manifest["anos_excluidos"])
        L.append(f"| Years excluded | {fora} |")
    else:
        L.append("| Years excluded | none |")

    L += ["", "### External reconciliation", "",
          "| Source | Period | Metric | Official | This project | Difference | Difference % | Official source scope |",
          "|---|---|---|---|---|---|---|---|"]
    for _, r in ref.sort_values(["ano", "metrica"]).iterrows():
        oficial_gwh = r["valor"] * PARA_GWH[r["unidade"]]
        meu = valor_do_projeto(anual, int(r["ano"]), r["metrica"])
        fonte = f"[{r['fonte_oficial']}]({r['url']})"
        if meu is None:
            L.append(f"| {fonte} | {r['ano']} | {r['metrica']} | {fmt(oficial_gwh)} | n/a (year outside project period) | — | — | {r['escopo_oficial']} |")
            continue
        dif = meu - oficial_gwh
        L.append(
            f"| {fonte} | {r['ano']} | {r['metrica']} | {fmt(oficial_gwh)} | {fmt(meu)} | "
            f"{fmt(dif)} | {pct(dif / oficial_gwh * 100)} | {r['escopo_oficial']} |"
        )
    L += ["",
          "Differences are reported, not corrected. When the official source covers a wider scope "
          "than ONS operational data, a gap is expected and must be read together with the scope column.",
          ""]
    return "\n".join(L)


def main() -> int:
    try:
        bloco = gerar_bloco()
    except (ValidacaoError, ProvenienciaError, FileNotFoundError) as exc:
        print(f"ERRO DE VALIDAÇÃO: {exc}", file=sys.stderr)
        return 2
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(bloco, encoding="utf-8")
    print(bloco)
    print(f"\nEscrito em {SAIDA.relative_to(RAIZ)}. Cole o bloco no README.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
