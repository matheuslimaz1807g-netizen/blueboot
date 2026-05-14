# Fix: Volume .env não montado no container do cliente

**Data**: 2026-05-14 19:30
**Tipo**: Correção de infraestrutura Docker

## Problema

O log do bot mostra:
```
bot_matheus  | [16:52:39] [WARNING] ⚠️ Arquivo .env não encontrado. Criando .env...
```

### Causa Raiz

O `docker-compose.yml` do cliente `matheus` na VPS estava com:
1. **`whatsapp_matheus`** sem o volume `./.env:/app/.env` → WhatsApp não via o .env
2. **`networks.bluebot_network.external: tru`** → typo (falta o `e`)
3. Containers possivelmente não recriados após adição do volume no bot

### Fluxo do problema

```
.env no host (/opt/bluebot/clientes/matheus/.env)
    ↓
env_file: .env → carrega vars como ENV no START do container
    ↓
volume ./.env:/app/.env → monta o ARQUIVO dentro do container
    ↓
load_dotenv(override=False) → lê /app/.env mas NÃO sobrescreve env vars existentes
    ↓
find_env_file() → procura /app/.env para escrita (save_session, sync_env_vars)
```

Se o volume não está montado, o `find_env_file()` não encontra `/app/.env`, e qualquer tentativa de persistir dados no .env falha.

## Mudanças

### 1. Template (`clientes/template/docker-compose.yml`)
- Confirmado que ambos os serviços (bot + whatsapp) têm `./.env:/app/.env`

### 2. Instruções para VPS
- Substituir o `docker-compose.yml` do cliente `matheus` com versão corrigida
- Recriar containers com `docker compose down && docker compose up -d`

## Impacto
- Bot passa a ler e escrever no .env corretamente
- Session string do Telegram persiste após restart
- Sync de credenciais (ML_COOKIES, tokens) funciona via painel

## Próximos Passos
- Aplicar o fix na VPS
- Verificar com `docker exec bot_matheus cat /app/.env`
- Monitorar logs para confirmar que o warning sumiu
