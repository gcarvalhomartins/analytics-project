# Contexto do Projeto: Analytics Platform

## Visão Geral
Plataforma de dashboards dinâmicos em Python/Dash com descoberta automática de novas rotas. Desenvolvedores criam pastas em `dashboards/` e o sistema automaticamente expõe via URL.

## Stack Técnica
- Frontend: Dash 2.x, Plotly
- Backend: Flask (embutido no Dash), Gunicorn
- Proxy Reverso: Nginx
- Banco de dados: SQLAlchemy 2.x (multi-DB)
- CI/CD: GitHub Actions
- Gerenciamento: systemd
- Infra: Hostinger VPS (Ubuntu 22.04)

## Decisões Arquiteturais
- [Data] — DashboardRouter usa importlib para carregamento dinâmico
- [Data] — Cada dashboard é sub-aplicação com url_base_pathname
- [Data] — Fallback com dados mockados para desenvolvimento local

## Tarefas em Andamento
- [ ] Criar todos os arquivos do projeto (main.py, core/, dashboards/, etc.)

## Tarefas Concluídas
- [x] Estrutura de pastas criada

## Padrões e Convenções
- Arquivos de dashboard: app.py + config.yaml obrigatórios
- Variáveis de ambiente: prefixo DB_[NOME]_ para cada dashboard
- Logging: formato `[%(asctime)s] %(levelname)s - %(message)s`

## Dependências Importantes
- dash, plotly, flask, gunicorn, sqlalchemy, pandas, pyyaml, python-dotenv

## Problemas Conhecidos / Débitos Técnicos
- Nenhum identificado ainda

## Notas Importantes
- Sistema detecta automaticamente novas pastas em dashboards/
- Cada dashboard precisa exportar `layout` e `register_callbacks(app)`
