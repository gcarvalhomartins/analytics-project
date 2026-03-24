"""
Dashboard Router - Descoberta e Registro Dinâmico de Dashboards

Este módulo é responsável por:
1. Descobrir automaticamente pastas dentro de dashboards/
2. Validar que cada pasta contém app.py e config.yaml
3. Importar dinamicamente o layout e callbacks de cada dashboard
4. Registrar cada dashboard como sub-aplicação com rota própria

Comportamento:
- Pastas que começam com _ ou . são ignoradas
- Cada dashboard precisa exportar: layout e register_callbacks(app)
- Erros de import são tratados e logados, sem afectar outros dashboards
"""
import importlib.util
import logging
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from werkzeug.middleware.dispatcher import DispatcherMiddleware

logger = logging.getLogger(__name__)


class DashboardRouter:
    """Responsável por descobrir e registrar dashboards dinamicamente."""
    
    def __init__(self, dashboards_dir: Optional[Path] = None) -> None:
        self.dashboards_dir = dashboards_dir or Path(__file__).parent.parent / "dashboards"
        self.dashboards: Dict[str, Dict[str, Any]] = {}
        self.flask_apps: Dict[str, Any] = {}
    
    def discover_and_register(self, app: Any) -> None:
        """Descobre e registra todos os dashboards válidos."""
        if not self.dashboards_dir.exists():
            logger.warning(f"Diretório de dashboards não encontrado: {self.dashboards_dir}")
            app.index_string = self._create_index_string([])
            return
        
        logger.info(f"Descobrindo dashboards em: {self.dashboards_dir}")
        
        for folder in self.dashboards_dir.iterdir():
            if not folder.is_dir():
                continue
            
            if folder.name.startswith("_") or folder.name.startswith("."):
                logger.debug(f"Ignorando pasta oculta: {folder.name}")
                continue
            
            self._register_dashboard(app, folder)
        
        app.index_string = self._create_index_string(list(self.dashboards.keys()))
    
    def _register_dashboard(self, app: Any, folder: Path) -> None:
        """Registra um único dashboard."""
        name = folder.name
        app_file = folder / "app.py"
        config_file = folder / "config.yaml"
        
        if not app_file.exists():
            logger.warning(f"❌ Dashboard '{name}': app.py não encontrado")
            return
        
        if not config_file.exists():
            logger.warning(f"❌ Dashboard '{name}': config.yaml não encontrado")
            return
        
        try:
            config = self._load_config(config_file)
            
            module = self._import_app_module(app_file)
            
            if not hasattr(module, "layout"):
                raise AttributeError("Módulo não exporta 'layout'")
            
            if not hasattr(module, "register_callbacks"):
                raise AttributeError("Módulo não exporta 'register_callbacks'")
            
            url_base = f"/{name}/"
            
            from dash import Dash
            
            external_stylesheets = [
                "https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css",
                "https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800&display=swap",
                "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css",
            ]
            
            assets_path = folder / "assets"
            
            dash_kwargs = {
                "name": name,
                "server": app.server,
                "url_base_pathname": url_base,
                "suppress_callback_exceptions": True,
                "external_stylesheets": external_stylesheets,
            }
            
            if assets_path.exists():
                dash_kwargs["assets_folder"] = str(assets_path)
            
            sub_app = Dash(**dash_kwargs)
            
            sub_app.layout = module.layout
            module.register_callbacks(sub_app)
            
            self.dashboards[name] = {
                "module": module,
                "config": config,
                "url_base": url_base,
                "sub_app": sub_app,
            }
            
            logger.info(f"✅ Dashboard registrado: /{name}/")
            
        except Exception as e:
            logger.error(f"❌ Erro ao carregar /{name}/: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def _load_config(self, config_file: Path) -> Dict[str, Any]:
        """Carrega configuração YAML do dashboard."""
        with open(config_file, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        
        return config or {}
    
    def _import_app_module(self, app_file: Path):
        """Importa dinamicamente o módulo app.py do dashboard."""
        module_name = f"dashboards.{app_file.parent.name}.app"
        spec = importlib.util.spec_from_file_location(module_name, app_file)
        
        if spec is None or spec.loader is None:
            raise ImportError(f"Não foi possível carregar spec para {app_file}")
        
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        return module
    
    def _create_index_string(self, dashboards: list) -> str:
        """Cria HTML de navegação para os dashboards."""
        nav_items = ""
        for name in dashboards:
            nav_items += f'<li><a href="/{name}/">{name.capitalize()}</a></li>'
        
        return f'''<!DOCTYPE html>
<html>
    <head>
        {{%metas%}}
        <title>Analytics Platform</title>
        {{%favicon%}}
        {{%css%}}
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                margin: 0;
                padding: 0;
                background: #f5f5f5;
            }}
            .navbar {{
                background: #2c3e50;
                padding: 15px 30px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            .navbar h1 {{
                color: white;
                margin: 0;
                font-size: 24px;
                display: inline-block;
            }}
            .navbar ul {{
                list-style: none;
                margin: 0;
                padding: 0;
                display: inline-block;
                float: right;
            }}
            .navbar li {{
                display: inline-block;
                margin-left: 20px;
            }}
            .navbar a {{
                color: #ecf0f1;
                text-decoration: none;
                font-weight: 500;
            }}
            .navbar a:hover {{
                color: #3498db;
            }}
            .dash-footer {{
                display: none;
            }}
        </style>
    </head>
    <body>
        <div class="navbar">
            <h1>Analytics Platform</h1>
            <ul>
                <li><a href="/">Home</a></li>
                {nav_items}
            </ul>
        </div>
        {{%app_entry%}}
        <footer>
            {{%config%}}
            {{%scripts%}}
            {{%renderer%}}
        </footer>
    </body>
</html>'''
