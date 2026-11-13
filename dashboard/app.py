"""
dashboard/app.py
----------------
Dashboard interativo da Matriz Energética Brasileira.
Dark mode · Filtros por ano, mês e fonte · Plotly Dash

Execução:
    pip install -r requirements.txt
    python dashboard/app.py
    Acesse: http://localhost:8050
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

import dash_bootstrap_components as dbc  # noqa: E402
import pandas as pd  # noqa: E402
import plotly.express as px  # noqa: E402
import plotly.graph_objects as go  # noqa: E402
from dash import Dash, Input, Output, dcc, html  # noqa: E402

from src.proveniencia import ORIGEM_REAL, ler_manifest  # noqa: E402
from src.regimes import ANO_TRANSICAO, TEXTO_QUEBRA_CURTO, janela_comparavel  # noqa: E402

# ---------------------------------------------------------------------------
# Paleta dark mode
# ---------------------------------------------------------------------------

BG_PAGE   = "#0f1117"
BG_CARD   = "#1a1d27"
BG_CARD2  = "#22263a"
BG_FILTER = "#13161f"
BORDER    = "#2a2d3e"
TEXT_PRI  = "#e8eaf0"
TEXT_SEC  = "#8b8fa8"
ACCENT    = "#7c6af7"
PLOT_BG   = "#1a1d27"
GRID_COL  = "#2a2d3e"

CORES_FONTE = {
    "Hidráulica":   "#4a9eff",
    "Eólica":       "#3ecf8e",
    "Solar":        "#f5c542",
    "Termelétrica": "#ff6b6b",
}

NOMES_MESES = {
    1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr",
    5: "Mai", 6: "Jun", 7: "Jul", 8: "Ago",
    9: "Set", 10: "Out", 11: "Nov", 12: "Dez",
}

LAYOUT_BASE = dict(
    plot_bgcolor=PLOT_BG,
    paper_bgcolor=PLOT_BG,
    font=dict(color=TEXT_PRI, family="Inter, system-ui, sans-serif", size=12),
    xaxis=dict(gridcolor=GRID_COL, zerolinecolor=GRID_COL, tickfont=dict(color=TEXT_SEC)),
    yaxis=dict(gridcolor=GRID_COL, zerolinecolor=GRID_COL, tickfont=dict(color=TEXT_SEC)),
    legend=dict(
        bgcolor="rgba(0,0,0,0)", font=dict(color=TEXT_SEC),
        orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
    ),
    margin=dict(l=8, r=8, t=36, b=8),
    hoverlabel=dict(bgcolor=BG_CARD2, font_color=TEXT_PRI, bordercolor=BORDER),
)

# ---------------------------------------------------------------------------
# Dados
# ---------------------------------------------------------------------------

PROC_DIR = Path(__file__).parent.parent / "data" / "processed"


def carregar_dados():
    """
    Lê SOMENTE data/processed/geracao_completa.parquet, e só se o manifest ao lado disser
    que a origem é dado real (ons_bigquery). Não existe gerador de demonstração nem fallback:
    sem dado real e rastreável, o app não sobe.
    """
    arquivo = PROC_DIR / "geracao_completa.parquet"
    if not arquivo.exists():
        raise FileNotFoundError(
            f"{arquivo} não existe. Rode: python src/ingestao.py && python src/transformacao.py"
        )
    manifest = ler_manifest(arquivo, ORIGEM_REAL)  # levanta ProvenienciaError se não for dado real
    df = pd.read_parquet(arquivo)
    df["mes"] = df["mes"].astype(int)
    df["ano"] = df["ano"].astype(int)
    return df, manifest


df_raw, MANIFEST = carregar_dados()
anos_disp   = [int(a) for a in sorted(df_raw["ano"].unique())]
meses_disp  = list(range(1, 13))
fontes_disp = sorted(df_raw["fonte"].unique())

# ---------------------------------------------------------------------------
# Estilos
# ---------------------------------------------------------------------------

CARD_STYLE = {
    "background": BG_CARD, "border": f"1px solid {BORDER}",
    "borderRadius": "12px", "padding": "16px 20px", "height": "100%",
}
CARD_HDR = {
    "color": TEXT_SEC, "fontSize": "12px", "fontWeight": "500",
    "letterSpacing": "0.06em", "textTransform": "uppercase", "marginBottom": "12px",
}
LABEL_ST = {
    "color": TEXT_SEC, "fontSize": "12px", "fontWeight": "500",
    "marginBottom": "6px", "display": "block",
}
DROP_ST = {"backgroundColor": BG_CARD2, "border": f"1px solid {BORDER}", "borderRadius": "8px"}

# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------

app = Dash(
    __name__,
    external_stylesheets=[
        dbc.themes.CYBORG,
        "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap",
    ],
    title="Matriz Energética BR",
)

app.index_string = (
    "<!DOCTYPE html><html>"
    "<head>{%metas%}<title>{%title%}</title>{%favicon%}{%css%}</head>"
    f"<body style='background:{BG_PAGE};margin:0;'>"
    "{%app_entry%}<footer>{%config%}{%scripts%}{%renderer%}</footer>"
    "</body></html>"
)

app.layout = html.Div(
    style={"background": BG_PAGE, "minHeight": "100vh", "fontFamily": "Inter, system-ui, sans-serif"},
    children=[

        # Header
        html.Div(style={
            "background": BG_CARD, "borderBottom": f"1px solid {BORDER}",
            "padding": "20px 32px 16px", "marginBottom": "24px",
        }, children=[
            html.Div(style={"display": "flex", "alignItems": "center", "gap": "14px"}, children=[
                html.Span("⚡", style={"fontSize": "30px"}),
                html.Div([
                    html.H1("Matriz Energética Brasileira",
                            style={"margin": 0, "fontSize": "22px", "fontWeight": "600", "color": TEXT_PRI}),
                    html.P(f"Geração mensal por fonte · SIN · {min(anos_disp)}–{max(anos_disp)} · "
                           f"Fonte: ONS, Balanço de Energia nos Subsistemas · extraído em {MANIFEST['extraido_em_utc'][:10]}",
                           style={"margin": 0, "fontSize": "13px", "color": TEXT_SEC}),
                ]),
            ]),
        ]),

        html.Div(style={"padding": "0 24px 40px"}, children=[

            # Filtros
            html.Div(style={
                "background": BG_FILTER, "border": f"1px solid {BORDER}",
                "borderRadius": "12px", "padding": "20px 24px", "marginBottom": "24px",
            }, children=[
                dbc.Row([
                    dbc.Col([
                        html.Label("Período (ano)", style=LABEL_ST),
                        dcc.RangeSlider(
                            id="filtro-ano",
                            min=min(anos_disp), max=max(anos_disp), step=1,
                            value=[min(anos_disp), max(anos_disp)],
                            marks={int(a): {"label": str(a), "style": {"color": TEXT_SEC, "fontSize": "11px"}}
                                   for a in anos_disp},
                            tooltip={"always_visible": False, "placement": "bottom"},
                        ),
                    ], md=5),
                    dbc.Col([
                        html.Label("Meses", style=LABEL_ST),
                        dcc.Dropdown(
                            id="filtro-mes",
                            options=[{"label": NOMES_MESES[m], "value": str(m)} for m in meses_disp],
                            value=[str(m) for m in meses_disp],
                            multi=True,
                            placeholder="Todos os meses",
                            style=DROP_ST,
                        ),
                    ], md=4),
                    dbc.Col([
                        html.Label("Fontes", style=LABEL_ST),
                        dcc.Dropdown(
                            id="filtro-fontes",
                            options=[{"label": f, "value": f} for f in fontes_disp],
                            value=list(fontes_disp),
                            multi=True,
                            placeholder="Todas as fontes",
                            style=DROP_ST,
                        ),
                    ], md=3),
                ], align="center"),
            ]),

            # KPIs
            dbc.Row(id="kpi-row", className="mb-4 g-3"),

            # Gráficos linha 1
            dbc.Row([
                dbc.Col([
                    html.Div(style=CARD_STYLE, children=[
                        html.P("Evolução da geração por fonte", style=CARD_HDR),
                        dcc.Graph(id="grafico-evolucao", style={"height": "340px"},
                                  config={"displayModeBar": False}),
                    ])
                ], md=8),
                dbc.Col([
                    html.Div(style=CARD_STYLE, children=[
                        html.P("Composição da matriz — período", style=CARD_HDR),
                        dcc.Graph(id="grafico-pizza", style={"height": "340px"},
                                  config={"displayModeBar": False}),
                    ])
                ], md=4),
            ], className="mb-4 g-3"),

            # Gráficos linha 2
            dbc.Row([
                dbc.Col([
                    html.Div(style=CARD_STYLE, children=[
                        html.P("Participação % por fonte ao longo do tempo", style=CARD_HDR),
                        dcc.Graph(id="grafico-area", style={"height": "300px"},
                                  config={"displayModeBar": False}),
                    ])
                ], md=7),
                dbc.Col([
                    html.Div(style=CARD_STYLE, children=[
                        html.P("Hidro + eólica + solar (% da geração)", style=CARD_HDR),
                        dcc.Graph(id="grafico-renovavel", style={"height": "300px"},
                                  config={"displayModeBar": False}),
                    ])
                ], md=5),
            ], className="mb-4 g-3"),

            # Sazonalidade
            dbc.Row([
                dbc.Col([
                    html.Div(style=CARD_STYLE, children=[
                        html.P("Sazonalidade mensal por fonte (média do período)", style=CARD_HDR),
                        dcc.Graph(id="grafico-sazonalidade", style={"height": "280px"},
                                  config={"displayModeBar": False}),
                    ])
                ]),
            ], className="mb-4 g-3"),

            # Insights
            dbc.Row([
                dbc.Col([
                    html.Div(style={**CARD_STYLE, "borderLeft": f"3px solid {ACCENT}"}, children=[
                        html.P("💡 Insights do período selecionado", style=CARD_HDR),
                        html.Div(id="insights-texto",
                                 style={"color": TEXT_PRI, "fontSize": "14px", "lineHeight": "1.9"}),
                    ])
                ])
            ], className="mb-4 g-3"),

            html.P(
                "Carlos Henrique · Analytics Engineer · github.com/carlosMartinez93/brazil-energy-matrix",
                style={"textAlign": "center", "color": TEXT_SEC, "fontSize": "12px", "marginTop": "8px"},
            ),
        ]),
    ]
)

# ---------------------------------------------------------------------------
# Callback
# ---------------------------------------------------------------------------

@app.callback(
    [
        Output("kpi-row", "children"),
        Output("grafico-evolucao", "figure"),
        Output("grafico-pizza", "figure"),
        Output("grafico-area", "figure"),
        Output("grafico-renovavel", "figure"),
        Output("grafico-sazonalidade", "figure"),
        Output("insights-texto", "children"),
    ],
    [
        Input("filtro-ano", "value"),
        Input("filtro-mes", "value"),
        Input("filtro-fontes", "value"),
    ],
)
def atualizar(intervalo_anos, meses_sel, fontes_sel):
    ano_ini = int(intervalo_anos[0])
    ano_fim = int(intervalo_anos[1])
    meses   = [int(m) for m in (meses_sel or [str(m) for m in meses_disp])]
    fontes  = fontes_sel or list(fontes_disp)

    df = df_raw[
        (df_raw["ano"] >= ano_ini) &
        (df_raw["ano"] <= ano_fim) &
        (df_raw["mes"].isin(meses)) &
        (df_raw["fonte"].isin(fontes))
    ].copy()

    vazio = _fig_vazio()
    if df.empty:
        return [], vazio, vazio, vazio, vazio, vazio, "Sem dados para os filtros selecionados."

    # Agrega anual
    df_an = df.groupby(["ano", "fonte", "tipo_fonte", "renovavel"])["geracao_gwh"].sum().reset_index()
    tot_an = df_an.groupby("ano")["geracao_gwh"].transform("sum")
    df_an["participacao_pct"] = (df_an["geracao_gwh"] / tot_an * 100).round(2)

    ult_ano  = int(df_an["ano"].max())
    df_ult   = df_an[df_an["ano"] == ult_ano]
    tot_ult  = float(df_ult["geracao_gwh"].sum())
    pct_ren  = _pct_hes(df_an, ult_ano)

    # Os 4 cards comparam os MESMOS dois anos: a maior janela válida para todos ao mesmo tempo.
    # Solar, total e participações são afetados pela quebra de 2023 (src/regimes.py), então a
    # janela comum é a deles; a Eólica só acompanha para os cards ficarem na mesma régua.
    janela   = janela_comparavel(ano_ini, ult_ano, "Solar")
    var_sol  = _delta(df_an, "Solar", janela)
    var_eol  = _delta(df_an, "Eólica", janela)
    var_tot  = _delta(df_an, None, janela)
    pct_ren_ini = _pct_hes(df_an, janela[0]) if janela else None
    # Nos insights cada fonte usa a sua maior janela válida (a Eólica mantém o histórico longo).
    var_eol_longo = _variacao(df_an, "Eólica", ano_ini, ult_ano)

    # KPIs
    sub_tot = f"Ano {ult_ano}"
    sub_ren = f"% da geração, ano {ult_ano}"
    if var_tot is not None:
        sub_tot = f"vs {var_tot['ini']/1000:.0f} TWh em {var_tot['ano_ini']} ({var_tot['pct']:+.1f}%)"
    if pct_ren_ini is not None:
        sub_ren = f"vs {pct_ren_ini:.1f}% em {janela[0]}"
    kpis = [
        _kpi("Geração Total (SIN)",  f"{tot_ult/1000:.0f} TWh", sub_tot, "#4a9eff"),
        _kpi("Hidro + Eólica + Solar", f"{pct_ren:.1f}%",       sub_ren, "#3ecf8e"),
        _kpi("Solar",  _fmt_var(var_sol), _sub_var(var_sol, ano_ini, ult_ano, janela), "#f5c542"),
        _kpi("Eólica", _fmt_var(var_eol), _sub_var(var_eol, ano_ini, ult_ano, janela), "#c084fc"),
    ]

    # Evolução
    fig_ev = px.line(
        df_an, x="ano", y="geracao_gwh", color="fonte",
        color_discrete_map=CORES_FONTE, markers=True,
        labels={"geracao_gwh": "GWh", "ano": "Ano", "fonte": "Fonte"},
    )
    fig_ev.update_traces(line=dict(width=2.5), marker=dict(size=6))
    fig_ev.update_layout(**LAYOUT_BASE)
    _eixo_ano(fig_ev, ano_ini, ano_fim)

    # Donut
    df_pz = df_an.groupby("fonte")["geracao_gwh"].sum().reset_index()
    fig_pz = px.pie(
        df_pz, values="geracao_gwh", names="fonte",
        color="fonte", color_discrete_map=CORES_FONTE, hole=0.45,
    )
    fig_pz.update_traces(
        textposition="inside", textinfo="percent+label",
        textfont=dict(color=BG_PAGE, size=11),
        marker=dict(line=dict(color=BG_CARD, width=2)),
    )
    fig_pz.update_layout(
        plot_bgcolor=PLOT_BG, paper_bgcolor=PLOT_BG,
        font=dict(color=TEXT_PRI, family="Inter, system-ui, sans-serif"),
        showlegend=False, margin=dict(l=8, r=8, t=8, b=8),
        hoverlabel=dict(bgcolor=BG_CARD2, font_color=TEXT_PRI, bordercolor=BORDER),
    )

    # Área %
    fig_ar = px.area(
        df_an, x="ano", y="participacao_pct", color="fonte",
        color_discrete_map=CORES_FONTE,
        labels={"participacao_pct": "%", "ano": "Ano"},
    )
    fig_ar.update_traces(line=dict(width=0.5))
    fig_ar.update_layout(**LAYOUT_BASE)
    _eixo_ano(fig_ar, ano_ini, ano_fim)

    # Mix renovável
    mix = df_an.groupby(["ano", "renovavel"])["geracao_gwh"].sum().reset_index()
    tot_mix = mix.groupby("ano")["geracao_gwh"].transform("sum")
    mix["pct"] = (mix["geracao_gwh"] / tot_mix * 100).round(1)
    ren = mix[mix["renovavel"]].sort_values("ano")
    fig_ren = go.Figure()
    fig_ren.add_trace(go.Scatter(
        x=ren["ano"].tolist(), y=ren["pct"].tolist(),
        mode="lines+markers",
        line=dict(color="#3ecf8e", width=3),
        fill="tozeroy", fillcolor="rgba(62,207,142,0.12)",
        marker=dict(size=7, color="#3ecf8e"),
        hovertemplate="%{x}: %{y:.1f}%<extra></extra>",
    ))
    for _, row in ren.iterrows():
        fig_ren.add_annotation(
            x=row["ano"], y=float(row["pct"]) + 1.5,
            text=f"{row['pct']:.1f}%", showarrow=False,
            font=dict(size=10, color="#3ecf8e"),
        )
    layout_ren = {**LAYOUT_BASE}
    layout_ren["yaxis"] = dict(range=[0, 108], ticksuffix="%", gridcolor=GRID_COL, tickfont=dict(color=TEXT_SEC))
    layout_ren["showlegend"] = False
    fig_ren.update_layout(**layout_ren)
    _eixo_ano(fig_ren, ano_ini, ano_fim)

    # Sazonalidade — deriva nome_mes aqui para funcionar com qualquer fonte de dados
    saz = df.groupby(["mes", "fonte"])["geracao_gwh"].mean().reset_index().sort_values("mes")
    saz["nome_mes"] = saz["mes"].map(NOMES_MESES)
    ordem = [NOMES_MESES[m] for m in range(1, 13) if m in saz["mes"].values]
    fig_saz = px.line(
        saz, x="nome_mes", y="geracao_gwh", color="fonte",
        color_discrete_map=CORES_FONTE, markers=True,
        category_orders={"nome_mes": ordem},
        labels={"geracao_gwh": "GWh médio", "nome_mes": "Mês", "fonte": "Fonte"},
    )
    fig_saz.update_traces(line=dict(width=2), marker=dict(size=5))
    fig_saz.update_layout(**LAYOUT_BASE)

    # Insights
    fonte_lider = str(df_ult.loc[df_ult["geracao_gwh"].idxmax(), "fonte"])
    pct_lider   = float(df_ult[df_ult["fonte"] == fonte_lider]["participacao_pct"].values[0])

    itens = [html.Li(f"{fonte_lider} lidera a geração em {ult_ano} com {pct_lider:.1f}% do total.")]
    for nome, v in (("Solar", var_sol), ("Eólica", var_eol_longo)):
        if v is not None:
            itens.append(html.Li(
                f"{nome}: {_fmt_pct(v)} entre {v['ano_ini']} e {v['ano_fim']} "
                f"({v['ini']:,.0f} → {v['fim']:,.0f} GWh)."
            ))
    itens.append(html.Li(f"Hidro + eólica + solar somaram {pct_ren:.1f}% da geração em {ult_ano}."))
    if var_tot is not None:
        itens.append(html.Li(
            f"Geração total variou {var_tot['pct']:+.0f}% entre {var_tot['ano_ini']} e {var_tot['ano_fim']} "
            f"({var_tot['ini']/1000:.0f} → {var_tot['fim']/1000:.0f} TWh)."
        ))
    nota = (
        "Escopo: dado operativo do SIN publicado pela ONS; pode diferir de balanços nacionais. "
        "Biomassa e nuclear estão dentro de Termelétrica. Reconciliação em docs/validacao.md."
    )
    if ano_ini <= ANO_TRANSICAO <= ano_fim:
        nota += " " + TEXTO_QUEBRA_CURTO
    insights = html.Div([
        html.Ul(itens, style={"paddingLeft": "20px", "lineHeight": "2"}),
        html.P(nota, style={"color": TEXT_SEC, "fontSize": "12px", "margin": "8px 0 0"}),
    ])

    return kpis, fig_ev, fig_pz, fig_ar, fig_ren, fig_saz, insights


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fig_vazio():
    layout = {**LAYOUT_BASE}
    layout["xaxis"] = dict(visible=False, gridcolor=GRID_COL)
    layout["yaxis"] = dict(visible=False, gridcolor=GRID_COL)
    layout["annotations"] = [dict(
        text="Sem dados para os filtros selecionados",
        showarrow=False, font=dict(color=TEXT_SEC, size=13),
    )]
    fig = go.Figure()
    fig.update_layout(**layout)
    return fig


def _kpi(titulo, valor, sub, cor):
    return dbc.Col(
        html.Div(style={
            "background": BG_CARD, "border": f"1px solid {BORDER}",
            "borderRadius": "12px", "borderTop": f"3px solid {cor}",
            "padding": "16px 20px", "textAlign": "center",
        }, children=[
            html.P(titulo, style={"color": TEXT_SEC, "fontSize": "12px", "margin": "0 0 4px", "fontWeight": "500"}),
            html.H3(valor, style={"color": cor, "margin": "0 0 4px", "fontSize": "26px", "fontWeight": "600"}),
            html.P(sub, style={"color": TEXT_SEC, "fontSize": "11px", "margin": 0}),
        ]),
        md=3,
    )


def _delta(df, fonte, janela):
    """Variação % entre os dois anos da janela (fonte=None -> geração total). None sem janela ou sem base."""
    if janela is None:
        return None
    a, b = janela
    base = df if fonte is None else df[df["fonte"] == fonte]
    ini = float(base[base["ano"] == a]["geracao_gwh"].sum())
    fim = float(base[base["ano"] == b]["geracao_gwh"].sum())
    if ini <= 0:
        return None
    return {"pct": (fim / ini - 1) * 100, "ini": ini, "fim": fim, "ano_ini": a, "ano_fim": b}


def _variacao(df, fonte, ano_ini, ano_fim):
    """
    Variação % de uma fonte (fonte=None -> total) na maior janela válida dentro de [ano_ini, ano_fim]
    (src/regimes.py: nunca cruza a quebra de 2023). None quando não há janela válida.
    """
    return _delta(df, fonte, janela_comparavel(ano_ini, ano_fim, fonte))


def _pct_hes(df, ano):
    """% da geração do ano vinda de hidro + eólica + solar (flag renovavel)."""
    d = df[df["ano"] == ano]
    total = float(d["geracao_gwh"].sum())
    return float(d[d["renovavel"]]["geracao_gwh"].sum() / total * 100) if total > 0 else 0.0


def _fmt_pct(v):
    """+25%; acima de +1000% (base minúscula) mostra o múltiplo, ex.: ×711, que é o mesmo fato sem o número absurdo."""
    if v["pct"] >= 1000:
        return f"×{v['fim'] / v['ini']:,.0f}"
    return f"{v['pct']:+.0f}%"


def _fmt_var(v):
    return "n/d" if v is None else _fmt_pct(v)


def _sub_var(v, ano_ini, ano_fim, janela):
    """Legenda do KPI: anos realmente comparados, ou o motivo de não haver número."""
    if v is not None:
        return f"{v['ano_ini']}→{v['ano_fim']}"
    if ano_fim <= ano_ini:
        return "selecione mais de um ano"
    if janela is None:
        return "sem janela comparável (quebra em 2023)"
    return "sem dados nos filtros"


def _eixo_ano(fig, ano_ini, ano_fim):
    """Eixo X com anos inteiros (sem '2,022.5') e marca da transição de 2023, se estiver no intervalo."""
    # tickvals explícitos: com dtick sozinho o último ano some em alguns gráficos (ex.: área)
    fig.update_xaxes(tickmode="array", tickvals=list(range(ano_ini, ano_fim + 1)), tickformat="d")
    if ano_ini <= ANO_TRANSICAO <= ano_fim and ano_fim > ano_ini:
        fig.add_vline(x=ANO_TRANSICAO, line_dash="dot", line_color=TEXT_SEC, line_width=1)
        # se 2023 é o último ano do slider, o rótulo à direita esticaria o eixo até 2024-2025
        ancora = "right" if ano_fim == ANO_TRANSICAO else "left"
        fig.add_annotation(
            x=ANO_TRANSICAO, y=1, yref="paper", xanchor=ancora, yanchor="top", showarrow=False,
            text="2023: quebra na série solar", font=dict(size=10, color=TEXT_PRI),
            bgcolor="rgba(26,29,39,0.85)",
        )


if __name__ == "__main__":
    app.run(debug=True, port=8050)
