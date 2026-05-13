# 🏗️ Arquitetura Técnica

## Diagrama de Componentes

```
                         Internet (HTTPS)
                              │
                   ┌──────────┼──────────┐
                   │          │          │
          console.*     api.*      app.*
                   │          │          │
                   └──────────┼──────────┘
                              │
                    ┌─────────▼─────────┐
                    │      Nginx        │ ← Porta 80/443
                    │  (Proxy Reverso)  │ ← SSL Termination
                    │  nginx:1.27       │ ← Rate Limiting
                    └──┬──────┬──────┬──┘
                       │      │      │
        ┌──────────────┘      │      └──────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
  ┌───────────┐        ┌───────────┐         ┌───────────┐
  │  admin/   │        │  FastAPI  │         │client_app/│
  │  (HTML)   │        │  (api)    │         │  (HTML)   │
  │  estático │        │ :8000     │         │  estático │
  └───────────┘        └─────┬─────┘         └───────────┘
                             │
                    ┌────────▼────────┐
                    │   PostgreSQL    │
                    │   (postgres)    │
                    │   :5432         │
                    └─────────────────┘

         rede: bluebot_network
         ┌────────────────────────────┐
         │                            │
    ┌────▼────┐              ┌────────▼─────────┐
    │ bot_    │              │ whatsapp_         │
    │ matheus │◄────────────►│ matheus           │
    │ :8080   │              │ :4000             │
    └─────────┘              └──────────────────┘
```

## Fluxo de uma Requisição

### Admin faz login:
```
1. Browser abre https://console.bluebotapp.com.br
2. Nginx recebe → serve admin/index.html (arquivo estático)
3. JavaScript faz POST /auth/login/admin com username/password
4. Nginx proxeia → FastAPI valida credenciais → retorna JWT
5. Browser salva o JWT e usa em todas as próximas requisições
```

### Cliente abre o painel:
```
1. Browser abre https://app.bluebotapp.com.br
2. Nginx recebe → proxeia para FastAPI
3. FastAPI redireciona para /app_static/ (arquivos do cliente)
4. JavaScript faz POST /auth/login/client com license_key/password
5. FastAPI valida → retorna JWT com license_id
6. Todas as queries usam WHERE license_id = JWT.sub
```

### Bot envia heartbeat:
```
1. Container bot_matheus faz POST http://bluebot_api:8000/license/heartbeat
   (comunicação interna pela rede Docker, sem passar pelo Nginx)
2. FastAPI salva status do WhatsApp e QR code no banco
3. Admin abre o painel → GET /admin/whatsapp/status → vê o QR code
```

---

## Redes Docker

```
bluebot_network (bridge)
├── bluebot_postgres    ← :5432 (só interno)
├── bluebot_api         ← :8000 (só interno)
├── bluebot_nginx       ← :80/:443 (exposto para internet)
├── bluebot_certbot     ← (sem porta)
├── bot_matheus         ← :8080 (só interno)
└── whatsapp_matheus    ← :4000 (só interno)
```

Apenas o **Nginx** tem portas expostas para a internet. Todos os outros containers se comunicam apenas pela rede interna Docker.

---

## Volumes e Persistência

| Volume/Bind | Tipo | Container | O que guarda |
|-------------|------|-----------|-------------|
| `postgres_data` | Volume nomeado | postgres | Banco de dados inteiro |
| `./data/ssl` | Bind mount | nginx, certbot | Certificados SSL |
| `./admin` | Bind mount | nginx, api | HTML do painel admin |
| `./client_app` | Bind mount | nginx, api | HTML do painel cliente |
| `whatsapp_auth_*` | Volume nomeado | whatsapp_* | Sessão WhatsApp |
| `bot_sessions_*` | Volume nomeado | bot_* | Sessão Telegram |

> 💡 **Volumes nomeados** (como `postgres_data`) sobrevivem ao `docker compose down`. São gerenciados pelo Docker em `/var/lib/docker/volumes/`.

---

## Multi-Tenancy

```
┌─────────────────────────────────────────────────┐
│                  PostgreSQL                      │
│                                                  │
│  Tabela: licenses                                │
│  ┌──────────┬───────────┬──────────┬────────┐   │
│  │ id (UUID)│ key       │ active   │ plan   │   │
│  ├──────────┼───────────┼──────────┼────────┤   │
│  │ aaa-111  │ APRO-0001 │ true     │ pro    │   │
│  │ bbb-222  │ APRO-0002 │ true     │ basic  │   │
│  └──────────┴───────────┴──────────┴────────┘   │
│                                                  │
│  Tabela: client_configs                          │
│  ┌────────────┬──────────────┬───────────────┐  │
│  │ license_id │ telegram_src │ whatsapp_dest │  │
│  ├────────────┼──────────────┼───────────────┤  │
│  │ aaa-111    │ @canal_a     │ grupo_a       │  │
│  │ bbb-222    │ @canal_b     │ grupo_b       │  │
│  └────────────┴──────────────┴───────────────┘  │
│                                                  │
│  Cliente aaa-111 NUNCA vê dados de bbb-222       │
│  (filtrado por license_id no JWT)                │
└─────────────────────────────────────────────────┘
```

---

## Nginx — Configuração Modular

```
nginx/
├── nginx.conf          ← Config principal (HTTP→HTTPS, includes)
├── conf.d/
│   ├── 00-default.conf ← Bloqueia acesso direto por IP
│   ├── api.conf        ← api.bluebotapp.com.br → proxy FastAPI
│   ├── admin.conf      ← console.bluebotapp.com.br → HTML + proxy API
│   ├── client-app.conf ← app.bluebotapp.com.br → proxy FastAPI
│   └── redirect.conf   ← bluebotapp.com.br → redirect console
└── snippets/
    ├── ssl.conf        ← Caminhos dos certificados + TLS config
    ├── proxy.conf      ← Headers de proxy (X-Real-IP, etc.)
    ├── cors.conf       ← CORS headers (NÃO usado — FastAPI gerencia)
    └── security.conf   ← Headers de segurança (HSTS, X-Frame, etc.)
```

Cada subdomínio tem seu próprio arquivo em `conf.d/`. Isso facilita adicionar novos subdomínios ou modificar um sem afetar os outros.
