# 🔨 Manutenção Rotineira

## Backup Automático do PostgreSQL

O script `scripts/backup-postgres.sh` faz backup diário do banco.

### Configurar (uma vez)

```bash
# Adicionar ao crontab (agenda de tarefas do Linux)
crontab -e

# Adicionar esta linha (backup todo dia às 3h da manhã):
0 3 * * * /opt/bluebot/scripts/backup-postgres.sh
```

### Rodar manualmente

```bash
bash scripts/backup-postgres.sh
# Saída: Backup salvo em data/backups/postgres/bluebot_20260512_030000.sql.gz (1.2M)
```

### Restaurar um backup

```bash
# Listar backups disponíveis
ls -lh data/backups/postgres/

# Restaurar (CUIDADO: sobrescreve o banco atual!)
gunzip < data/backups/postgres/bluebot_20260512_030000.sql.gz | \
  docker compose exec -T postgres psql -U bluebot bluebot
```

> ⚠️ Sempre faça backup ANTES de qualquer atualização ou mudança!

---

## Renovação de SSL

O Certbot renova automaticamente via container. Para forçar:

```bash
# Renovar certificados existentes
bash scripts/renew-ssl.sh

# Gerar novos certificados (para domínio)
bash scripts/renew-ssl.sh --new
```

### Configurar renovação automática

```bash
crontab -e

# Toda segunda-feira às 4h:
0 4 * * 1 /opt/bluebot/scripts/renew-ssl.sh
```

### Verificar quando expira

```bash
openssl x509 -in data/ssl/live/bluebotapp.com.br/fullchain.pem -noout -dates
# notAfter=Aug  6 00:00:00 2026 GMT
```

---

## Monitoramento

### Health Check

```bash
bash scripts/health-check.sh
```

Verifica automaticamente:
- ✅ Containers rodando e saudáveis
- ✅ HTTPS respondendo em todos os domínios
- ✅ Certificado SSL válido (e quantos dias restam)
- ✅ Uso de disco
- ✅ Containers de clientes

### Limpeza de Logs

```bash
# Ver tamanho dos logs Docker
docker system df

# Limpar logs de containers (mantém os últimos 100MB)
truncate -s 100M /var/lib/docker/containers/*/*-json.log 2>/dev/null
```

### Atualizar Imagens Docker

```bash
cd /opt/bluebot

# Atualizar imagens base (nginx, postgres, certbot)
docker compose pull

# Rebuild da API (após mudanças no código)
docker compose build api

# Aplicar tudo
docker compose up -d
```

---

## Crontab Recomendado Completo

```bash
crontab -e
```

```cron
# Backup do PostgreSQL - todo dia às 3h
0 3 * * * /opt/bluebot/scripts/backup-postgres.sh

# Renovar SSL - toda segunda às 4h
0 4 * * 1 /opt/bluebot/scripts/renew-ssl.sh

# Health check silencioso - a cada 5 minutos (loga erros)
*/5 * * * * /opt/bluebot/scripts/health-check.sh --quiet 2>> /opt/bluebot/logs/health.log
```
