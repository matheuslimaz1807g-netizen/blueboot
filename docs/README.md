# 📘 BlueBotApp — Documentação

Bem-vindo à documentação completa do BlueBotApp! Este sistema é uma plataforma SaaS multi-tenant para automação de mensagens via WhatsApp e Telegram.

## 📖 Guias

| Documento | Para quem? | Descrição |
|-----------|-----------|-----------|
| [🚀 Getting Started](GETTING-STARTED.md) | **Iniciantes** | Docker, Git e comandos básicos explicados de forma simples |
| [🔧 Setup](SETUP.md) | **Deploy inicial** | Instalação do zero na VPS, passo a passo |
| [🏗️ Architecture](ARCHITECTURE.md) | **Técnico** | Como os serviços se conectam, fluxo de requisições |
| [📡 API](API.md) | **Desenvolvedores** | Endpoints, autenticação JWT, exemplos com curl |
| [👥 Tenant Management](TENANT-MANAGEMENT.md) | **Operações** | Adicionar/remover clientes |
| [🚢 Deployment](DEPLOYMENT.md) | **Deploy** | Atualizar código, rollback, CI/CD |
| [🔨 Maintenance](MAINTENANCE.md) | **Operações** | Backups, SSL, logs, monitoramento |
| [🐛 Troubleshooting](TROUBLESHOOTING.md) | **Problemas** | Soluções para erros comuns |
| [📚 Git Basics](GIT-BASICS.md) | **Iniciantes** | Git do zero para quem nunca usou |

## 🏛️ Visão Geral da Arquitetura

```
                    Internet
                       │
                       ▼
              ┌────────────────┐
              │     Nginx      │ ← SSL termination
              │   (porta 443)  │
              └────┬───┬───┬───┘
                   │   │   │
    ┌──────────────┤   │   ├──────────────┐
    │              │   │                  │
    ▼              ▼   ▼                  ▼
┌────────┐   ┌──────────┐          ┌──────────┐
│console.│   │  api.    │          │  app.    │
│(admin) │   │(FastAPI) │          │(cliente) │
└────────┘   └────┬─────┘          └──────────┘
                  │
                  ▼
           ┌────────────┐
           │ PostgreSQL  │
           │  (dados)    │
           └────────────┘
```

## 🔗 Domínios

| Subdomínio | Função |
|------------|--------|
| `console.bluebotapp.com.br` | Painel administrativo |
| `api.bluebotapp.com.br` | API REST (FastAPI) |
| `app.bluebotapp.com.br` | Painel do cliente (SaaS) |
| `bluebotapp.com.br` | Redireciona para console |

## 🛠️ Tecnologias

- **Backend**: Python 3.11 + FastAPI
- **Banco de Dados**: PostgreSQL 16
- **Proxy Reverso**: Nginx 1.27
- **SSL**: Let's Encrypt (Certbot)
- **Containers**: Docker + Docker Compose
- **Automação**: WhatsApp Web.js + Telegram (Telethon)
- **VPS**: Ubuntu 22.04 (Hostinger)
