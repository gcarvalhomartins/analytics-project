"""
Dashboard de Vendas

Este dashboard exibe métricas de vendas incluindo:
- Total de vendas por mês
- Ticket médio
- Número de pedidos
- Taxa de conversão
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
        "vendas": [45000, 52000, 48000, 61000, 55000, 67000],
        "pedidos": [120, 145, 138, 178, 162, 195],
        "clientes_novos": [45, 52, 48, 61, 55, 72],
    })


def get_sales_data() -> pd.DataFrame:
    """Obtém dados de vendas (do banco ou mock)."""
    if not DB_CONFIG:
        return get_mock_data()
    
    try:
        from core.db import DatabaseFactory

        if not DatabaseFactory.test_connection(DB_CONFIG):
            return get_mock_data()

        from dashboards.vendas.queries import get_monthly_sales

        engine = DatabaseFactory.get_engine(DB_CONFIG)
        return get_monthly_sales(engine)
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
    html.H1(CONFIG.get("name", "Dashboard de Vendas"), style=STYLES["title"]),
    html.P(CONFIG.get("description", ""), style=STYLES["description"]),
    
    dcc.Interval(
        id="vendas-interval",
        interval=REFRESH_INTERVAL if REFRESH_INTERVAL > 0 else None,
        n_intervals=0,
    ),
    
    html.Div([
        html.Div([
            html.Div([
                html.H3("R$ 0", id="total-vendas", style=STYLES["metricValue"]),
                html.P("Vendas Totais", style=STYLES["metricLabel"])
            ], style=STYLES["metricCard"])
        ], style=STYLES["metricContainer"]),
        
        html.Div([
            html.Div([
                html.H3("R$ 0", id="ticket-medio", style=STYLES["metricValue"]),
                html.P("Ticket Médio", style=STYLES["metricLabel"])
            ], style=STYLES["metricCard"])
        ], style=STYLES["metricContainer"]),
        
        html.Div([
            html.Div([
                html.H3("0", id="total-pedidos", style=STYLES["metricValue"]),
                html.P("Total de Pedidos", style=STYLES["metricLabel"])
            ], style=STYLES["metricCard"])
        ], style=STYLES["metricContainer"]),
        
        html.Div([
            html.Div([
                html.H3("0%", id="taxa-conversao", style=STYLES["metricValue"]),
                html.P("Taxa de Conversão", style=STYLES["metricLabel"])
            ], style=STYLES["metricCard"])
        ], style=STYLES["metricContainer"]),
    ], style=STYLES["metricsRow"]),
    
    html.Div([
        dcc.Graph(id="vendas-grafico")
    ], style=STYLES["chartContainer"]),
    
    html.Div([
        dcc.Graph(id="pedidos-grafico")
    ], style=STYLES["chartContainer"]),
], style=STYLES["container"])


def register_callbacks(app: Dash) -> None:
    """Registra os callbacks do dashboard."""

    @app.callback(
        [Output("total-vendas", "children"),
         Output("ticket-medio", "children"),
         Output("total-pedidos", "children"),
         Output("taxa-conversao", "children"),
         Output("vendas-grafico", "figure"),
         Output("pedidos-grafico", "figure")],
        [Input("vendas-interval", "n_intervals")]
    )
    def update_dashboard(n: int):
        """Atualiza todos os componentes do dashboard."""
        try:
            df = get_sales_data()

            if df.empty:
                return ("R$ 0", "R$ 0", "0", "0%", {"data": []}, {"data": []})

            total_vendas = df["vendas"].sum()
            total_pedidos = df["pedidos"].sum()
            ticket_medio = total_vendas / total_pedidos if total_pedidos > 0 else 0

            clientes_novos = df["clientes_novos"].sum() if "clientes_novos" in df.columns else 0
            taxa_conversao = (clientes_novos / total_pedidos * 100) if total_pedidos > 0 else 0

            fig_vendas = px.bar(
                df,
                x="mes",
                y="vendas",
                title="Vendas por Mês",
                color_discrete_sequence=["#3498db"]
            )
            fig_vendas.update_layout(plot_bgcolor="white", paper_bgcolor="white")

            fig_pedidos = px.line(
                df,
                x="mes",
                y="pedidos",
                title="Pedidos por Mês",
                markers=True,
                color_discrete_sequence=["#2ecc71"]
            )
            fig_pedidos.update_layout(plot_bgcolor="white", paper_bgcolor="white")

            return (
                f"R$ {total_vendas:,.0f}",
                f"R$ {ticket_medio:,.0f}",
                f"{total_pedidos}",
                f"{taxa_conversao:.1f}%",
                fig_vendas,
                fig_pedidos
            )

        except Exception:
            return ("R$ 0", "R$ 0", "0", "0%", {"data": []}, {"data": []})
