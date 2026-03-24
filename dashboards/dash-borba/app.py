"""
BI Monitoramento - Município de Borba - AM

Dashboard de monitoramento de solicitações e alertas.
"""

from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import yaml
from dash import Dash, dash_table, dcc, html
from dash.dependencies import Input, Output

DASHBOARD_DIR = Path(__file__).parent

with open(DASHBOARD_DIR / "config.yaml", "r") as f:
    CONFIG = yaml.safe_load(f)

DB_CONFIG = CONFIG.get("database", {})
REFRESH_INTERVAL = CONFIG.get("refresh_interval", 0) * 1000

VERDE_LOGO = "#009440"
VERDE_LOGO_DARK = "#006e2f"
VERDE_LOGO_LIGHT = "#e6f4ec"
VERDE_SUCESSO = "#31AA05"
VERDE_SUCESSO_BG = "#edf9e6"
PENDENTE = "#E07B00"
PENDENTE_BG = "#fff4e5"


def chart_layout(**kwargs):
    base = dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_family="Nunito, Segoe UI, sans-serif",
        font_color="#475569",
        title_font_color="#1e293b",
        title_font_size=14,
        margin=dict(l=0, r=0, t=40, b=0),
        xaxis=dict(gridcolor="#e8ecf1", zeroline=False),
        yaxis=dict(gridcolor="#e8ecf1", zeroline=False),
    )
    base.update(kwargs)
    return base


def get_mock_data() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "secretaria": ["SEMED", "SEMSA", "SEMOB", "SEMJEL", "SEINF", "SEMURB"],
            "total": [45, 38, 32, 28, 22, 18],
        }
    )


def get_data():
    """Obtém dados da fonte configurada (banco ou CSV) ou mock."""
    try:
        from core.db import DatabaseFactory

        if not DB_CONFIG:
            return get_mock_data(), pd.DataFrame()

        if not DatabaseFactory.test_connection(DB_CONFIG):
            return get_mock_data(), pd.DataFrame()

        if DB_CONFIG.get("type") == "csv":
            df = DatabaseFactory.get_data_source(DB_CONFIG)
            return df, pd.DataFrame()

        import sys
        from pathlib import Path

        queries_path = Path(__file__).parent / "queries.py"
        import importlib.util

        spec = importlib.util.spec_from_file_location("borba_queries", queries_path)
        borba_queries = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(borba_queries)

        engine = DatabaseFactory._get_engine(DB_CONFIG)
        df_events = borba_queries.load_sasi_events(engine)
        df_secretarias = borba_queries.load_secretarias(engine)
        return df_events, df_secretarias
    except Exception as e:
        print(f"Erro ao buscar dados: {e}")
        return get_mock_data(), pd.DataFrame()


df_events, df_secretarias = get_data()


def stat_card(icon, label, value_id, card_class, value_class=""):
    return html.Div(
        [
            html.Div(
                html.I(className=f"fas {icon}"),
                className=f"kpi-icon kpi-icon-{card_class}",
            ),
            html.Div(
                [
                    html.P(label, className="kpi-label"),
                    html.H3("—", id=value_id, className=f"kpi-value {value_class}"),
                ],
                className="kpi-text",
            ),
        ],
        className=f"kpi-card kpi-card-{card_class}",
    )


def dash_card(title, icon, children):
    return html.Div(
        [
            html.Div(
                [
                    html.Span(
                        [
                            html.I(
                                className=f"fas {icon}",
                                style={"color": VERDE_LOGO, "marginRight": "8px"},
                            ),
                            title,
                        ],
                        className="chart-title",
                    ),
                ],
                className="chart-card-header",
            ),
            html.Div(children, className="chart-card-body"),
        ],
        className="chart-card",
    )


layout = html.Div(
    [
        dcc.Interval(
            id="borba-interval",
            interval=REFRESH_INTERVAL if REFRESH_INTERVAL > 0 else None,
            n_intervals=0,
        ),
        html.Header(
            [
                html.Div(
                    [
                        html.Img(
                            src="/dash-borba/assets/logo_borba.jpeg",
                            className="header-logo",
                            alt="Logo Município de Borba",
                        ),
                    ],
                    className="header-left",
                ),
                html.Div(
                    [
                        html.I(
                            className="fas fa-map-marker-alt",
                            style={"marginRight": "6px", "opacity": ".8"},
                        ),
                        "Município de Borba — AM",
                    ],
                    className="header-right",
                ),
            ],
            className="app-header",
        ),
        html.Div(
            [
                html.Div(
                    [
                        html.Div(
                            [
                                html.Label("Período", className="filter-label"),
                                dcc.Dropdown(
                                    id="mes-dropdown",
                                    options=[],
                                    placeholder="Todos os períodos",
                                    clearable=True,
                                    className="filter-dropdown",
                                ),
                            ],
                            className="filter-group",
                        ),
                        html.Div(
                            [
                                html.Label("Secretaria", className="filter-label"),
                                dcc.Dropdown(
                                    id="secretaria-dropdown",
                                    options=[],
                                    placeholder="Todas as Secretarias",
                                    clearable=True,
                                    className="filter-dropdown",
                                ),
                            ],
                            className="filter-group",
                        ),
                        html.Button(
                            [
                                html.I(
                                    className="fas fa-sync-alt",
                                    style={"marginRight": "8px"},
                                ),
                                "Atualizar",
                            ],
                            id="refresh-btn",
                            className="btn-refresh",
                        ),
                        html.Div(id="last-update", className="last-update"),
                    ],
                    className="filter-bar-inner",
                ),
            ],
            className="filter-bar",
        ),
        html.Div(
            [
                html.Div(
                    [
                        stat_card(
                            "fa-bell",
                            "Total de Solicitações",
                            "total-solicitacoes",
                            "total",
                        ),
                        stat_card(
                            "fa-check-circle",
                            "Concluídos",
                            "total-concluidos",
                            "concluidos",
                            "kpi-value-concluidos",
                        ),
                        stat_card(
                            "fa-clock",
                            "Pendentes",
                            "total-pendentes",
                            "pendentes",
                            "kpi-value-pendentes",
                        ),
                        stat_card(
                            "fa-building",
                            "Secretarias Ativas",
                            "total-secretarias",
                            "secretarias",
                        ),
                    ],
                    className="kpi-row",
                ),
                html.Div(
                    [
                        html.Div(
                            dash_card(
                                "Solicitações por Secretaria",
                                "fa-chart-bar",
                                dcc.Graph(
                                    id="grafico-secretarias",
                                    config={"displayModeBar": False},
                                    style={"height": "340px"},
                                ),
                            ),
                            className="col-wide",
                        ),
                        html.Div(
                            dash_card(
                                "Distribuição por Status",
                                "fa-chart-pie",
                                dcc.Graph(
                                    id="grafico-status",
                                    config={"displayModeBar": False},
                                    style={"height": "340px"},
                                ),
                            ),
                            className="col-narrow",
                        ),
                    ],
                    className="chart-row",
                ),
                html.Div(
                    [
                        html.Div(
                            dash_card(
                                "Evolução Mensal de Solicitações",
                                "fa-chart-line",
                                dcc.Graph(
                                    id="grafico-evolucao",
                                    config={"displayModeBar": False},
                                    style={"height": "320px"},
                                ),
                            ),
                            className="col-wide",
                        ),
                        html.Div(
                            dash_card(
                                "Ranking de Secretarias",
                                "fa-trophy",
                                dcc.Graph(
                                    id="grafico-ranking",
                                    config={"displayModeBar": False},
                                    style={"height": "320px"},
                                ),
                            ),
                            className="col-narrow",
                        ),
                    ],
                    className="chart-row",
                ),
                dash_card(
                    "Dados Detalhados por Secretaria",
                    "fa-table",
                    html.Div(id="tabela-detalhada"),
                ),
            ],
            className="dashboard-body",
        ),
    ],
    className="dashboard-root",
)


def register_callbacks(app: Dash) -> None:
    @app.callback(
        [
            Output("mes-dropdown", "options"),
            Output("secretaria-dropdown", "options"),
            Output("last-update", "children"),
        ],
        [Input("refresh-btn", "n_clicks"), Input("borba-interval", "n_intervals")],
    )
    def update_dropdowns(_, __):
        global df_events, df_secretarias
        df_events, df_secretarias = get_data()

        mes_opts = []
        if not df_events.empty and "mes" in df_events.columns:
            meses = sorted(df_events["mes"].dropna().unique())
            mes_opts = [{"label": m, "value": m} for m in meses]

        sec_opts = [{"label": "Todas as Secretarias", "value": "all"}]
        if not df_secretarias.empty and "secretaria" in df_secretarias.columns:
            secs = sorted(df_secretarias["secretaria"].dropna().unique())
            sec_opts += [{"label": s.strip(), "value": s.strip()} for s in secs if s]

        now = datetime.now().strftime("%d/%m/%Y %H:%M")
        return mes_opts, sec_opts, f"Atualizado: {now}"

    @app.callback(
        [
            Output("total-solicitacoes", "children"),
            Output("total-concluidos", "children"),
            Output("total-pendentes", "children"),
            Output("total-secretarias", "children"),
            Output("grafico-secretarias", "figure"),
            Output("grafico-evolucao", "figure"),
            Output("grafico-ranking", "figure"),
            Output("grafico-status", "figure"),
            Output("tabela-detalhada", "children"),
        ],
        [
            Input("mes-dropdown", "value"),
            Input("secretaria-dropdown", "value"),
            Input("refresh-btn", "n_clicks"),
            Input("borba-interval", "n_intervals"),
        ],
    )
    def update_dashboard(selected_mes, selected_sec, _nc, _ni):
        global df_events

        df = df_events.copy() if not df_events.empty else pd.DataFrame()

        if selected_mes and not df.empty:
            df = df[df["mes"] == selected_mes]
        if selected_sec and selected_sec != "all" and not df.empty:
            df = df[df["secretaria"] == selected_sec]

        total = len(df)

        concluidos = pendentes = 0
        if not df.empty and "message" in df.columns:
            mask = df["message"].str.contains(
                r"Finaliz|Concluíd|Aprovad", case=False, na=False
            )
            concluidos = int(mask.sum())
            pendentes = total - concluidos

        sec_unicas = int(df["secretaria"].nunique()) if not df.empty else 0

        fig_sec = go.Figure()
        if not df.empty and "secretaria" in df.columns:
            cnt = df["secretaria"].value_counts().head(15).reset_index()
            cnt.columns = ["Secretaria", "Quantidade"]
            fig_sec = px.bar(
                cnt,
                x="Quantidade",
                y="Secretaria",
                orientation="h",
                text="Quantidade",
                color_discrete_sequence=[VERDE_LOGO],
            )
            fig_sec.update_traces(
                marker_color=VERDE_LOGO, textposition="outside", marker_line_width=0
            )
            fig_sec.update_layout(
                **chart_layout(
                    height=340,
                    margin=dict(l=10, r=40, t=10, b=10),
                    yaxis=dict(
                        categoryorder="total ascending",
                        color="#475569",
                        showgrid=False,
                        linecolor="#e8ecf1",
                    ),
                    xaxis=dict(color="#475569", gridcolor="#e8ecf1"),
                )
            )

        fig_evo = go.Figure()
        if not df_events.empty and "mes" in df_events.columns:
            dfe = df_events.copy()
            mensal = (
                dfe.groupby("mes").size().reset_index(name="Total").sort_values("mes")
            )

            mask_c = (
                dfe["message"].str.contains(r"Finaliz|Concluíd", case=False, na=False)
                if "message" in dfe.columns
                else pd.Series(False, index=dfe.index)
            )
            if mask_c.any():
                concl_m = (
                    dfe[mask_c].groupby("mes").size().reset_index(name="Concluídos")
                )
                mensal = mensal.merge(concl_m, on="mes", how="left").fillna(0)

            fig_evo.add_trace(
                go.Bar(
                    x=mensal["mes"],
                    y=mensal["Total"],
                    name="Total",
                    marker_color=VERDE_LOGO,
                    opacity=0.7,
                )
            )
            if "Concluídos" in mensal.columns:
                fig_evo.add_trace(
                    go.Scatter(
                        x=mensal["mes"],
                        y=mensal["Concluídos"],
                        name="Concluídos",
                        mode="lines+markers",
                        line=dict(color=VERDE_SUCESSO, width=3),
                        marker=dict(color=VERDE_SUCESSO, size=8),
                    )
                )

            fig_evo.update_layout(
                **chart_layout(
                    height=320,
                    margin=dict(l=10, r=10, t=10, b=30),
                    barmode="group",
                    legend=dict(orientation="h", y=1.08, font=dict(color="#475569")),
                    xaxis=dict(title=None, color="#475569", gridcolor="#e8ecf1"),
                    yaxis=dict(
                        title="Quantidade", color="#475569", gridcolor="#e8ecf1"
                    ),
                )
            )

        fig_rank = go.Figure()
        if not df.empty and "secretaria" in df.columns:
            rank = df["secretaria"].value_counts().head(8).reset_index()
            rank.columns = ["Secretaria", "Quantidade"]
            rank["Label"] = [
                f"{i+1}. {s[:22]}" for i, s in enumerate(rank["Secretaria"])
            ]
            colors = [VERDE_SUCESSO if i == 0 else VERDE_LOGO for i in range(len(rank))]

            fig_rank = go.Figure(
                go.Bar(
                    x=rank["Quantidade"],
                    y=rank["Label"],
                    orientation="h",
                    text=rank["Quantidade"],
                    textposition="outside",
                    marker_color=colors,
                    marker_line_width=0,
                )
            )
            fig_rank.update_layout(
                **chart_layout(
                    height=320,
                    margin=dict(l=10, r=40, t=10, b=10),
                    yaxis=dict(
                        categoryorder="total ascending",
                        color="#475569",
                        showgrid=False,
                        linecolor="#e8ecf1",
                    ),
                    xaxis=dict(color="#475569", gridcolor="#e8ecf1"),
                )
            )

        fig_status = go.Figure()
        if total > 0:
            fig_status = go.Figure(
                go.Pie(
                    labels=["Concluídos", "Pendentes"],
                    values=[concluidos, pendentes],
                    hole=0.55,
                    marker_colors=[VERDE_SUCESSO, PENDENTE],
                    textinfo="percent+label",
                    textposition="inside",
                    textfont_size=14,
                    textfont_color="white",
                )
            )
            fig_status.update_layout(
                **chart_layout(
                    height=340,
                    margin=dict(l=10, r=10, t=10, b=10),
                    legend=dict(orientation="h", y=-0.08, font=dict(color="#475569")),
                    showlegend=True,
                )
            )

        tabela = html.Div("Sem dados disponíveis.", style={"color": "#475569"})
        if not df.empty and "secretaria" in df.columns:
            cnt_df = df["secretaria"].value_counts().reset_index()
            cnt_df.columns = ["Secretaria", "Total"]
            cnt_df["%"] = (cnt_df["Total"] / cnt_df["Total"].sum() * 100).round(
                1
            ).astype(str) + "%"

            tabela = dash_table.DataTable(
                data=cnt_df.head(20).to_dict("records"),
                columns=[{"name": c, "id": c} for c in cnt_df.columns],
                style_table={"overflowX": "auto", "fontSize": "13px"},
                style_cell={
                    "textAlign": "left",
                    "padding": "10px 14px",
                    "color": "#1e293b",
                    "fontFamily": "'Nunito', sans-serif",
                    "border": "1px solid #e8ecf1",
                },
                style_header={
                    "backgroundColor": VERDE_LOGO_LIGHT,
                    "color": VERDE_LOGO_DARK,
                    "fontWeight": "700",
                    "fontSize": "12px",
                    "textTransform": "uppercase",
                    "letterSpacing": ".4px",
                    "border": "1px solid #e8ecf1",
                },
                style_data_conditional=[
                    {"if": {"row_index": "odd"}, "backgroundColor": "#f8fafc"},
                    {
                        "if": {"column_id": "%"},
                        "color": VERDE_LOGO,
                        "fontWeight": "700",
                    },
                ],
                page_size=20,
            )

        return (
            f"{total:,}",
            f"{concluidos:,}",
            f"{pendentes:,}",
            f"{sec_unicas}",
            fig_sec,
            fig_evo,
            fig_rank,
            fig_status,
            tabela,
        )
