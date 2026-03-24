# Guia de Deploy - Hostinger VPS

Este guia passo a passo mostra como fazer deploy da Analytics Platform no servidor Hostinger VPS.

## Pré-requisitos

- Servidor Hostinger VPS com Ubuntu 22.04
- Domínio configurado (analytics.sasi.net)
- Acesso SSH ao servidor

## Passo 1: Conectar ao Servidor

```bash
ssh usuario@ip-do-servidor
```

## Passo 2: Instalar Dependências do Sistema

```bash
sudo apt update
sudo apt install -y git python3.11 python3.11-venv python3-pip nginx certbot python3-certbot-nginx
```

## Passo 3: Criar Usuário do Aplicativo (Opcional)

```bash
sudo useradd -m -s /bin/bash analytics
sudo usermod -aG sudo analytics
```

## Passo 4: Clonar o Repositório

```bash
cd /home
sudo mkdir -p analytics/app
cd analytics/app
sudo git clone <url-do-repositorio> .
sudo chown -R analytics:analytics /home/analytics
```

## Passo 5: Configurar Variáveis de Ambiente

```bash
cd /home/analytics/app
sudo cp .env.example .env
sudo nano .env
```

Configure as variáveis:
```
ENV=production
SECRET_KEY=uma-chave-secreta-forte-aqui

DB_VENDAS_HOST=localhost
DB_VENDAS_PORT=5432
DB_VENDAS_NAME=vendas
DB_VENDAS_USER=usuario
DB_VENDAS_PASS=senha

DB_FINANCEIRO_HOST=localhost
DB_FINANCEIRO_PORT=5432
DB_FINANCEIRO_NAME=financeiro
DB_FINANCEIRO_USER=usuario
DB_FINANCEIRO_PASS=senha
```

## Passo 6: Criar Serviço systemd

```bash
sudo nano /etc/systemd/system/analytics-dash.service
```

Cole o seguinte conteúdo:

```ini
[Unit]
Description=Analytics Dashboard Platform
After=network.target

[Service]
Type=simple
User=analytics
Group=analytics
WorkingDirectory=/home/analytics/app
ExecStart=/usr/bin/python3.11 -m gunicorn main:server -c gunicorn.conf.py
Restart=always
RestartSec=5
EnvironmentFile=/home/analytics/app/.env
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

## Passo 7: Habilitar e Iniciar o Serviço

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now analytics-dash
sudo systemctl status analytics-dash
```

## Passo 8: Configurar Nginx

```bash
sudo cp nginx.conf /etc/nginx/sites-available/analytics
sudo rm -f /etc/nginx/sites-enabled/default
sudo ln -s /etc/nginx/sites-available/analytics /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## Passo 9: Configurar SSL (Certbot)

```bash
sudo certbot --nginx -d analytics.sasi.net
```

Siga as instruções na tela. Escolha a opção para redirecionar HTTP para HTTPS automaticamente.

## Passo 10: Configurar GitHub Actions

No GitHub, vá em Settings > Secrets and variables > Actions e adicione:

| Secret | Valor |
|--------|-------|
| HOSTINGER_HOST | IP ou hostname do servidor |
| HOSTINGER_USER | usuário SSH (analytics) |
| HOSTINGER_SSH_KEY | chave SSH privada |

## Configurar Deploy Key no GitHub

1. Gere a chave SSH no servidor:
```bash
ssh-keygen -t ed25519 -C "deploy@analytics"
```

2. Adicione a chave pública em:
   - GitHub > Settings > Deploy Keys (para o repo)
   - Ou no servidor em `~/.authorized_keys`

## Verificar Deploy

```bash
# Ver logs do serviço
sudo journalctl -u analytics-dash -f

# Reiniciar após mudanças
sudo systemctl restart analytics-dash

# Verificar status
sudo systemctl status analytics-dash
```

## Comandos Úteis

| Comando | Descrição |
|---------|-----------|
| `sudo systemctl start analytics-dash` | Iniciar o serviço |
| `sudo systemctl stop analytics-dash` | Parar o serviço |
| `sudo systemctl restart analytics-dash` | Reiniciar o serviço |
| `sudo journalctl -u analytics-dash -f` | Ver logs em tempo real |
| `sudo systemctl status analytics-dash` | Ver status do serviço |

## Troubleshooting

### Serviço não inicia
```bash
sudo journalctl -u analytics-dash --no-pager -n 50
```

### Erro de permissão
```bash
sudo chown -R analytics:analytics /home/analytics/app
```

### Problemas com Nginx
```bash
sudo nginx -t
sudo systemctl restart nginx
```

### Verificar se a porta está liberada
```bash
sudo ufw allow 8050/tcp
```

## Estrutura Final

```
/home/analytics/
└── app/
    ├── main.py
    ├── config.py
    ├── requirements.txt
    ├── gunicorn.conf.py
    ├── .env
    ├── core/
    ├── dashboards/
    └── ...

/etc/systemd/system/
└── analytics-dash.service

/etc/nginx/sites-available/
└── analytics
```

## Fluxo de Deploy

1. Faça push para a branch `main`
2. GitHub Actions executa testes
3. Se aprovado, faz deploy via SSH
4. Sistema faz pull, install dependencies e restart do serviço
5. Dashboard está disponível em analytics.sasi.net
