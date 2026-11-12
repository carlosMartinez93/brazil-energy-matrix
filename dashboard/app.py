"""
dashboard/app.py
----------------
Dashboard interativo da Matriz Energética Brasileira.
Dark mode · Filtros por ano, mês e fonte · Plotly Dash

Execução:
    pip install dash plotly pandas pyarrow dash-bootstrap-components
    python dashboard/app.py
    Acesse: http://localhost:8050
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from src.proveniencia import ORIGEM_REAL, ler_manifest

import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output
import dash_bootstrap_components as dbc

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
                "Carlos Henrique · Analytics & ML Engineer · github.com/carlosMartinez93/brazil-energy-matrix",
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
    df_pri   = df_an[df_an["ano"] == ano_ini]
    tot_ult  = float(df_ult["geracao_gwh"].sum())
    tot_ini  = float(df_pri["geracao_gwh"].sum())
    pct_ren  = float(df_ult[df_ult["renovavel"]]["geracao_gwh"].sum() / tot_ult * 100)
    var_sol  = _variacao(df_an, "Solar",  ano_ini, ult_ano)
    var_eol  = _variacao(df_an, "Eólica", ano_ini, ult_ano)

    # KPIs
    kpis = [
        _kpi("Geração Total (SIN)",  f"{tot_ult/1000:.0f} TWh", f"Ano {ult_ano}", "#4a9eff"),
        _kpi("Hidro + Eólica + Solar", f"{pct_ren:.1f}%",       f"% da geração, ano {ult_ano}", "#3ecf8e"),
        _kpi("Solar",  _fmt_var(var_sol), f"{ano_ini}→{ult_ano}", "#f5c542"),
        _kpi("Eólica", _fmt_var(var_eol), f"{ano_ini}→{ult_ano}", "#c084fc"),
    ]

    # Evolução
    fig_ev = px.line(
        df_an, x="ano", y="geracao_gwh", color="fonte",
        color_discrete_map=CORES_FONTE, markers=True,
        labels={"geracao_gwh": "GWh", "ano": "Ano", "fonte": "Fonte"},
    )
    fig_ev.update_traces(line=dict(width=2.5), marker=dict(size=6))
    fig_ev.update_layout(**LAYOUT_BASE)

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

    # Mix renovável
    mix = df_an.groupby(["ano", "renovavel"])["geracao_gwh"].sum().reset_index()
    tot_mix = mix.groupby("ano")["geracao_gwh"].transform("sum")
    mix["pct"] = (mix["geracao_gwh"] / tot_mix * 100).round(1)
    ren = mix[mix["renovavel"] == True].sort_values("ano")
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
    variacao    = (tot_ult / tot_ini - 1) * 100 if tot_ini > 0 else 0.0

    itens = [html.Li(f"{fonte_lider} lidera a geração em {ult_ano} com {pct_lider:.1f}% do total.")]
    for nome, v in (("Solar", var_sol), ("Eólica", var_eol)):
        if v is not None:
            itens.append(html.Li(
                f"{nome}: {v['pct']:+.0f}% entre {ano_ini} e {ult_ano} "
                f"({v['ini']:,.0f} → {v['fim']:,.0f} GWh)."
            ))
    itens.append(html.Li(f"Hidro + eólica + solar somaram {pct_ren:.1f}% da geração em {ult_ano}."))
    if ult_ano > ano_ini:
        itens.append(html.Li(
            f"Geração total variou {variacao:+.0f}% entre {ano_ini} e {ult_ano} "
            f"({tot_ini/1000:.0f} → {tot_ult/1000:.0f} TWh)."
        ))
    insights = html.Div([
        html.Ul(itens, style={"paddingLeft": "20px", "lineHeight": "2"}),
        html.P(
            "Escopo: dado operativo do SIN publicado pela ONS; pode diferir de balanços nacionais. "
            "Biomassa e nuclear estão dentro de Termelétrica. Reconciliação em docs/validacao.md.",
            style={"color": TEXT_SEC, "fontSize": "12px", "margin": "8px 0 0"},
        ),
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


def _variacao(df, fonte, ano_ini, ano_fim):
    """Variação % da fonte entre dois anos. None quando não há base de comparação."""
    if ano_fim <= ano_ini:
        return None
    ini = float(df[(df["fonte"] == fonte) & (df["ano"] == ano_ini)]["geracao_gwh"].sum())
    fim = float(df[(df["fonte"] == fonte) & (df["ano"] == ano_fim)]["geracao_gwh"].sum())
    if ini <= 0:
        return None
    return {"pct": (fim / ini - 1) * 100, "ini": ini, "fim": fim}


def _fmt_var(v):
    return "n/d" if v is None else f"{v['pct']:+.0f}%"


if __name__ == "__main__":
    app.run(debug=True, port=8050)
