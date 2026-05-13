# 🐛 Troubleshooting — Solução de Problemas

## PostgreSQL Não Inicia

### Sintomas
- `docker compose ps` mostra postgres como "Exited" ou "Restarting"
- API retorna erro 500

### Verificar
```bash
docker compose logs postgres --tail 30
```

### Causas e Soluções

| Causa | Log mostra | Solução |
|-------|-----------|---------|
| Senha errada no .env | `FATAL: password authentication failed` | Verifique `POSTGRES_PASSWORD` no `.env` |
| Banco corrompido | `could not open file` | Restaure backup: `gunzip < data/backups/postgres/ULTIMO.sql.gz \| docker compose exec -T postgres psql -U bluebot bluebot` |
| Disco cheio | `No space left on device` | `docker system prune -f` (sem `--volumes`!) |
| Porta em uso | `Address already in use` | `docker compose down` e tente novamente |

---

## API Não Responde (502 Bad Gateway)

### Sintomas
- Browser mostra "502 Bad Gateway"
- `curl https://api.bluebotapp.com.br` retorna 502

### O que significa
O Nginx está funcionando, mas não consegue conectar com a API (FastAPI). A API está parada ou com erro.

### Verificar
```bash
# 1. A API está rodando?
docker compose ps api

# 2. Ver logs da API
docker compose logs api --tail 50

# 3. Testar de dentro do nginx
docker compose exec nginx wget -qO- http://api:8000/health
```

### Causas e Soluções

| Causa | Log mostra | Solução |
|-------|-----------|---------|
| Banco indisponível | `Connection refused` no log da API | Verifique postgres: `docker compose ps postgres` |
| Erro no código Python | `ImportError`, `SyntaxError` | Verifique o log, corrija o código, rebuild: `docker compose build api && docker compose up -d api` |
| `.env` com erro | `KeyError`, `ValidationError` | Compare `.env` com `.env.example` |
| Migration falhou | `alembic.util.exc` | `docker compose exec api alembic upgrade head` |

---

## CORS Bloqueado

### Sintomas
- Console do browser mostra: `Access-Control-Allow-Origin` error
- Login funciona no Swagger mas não no painel

### Verificar
```bash
# Testar CORS
curl -I -X OPTIONS https://api.bluebotapp.com.br/auth/login/admin \
  -H "Origin: https://console.bluebotapp.com.br" \
  -H "Access-Control-Request-Method: POST"

# Verificar se há CORS duplicado (Nginx + FastAPI)
curl -sI https://api.bluebotapp.com.br/health \
  -H "Origin: https://console.bluebotapp.com.br" | grep -i "access-control"
```

### Solução
O CORS é gerenciado **apenas pelo FastAPI** (`api/app/main.py`). O Nginx **NÃO deve** adicionar headers CORS. Se vir headers duplicados, verifique:
- `nginx/conf.d/api.conf` — NÃO deve ter `include cors.conf`
- `api/app/main.py` — `allowed_origins` deve conter `https://console.bluebotapp.com.br`

---

## SSL Não Funciona (ERR_CERT_COMMON_NAME_INVALID)

### Sintomas
- Browser mostra "Sua conexão não é particular"
- Cadeado vermelho na barra de endereço

### Verificar
```bash
# Ver qual certificado está sendo servido
echo | openssl s_client -connect api.bluebotapp.com.br:443 -servername api.bluebotapp.com.br 2>/dev/null | openssl x509 -noout -subject -issuer

# Ver domínios cobertos pelo certificado
openssl x509 -in data/ssl/live/bluebotapp.com.br/fullchain.pem -text -noout | grep -A1 "Subject Alternative Name"

# Verificar paths no nginx
grep -r "ssl_certificate" nginx/snippets/ssl.conf
```

### Causas e Soluções

| Causa | Solução |
|-------|---------|
| Certificado não cobre o subdomínio | Regenerar: `bash scripts/renew-ssl.sh --new` |
| Path errado no nginx | Verificar `nginx/snippets/ssl.conf` — deve apontar para `/etc/letsencrypt/live/bluebotapp.com.br/` |
| Certificado expirou | Renovar: `bash scripts/renew-ssl.sh` |
| Volume Docker não montado | Verificar `docker compose config \| grep letsencrypt` |

---

## Nginx Não Inicia (Restart Loop)

### Verificar
```bash
docker logs bluebot_nginx --tail 20
```

### Causas Comuns

| Erro no log | Causa | Solução |
|-------------|-------|---------|
| `cannot load certificate` | Certificado não encontrado | Verifique `data/ssl/live/bluebotapp.com.br/` existe |
| `"location" directive is not allowed here` | Diretiva no lugar errado (ex: `location` fora de `server`) | Corrija o arquivo indicado no erro |
| `host not found in upstream "api"` | Container da API não está rodando | `docker compose up -d api` primeiro |
| `bind() to 0.0.0.0:443 failed` | Outra coisa usando a porta 443 | `lsof -i :443` para ver quem está usando |

---

## WhatsApp Não Funciona

### Verificar
```bash
# Ver status pelo admin
curl -H "Authorization: Bearer SEU_TOKEN" \
  https://console.bluebotapp.com.br/admin/whatsapp/status

# Ver logs do container WhatsApp
docker logs whatsapp_matheus --tail 30

# Ver logs do bot
docker logs bot_matheus --tail 30
```

### Causas Comuns

| Problema | Solução |
|----------|---------|
| QR Code não aparece | Verificar se `whatsapp_matheus` está `Up (healthy)` |
| WhatsApp desconectou | Escanear QR novamente pelo painel |
| `Could not find browser revision` | Rebuild: `docker compose -f clientes/matheus/docker-compose.yml build` |
| Sem permissão no Chrome | Verificar `shm_size: "256m"` no docker-compose do cliente |

---

## Login Admin Falha (401)

### Verificar
```bash
# Testar direto na API
curl -X POST https://api.bluebotapp.com.br/auth/login/admin \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "SUA_SENHA"}'

# Verificar variáveis no .env
grep -E "ADMIN_(USERNAME|PASSWORD)" .env
```

### Causas

| Causa | Solução |
|-------|---------|
| Espaços extras na senha do `.env` | Remover espaços: `ADMIN_PASSWORD=senha` (sem espaços ao redor do `=`) |
| Senha com caracteres especiais | Colocar entre aspas: `ADMIN_PASSWORD="senh@!123"` |
| Rate limit (muitas tentativas) | Aguardar 1 minuto (limite: 5/minuto) |

---

## Comandos de Diagnóstico Rápido

```bash
# Status geral
docker compose ps

# Logs de todos os serviços
docker compose logs --tail 20

# Testar conectividade entre containers
docker compose exec api curl -s http://postgres:5432 2>&1 | head -1
docker compose exec nginx wget -qO- http://api:8000/health

# Uso de recursos
docker stats --no-stream

# Health check completo
bash scripts/health-check.sh
```
