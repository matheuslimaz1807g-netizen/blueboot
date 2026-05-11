# Plano de Diagnóstico Completo — BlueBot

## Situação Atual

### ✅ Funcionando:

- API (bluebot_api) — rodando, conectando ao PostgreSQL
- PostgreSQL (bluebot_postgres) — rodando com senha `bluebot_secret`
- Nginx (bluebot_nginx) — rodando
- Painel Admin (bluebot_panel) — rodando
- Licença validada: `APRO-CFXN-U6VD-A***` — Plano BASIC
- Bot descobre licença via auto-descoberta no painel ✅

### ❌ Problemas:

1. **`Incorrect padding`** — Session string do Telegram inválida/corrompida
2. **`free variable 'config'`** — Erro de escopo no heartbeat callback (já corrigido no commit, mas precisa rebuild)
3. **Bot não pede código de autenticação** — Por causa do erro `Incorrect padding`, o bot morre antes de chegar na fase de autenticação

## Causa Raiz

O `docker compose down -v` apagou o volume `postgres_data` e também a pasta `./sessions` do cliente Matheus. A session string do Telegram que estava no banco (config remota) também foi perdida.

## Plano de Correção

### Passo 1: Rebuild do bot com as correções

```bash
cd /usr/blueboot
git pull origin main
cd clientes/matheus
docker compose down
docker compose up -d --build
```

### Passo 2: Verificar se o bot inicia e pede código

```bash
docker logs bot_matheus -f
```

Deverá aparecer: `"Sessão requer autorização. Solicitando código para +5562981416890..."`

### Passo 3: Fornecer o código de autenticação

Acessar `https://console.bluebotapp.com.br` ou via API.

### Passo 4: Verificar conectividade WhatsApp

O erro `cannot access free variable 'config'` já foi corrigido no commit `0292f9f`.

## Estrutura de Múltiplos Clientes

```
/usr/blueboot/
├── clientes/
│   ├── matheus/          ← Cliente atual
│   │   ├── docker-compose.yml
│   │   ├── .env
│   │   ├── sessions/     ← Sessão Telegram (persistente)
│   │   ├── auth/         ← Auth WhatsApp (persistente)
│   │   └── data/         ← Dados do bot
│   └── template/         ← Template para novos clientes
├── scripts/
│   ├── novo-cliente.sh   ← Script para criar novo cliente
│   └── remover-cliente.sh
└── docker-compose.yml    ← Core (API + Postgres + Nginx + Panel)
```

Para adicionar novo cliente:

```bash
bash /usr/blueboot/scripts/novo-cliente.sh <slug>
```
