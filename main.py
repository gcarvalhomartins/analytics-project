"""
Analytics Platform - Main Entry Point

Sistema de dashboards dinâmicos que detecta automaticamente
novas pastas em dashboards/ e as expõe como rotas URL.
"""
import logging
from pathlib import Path

import dash
from dotenv import load_dotenv

from core.router import DashboardRouter

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

ENV = Path(__file__).parent / ".env"
DEBUG = ENV.exists() and load_dotenv(ENV, override=True) or False

app = dash.Dash(
    __name__,
    suppress_callback_exceptions=True,
    update_title=None,
)

router = DashboardRouter()
router.discover_and_register(app)

if not app.layout:
    from dash import html, dcc
    app.layout = html.Div([
        dcc.Location(id="url", refresh=True),
        html.Div(id="redirect")
    ])
    
    from dash.dependencies import Input, Output
    @app.callback(
        Output("redirect", "children"),
        [Input("url", "pathname")]
    )
    def redirect_to_dashboard(pathname):
        if pathname == "/" and router.dashboards:
            first_dashboard = list(router.dashboards.keys())[0]
            return dcc.Location(pathname=f"/{first_dashboard}/", id="redirect-url")
        return None

server = app.server

if __name__ == "__main__":
    debug_mode = DEBUG
    logger.info("=" * 60)
    logger.info("Analytics Platform - Servidor iniciado")
    logger.info(f"Modo debug: {debug_mode}")
    logger.info(f"Dashboards registrados: {len(router.dashboards)}")
    for name, route in router.dashboards.items():
        logger.info(f"  → /{name}/")
    logger.info("=" * 60)
    
    app.run_server(
        host="0.0.0.0",
        port=8050,
        debug=debug_mode,
        use_reloader=debug_mode,
    )
