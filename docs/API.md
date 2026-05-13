# 📡 API — Endpoints e Autenticação

## Visão Geral

A API do BlueBotApp é construída com **FastAPI** (Python) e roda em `https://api.bluebotapp.com.br`.

Documentação interativa (Swagger): `https://api.bluebotapp.com.br/docs`

## Autenticação

A API usa **JWT (JSON Web Tokens)**. Existem dois tipos de usuário:

| Tipo | Como logar | O que pode acessar |
|------|-----------|-------------------|
| **Admin** | Username + Password | Tudo: licenças, configs, logs, WhatsApp |
| **Client** | License Key + Password | Apenas seus próprios dados |

### Login Admin

```bash
# 1. Fazer login e obter o token
curl -X POST https://api.bluebotapp.com.br/auth/login/admin \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "SUA_SENHA"}'

# Resposta:
# {"access_token": "eyJhbGciOiJIUzI1NiI..."}

# 2. Usar o token em todas as requisições seguintes
curl https://api.bluebotapp.com.br/admin/licenses \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiI..."
```

### Login Cliente

```bash
curl -X POST https://api.bluebotapp.com.br/auth/login/client \
  -H "Content-Type: application/json" \
  -d '{"license_key": "APRO-XXXX-XXXX-XXXX", "password": "senha_do_cliente"}'
```

---

## Endpoints

### 🔐 Autenticação (`/auth`)

| Método | Rota | Descrição | Auth? |
|--------|------|-----------|-------|
| POST | `/auth/login/admin` | Login do administrador | Não |
| POST | `/auth/login/admin/verify` | Verificar código 2FA | Não |
| POST | `/auth/login/client` | Login do cliente (license_key + password) | Não |

### 👑 Admin (`/admin`) — Requer JWT admin

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/admin/licenses` | Listar todas as licenças |
| POST | `/admin/licenses` | Criar nova licença |
| PATCH | `/admin/licenses/{id}` | Editar licença (ativar/desativar, mudar plano) |
| GET | `/admin/licenses/{id}/config` | Ver config de uma licença |
| PUT | `/admin/licenses/{id}/config` | Atualizar config de uma licença |
| GET | `/admin/licenses/{id}/logs` | Ver logs de uma licença |
| POST | `/admin/licenses/{id}/auth-code` | Enviar código Telegram |
| GET | `/admin/pending` | Listar máquinas aguardando vinculação |
| POST | `/admin/link` | Vincular máquina a uma licença |
| DELETE | `/admin/pending/{machine_id}` | Remover máquina da lista |
| GET | `/admin/versions` | Listar versões do app |
| POST | `/admin/versions` | Registrar nova versão |
| GET | `/admin/whatsapp/status` | Status do WhatsApp |

### 👤 Cliente (`/client`) — Requer JWT client

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/client/me` | Ver dados da própria licença |
| GET | `/client/config` | Ver própria configuração |
| PUT | `/client/config` | Atualizar própria configuração |
| GET | `/client/logs` | Ver próprios logs |
| GET | `/client/whatsapp/qr` | Ver QR Code do WhatsApp |

### 🤖 Licença Pública (usada pelo executável do bot)

| Método | Rota | Descrição | Auth? |
|--------|------|-----------|-------|
| POST | `/license/discover` | Registrar máquina para aprovação | Install Token |
| POST | `/license/validate` | Validar licença + machine_id | Não |
| POST | `/license/heartbeat` | Enviar heartbeat (status WhatsApp, QR) | Não |
| GET | `/license/auth-code` | Buscar código Telegram pendente | Não |
| GET | `/config/{license_key}` | Buscar config por chave | Não |

---

## Fluxo: Como um novo cliente é vinculado

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Bot do       │     │    API       │     │   Painel     │
│  Cliente      │     │  (FastAPI)   │     │   Admin      │
└──────┬───────┘     └──────┬───────┘     └──────┬───────┘
       │                    │                    │
  1.   │ POST /license/     │                    │
       │    discover        │                    │
       │───────────────────>│                    │
       │   {machine_id,     │  2. Salva na       │
       │    hostname}       │     tabela         │
       │                    │  pending_machines  │
       │<───────────────────│                    │
       │  {"pending": true} │                    │
       │                    │                    │
       │                    │  3. Admin abre o   │
       │                    │     painel         │
       │                    │<───────────────────│
       │                    │  GET /admin/pending│
       │                    │───────────────────>│
       │                    │  Lista de máquinas │
       │                    │  esperando         │
       │                    │                    │
       │                    │  4. Admin clica    │
       │                    │     "Vincular"     │
       │                    │<───────────────────│
       │                    │  POST /admin/link  │
       │                    │  {license_id,      │
       │                    │   machine_id}      │
       │                    │                    │
  5.   │ POST /license/     │                    │
       │    discover        │                    │
       │───────────────────>│                    │
       │<───────────────────│                    │
       │ {"pending": false, │                    │
       │  "assigned_key":   │                    │
       │  "APRO-XXXX-..."}  │                    │
       │                    │                    │
  6.   │ Bot começa a       │                    │
       │ funcionar com      │                    │
       │ a license_key      │                    │
```

### Resumo do fluxo:
1. O bot do cliente liga e chama `/license/discover` com seu `machine_id`
2. A API salva essa máquina em "pendentes"
3. No painel admin (`console.bluebotapp.com.br`), aparece a máquina na aba "Pendentes"
4. Você (admin) seleciona uma licença e clica "Vincular"
5. Na próxima vez que o bot ligar, recebe a `license_key` e começa a operar
6. A partir daí, o bot faz `heartbeat` a cada poucos segundos para manter o status atualizado

---

## Variáveis de Ambiente da API

| Variável | Descrição | Exemplo |
|----------|-----------|---------|
| `POSTGRES_USER` | Usuário do banco | `bluebot` |
| `POSTGRES_PASSWORD` | Senha do banco | (gerar com openssl) |
| `POSTGRES_DB` | Nome do banco | `bluebot` |
| `DATABASE_URL` | URL completa de conexão | `postgresql+asyncpg://...` |
| `JWT_SECRET` | Chave para assinar tokens JWT | (gerar com python secrets) |
| `FERNET_KEY` | Chave para criptografia simétrica | (gerar com Fernet) |
| `INSTALL_TOKEN` | Token para bots se registrarem | (gerar com secrets) |
| `ADMIN_USERNAME` | Login do admin | `admin` |
| `ADMIN_PASSWORD` | Senha do admin | (sua escolha) |
| `RATE_LIMIT_PER_MINUTE` | Limite de requisições por minuto | `60` |

> ⚠️ **NUNCA** compartilhe o arquivo `.env` ou commite ele no Git!
