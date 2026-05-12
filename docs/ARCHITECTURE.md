# BlueBot — Arquitetura

## Visão Geral

```
┌─────────────────────────────────────────────────────────────┐
│                    VPS (Hostinger)                           │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  INFRA (docker-compose.yml da raiz)                 │    │
│  │                                                     │    │
│  │  Nginx:443 ──► api:8000 (FastAPI)                   │    │
│  │    │             │                                   │    │
│  │    │             └──► postgres:5432                  │    │
│  │    │                                                 │    │
│  │    ├─ console.bluebotapp.com.br → admin/ (estático)  │    │
│  │    ├─ api.bluebotapp.com.br     → proxy api:8000     │    │
│  │    ├─ app.bluebotapp.com.br     → proxy api:8000     │    │
│  │    └─ bluebotapp.com.br         → redirect console   │    │
│  │                                                     │    │
│  │  Certbot → renovação SSL automática                  │    │
│  └─────────────────────────────────────────────────────┘    │
│                          │                                  │
│              bluebot_network (Docker)                       │
│                          │                                  │
│  ┌───────────────────────┴─────────────────────────────┐    │
│  │  CLIENTES (clientes/<slug>/docker-compose.yml)      │    │
│  │                                                     │    │
│  │  ┌─────────────┐  ┌─────────────┐                   │    │
│  │  │ matheus     │  │ empresa-abc │                   │    │
│  │  │  bot        │  │  bot        │                   │    │
│  │  │  whatsapp   │  │  whatsapp   │                   │    │
│  │  └─────────────┘  └─────────────┘                   │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## Estrutura de Pastas

```
/opt/bluebot/
├── docker-compose.yml      # Infra: postgres, api, nginx, certbot
├── .env                    # Secrets (NÃO versionado)
├── api/                    # FastAPI backend
├── admin/                  # Painel admin (HTML estático)
├── client_app/             # Painel cliente (HTML estático)
├── nginx/
│   ├── nginx.conf          # Config principal (com includes)
│   ├── conf.d/             # Server blocks por domínio
│   └── snippets/           # SSL, CORS, proxy, security
├── data/
│   ├── ssl/                # Certificados Let's Encrypt
│   └── backups/postgres/   # Backups automáticos
├── certbot/www/            # ACME challenge
├── clientes/
│   ├── template/           # Template para novos clientes
│   └── <slug>/             # Pasta por cliente
├── scripts/                # Automação
└── docs/                   # Documentação
```

## Isolamento de Dados

Cada cliente é identificado por um `license_id` (UUID). O isolamento funciona assim:

1. **Autenticação**: Cliente faz login com `license_key` + `password` → recebe JWT com `role: client` e `sub: license_id`
2. **Autorização**: Middleware `get_current_license()` extrai `license_id` do JWT
3. **Filtragem**: Toda query filtra `WHERE license_id = <JWT.sub>`

Não é possível um cliente acessar dados de outro — o JWT garante o escopo.

## Comunicação

| De | Para | Como |
|----|------|------|
| Browser admin | API | HTTPS via `api.bluebotapp.com.br` |
| Browser cliente | API | HTTPS via `app.bluebotapp.com.br` |
| Bot (container) | API | HTTP via `http://bluebot_api:8000` (rede Docker interna) |
| WhatsApp (container) | Bot | HTTP via `http://whatsapp_<slug>:4000` (rede Docker interna) |

## Migração para VPS Separadas (Futuro)

Quando necessário, cada cliente pode ser movido para uma VPS própria:

1. Copiar `clientes/<slug>/` para a nova VPS
2. Alterar `APRO_API_BASE` no `.env` de `http://bluebot_api:8000` para `https://api.bluebotapp.com.br`
3. Rodar `docker compose up -d` na nova VPS
4. Os containers do cliente se comunicam com a API central via HTTPS público
