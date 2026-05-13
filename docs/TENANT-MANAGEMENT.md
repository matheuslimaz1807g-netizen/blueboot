# 👥 Gerenciamento de Clientes (Tenants)

## Como funciona o Multi-Tenancy

Cada cliente (tenant) tem:
- **Uma licença** no banco de dados (UUID único)
- **Um par de containers**: `bot_<slug>` + `whatsapp_<slug>`
- **Uma pasta** em `clientes/<slug>/` com `.env` e `docker-compose.yml`

Os clientes **compartilham** o mesmo banco de dados (PostgreSQL), mas cada um só acessa seus próprios dados através do `license_id` no JWT.

---

## Adicionar Novo Cliente

### Método Automático (recomendado)

```bash
cd /opt/bluebot
bash scripts/novo-cliente.sh empresa-abc
```

O script vai pedir:
1. Chave de licença (criada no painel admin)
2. Senha do cliente
3. Configurações do Telegram (API ID, Hash, telefone)
4. Canais de origem e destino

### O que o script faz (passo a passo):

```
1. Cria pasta: clientes/empresa-abc/
2. Copia template: clientes/template/docker-compose.yml
3. Gera .env com as configurações informadas
4. Substitui ${CLIENTE_SLUG} por "empresa-abc" em todos os arquivos
5. Sobe os containers: docker compose up -d
6. Verifica saúde dos containers
```

### Resultado:

```
clientes/empresa-abc/
├── docker-compose.yml    ← Define bot + whatsapp containers
└── .env                  ← Configs específicas do cliente
```

Novos containers criados:
- `whatsapp_empresa-abc` — Sessão WhatsApp Web
- `bot_empresa-abc` — Bot de automação

---

## Vincular Cliente a uma Licença

### 1. Crie a licença no painel admin

1. Acesse `https://console.bluebotapp.com.br`
2. Faça login com admin/senha
3. Clique em **"Nova Licença"**
4. Escolha o plano e defina uma senha para o cliente
5. Copie a **chave da licença** (formato: `APRO-XXXX-XXXX-XXXX`)

### 2. O bot do cliente se registra automaticamente

Quando o container `bot_empresa-abc` sobe, ele:
1. Chama `POST /license/discover` com seu `machine_id`
2. Aparece na aba **"Pendentes"** do painel admin

### 3. Vincule no painel admin

1. No painel, vá à aba **"Máquinas Pendentes"**
2. Selecione a máquina do cliente
3. Escolha a licença criada no passo 1
4. Clique **"Vincular"**

### 4. Pronto!

O bot recebe a `license_key` automaticamente e começa a operar.

---

## Remover Cliente

```bash
cd /opt/bluebot
bash scripts/remover-cliente.sh empresa-abc
```

Isso vai:
1. Parar os containers (`docker compose down`)
2. Remover os volumes de dados do WhatsApp
3. (Opcionalmente) remover a pasta do cliente

> ⚠️ A licença no banco de dados **não é removida** — apenas desative-a no painel admin.

---

## Ver Status de Todos os Clientes

```bash
# Ver containers de clientes rodando
docker ps --filter "name=bot_" --filter "name=whatsapp_" --format "table {{.Names}}\t{{.Status}}"

# Resultado:
# NAMES                STATUS
# bot_matheus          Up 2 hours (healthy)
# whatsapp_matheus     Up 2 hours (healthy)
# bot_empresa-abc      Up 30 minutes (healthy)
# whatsapp_empresa-abc Up 30 minutes (healthy)
```

```bash
# Health check completo
bash scripts/health-check.sh
```

---

## Migrar Cliente para Outra VPS (Futuro)

Quando o cliente crescer e precisar de VPS própria:

1. Copie `clientes/<slug>/` para a nova VPS
2. No `.env` do cliente, mude:
   ```
   # De (rede Docker interna):
   APRO_API_BASE=http://bluebot_api:8000
   
   # Para (API pública):
   APRO_API_BASE=https://api.bluebotapp.com.br
   ```
3. Na nova VPS: `docker compose up -d`
4. O bot se comunica com a API central via HTTPS
