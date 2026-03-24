"""
Dashboard Financeiro

Este dashboard exibe métricas financeiras incluindo:
- Fluxo de caixa
- Receitas vs Despesas
- Taxa de inadimplência
- Projeções futuras
"""
from pathlib import Path

import pandas as pd
import plotly.express as px
import yaml
from dash import Dash, dcc, html
from dash.dependencies import Input, Output

DASHBOARD_DIR = Path(__file__).parent

with open(DASHBOARD_DIR / "config.yaml", "r") as f:
    CONFIG = yaml.safe_load(f)

DB_CONFIG = CONFIG.get("database", {})
REFRESH_INTERVAL = CONFIG.get("refresh_interval", 0) * 1000


def get_mock_data() -> pd.DataFrame:
    """Retorna dados mockados para desenvolvimento."""
    return pd.DataFrame({
        "mes": ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun"],
        "receita": [85000, 92000, 88000, 105000, 98000, 112000],
        "despesa": [65000, 72000, 68000, 75000, 71000, 78000],
        "recebimentos": [78000, 85000, 82000, 95000, 91000, 105000],
        "pagamentos": [62000, 68000, 65000, 72000, 69000, 75000],
    })


def get_financial_data() -> pd.DataFrame:
    """Obtém dados financeiros (do banco ou mock)."""
    if not DB_CONFIG:
        return get_mock_data()
    
    try:
        from core.db import DatabaseFactory

        if not DatabaseFactory.test_connection(DB_CONFIG):
            return get_mock_data()

        from dashboards.financeiro.queries import get_monthly_cash_flow

        engine = DatabaseFactory.get_engine(DB_CONFIG)
        return get_monthly_cash_flow(engine)
    except Exception:
        return get_mock_data()


STYLES = {
    "container": {"padding": "20px", "maxWidth": "1200px", "margin": "0 auto"},
    "title": {"textAlign": "center", "marginBottom": "20px", "color": "#2c3e50"},
    "description": {"textAlign": "center", "color": "#666", "marginBottom": "30px"},
    "metricsRow": {"display": "flex", "justifyContent": "space-around", "margin": "20px 0", "flexWrap": "wrap"},
    "metricContainer": {"flex": "1", "minWidth": "200px", "padding": "10px"},
    "metricCard": {
        "background": "#f8f9fa",
        "padding": "20px",
        "borderRadius": "8px",
        "textAlign": "center",
        "boxShadow": "0 2px 4px rgba(0,0,0,0.1)",
    },
    "metricValue": {"margin": "0", "fontSize": "28px", "color": "#2c3e50"},
    "metricLabel": {"margin": "5px 0 0 0", "color": "#7f8c8d", "fontSize": "14px"},
    "chartContainer": {"margin": "20px 0", "padding": "10px"},
}

layout = html.Div([
    html.H1(CONFIG.get("name", "Dashboard Financeiro"), style=STYLES["title"]),
    html.P(CONFIG.get("description", ""), style=STYLES["description"]),
    
    dcc.Interval(
        id="financeiro-interval",
        interval=REFRESH_INTERVAL if REFRESH_INTERVAL > 0 else None,
        n_intervals=0,
    ),
    
    html.Div([
        html.Div([
            html.Div([
                html.H3("R$ 0", id="receita-total", style=STYLES["metricValue"]),
                html.P("Receita Total", style=STYLES["metricLabel"])
            ], style=STYLES["metricCard"])
        ], style=STYLES["metricContainer"]),
        
        html.Div([
            html.Div([
                html.H3("R$ 0", id="despesa-total", style=STYLES["metricValue"]),
                html.P("Despesas Totais", style=STYLES["metricLabel"])
            ], style=STYLES["metricCard"])
        ], style=STYLES["metricContainer"]),
        
        html.Div([
            html.Div([
                html.H3("R$ 0", id="lucro-bruto", style=STYLES["metricValue"]),
                html.P("Lucro Bruto", style=STYLES["metricLabel"])
            ], style=STYLES["metricCard"])
        ], style=STYLES["metricContainer"]),
        
        html.Div([
            html.Div([
                html.H3("0%", id="margem-lucro", style=STYLES["metricValue"]),
                html.P("Margem de Lucro", style=STYLES["metricLabel"])
            ], style=STYLES["metricCard"])
        ], style=STYLES["metricContainer"]),
    ], style=STYLES["metricsRow"]),
    
    html.Div([
        dcc.Graph(id="fluxo-caixa-grafico")
    ], style=STYLES["chartContainer"]),
    
    html.Div([
        dcc.Graph(id="receita-despesa-grafico")
    ], style=STYLES["chartContainer"]),
], style=STYLES["container"])


def register_callbacks(app: Dash) -> None:
    """Registra os callbacks do dashboard."""

    @app.callback(
        [Output("receita-total", "children"),
         Output("despesa-total", "children"),
         Output("lucro-bruto", "children"),
         Output("margem-lucro", "children"),
         Output("fluxo-caixa-grafico", "figure"),
         Output("receita-despesa-grafico", "figure")],
        [Input("financeiro-interval", "n_intervals")]
    )
    def update_dashboard(n: int):
        """Atualiza todos os componentes do dashboard."""
        try:
            df = get_financial_data()

            if df.empty:
                return ("R$ 0", "R$ 0", "R$ 0", "0%", {"data": []}, {"data": []})

            receita_total = df["receita"].sum()
            despesa_total = df["despesa"].sum()
            lucro_bruto = receita_total - despesa_total
            margem_lucro = (lucro_bruto / receita_total * 100) if receita_total > 0 else 0

            df_caixa = pd.DataFrame({
                "mes": df["mes"],
                "fluxo": df["recebimentos"] - df["pagamentos"],
            })

            fig_fluxo = px.bar(
                df_caixa,
                x="mes",
                y="fluxo",
                title="Fluxo de Caixa",
                color="fluxo",
                color_continuous_scale=["#e74c3c", "#f1c40f", "#2ecc71"]
            )
            fig_fluxo.update_layout(plot_bgcolor="white", paper_bgcolor="white")

            fig_rec_des = px.bar(
                df,
                x="mes",
                y=["receita", "despesa"],
                title="Receita vs Despesa",
                barmode="group",
                color_discrete_sequence=["#2ecc71", "#e74c3c"]
            )
            fig_rec_des.update_layout(plot_bgcolor="white", paper_bgcolor="white")

            return (
                f"R$ {receita_total:,.0f}",
                f"R$ {despesa_total:,.0f}",
                f"R$ {lucro_bruto:,.0f}",
                f"{margem_lucro:.1f}%",
                fig_fluxo,
                fig_rec_des
            )

        except Exception:
            return ("R$ 0", "R$ 0", "R$ 0", "0%", {"data": []}, {"data": []})
