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
    "Nuclear":      "#c084fc",
    "Biomassa":     "#fb923c",
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


def _gerar_dados_demo() -> pd.DataFrame:
    np.random.seed(42)
    fontes_config = {
        "Hidráulica":   (29000, -0.012, "Renovável",     0.22),
        "Eólica":       ( 4000,  0.090, "Renovável",     0.18),
        "Solar":        (  150,  0.170, "Renovável",     0.30),
        "Termelétrica": ( 6500,  0.008, "Não renovável", 0.08),
        "Nuclear":      ( 1250,  0.001, "Baixo carbono", 0.02),
        "Biomassa":     ( 2500,  0.022, "Renovável",     0.14),
    }
    rows = []
    datas = pd.date_range("2015-01-01", "2024-12-01", freq="MS")
    for data in datas:
        anos_dec = (data.year - 2015) + data.month / 12
        for fonte, (base, taxa, tipo, saz_amp) in fontes_config.items():
            tendencia = base * (1 + taxa) ** anos_dec
            if fonte == "Solar":
                saz = 1 + 0.35 * np.cos(2 * np.pi * (data.month - 1) / 12)
            else:
                saz = 1 + saz_amp * np.sin(2 * np.pi * (data.month - 3) / 12)
            gwh = round(float(max(0, tendencia * saz * np.random.normal(1, 0.025))), 1)
            rows.append({
                "data":       data,
                "ano":        int(data.year),
                "mes":        int(data.month),
                "nome_mes":   NOMES_MESES[data.month],
                "fonte":      fonte,
                "tipo_fonte": tipo,
                "renovavel":  tipo == "Renovável",
                "geracao_gwh": gwh,
            })
    df = pd.DataFrame(rows)
    tot = df.groupby(["ano", "mes"])["geracao_gwh"].transform("sum")
    df["participacao_pct"] = (df["geracao_gwh"] / tot * 100).round(2)
    return df


def carregar_dados() -> pd.DataFrame:
    for nome in ["geracao_completa.parquet", "geracao_sintetica.parquet"]:
        p = PROC_DIR / nome
        if p.exists():
            df = pd.read_parquet(p)
            # Normaliza nomes de colunas para o padrão do dashboard
            if "geracao_mwmed" in df.columns and "geracao_gwh" not in df.columns:
                df["geracao_gwh"] = (df["geracao_mwmed"] * 24 * 30 / 1000).round(1)
            if "geracao_gwh" not in df.columns:
                continue
            if "mes" not in df.columns and "data" in df.columns:
                df["data"] = pd.to_datetime(df["data"])
                df["mes"] = df["data"].dt.month
                df["ano"] = df["data"].dt.year
            df["mes"] = df["mes"].astype(int)
            df["ano"] = df["ano"].astype(int)
            return df
    return _gerar_dados_demo()


df_raw      = carregar_dados()
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
                    html.P("Geração por fonte · 2015–2024 · Fontes: ONS & ANEEL",
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
                        html.P("Mix renovável (%)", style=CARD_HDR),
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
    cr_sol   = float(_yoy(df_an, "Solar",  ano_ini, ult_ano))
    cr_eol   = float(_yoy(df_an, "Eólica", ano_ini, ult_ano))

    # KPIs
    kpis = [
        _kpi("Geração Total",  f"{tot_ult/1000:.0f} TWh", f"Ano {ult_ano}", "#4a9eff"),
        _kpi("Mix Renovável",  f"{pct_ren:.1f}%",         f"Ano {ult_ano}", "#3ecf8e"),
        _kpi("Solar ↑",       f"+{cr_sol:.0f}%",         f"{ano_ini}→{ult_ano}", "#f5c542"),
        _kpi("Eólica ↑",      f"+{cr_eol:.0f}%",         f"{ano_ini}→{ult_ano}", "#c084fc"),
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

    insights = html.Ul([
        html.Li(f"{fonte_lider} lidera a matriz em {ult_ano} com {pct_lider:.1f}% da geração."),
        html.Li(f"Energia solar cresceu {cr_sol:.0f}% entre {ano_ini} e {ult_ano} — maior expansão do período."),
        html.Li(f"Energia eólica cresceu {cr_eol:.0f}% no mesmo período, consolidando o Nordeste como polo renovável."),
        html.Li(f"Mix renovável atingiu {pct_ren:.1f}% em {ult_ano}, mantendo o Brasil entre os líderes mundiais."),
        html.Li(f"Geração total variou {variacao:+.0f}% entre {ano_ini} e {ult_ano} "
                f"({tot_ini/1000:.0f} → {tot_ult/1000:.0f} TWh)."),
    ], style={"paddingLeft": "20px", "lineHeight": "2"})

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


def _yoy(df, fonte, ano_ini, ano_fim):
    vi = df[(df["fonte"] == fonte) & (df["ano"] == ano_ini)]["geracao_gwh"].sum()
    vf = df[(df["fonte"] == fonte) & (df["ano"] == ano_fim)]["geracao_gwh"].sum()
    return float((vf / vi - 1) * 100) if vi > 0 else 0.0


if __name__ == "__main__":
    app.run(debug=True, port=8050)
