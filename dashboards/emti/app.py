"""
PROGRAMA FOMENTO EMTI - Dashboard de Monitoramento

Dashboard de alertas da Secretaria de Estado de Educação e Desporto Escolar.
Adaptado para Analytics Platform.
"""
from pathlib import Path

import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import yaml
from dash import Dash, dcc, html, Input, Output, State
from dash.dependencies import ClientsideFunction

DASHBOARD_DIR = Path(__file__).parent

with open(DASHBOARD_DIR / "config.yaml", "r") as f:
    CONFIG = yaml.safe_load(f)

DB_CONFIG = CONFIG.get("database", {})
REFRESH_INTERVAL = CONFIG.get("refresh_interval", 0) * 1000


CATEGORIAS = {
    'Categoria 1 - Material Pedagógico e Didático': [
        'principal_necessidade_escolar_material_tempo_integral',
        'nome_item_livro_didatico_complementar',
        'quantidade_item_livro_didatico_complementar',
        'nome_item_acervo_bibliografico',
        'quantidade_item_acervo_bibliografico',
        'nome_item_material_laboratorio',
        'quantidade_item_material_laboratorio',
        'nome_item_kit_robotica_tecnologia',
        'quantidade_item_kit_robotica_tecnologia',
        'nome_item_equipamento_esportivo',
        'quantidade_item_equipamento_esportivo',
        'nome_item_equipamento_cultural',
        'quantidade_item_equipamento_cultural',
        'nome_item_material_consumo',
        'quantidade_item_material_consumo',
    ],
    'Categoria 2 - Manutenção Predial': [
        'principais_necessidades_manutencao_predial',
        'descricao_manutencao_telhado',
        'quantidade_manutencao_telhado',
        'descricao_manutencao_eletrica',
        'quantidade_manutencao_eletrica',
        'descricao_manutencao_hidraulica',
        'quantidade_manutencao_hidraulica',
        'descricao_manutencao_pintura',
        'quantidade_manutencao_pintura',
        'descricao_manutencao_piso',
        'quantidade_manutencao_piso',
    ],
    'Categoria 3 - Construção, Reforma e Ampliação': [
        'tipo_intervencao_estrutural_escola_necessita',
        'descricao_intervencao_construcao_nova_areas',
        'quantidade_intervencao_construcao_nova_areas',
        'descricao_intervencao_reforma_ambientes_existentes',
        'quantidade_intervencao_reforma_ambientes_existentes',
    ],
    'Categoria 4 - Equipamentos e Mobiliário Escolar': [
        'principal_necessidade_mobiliario_escolar',
        'descricao_mobiliario_sala_aula',
        'quantidade_mobiliario_sala_aula',
        'principal_necessidade_equipamentos_cozinha',
        'descricao_cozinha_fogao',
        'quantidade_cozinha_fogao',
    ],
    'Categoria 5 - Material de Limpeza, Expediente e Utensílios': [
        'principal_necessidade_material_limpeza_expediente',
        'descricao_item_limpeza_produtos',
        'quantidade_limpeza_produtos',
    ]
}

ORDEM_EXPORTACAO = [
    'sasiAPIId', 'generatedAt', 'channel', 'recado',
    'nome_diretor', 'contato_diretor', 'municipios', 'nome_escola', 'email'
]

PRINCIPAL_COLS = [
    'principal_necessidade_mobiliario_escolar',
    'principais_necessidades_manutencao_predial',
    'principal_necessidade_equipamentos_cozinha',
    'principal_necessidade_material_limpeza_expediente',
    'principal_necessidade_escolar_material_tempo_integral'
]

REQUIRED_COLS = ['generatedAt', 'ano', 'mes', 'dia', 'data_str', 'mes_ano_str', 'nome_escola', 'lat', 'lon'] + PRINCIPAL_COLS


def load_data():
    """Carrega dados do CSV via DatabaseFactory."""
    try:
        from core.db import DatabaseFactory

        if not DB_CONFIG:
            return pd.DataFrame(columns=REQUIRED_COLS)

        if not DatabaseFactory.test_connection(DB_CONFIG):
            return pd.DataFrame(columns=REQUIRED_COLS)

        df = DatabaseFactory.get_data_source(DB_CONFIG)

        if df.empty:
            return pd.DataFrame(columns=REQUIRED_COLS)

        todas_colunas_necessarias = set(ORDEM_EXPORTACAO) | set(REQUIRED_COLS)
        for colunas_cat in CATEGORIAS.values():
            todas_colunas_necessarias.update(colunas_cat)

        colunas_faltantes = [col for col in todas_colunas_necessarias if col not in df.columns]

        if colunas_faltantes:
            df_missing = pd.DataFrame('Não Informado', index=df.index, columns=colunas_faltantes)
            df = pd.concat([df, df_missing], axis=1)

        df = df.copy()

        df['data_completa'] = pd.to_datetime(df['generatedAt'], errors='coerce')
        df = df.dropna(subset=['data_completa'])
        df['ano'] = df['data_completa'].dt.year
        df['mes'] = df['data_completa'].dt.month
        df['dia'] = df['data_completa'].dt.day
        df['data_str'] = df['data_completa'].dt.date
        df['mes_ano_str'] = df['data_completa'].dt.to_period('M').astype(str)

        if 'lat' in df.columns:
            df['lat'] = df['lat'].astype(str).str.replace(',', '.', regex=False)
            df['lat'] = pd.to_numeric(df['lat'], errors='coerce')

        if 'lon' in df.columns:
            df['lon'] = df['lon'].astype(str).str.replace(',', '.', regex=False)
            df['lon'] = pd.to_numeric(df['lon'], errors='coerce')

        return df
    except Exception as e:
        print(f"Erro ao carregar dados: {e}")
        return pd.DataFrame(columns=REQUIRED_COLS)


df = load_data()


layout = dbc.Container(fluid=True, style={
    'background': 'linear-gradient(to bottom right, #F8FAFC 0%, #F1F5F9 100%)',
    'minHeight': '100vh',
    'padding': '2rem'
}, children=[
    dcc.Download(id="download-excel"),
    dcc.Interval(
        id="emti-interval",
        interval=REFRESH_INTERVAL if REFRESH_INTERVAL > 0 else None,
        n_intervals=0,
    ),

    dbc.Row([
        dbc.Col([
            html.Div([
                html.Div([
                    html.Div([
                        html.H1("PROGRAMA FOMENTO EMTI", style={'fontSize': '2.5rem', 'fontWeight': '700', 'color': 'white', 'marginBottom': '0', 'letterSpacing': '-0.02em'}),
                        html.P("Secretaria de Estado de Educação e Desporto Escolar", style={'fontSize': '1.125rem', 'color': 'rgba(255, 255, 255, 0.8)', 'marginBottom': '0'})
                    ])
                ], style={'display': 'flex', 'alignItems': 'center'})
            ], style={
                'background': 'linear-gradient(135deg, #1E40AF 0%, #1E3A8A 50%, #15803D 100%)',
                'padding': '2rem', 'borderRadius': '1rem', 'marginBottom': '2rem', 'boxShadow': '0 10px 25px rgba(30, 64, 175, 0.3)'
            })
        ], width=12)
    ]),

    dbc.Row([
        dbc.Col(width=3, children=[
            html.Div([
                html.Div([
                    html.I(className="bi bi-funnel-fill", style={'fontSize': '1.5rem', 'color': '#4F46E5', 'marginRight': '0.5rem'}),
                    html.H4("Filtros", style={'fontSize': '1.25rem', 'fontWeight': '700', 'color': '#1E293B', 'marginBottom': '0', 'display': 'inline'})
                ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '1.5rem', 'paddingBottom': '1rem', 'borderBottom': '2px solid #E2E8F0'}),

                html.Label([html.I(className="bi bi-calendar-event", style={'marginRight': '0.5rem'}), "Ano:"], style={'fontWeight': '600', 'color': '#475569', 'marginBottom': '0.5rem', 'display': 'block'}),
                dcc.Dropdown(
                    id='filtro-ano',
                    options=[{'label': str(ano), 'value': ano} for ano in sorted(df['ano'].unique())] if not df.empty else [],
                    placeholder="Selecione um ano",
                    style={'marginBottom': '1rem'}
                ),

                html.Label([html.I(className="bi bi-calendar-month", style={'marginRight': '0.5rem'}), "Mês:"], style={'fontWeight': '600', 'color': '#475569', 'marginBottom': '0.5rem', 'display': 'block'}),
                dcc.Dropdown(id='filtro-mes', placeholder="Selecione um mês", style={'marginBottom': '1rem'}),

                html.Label([html.I(className="bi bi-calendar-day", style={'marginRight': '0.5rem'}), "Dia:"], style={'fontWeight': '600', 'color': '#475569', 'marginBottom': '0.5rem', 'display': 'block'}),
                dcc.Dropdown(id='filtro-dia', placeholder="Selecione um dia", style={'marginBottom': '1rem'}),

                html.Label([html.I(className="bi bi-building", style={'marginRight': '0.5rem'}), "Unidade:"], style={'fontWeight': '600', 'color': '#475569', 'marginBottom': '0.5rem', 'display': 'block'}),
                dcc.Dropdown(
                    id='filtro-unidade',
                    options=[{'label': escola, 'value': escola} for escola in sorted(df['nome_escola'].dropna().unique())] if not df.empty else [],
                    placeholder="Selecione uma unidade"
                ),

                dbc.Button(
                    "Exportar para Excel",
                    id="btn-exportar",
                    color="primary",
                    className="mt-4 w-100"
                )

            ], style={
                'background': 'white',
                'borderRadius': '1rem',
                'boxShadow': '0 10px 15px rgba(0, 0, 0, 0.1)',
                'padding': '1.5rem'
            })
        ]),

        dbc.Col(width=9, children=[
            dbc.Row([
                dbc.Col(width=3, children=[html.Div(id='card-total-alertas', style={
                    'background': 'white', 
                    'borderRadius': '1rem', 
                    'boxShadow': '0 10px 15px rgba(0, 0, 0, 0.1)', 
                    'height': '200px',
                    'overflow': 'hidden'
                })]),

                dbc.Col(width=9, children=[
                    html.Div([
                        html.Div([
                            html.I(className="bi bi-geo-alt-fill", style={'fontSize': '1.5rem', 'color': '#4F46E5', 'marginRight': '0.5rem'}),
                            html.H4("Geolocalização das Unidades", style={'fontSize': '1.25rem', 'fontWeight': '700', 'color': '#1E293B', 'marginBottom': '0', 'display': 'inline'})
                        ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '1rem'}),

                        html.Div(
                            dcc.Graph(
                                id='mapa-geolocalizacao',
                                config={'displayModeBar': False, 'scrollZoom': True}
                            ),
                            style={'height': '280px'}
                        )
                    ], style={
                        'background': 'white', 
                        'borderRadius': '1rem', 
                        'boxShadow': '0 10px 15px rgba(0, 0, 0, 0.1)', 
                        'padding': '1.5rem',
                        'overflow': 'hidden'
                    })
                ]),
            ], className="mb-4"),

            dbc.Row([
                dbc.Col(children=[
                    html.Div([
                        html.I(className="bi bi-building", style={'fontSize': '1.5rem', 'color': '#4F46E5', 'marginRight': '0.5rem'}),
                        html.H4("Top 10 Alertas por Unidade", style={'fontSize': '1.25rem', 'fontWeight': '700', 'color': '#1E293B', 'marginBottom': '0', 'display': 'inline'})
                    ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '1.5rem'}),
                    html.Div(dcc.Graph(id='grafico-unidades'), style={
                        'background': 'white', 
                        'borderRadius': '1rem', 
                        'boxShadow': '0 10px 15px rgba(0, 0, 0, 0.1)', 
                        'padding': '1rem',
                        'overflow': 'hidden'
                    })
                ])
            ]),

            dbc.Row([
                dbc.Col(children=[
                    html.Div([
                        html.I(className="bi bi-bar-chart-fill", style={'fontSize': '1.5rem', 'color': '#4F46E5', 'marginRight': '0.5rem'}),
                        html.H4(id='titulo-secao-necessidades', children="Principais Necessidades", style={'fontSize': '1.25rem', 'fontWeight': '700', 'color': '#1E293B', 'marginBottom': '0', 'display': 'inline'})
                    ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '1.5rem', 'marginTop': '2rem'}),
                    html.Div(id='top-10-container')
                ])
            ]),
        ])
    ])
])


def register_callbacks(app: Dash) -> None:
    @app.callback(
        [Output('filtro-mes', 'options'),
         Output('filtro-dia', 'options')],
        [Input('filtro-ano', 'value'),
         Input('filtro-mes', 'value'),
         Input('emti-interval', 'n_intervals')]
    )
    def atualizar_filtros_dependentes(ano_selecionado, mes_selecionado, n):
        global df
        if n == 0:
            df = load_data()

        mes_options = []
        dia_options = []

        if ano_selecionado:
            meses_disponiveis = df[df['ano'] == ano_selecionado]['mes'].unique()
            mes_options = [{'label': str(mes), 'value': mes} for mes in sorted(meses_disponiveis)]

        if ano_selecionado and mes_selecionado:
            dias_disponiveis = df[(df['ano'] == ano_selecionado) & (df['mes'] == mes_selecionado)]['dia'].unique()
            dia_options = [{'label': str(dia), 'value': dia} for dia in sorted(dias_disponiveis)]

        return mes_options, dia_options

    @app.callback(
        [Output('card-total-alertas', 'children'),
         Output('mapa-geolocalizacao', 'figure'),
         Output('top-10-container', 'children'),
         Output('titulo-secao-necessidades', 'children'),
         Output('grafico-unidades', 'figure')],
        [Input('filtro-ano', 'value'),
         Input('filtro-mes', 'value'),
         Input('filtro-dia', 'value'),
         Input('filtro-unidade', 'value')]
    )
    def atualizar_dashboard(ano, mes, dia, unidade):
        if df.empty:
            fig_vazia = go.Figure().update_layout(title="Sem dados", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            return html.Div("Erro"), fig_vazia, [], "Erro", fig_vazia

        df_filtrado = df.copy()

        if ano:
            df_filtrado = df_filtrado[df_filtrado['ano'] == ano]
        if mes:
            df_filtrado = df_filtrado[df_filtrado['mes'] == mes]
        if dia:
            df_filtrado = df_filtrado[df_filtrado['dia'] == dia]
        if unidade:
            df_filtrado = df_filtrado[df_filtrado['nome_escola'] == unidade]

        total_alertas = len(df_filtrado)
        card_alertas = html.Div([
            html.Div(style={'height': '0.5rem', 'background': 'linear-gradient(90deg, #06B6D4 0%, #0891B2 100%)', 'borderTopLeftRadius': '1rem', 'borderTopRightRadius': '1rem'}),
            html.Div([
                html.Div([html.I(className="bi bi-bell-fill", style={'fontSize': '2rem', 'color': 'white'})],
                         style={'background': 'linear-gradient(135deg, #06B6D4 0%, #0891B2 100%)', 'padding': '0.75rem', 'borderRadius': '0.75rem', 'display': 'inline-block', 'marginBottom': '1rem'}),
                html.P("Total de Alertas", style={'fontSize': '0.875rem', 'fontWeight': '500', 'color': '#64748B', 'marginBottom': '0.25rem'}),
                html.H2(f"{total_alertas:,}", style={'fontSize': '2.25rem', 'fontWeight': '700', 'color': '#1E293B', 'marginBottom': '0'})
            ], style={'padding': '1.5rem', 'textAlign': 'center'})
        ])

        layout_common = dict(
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            font=dict(family="Inter, sans-serif", color='#1E293B'),
            margin=dict(l=10, r=10, t=30, b=10),
            height=240,
        )

        fig_mapa = go.Figure()

        if 'lat' in df_filtrado.columns and 'lon' in df_filtrado.columns:
            df_mapa = df_filtrado.groupby(['nome_escola', 'lat', 'lon', 'municipios']).size().reset_index(name='Total')

            if not df_mapa.empty:
                if len(df_mapa) == 1:
                    zoom_level = 15
                elif len(df_mapa) < 5:
                    zoom_level = 10
                else:
                    zoom_level = 5

                fig_mapa = px.scatter_mapbox(
                    df_mapa,
                    lat="lat",
                    lon="lon",
                    size="Total",
                    hover_name="nome_escola",
                    hover_data={"municipios": True, "Total": True, "lat": False, "lon": False},
                    color_discrete_sequence=["#4F46E5"],
                    zoom=zoom_level,
                    size_max=10,
                    center={"lat": df_mapa['lat'].mean(), "lon": df_mapa['lon'].mean()}
                )
                fig_mapa.update_layout(mapbox_style="carto-positron")
                fig_mapa.update_layout(**layout_common)
            else:
                fig_mapa.update_layout(
                    title="Sem dados de geolocalização",
                    xaxis={"visible": False}, yaxis={"visible": False}
                )
        else:
            fig_mapa.update_layout(title="Colunas 'lat' e 'lon' não encontradas")

        colunas_alvo = PRINCIPAL_COLS
        titulo_secao = "Top 10 Principais Necessidades (Geral)"

        top_10_graficos = []
        cores = ['#F59E0B', '#8B5CF6', '#EC4899', '#14B8A6', '#F97316']

        for idx, coluna in enumerate(colunas_alvo):
            if coluna not in df_filtrado.columns:
                continue

            df_limpo = df_filtrado[df_filtrado[coluna].notna() & (~df_filtrado[coluna].astype(str).isin(['nao_se_aplica', 'Não Informado', '', 'nan']))]

            if df_limpo.empty:
                continue

            df_top = df_limpo[coluna].value_counts().nlargest(10).sort_values(ascending=True).reset_index()
            df_top.columns = ['Item', 'Contagem']

            titulo_graf = coluna.replace('_', ' ').title().replace('Principal Necessidade', '').replace('Quantidade', 'Qtd.')

            fig = go.Figure(go.Bar(
                x=df_top['Contagem'],
                y=df_top['Item'],
                orientation='h',
                marker=dict(color=cores[idx % 5]),
                text=df_top['Contagem'],
                textposition='outside',
                texttemplate='%{x}'
            ))
            fig.update_layout(
                title=titulo_graf,
                height=300,
                margin=dict(l=10, r=40, t=40, b=30),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)'
            )
            fig.update_traces(cliponaxis=False)

            top_10_graficos.append(dbc.Col(width=6, className="mb-4", children=[
                html.Div(dcc.Graph(figure=fig, config={'displayModeBar': False}),
                         style={
                             'background': 'white', 
                             'borderRadius': '1rem', 
                             'boxShadow': '0 10px 15px rgba(0,0,0,0.1)', 
                             'padding': '1rem',
                             'overflow': 'hidden'
                         })
            ]))

        if not top_10_graficos:
            top_10_graficos = [html.Div("Nenhum dado relevante encontrado para os filtros selecionados.", className="text-muted p-3")]

        if 'nome_escola' in df_filtrado.columns:
            df_uni = df_filtrado[df_filtrado['nome_escola'].notna() & (df_filtrado['nome_escola'] != 'Não Informado')]
            if not df_uni.empty:
                df_top_uni = df_uni['nome_escola'].value_counts().nlargest(10).sort_values(ascending=True).reset_index()
                df_top_uni.columns = ['Unidade', 'Contagem']
                fig_uni = go.Figure(go.Bar(
                    x=df_top_uni['Contagem'],
                    y=df_top_uni['Unidade'],
                    orientation='h',
                    marker=dict(color='#4F46E5'),
                    text=df_top_uni['Contagem'],
                    textposition='outside',
                    texttemplate='%{x}'
                ))
                fig_uni.update_layout(title="Top 10 Unidades", height=300, margin=dict(l=10, r=40, t=40, b=30), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                fig_uni.update_traces(cliponaxis=False)
            else:
                fig_uni = go.Figure()
        else:
            fig_uni = go.Figure()

        return card_alertas, fig_mapa, dbc.Row(top_10_graficos), titulo_secao, fig_uni

    @app.callback(
        Output("download-excel", "data"),
        Input("btn-exportar", "n_clicks"),
        [State('filtro-ano', 'value'),
         State('filtro-mes', 'value'),
         State('filtro-dia', 'value'),
         State('filtro-unidade', 'value')],
        prevent_initial_call=True,
    )
    def exportar_excel(n_clicks, ano, mes, dia, unidade):
        df_filtrado = df.copy()
        if ano:
            df_filtrado = df_filtrado[df_filtrado['ano'] == ano]
        if mes:
            df_filtrado = df_filtrado[df_filtrado['mes'] == mes]
        if dia:
            df_filtrado = df_filtrado[df_filtrado['dia'] == dia]
        if unidade:
            df_filtrado = df_filtrado[df_filtrado['nome_escola'] == unidade]

        colunas_exportacao = []
        colunas_exportacao.extend([col for col in ORDEM_EXPORTACAO if col in df_filtrado.columns])

        for cat_nome, cat_cols in CATEGORIAS.items():
            colunas_exportacao.extend([col for col in cat_cols if col in df_filtrado.columns])

        colunas_exportacao = list(dict.fromkeys(colunas_exportacao))

        df_final = df_filtrado[colunas_exportacao]
        df_final.columns = [col.replace('_', ' ').title() for col in df_final.columns]

        return dcc.send_data_frame(
            df_final.to_excel,
            f"dados_emti_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.xlsx",
            sheet_name="Dados Filtrados",
            index=False
        )
