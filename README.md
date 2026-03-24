# Analytics Platform

Plataforma de dashboards dinâmicos em Python/Dash com descoberta automática de rotas. O sistema detecta automaticamente novas pastas dentro do diretório `dashboards/` e as expõe como rotas URL acessíveis.

---

## Visão Geral do Projeto

```
analytics-application/
├── main.py                     # Ponto de entrada da aplicação
├── config.py                   # Configurações globais
├── core/                       # Módulos principais
│   ├── router.py              # Sistema de descoberta automática de dashboards
│   ├── db.py                  # Factory de conexões SQLAlchemy
│   └── auth.py                # Middleware de autenticação
├── dashboards/                # Dashboards (cada pasta = uma rota URL)
│   ├── vendas/               # → disponível em /vendas/
│   └── financeiro/           # → disponível em /financeiro/
├── scripts/                   # Utilitários
│   └── new_dashboard.py     # CLI para criar novos dashboards
├── .github/workflows/        # CI/CD
└── nginx.conf, gunicorn.conf.py, Dockerfile  # Configurações de deploy
```

---

## Como o Sistema Funciona

### 1. Ponto de Entrada (`main.py`)

O arquivo `main.py` é o ponto de entrada da aplicação:

```python
# 1. Criação do app Dash principal
app = dash.Dash(__name__, suppress_callback_exceptions=True)

# 2. Inicialização do router
router = DashboardRouter()

# 3. Descoberta e registro automático de dashboards
router.discover_and_register(app)

# 4. Exposição do servidor Flask para Gunicorn
server = app.server
```

**Fluxo de execução:**

1. O app Dash principal é criado
2. O `DashboardRouter` varre o diretório `dashboards/`
3. Para cada pasta válida (com `app.py` + `config.yaml`), cria uma sub-app Dash
4. Cada dashboard fica disponível em `/{nome-da-pasta}/`

### 2. Router de Descoberta (`core/router.py`)

O `DashboardRouter` é o coração do sistema. Ele faz:

1. **Descobre**: Varre o diretório `dashboards/` buscando pastas
2. **Valida**: Verifica se cada pasta tem `app.py` e `config.yaml`
3. **Importa**: Carrega dinamicamente o módulo `app.py` usando `importlib.util`
4. **Registra**: Cria uma sub-app Dash com `url_base_pathname` para cada dashboard
5. **Navegação**: Gera automaticamente a navbar com links para todos os dashboards

**Comportamento:**

- Pastas que começam com `_` ou `.` são ignoradas
- Cada dashboard DEVE exportar: `layout` e `register_callbacks(app)`
- Erros são isolados (um dashboard com erro não afeta os outros)

### 3. Factory de Banco de Dados (`core/db.py`)

O `DatabaseFactory` gerencia conexões de banco de dados:

- **Cache de engines**: Evita reconnections desnecessárias
- **Suporte multi-DB**: PostgreSQL, MySQL, SQLite, MSSQL
- **Variáveis de ambiente**: Resolve `${VAR}` no config.yaml automaticamente
- **Pool de conexões**: `pool_size=5`, `max_overflow=10`, `pool_pre_ping=True`

### 4. Arquitetura de Dashboard

Cada dashboard é uma sub-app Dash independente com sua própria rota:

```
dashboards/
└── nome-dashboard/
    ├── __init__.py           # Obrigatório (pode estar vazio)
    ├── app.py                # Layout + Callbacks (OBRIGATÓRIO)
    ├── config.yaml           # Configurações (OBRIGATÓRIO)
    ├── queries.py            # Queries SQL (OPCIONAL)
    ├── assets/               # Arquivos estáticos (OPCIONAL)
    │   ├── styles.css       # CSS personalizado
    │   └── logo.png        # Logotipos/imagens
    └── requirements.txt     # Dependências específicas (OPCIONAL)
```

---

## Instalação Local

### 1. Clone e Setup

```bash
git clone <seu-repo>
cd analytics-application

# Criar ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Instalar dependências
pip install -r requirements.txt
```

### 2. Configurar Variáveis de Ambiente

```bash
# Copiar template
cp .env.example .env

# Editar com suas configurações
nano .env
```

**Exemplo de `.env`:**

```bash
ENV=development
SECRET_KEY=sua-chave-secreta-aqui

# Banco de dados (opcional - funciona sem banco usando dados mock)
DB_VENDAS_HOST=localhost
DB_VENDAS_PORT=5432
DB_VENDAS_NAME=vendas_db
DB_VENDAS_USER=usuario
DB_VENDAS_PASS=senha
```

### 3. Executar

```bash
# Modo desenvolvimento (com hot-reload automático)
ENV=development python main.py

# Modo produção
python main.py
```

Acesse no navegador:

- http://localhost:8050/ (página inicial com navegação)
- http://localhost:8050/vendas/
- http://localhost:8050/financeiro/

---

## Criando um Novo Dashboard

### Método 1: CLI Automático (Recomendado)

```bash
python scripts/new_dashboard.py nome-do-dashboard --desc "Descrição do dashboard"
```

Isso cria automaticamente:

```
dashboards/nome-do-dashboard/
├── __init__.py
├── app.py           # Template completo com exemplo
├── config.yaml      # Configuração com variáveis de ambiente
└── queries.py       # Template de queries SQL
```

### Método 2: Manual

1. Crie a pasta em `dashboards/seu-dashboard/`
2. Adicione os arquivos obrigatórios (veja próximo tópico)

---

## Estrutura Completa de um Dashboard

### `app.py` (ARQUIVO OBRIGATÓRIO)

Este é o arquivo principal do dashboard. Deve exportar obrigatoriamente:

1. **`layout`**: Componente Dash com a estrutura visual
2. **`register_callbacks(app)`**: Função que registra os callbacks

```python
from pathlib import Path
import pandas as pd
import plotly.express as px
import yaml
from dash import Dash, dcc, html
from dash.dependencies import Input, Output

# 1. Configuração - carrega config.yaml
DASHBOARD_DIR = Path(__file__).parent
with open(DASHBOARD_DIR / "config.yaml") as f:
    CONFIG = yaml.safe_load(f)

DB_CONFIG = CONFIG.get("database", {})
REFRESH_INTERVAL = CONFIG.get("refresh_interval", 0) * 1000

# 2. Funções de dados (do banco ou mock)
def get_data():
    """Retorna dados do banco ou mock"""
    try:
        from core.db import DatabaseFactory

        # Testa conexão com banco
        if not DatabaseFactory.test_connection(DB_CONFIG):
            return get_mock_data()

        # Se conectou, usa queries
        from dashboards.meu_dashboard.queries import get_data_query
        engine = DatabaseFactory.get_engine(DB_CONFIG)
        return get_data_query(engine)
    except Exception:
        return get_mock_data()

def get_mock_data():
    """Dados mockados para desenvolvimento sem banco"""
    return pd.DataFrame({
        "categoria": ["A", "B", "C"],
        "valor": [100, 200, 150],
    })

# 3. Estilos CSS (inline para simplicidade)
STYLES = {
    "container": {"padding": "20px", "maxWidth": "1200px", "margin": "0 auto"},
    "title": {"textAlign": "center", "marginBottom": "20px"},
}

# 4. Layout (OBRIGATÓRIO)
layout = html.Div([
    html.H1(CONFIG["name"], style=STYLES["title"]),
    html.P(CONFIG.get("description", "")),

    # Interval para auto-refresh (opcional)
    dcc.Interval(
        id="meu-dashboard-interval",
        interval=REFRESH_INTERVAL if REFRESH_INTERVAL > 0 else None,
        n_intervals=0,
    ),

    # Gráfico
    dcc.Graph(id="meu-grafico"),

], style=STYLES["container"])

# 5. Callbacks (OBRIGATÓRIO)
def register_callbacks(app: Dash):
    @app.callback(
        Output("meu-grafico", "figure"),
        [Input("meu-dashboard-interval", "n_intervals")]
    )
    def update_graph(n):
        df = get_data()
        fig = px.bar(df, x="categoria", y="valor", title="Meu Gráfico")
        fig.update_layout(plot_bgcolor="white", paper_bgcolor="white")
        return fig
```

### `config.yaml` (ARQUIVO OBRIGATÓRIO)

Configurações do dashboard:

```yaml
name: "Nome do Dashboard"
description: "Descrição breve do dashboard"

# Configuração do banco (opcional - funciona sem)
database:
  type: postgresql # postgresql | mysql | sqlite | mssql
  host: ${DB_NOME_HOST} # Variável de ambiente (formato ${VAR})
  port: 5432
  name: ${DB_NOME_NAME}
  user: ${DB_NOME_USER}
  password: ${DB_NOME_PASS}

# Configurações do dashboard
auth_required: false # Requer autenticação (futuro)
refresh_interval: 60 # Auto-refresh em segundos (0 = desativado)
theme: "light" # light | dark
```

---

## Adicionando Assets (CSS, Imagens, Logos)

### Estrutura de Assets

Cada dashboard pode ter uma pasta `assets/` com arquivos estáticos (CSS, imagens, logos):

```
dashboards/vendas/
├── app.py
├── config.yaml
├── queries.py
└── assets/
    ├── styles.css          # CSS personalizado do dashboard
    ├── logo.png            # Logo do cliente/empresa
    ├── logo.svg           # Logo vetorial
    ├── background.jpg     # Imagem de fundo
    └── favicon.ico        # Favicon específico
```

### Usando CSS Personalizado

**1. Crie o arquivo CSS:**

```css
/* dashboards/vendas/assets/styles.css */

/* Header personalizado */
.vendas-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 30px;
  border-radius: 10px;
  color: white;
  margin-bottom: 20px;
}

/* Cards de métricas */
.vendas-metric-card {
  background: #ffffff;
  border-left: 4px solid #667eea;
  padding: 20px;
  margin: 10px 0;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  border-radius: 8px;
}

.vendas-metric-value {
  font-size: 28px;
  font-weight: bold;
  color: #2c3e50;
  margin: 0;
}

.vendas-metric-label {
  color: #7f8c8d;
  font-size: 14px;
  margin-top: 5px;
}

/* Gráficos */
.vendas-chart {
  border: 1px solid #e0e0e0;
  border-radius: 10px;
  padding: 15px;
  background: white;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

/* Container do dashboard */
.vendas-container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 20px;
}
```

**2. Carregue o CSS no `app.py`:**

O Dash automaticamente carrega todos os arquivos CSS da pasta `assets/`:

```python
from pathlib import Path

DASHBOARD_DIR = Path(__file__).parent
ASSETS_DIR = DASHBOARD_DIR / "assets"

# O Dash automaticamente serve:
# /assets/styles.css → dashboards/vendas/assets/styles.css
```

**3. Use as classes no layout:**

```python
layout = html.Div([
    # Header com logo
    html.Div([
        html.Img(
            src="/assets/logo.png",  # Caminho direto ou use get_asset_url()
            style={"height": "50px"}
        ),
        html.H1("Dashboard de Vendas", style={"marginLeft": "20px"})
    ], className="vendas-header"),

    # Métricas em row
    html.Div([
        html.Div([
            html.H3("R$ 50.000", className="vendas-metric-value"),
            html.P("Vendas Totais", className="vendas-metric-label")
        ], className="vendas-metric-card"),

        html.Div([
            html.H3("R$ 250", className="vendas-metric-value"),
            html.P("Ticket Médio", className="vendas-metric-label")
        ], className="vendas-metric-card"),

        html.Div([
            html.H3("150", className="vendas-metric-value"),
            html.P("Pedidos", className="vendas-metric-label")
        ], className="vendas-metric-card"),
    ], style={"display": "flex", "gap": "20px", "flexWrap": "wrap"}),

    # Gráfico
    dcc.Graph(
        id="vendas-grafico",
        className="vendas-chart"
    ),

], className="vendas-container")
```

### Adicionando Logos e Imagens

**1. Coloque a imagem em `assets/`:**

```
dashboards/vendas/assets/
├── styles.css
└── logo.png
```

**2. Use no layout com caminho correto:**

```python
from pathlib import Path

DASHBOARD_DIR = Path(__file__).parent

layout = html.Div([
    # Logo com caminho relativo
    html.Div([
        html.Img(
            src=str((DASHBOARD_DIR / "assets" / "logo.png").relative_to(Path.cwd()))
                .replace("\\", "/"),
            style={"height": "60px"}
        ),
    ]),

    # Imagem de fundo em div
    html.Div(
        html.H2("Conteúdo Principal"),
        style={
            "backgroundImage": "url(/assets/background.jpg)",
            "backgroundSize": "cover",
            "backgroundPosition": "center",
            "padding": "100px",
            "borderRadius": "10px",
            "color": "white",
            "textAlign": "center"
        }
    ),

    # Gallery de imagens
    html.Div([
        html.Img(
            src=str((DASHBOARD_DIR / "assets" / f"cliente_{i}.png").relative_to(Path.cwd()))
                .replace("\\", "/"),
            style={"width": "100px", "margin": "10px"}
        )
        for i in range(1, 4)
    ], style={"display": "flex", "flexWrap": "wrap"}),
])
```

### Exemplo Completo: Dashboard com Assets

```python
# dashboards/meu-dashboard/app.py
from pathlib import Path
from dash import Dash, dcc, html
from dash.dependencies import Input, Output
import plotly.express as px

DASHBOARD_DIR = Path(__file__).parent

# O Dash automaticamente carrega CSS de assets/
# Use className="minha-classe" no layout

# 1. Configuração
import yaml
with open(DASHBOARD_DIR / "config.yaml") as f:
    CONFIG = yaml.safe_load(f)

# 2. Estilos
STYLES = {
    "header": {
        "background": "linear-gradient(135deg, #1e3c72 0%, #2a5298 100%)",
        "color": "white",
        "padding": "30px",
        "borderRadius": "10px",
        "marginBottom": "30px",
    },
    "container": {
        "maxWidth": "1200px",
        "margin": "0 auto",
        "padding": "20px",
    },
    "metricCard": {
        "background": "white",
        "padding": "25px",
        "borderRadius": "12px",
        "boxShadow": "0 4px 6px rgba(0,0,0,0.1)",
        "textAlign": "center",
    },
}

# 3. Layout
layout = html.Div([
    # Header com logo
    html.Div([
        html.Div([
            html.Img(
                src=str((DASHBOARD_DIR / "assets" / "logo.png").relative_to(Path.cwd()))
                    .replace("\\", "/"),
                style={"height": "50px"}
            ),
        ]),
        html.H1(CONFIG.get("name", "Meu Dashboard"), style={"marginTop": "10px"}),
        html.P(CONFIG.get("description", ""), style={"opacity": 0.8}),
    ], style=STYLES["header"]),

    # Container principal
    html.Div([
        # Métricas
        html.Div([
            html.Div([
                html.H3("R$ 100.000", style={"color": "#2ecc71", "margin": "0"}),
                html.P("Receita Total", style={"color": "#7f8c8d", "margin": "5px 0 0 0"})
            ], style=STYLES["metricCard"]),

            html.Div([
                html.H3("450", style={"color": "#3498db", "margin": "0"}),
                html.P("Pedidos", style={"color": "#7f8c8d", "margin": "5px 0 0 0"})
            ], style=STYLES["metricCard"]),

            html.Div([
                html.H3("12.5%", style={"color": "#9b59b6", "margin": "0"}),
                html.P("Crescimento", style={"color": "#7f8c8d", "margin": "5px 0 0 0"})
            ], style=STYLES["metricCard"]),
        ], style={"display": "grid", "gridTemplateColumns": "repeat(3, 1fr)", "gap": "20px", "marginBottom": "30px"}),

        # Gráfico
        dcc.Graph(id="meu-grafico"),

    ], style=STYLES["container"]),

], style={"background": "#f5f6fa", "minHeight": "100vh"})

# 4. Callbacks
def register_callbacks(app):
    @app.callback(
        Output("meu-grafico", "figure"),
        [Input("interval", "n_intervals")]
    )
    def update(n):
        import pandas as pd
        df = pd.DataFrame({
            "mes": ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun"],
            "vendas": [15000, 18000, 16000, 22000, 19000, 25000]
        })

        fig = px.bar(
            df,
            x="mes",
            y="vendas",
            title="Vendas por Mês",
            color_discrete_sequence=["#3498db"]
        )
        fig.update_layout(
            plot_bgcolor="white",
            paper_bgcolor="white",
            font=dict(family="Arial, sans-serif"),
        )
        return fig
```

```css
/* dashboards/meu-dashboard/assets/styles.css */

/* Você pode sobrescrever estilos aqui se necessário */
.dash-graph {
  border-radius: 10px;
  overflow: hidden;
}
```

---

## Variáveis de Ambiente

### Configurações Globais

| Variável                   | Descrição                                   | Padrão          |
| -------------------------- | ------------------------------------------- | --------------- |
| `ENV`                      | Ambiente (development/production)           | production      |
| `SECRET_KEY`               | Chave secreta para sessões                  | valor aleatório |
| `HOST`                     | Host do servidor                            | 0.0.0.0         |
| `PORT`                     | Porta do servidor                           | 8050            |
| `LOG_LEVEL`                | Nível de logs (DEBUG, INFO, WARNING, ERROR) | INFO            |
| `DEFAULT_REFRESH_INTERVAL` | Intervalo de refresh padrão (segundos)      | 0               |

### Configurações por Dashboard

Para cada dashboard, defina variáveis no formato `DB_{NOME}_{CAMPO}`:

```bash
# Dashboard de vendas
DB_VENDAS_HOST=localhost
DB_VENDAS_PORT=5432
DB_VENDAS_NAME=vendas
DB_VENDAS_USER=usuario
DB_VENDAS_PASS=senha

# Dashboard financeiro
DB_FINANCEIRO_HOST=localhost
DB_FINANCEIRO_PORT=5432
DB_FINANCEIRO_NAME=financeiro
DB_FINANCEIRO_USER=usuario
DB_FINANCEIRO_PASS=senha
```

No `config.yaml`, use a sintaxe `${VARIAVEL}`:

```yaml
database:
  host: ${DB_VENDAS_HOST}
  name: ${DB_VENDAS_NAME}
  user: ${DB_VENDAS_USER}
  password: ${DB_VENDAS_PASS}
```

O sistema automaticamente substitui `${DB_VENDAS_HOST}` pelo valor da variável de ambiente `DB_VENDAS_HOST`.

---

## Como Adicionar Queries SQL

O arquivo `queries.py` contém funções que retornam DataFrames:

```python
# dashboards/vendas/queries.py
from typing import Union
from sqlalchemy import Engine, text
import pandas as pd


def get_monthly_sales(engine: Engine) -> pd.DataFrame:
    """Retorna vendas mensais.

    Args:
        engine: Engine SQLAlchemy do banco de dados

    Returns:
        DataFrame com colunas: mes, vendas, pedidos
    """
    query = text("""
        SELECT
            TO_CHAR(data_venda, 'YYYY-MM') as mes,
            TO_CHAR(data_venda, 'Mon') as mes_nome,
            SUM(valor_total) as vendas,
            COUNT(DISTINCT id_pedido) as pedidos
        FROM vendas
        WHERE data_venda >= CURRENT_DATE - INTERVAL '12 months'
        GROUP BY TO_CHAR(data_venda, 'YYYY-MM'), TO_CHAR(data_venda, 'Mon')
        ORDER BY mes
    """)

    with engine.connect() as conn:
        return pd.read_sql(query, conn)


def get_top_products(engine: Engine, limit: int = 10) -> pd.DataFrame:
    """Retorna produtos mais vendidos.

    Args:
        engine: Engine SQLAlchemy
        limit: Número de produtos a retornar

    Returns:
        DataFrame com colunas: produto, quantidade, receita
    """
    query = text("""
        SELECT
            p.nome as produto,
            SUM(iv.quantidade) as quantidade,
            SUM(iv.quantidade * iv.preco_unitario) as receita
        FROM itens_venda iv
        JOIN produtos p ON iv.id_produto = p.id
        JOIN vendas v ON iv.id_venda = v.id
        WHERE v.data_venda >= CURRENT_DATE - INTERVAL '30 days'
        GROUP BY p.id, p.nome
        ORDER BY receita DESC
        LIMIT :limit
    """)

    with engine.connect() as conn:
        return pd.read_sql(query, conn, params={"limit": limit})


def get_sales_by_category(engine: Engine) -> pd.DataFrame:
    """Retorna vendas por categoria."""
    query = text("""
        SELECT
            c.nome as categoria,
            SUM(iv.quantidade * iv.preco_unitario) as vendas
        FROM itens_venda iv
        JOIN produtos p ON iv.id_produto = p.id
        JOIN categorias c ON p.id_categoria = c.id
        GROUP BY c.id, c.nome
        ORDER BY vendas DESC
    """)

    with engine.connect() as conn:
        return pd.read_sql(query, conn)
```

Use no `app.py`:

```python
from core.db import DatabaseFactory
from dashboards.vendas.queries import get_monthly_sales, get_top_products

def get_sales_data():
    # Obtém engine baseado no config.yaml
    engine = DatabaseFactory.get_engine(DB_CONFIG)

    # Chama a query
    return get_monthly_sales(engine)

def get_products_data(limit=5):
    engine = DatabaseFactory.get_engine(DB_CONFIG)
    return get_top_products(engine, limit=limit)
```

---

## Exemplos de Componentes Dash

### Cards de Métricas

```python
# Layout
html.Div([
    html.Div([
        html.H3("R$ 50.000", style={
            "fontSize": "32px",
            "margin": "0",
            "color": "#2c3e50"
        }),
        html.P("Vendas Totais", style={
            "color": "#7f8c8d",
            "margin": "5px 0 0 0",
            "fontSize": "14px"
        })
    ], style={
        "background": "#f8f9fa",
        "padding": "20px",
        "borderRadius": "8px",
        "textAlign": "center",
        "boxShadow": "0 2px 4px rgba(0,0,0,0.1)"
    })
])
```

### Gráficos com Plotly Express

```python
import plotly.express as px

# Gráfico de barras
fig_bar = px.bar(
    df,
    x="categoria",
    y="valor",
    title="Vendas por Categoria",
    color="valor",
    color_continuous_scale="Blues",
    text="valor"
)
fig_bar.update_traces(textposition="outside")
fig_bar.update_layout(
    plot_bgcolor="white",
    paper_bgcolor="white",
    font=dict(family="Arial", size=12),
)

# Gráfico de linha
fig_line = px.line(
    df,
    x="data",
    y="valor",
    title="Evolução Temporal",
    markers=True,
    line_shape="spline"
)

# Gráfico de pizza
fig_pie = px.pie(
    df,
    values="valor",
    names="categoria",
    title="Distribuição",
    hole=0.4  # Gráfico de rosca
)

# Scatter plot
fig_scatter = px.scatter(
    df,
    x="valor",
    y="quantidade",
    color="categoria",
    size="valor",
    title="Correlação",
    hover_data=["produto"]
)
```

### Tabelas Interativas

```python
from dash import dash_table

dash_table.DataTable(
    data=df.to_dict("records"),
    columns=[
        {"name": "Produto", "id": "produto"},
        {"name": "Quantidade", "id": "quantidade", "type": "numeric"},
        {"name": "Receita", "id": "receita", "type": "numeric", "format": {"locale": {"symbol": ["R$", ""]}, "specifier": "$.2f"}},
    ],
    page_size=10,
    page_action="native",
    sort_action="native",
    filter_action="native",
    style_table={"overflowX": "auto"},
    style_cell={
        "textAlign": "left",
        "padding": "10px",
    },
    style_header={
        "backgroundColor": "#f8f9fa",
        "fontWeight": "bold",
        "border": "1px solid #dee2e6",
    },
    style_data={
        "border": "1px solid #dee2e6",
    },
)
```

### Dropdowns e Filtros

```python
html.Div([
    # Dropdown simples
    html.Label("Selecione o período:"),
    dcc.Dropdown(
        id="periodo-dropdown",
        options=[
            {"label": "Últimos 7 dias", "value": "7"},
            {"label": "Últimos 30 dias", "value": "30"},
            {"label": "Últimos 90 dias", "value": "90"},
            {"label": "Último ano", "value": "365"},
        ],
        value="30",
        clearable=False,
    ),

    # Checklist multi-select
    html.Label("Categorias:"),
    dcc.Checklist(
        id="categoria-checklist",
        options=[
            {"label": " Eletrônicos", "value": "eletronicos"},
            {"label": " Vestuário", "value": "vestuario"},
            {"label": " Alimentos", "value": "alimentos"},
        ],
        value=["eletronicos", "vestuario"],
        inline=True,
    ),

    # Range Slider
    html.Label("Faixa de preço:"),
    dcc.RangeSlider(
        id="preco-slider",
        min=0,
        max=10000,
        step=100,
        value=[0, 5000],
        marks={0: "R$0", 5000: "R$5k", 10000: "R$10k"},
    ),

    # Date Picker
    html.Label("Período:"),
    dcc.DatePickerRange(
        id="date-picker",
        start_date="2024-01-01",
        end_date="2024-12-31",
    ),
])
```

### Interval para Auto-Refresh

```python
# Atualiza automaticamente a cada 60 segundos
dcc.Interval(
    id="auto-refresh",
    interval=60 * 1000,  # 60 segundos em milissegundos
    n_intervals=0,
)

# Callback
@app.callback(
    Output("grafico", "figure"),
    [Input("auto-refresh", "n_intervals")]
)
def update_graph(n):
    # Busca dados atualizados
    return grafico
```

---

## Modo Desenvolvimento vs Produção

### Desenvolvimento

```bash
ENV=development python main.py
```

- Hot-reload ativado
- Servidor reinicia automaticamente ao modificar arquivos
- Logs mais detalhados
- Mais informações de erro no navegador

### Produção

```bash
# Com Gunicorn (recomendado)
gunicorn main:server -c gunicorn.conf.py

# Ou com Python direto
python main.py
```

- Debug desligado
- 4 workers (Gunicorn)
- Logs otimizados
- Performance superior

---

## Deploy

Consulte [DEPLOY.md](DEPLOY.md) para instruções detalhadas de deploy no servidor Hostinger VPS.

### Quick Deploy (GitHub Actions)

1. Configure as secrets no GitHub:
   - `HOSTINGER_HOST` - IP do servidor
   - `HOSTINGER_USER` - usuário SSH
   - `HOSTINGER_SSH_KEY` - chave SSH privada

2. Faça push para branch `main`

3. O CI/CD automaticamente:
   - Roda testes (flake8)
   - Faz deploy via SSH
   - Reinicia o serviço
   - Comenta no commit com o status

---

## Troubleshooting

### Dashboard não aparece

1. Verifique se a pasta tem `app.py` e `config.yaml`
2. Execute com `ENV=development python main.py` e veja os logs
3. Verifique se não há erros de importação

### Erro de banco de dados

1. Configure as variáveis de ambiente no `.env`
2. O sistema usa dados mock se o banco não conectar
3. Verifique a string de conexão no config.yaml

### Assets (CSS/Imagens) não carregam

1. Verifique se a pasta `assets/` existe dentro do dashboard
2. Use caminhos relativos corretos no src
3. Limpe o cache do navegador (Ctrl+Shift+R)

### Erro de importação

```bash
# Recrie o ambiente virtual
rm -rf venv
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Porta já em uso

```bash
# Encontre o processo usando a porta
lsof -i :8050
# ou
netstat -tulpn | grep 8050

# Mate o processo
kill -9 <PID>
```

---

## Tech Stack

| Camada         | Tecnologia                                        |
| -------------- | ------------------------------------------------- |
| Dashboards     | Python 3.11+, Dash 2.x, Plotly                    |
| Servidor       | Flask 3.x + Gunicorn 23.x                         |
| Proxy Reverso  | Nginx                                             |
| Banco de Dados | SQLAlchemy 2.x (PostgreSQL, MySQL, SQLite, MSSQL) |
| CI/CD          | GitHub Actions                                    |
| Deploy         | Hostinger VPS (Ubuntu 22.04)                      |

---
# analytics-project
