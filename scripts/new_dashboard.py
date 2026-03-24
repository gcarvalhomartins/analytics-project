#!/usr/bin/env python3
"""
Script CLI para criar novos dashboards automaticamente.

Usage:
    python scripts/new_dashboard.py nome-do-dashboard
    python scripts/new_dashboard.py nome-do-dashboard --desc "Descrição do dashboard"
"""
import argparse
import sys
from pathlib import Path


DASHBOARDS_DIR = Path(__file__).parent.parent / "dashboards"


def create_dashboard(name: str, description: str = "") -> None:
    """Cria a estrutura de um novo dashboard.
    
    Args:
        name: Nome do dashboard (usado como nome da pasta)
        description: Descrição breve do dashboard
    """
    if not name.replace("-", "").replace("_", "").isalnum():
        print(f"❌ Erro: Nome inválido '{name}'. Use apenas letras, números, - e _")
        sys.exit(1)
    
    sanitized_name = name.lower().replace(" ", "-")
    dashboard_dir = DASHBOARDS_DIR / sanitized_name
    
    if dashboard_dir.exists():
        print(f"❌ Erro: Dashboard '{sanitized_name}' já existe")
        sys.exit(1)
    
    dashboard_dir.mkdir(parents=True)
    
    (dashboard_dir / "__init__.py").write_text(
        f'"""{sanitized_name} dashboard package."""\n'
    )
    
    config_content = f'''name: "{name.replace("-", " ").title()}"
description: "{description or "Dashboard de análise"}"
database:
  type: postgresql
  host: ${{DB_{sanitized_name.upper()}_HOST}}
  port: 5432
  name: ${{DB_{sanitized_name.upper()}_NAME}}
  user: ${{DB_{sanitized_name.upper()}_USER}}
  password: ${{DB_{sanitized_name.upper()}_PASS}}
auth_required: false
refresh_interval: 60
theme: "light"
'''
    (dashboard_dir / "config.yaml").write_text(config_content)
    
    app_content = f'''\"\"\"{name.replace("-", " ").title()} Dashboard

Este dashboard exibe métricas de {name}.
\"\"\"
from pathlib import Path

import pandas as pd
import plotly.express as px
import yaml
from dash import Dash, dcc, html
from dash.dependencies import Input, Output

DASHBOARD_DIR = Path(__file__).parent

with open(DASHBOARD_DIR / "config.yaml", "r") as f:
    CONFIG = yaml.safe_load(f)

DB_CONFIG = CONFIG.get("database", {{}})
REFRESH_INTERVAL = CONFIG.get("refresh_interval", 0) * 1000


def get_mock_data() -> pd.DataFrame:
    \"\"\"Retorna dados mockados para desenvolvimento.\"\"\"
    return pd.DataFrame({{
        "categoria": ["A", "B", "C", "D", "E"],
        "valor": [100, 200, 150, 300, 250],
    }})


def get_data() -> pd.DataFrame:
    \"\"\"Obtém dados (do banco ou mock).\"\"\"
    try:
        from core.db import DatabaseFactory
        
        if not DatabaseFactory.test_connection(DB_CONFIG):
            return get_mock_data()
        
        from dashboards.{sanitized_name}.queries import get_data_query
        
        engine = DatabaseFactory.get_engine(DB_CONFIG)
        return get_data_query(engine)
    except Exception:
        return get_mock_data()


STYLES = {{
    "container": {{"padding": "20px", "maxWidth": "1200px", "margin": "0 auto"}},
    "title": {{"textAlign": "center", "marginBottom": "20px", "color": "#2c3e50"}},
    "description": {{"textAlign": "center", "color": "#666", "marginBottom": "30px"}},
    "chartContainer": {{"margin": "20px 0", "padding": "10px"}},
}}

layout = html.Div([
    html.H1(CONFIG.get("name", "Dashboard"), style=STYLES["title"]),
    html.P(CONFIG.get("description", ""), style=STYLES["description"]),
    
    dcc.Interval(
        id="{sanitized_name}-interval",
        interval=REFRESH_INTERVAL if REFRESH_INTERVAL > 0 else None,
        n_intervals=0,
    ),
    
    html.Div([
        dcc.Graph(id="{sanitized_name}-grafico")
    ], style=STYLES["chartContainer"]),
    
], style=STYLES["container"])


def register_callbacks(app: Dash) -> None:
    \"\"\"Registra os callbacks do dashboard.\"\"\"
    
    @app.callback(
        Output("{sanitized_name}-grafico", "figure"),
        [Input("{sanitized_name}-interval", "n_intervals")]
    )
    def update_dashboard(n: int):
        \"\"\"Atualiza o dashboard.\"\"\"
        try:
            df = get_data()
            
            if df.empty:
                return px.bar(title="Sem dados disponíveis")
            
            fig = px.bar(
                df,
                x=df.columns[0],
                y=df.columns[1],
                title="{name.replace('-', ' ').title()}",
            )
            fig.update_layout(plot_bgcolor="white", paper_bgcolor="white")
            
            return fig
            
        except Exception as e:
            return px.bar(title=f"Erro: {{str(e)}}")
'''
    (dashboard_dir / "app.py").write_text(app_content)
    
    queries_content = f'''"""Queries SQL para o dashboard {name}."""
from typing import Any, Union

import pandas as pd
from sqlalchemy import Engine, text


def get_data_query(engine: Union[Engine, Any]) -> pd.DataFrame:
    """Retorna dados do dashboard.
    
    Args:
        engine: Engine SQLAlchemy do banco de dados
        
    Returns:
        DataFrame com os dados
    """
    query = text("""
        SELECT 
            categoria,
            valor
        FROM tabela_exemplo
        ORDER BY valor DESC
    """)
    
    try:
        with engine.connect() as conn:
            df = pd.read_sql(query, conn)
        return df
    except Exception:
        return pd.DataFrame()
'''
    (dashboard_dir / "queries.py").write_text(queries_content)
    
    print(f"✅ Dashboard '{sanitized_name}' criado com sucesso!")
    print(f"   Localização: {dashboard_dir}")
    print()
    print("📋 Próximos passos:")
    print(f"   1. Configure as variáveis de ambiente no arquivo .env:")
    print(f"      DB_{sanitized_name.upper()}_HOST=localhost")
    print(f"      DB_{sanitized_name.upper()}_NAME=meubanco")
    print(f"      DB_{sanitized_name.upper()}_USER=usuario")
    print(f"      DB_{sanitized_name.upper()}_PASS=senha")
    print(f"   2. Customize o arquivo {dashboard_dir / 'app.py'}")
    print(f"   3. Customize o arquivo {dashboard_dir / 'queries.py'}")
    print(f"   4. Execute: python main.py")
    print()
    print("💡 Para adicionar assets (CSS, logos), crie a pasta:")
    print(f"   {dashboard_dir / 'assets'}/")


def main() -> None:
    """Função principal do script."""
    parser = argparse.ArgumentParser(
        description="Cria um novo dashboard automaticamente",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "name",
        help="Nome do dashboard (ex: vendas, financeiro)",
    )
    parser.add_argument(
        "--desc",
        "--description",
        dest="description",
        default="",
        help="Descrição breve do dashboard",
    )
    
    args = parser.parse_args()
    
    create_dashboard(args.name, args.description)


if __name__ == "__main__":
    main()
